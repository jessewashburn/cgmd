"""
API views for the Classical Guitar Music Database.
"""

from collections import Counter

from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Value, F, Exists, OuterRef
from django.db.models.functions import Length, Replace, Lower
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.postgres.search import TrigramSimilarity
from .models import (
    Country, InstrumentationCategory, DataSource,
    Composer, ComposerEra, Work, Tag, UserSuggestion
)
from .serializers import (
    CountrySerializer, InstrumentationCategorySerializer,
    DataSourceSerializer, ComposerListSerializer, ComposerDetailSerializer,
    WorkListSerializer, WorkDetailSerializer, TagSerializer,
    WorkSearchSerializer, UserSuggestionSerializer, ComposerWorkSerializer
)
from .permissions import IsAdminOrReadOnly, IsCognitoAdmin


# Match the query against the best-matching *word* of a field rather than the whole
# string, and at 0.5 rather than word_similarity's 0.6 default.
#
# Why: a search is usually one name ("Taregas"), but the fields it's compared against
# are whole names ("francisco tarrega"). Whole-string similarity() is diluted by the
# rest of the field — "Taregas" scores only 0.24 there, under the 0.3 threshold the
# `%` operator uses, so typo tolerance silently never fired (the case this filter is
# named for returned nothing). word_similarity() scores the query against the closest
# single word instead: 0.50 for the same pair, while every unrelated composer stays
# at 0.00 — a wide margin, so this buys typo tolerance without inviting false hits.
#
# `<%`/`%>` are still GIN-index-backed (gin_trgm_ops), so this keeps the index scan
# that the `%` operator was chosen for.
WORD_SIMILARITY_THRESHOLD = 0.5


class TrigramSearchFilter(filters.SearchFilter):
    """
    PostgreSQL trigram fuzzy search with fallback to standard search.
    - PostgreSQL: Fuzzy matching (handles typos like "Taregas" -> "Tárrega")
    - SQLite/MySQL: Standard ILIKE search (exact substring matching)
    """
    def filter_queryset(self, request, queryset, view):
        from django.db import connection
        
        search_param = request.query_params.get(self.search_param, '')
        if not search_param:
            return queryset
        
        # Fall back to standard search on non-PostgreSQL databases
        if connection.vendor != 'postgresql':
            # For non-PostgreSQL, still try to order by relevance using basic matching
            queryset = super().filter_queryset(request, queryset, view)
            # Try to order by exact matches first, then partial matches
            if hasattr(view, 'search_fields') and view.search_fields:
                # Create case for exact matches to rank higher
                from django.db.models import Case, When, IntegerField
                exact_match_conditions = []
                partial_match_conditions = []
                
                for field in view.search_fields:
                    clean_field = field.lstrip('^=@')
                    exact_match_conditions.append(When(**{f"{clean_field}__iexact": search_param}, then=10))
                    partial_match_conditions.append(When(**{f"{clean_field}__icontains": search_param}, then=5))
                
                relevance_score = Case(
                    *exact_match_conditions,
                    *partial_match_conditions,
                    default=1,
                    output_field=IntegerField()
                )
                queryset = queryset.annotate(relevance=relevance_score).order_by('-relevance')
            return queryset
        
        # PostgreSQL trigram similarity search
        search_fields = getattr(view, 'search_fields', [])

        if not search_fields:
            return queryset

        # `<%`/`%>` read their cutoff from a session GUC, so it has to be set on the
        # connection before the query runs. set_config() (not SET) because SET can't
        # take a bound parameter. Connections are reused (DB_CONN_MAX_AGE), which is
        # harmless: nothing else in the app uses the word-similarity operators.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('pg_trgm.word_similarity_threshold', %s, false)",
                [str(WORD_SIMILARITY_THRESHOLD)],
            )

        q_objects = Q()
        for search_field in search_fields:
            field = search_field.lstrip('^=@')
            annotation_name = f'{field.replace("__", "_")}_similarity'
            # Annotate similarity for RANKING only (computed on the filtered subset).
            queryset = queryset.annotate(
                **{annotation_name: TrigramSimilarity(field, search_param)}
            )
            # FILTER with the `%>` operator (trigram_word_similar lookup) so the GIN
            # trigram indexes are used. Annotating word_similarity() and comparing it
            # here instead would force a full sequential scan. `%>` matches when
            # word_similarity(query, field) >= WORD_SIMILARITY_THRESHOLD, set above.
            if '__' in field:
                # A related-model field (e.g. works.composer__full_name). Matching it
                # directly puts the operator on the *joined* table, so the OR spans the join
                # and can't use a single-table index. Resolving it to an inline subquery
                # doesn't help either — a SubPlan inside an OR blocks bitmap index scans,
                # forcing a seq scan of this table. So resolve the related rows to a
                # literal id list FIRST (cheap, index-backed on the related table); a
                # literal `IN (...)` list CAN be bitmap-OR'd with the trigram indexes.
                relation, subfield = field.split('__', 1)
                related_model = queryset.model._meta.get_field(relation).related_model
                related_ids = list(
                    related_model.objects.filter(
                        **{f'{subfield}__trigram_word_similar': search_param}
                    ).values_list('pk', flat=True)[:2000]
                )
                if related_ids:
                    q_objects |= Q(**{f'{relation}__in': related_ids})
            else:
                q_objects |= Q(**{f'{field}__trigram_word_similar': search_param})
        
        if q_objects:
            similarity_fields = [
                f'{field.lstrip("^=@").replace("__", "_")}_similarity' 
                for field in search_fields
            ]
            queryset = queryset.filter(q_objects)
            if similarity_fields:
                # Weight primary field more heavily for better relevance ranking
                # For composers: full_name (contains both first and last name)
                # For works: title (the main identifier)
                from django.db.models import F, FloatField
                from django.db.models.functions import Greatest, Coalesce
                
                # Determine which field to weight (full_name for composers, title for works)
                primary_field = None
                if 'full_name_similarity' in similarity_fields:
                    primary_field = 'full_name_similarity'
                elif 'title_similarity' in similarity_fields:
                    primary_field = 'title_similarity'
                
                if primary_field:
                    # Calculate weighted score: primary field gets 2x weight, others get 1x
                    # This ensures exact/close matches to the primary field rank highest
                    other_fields = [f for f in similarity_fields if f != primary_field]
                    
                    if other_fields:
                        # Weighted: (primary * 2.0 + max(other fields)) / 2.0
                        max_other_similarity = Greatest(*other_fields)
                        weighted_score = (
                            F(primary_field) * 2.0 + Coalesce(max_other_similarity, 0.0)
                        ) / 2.0
                    else:
                        weighted_score = F(primary_field)
                else:
                    # Fallback if no primary field identified
                    weighted_score = Greatest(*similarity_fields)
                
                queryset = queryset.annotate(
                    relevance_score=weighted_score
                )
                queryset = queryset.order_by('-relevance_score')
        
        return queryset


class NullsLastOrderingFilter(filters.OrderingFilter):
    """OrderingFilter with two shared refinements for the list endpoints:

    1. NULLs always sort last, in both directions (Postgres otherwise puts them
       first on DESC), so a birth_year/country/etc. sort never leads with blanks.
    2. The *default* ordering (the view's `ordering` attribute) is skipped while a
       `search` term is active, so the trigram relevance ranking applied upstream by
       TrigramSearchFilter survives. An explicit `?ordering=` always wins — that is
       the "search-relevance vs. manual-sort" rule the frontend relies on.
    """

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset
        has_explicit_param = bool(request.query_params.get(self.ordering_param))
        if not has_explicit_param and request.query_params.get('search'):
            # Only the view default would apply here — defer to relevance ranking.
            return queryset
        return queryset.order_by(*self._nulls_last(ordering))

    @staticmethod
    def _nulls_last(ordering):
        terms = []
        for term in ordering:
            descending = term.startswith('-')
            field = term[1:] if descending else term
            expr = F(field)
            terms.append(
                expr.desc(nulls_last=True) if descending else expr.asc(nulls_last=True)
            )
        return terms


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for countries.
    Provides list and detail views for countries.
    By default, filters out descriptive entries (e.g., "American composer of X origin")
    and only returns actual country names for dropdowns.
    Use ?include_descriptions=true to get all entries.
    """
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'iso_code']
    ordering_fields = ['name']
    ordering = ['name']
    
    def get_queryset(self):
        from django.core.cache import cache
        
        queryset = super().get_queryset()
        
        # By default, exclude descriptive entries that aren't real countries
        # These are entries like "American composer of Pakistani origin"
        include_descriptions = self.request.query_params.get('include_descriptions', 'false').lower() == 'true'
        
        if not include_descriptions:
            # Filter out entries that look like descriptions, not countries
            queryset = queryset.exclude(
                Q(name__icontains='composer of') |
                Q(name__icontains='descent') |
                Q(name__icontains='origin') |
                Q(name__icontains='heritage')
            )
        
        return queryset


class InstrumentationCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for instrumentation categories.
    By default, filters out junk entries (titles, opus numbers, random text)
    and only returns actual instrumentation categories.
    Use ?include_all=true to get all entries.
    """
    queryset = InstrumentationCategory.objects.all()
    serializer_class = InstrumentationCategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    
    def list(self, request, *args, **kwargs):
        """Override list to return curated categories instead of raw database values"""
        from django.core.cache import cache
        
        include_all = request.query_params.get('include_all', 'false').lower() == 'true'
        
        if include_all:
            # Return all database values
            return super().list(request, *args, **kwargs)
        
        # Check cache first
        cache_key = 'instrumentation_categories_curated'
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return Response(cached_result)
        
        # The canonical buckets, in display order, limited to those with public works.
        # Each name is looked up exactly: this used to resolve a category's id by
        # OR'ing `name__icontains` over its variation list and taking .first(), which
        # reported whichever row matched a shared substring first — "Guitar and Voice"
        # came back carrying Bass Guitar's id, and names no category has ever held
        # ("Mixed Ensemble", "12-String Guitar") were listed as if they existed.
        from django.db.models import Count
        from .utils import CANONICAL_INSTRUMENTATION_CATEGORIES

        categories = {
            row['name']: row
            for row in InstrumentationCategory.objects
            .filter(name__in=CANONICAL_INSTRUMENTATION_CATEGORIES)
            .annotate(work_count=Count('work', filter=Q(work__is_public=True)))
            .filter(work_count__gt=0)
            .values('id', 'name', 'sort_order')
        }
        results = [
            {'id': categories[name]['id'], 'name': name,
             'sort_order': categories[name]['sort_order']}
            for name in CANONICAL_INSTRUMENTATION_CATEGORIES
            if name in categories
        ]

        # Cache for 1 hour
        cache.set(cache_key, results, 3600)
        return Response(results)
    
    def get_queryset(self):
        # For retrieve operations, return normal queryset
        return super().get_queryset()


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for data sources.
    """
    queryset = DataSource.objects.filter(is_active=True)
    serializer_class = DataSourceSerializer
    ordering = ['name']


class ComposerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for composers.
    
    list: Get all composers (lightweight)
    retrieve: Get detailed composer information
    create: Create new composer (admin only)
    update: Update composer (admin only)
    destroy: Delete composer (admin only)
    search: Full-text search composers (uses PostgreSQL trigram similarity for fuzzy matching)
    by_period: Filter composers by period
    by_country: Filter composers by country
    """
    # prefetch_related('eras'): both composer serializers render era labels, which
    # would otherwise cost one query per row on a 50-row page.
    queryset = Composer.objects.select_related('country', 'data_source').prefetch_related(
        'eras'
    ).annotate(
        work_count=Count('works', filter=Q(works__is_public=True))
    )
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, TrigramSearchFilter, NullsLastOrderingFilter]
    search_fields = ['full_name', 'last_name', 'first_name', 'name_normalized']
    ordering_fields = [
        'last_name',
        'first_name',
        'birth_year',
        'death_year',
        'country__name',
        'work_count'
    ]
    # Default browse order; skipped while searching (see NullsLastOrderingFilter).
    ordering = ['last_name', 'first_name']
    filterset_fields = ['period', 'country', 'is_living', 'is_verified']
    
    def get_queryset(self):
        return self._apply_filters(super().get_queryset())

    def _apply_filters(self, queryset, include_eras=True):
        """The hand-rolled ?instrumentation / ?birth_year_* / ?country_name / ?eras
        filters (the range and name filters django-filter's filterset_fields can't
        express).

        `include_eras=False` is for the era_facets action, which must count each era
        against every *other* filter but not against the era selection itself.
        """
        # Filter by instrumentation (composers who have works with this instrumentation).
        # Resolves to a single canonical category, as on /works — see WorkViewSet.
        instrumentation = self.request.query_params.get('instrumentation')
        if instrumentation:
            from .utils import resolve_instrumentation_filter

            category_name = resolve_instrumentation_filter(instrumentation)
            if not category_name:
                return queryset.none()

            # Use exists subquery to avoid duplicates and distinct() issues
            from .models import WorkInstrumentation

            # Primary or alternate, matching /works — a composer with a work merely
            # *playable* this way still belongs in the result.
            matching_works = Work.objects.filter(
                Q(instrumentation_category__name=category_name)
                | Q(Exists(WorkInstrumentation.objects.filter(
                    work=OuterRef('pk'), category__name=category_name))),
                composer=OuterRef('pk'),
                is_public=True,
            )
            queryset = queryset.filter(Exists(matching_works))

        if include_eras:
            queryset = self._apply_era_filter(queryset)

        # Filter by birth year range
        birth_year_min = self.request.query_params.get('birth_year_min')
        birth_year_max = self.request.query_params.get('birth_year_max')

        if birth_year_min:
            queryset = queryset.filter(birth_year__gte=birth_year_min)
        if birth_year_max:
            queryset = queryset.filter(birth_year__lte=birth_year_max)

        # Filter by country name - matches both primary country AND country_description
        # Handles variations like USA/America/American and country demonyms
        country_name = self.request.query_params.get('country_name')
        if country_name:
            # Map common country names to their variations
            search_terms = [country_name]
            
            # Comprehensive country variations mapping
            country_variations = {
                # North America
                'United States': ['USA', 'US', 'America', 'American'],
                'USA': ['United States', 'US', 'America', 'American'],
                'Canada': ['Canadian'],
                'Mexico': ['Mexican'],
                
                # Central America & Caribbean
                'Cuba': ['Cuban'],
                'Dominican Republic': ['Dominican'],
                'Guatemala': ['Guatemalan'],
                'Honduras': ['Honduran'],
                'Costa Rica': ['Costa Rican'],
                'Panama': ['Panamanian'],
                'Jamaica': ['Jamaican'],
                'Haiti': ['Haitian'],
                'Puerto Rico': ['Puerto Rican'],
                'Trinidad and Tobago': ['Trinidadian', 'Tobagonian'],
                'Barbados': ['Barbadian', 'Bajan'],
                'Bahamas': ['Bahamian'],
                'Nicaragua': ['Nicaraguan'],
                'El Salvador': ['Salvadoran'],
                'Belize': ['Belizean'],
                'Martinique': ['Martinican'],
                'Guadeloupe': ['Guadeloupean'],
                'Grenada': ['Grenadian'],
                'Saint Lucia': ['Saint Lucian'],
                'Saint Vincent': ['Vincentian'],
                'Antigua and Barbuda': ['Antiguan', 'Barbudan'],
                'Dominica': ['Dominican'],
                'Saint Kitts and Nevis': ['Kittitian', 'Nevisian'],
                'Aruba': ['Aruban'],
                'Curaçao': ['Curaçaoan'],
                'Suriname': ['Surinamese'],
                'Guyana': ['Guyanese'],
                
                # South America
                'Brazil': ['Brazilian'],
                'Argentina': ['Argentinian', 'Argentine'],
                'Chile': ['Chilean'],
                'Colombia': ['Colombian'],
                'Venezuela': ['Venezuelan'],
                'Peru': ['Peruvian'],
                'Uruguay': ['Uruguayan'],
                'Paraguay': ['Paraguayan'],
                'Bolivia': ['Bolivian'],
                'Ecuador': ['Ecuadorian', 'Ecuadorean'],
                
                # Western Europe
                'United Kingdom': ['UK', 'Britain', 'British', 'England', 'English', 'Scotland', 'Scottish', 'Wales', 'Welsh', 'Northern Ireland'],
                'UK': ['United Kingdom', 'Britain', 'British', 'England', 'English'],
                'England': ['English', 'British', 'UK'],
                'Scotland': ['Scottish', 'British', 'UK', 'Scots'],
                'Wales': ['Welsh', 'British', 'UK'],
                'Northern Ireland': ['Irish', 'British', 'UK'],
                'France': ['French'],
                'Germany': ['German'],
                'Italy': ['Italian'],
                'Spain': ['Spanish', 'Catalan', 'Catalonia', 'Basque'],
                'Portugal': ['Portuguese'],
                'Netherlands': ['Dutch', 'Holland', 'Netherlandic'],
                'Belgium': ['Belgian', 'Flemish', 'Walloon'],
                'Switzerland': ['Swiss'],
                'Austria': ['Austrian'],
                'Ireland': ['Irish'],
                'Luxembourg': ['Luxembourgish', 'Luxembourger'],
                'Monaco': ['Monégasque', 'Monacan'],
                'Andorra': ['Andorran'],
                'Liechtenstein': ['Liechtensteiner'],
                'San Marino': ['Sammarinese'],
                'Vatican': ['Vatican'],
                
                # Northern Europe
                'Sweden': ['Swedish'],
                'Norway': ['Norwegian'],
                'Denmark': ['Danish'],
                'Finland': ['Finnish'],
                'Iceland': ['Icelandic'],
                'Faroe Islands': ['Faroese'],
                'Greenland': ['Greenlandic'],
                
                # Eastern Europe
                'Poland': ['Polish'],
                'Russia': ['Russian', 'USSR', 'Soviet'],
                'Ukraine': ['Ukrainian'],
                'Czech Republic': ['Czech', 'Czechoslovakia', 'Czechoslovakian'],
                'Hungary': ['Hungarian', 'Magyar'],
                'Romania': ['Romanian'],
                'Bulgaria': ['Bulgarian'],
                'Serbia': ['Serbian'],
                'Croatia': ['Croatian'],
                'Slovenia': ['Slovenian'],
                'Slovakia': ['Slovak', 'Slovakian'],
                'Bosnia': ['Bosnian', 'Bosnia and Herzegovina'],
                'Lithuania': ['Lithuanian'],
                'Latvia': ['Latvian'],
                'Estonia': ['Estonian'],
                'Belarus': ['Belarusian'],
                'Moldova': ['Moldovan'],
                'Albania': ['Albanian'],
                'Macedonia': ['Macedonian'],
                'Montenegro': ['Montenegrin'],
                'Kosovo': ['Kosovar'],
                
                # Southern Europe
                'Greece': ['Greek', 'Hellenic'],
                'Turkey': ['Turkish'],
                'Cyprus': ['Cypriot'],
                'Malta': ['Maltese'],
                
                # Middle East
                'Israel': ['Israeli'],
                'Iran': ['Iranian', 'Persia', 'Persian'],
                'Iraq': ['Iraqi'],
                'Lebanon': ['Lebanese'],
                'Syria': ['Syrian'],
                'Jordan': ['Jordanian'],
                'Saudi Arabia': ['Saudi'],
                'Egypt': ['Egyptian'],
                'Yemen': ['Yemeni'],
                'Kuwait': ['Kuwaiti'],
                'Qatar': ['Qatari'],
                'Bahrain': ['Bahraini'],
                'Oman': ['Omani'],
                'United Arab Emirates': ['UAE', 'Emirati'],
                
                # Asia
                'China': ['Chinese', 'PRC'],
                'Japan': ['Japanese'],
                'Korea': ['Korean'],
                'South Korea': ['Korean'],
                'North Korea': ['Korean'],
                'India': ['Indian'],
                'Pakistan': ['Pakistani'],
                'Bangladesh': ['Bangladeshi'],
                'Vietnam': ['Vietnamese'],
                'Thailand': ['Thai'],
                'Indonesia': ['Indonesian'],
                'Philippines': ['Philippine', 'Filipino'],
                'Malaysia': ['Malaysian'],
                'Singapore': ['Singaporean'],
                'Taiwan': ['Taiwanese'],
                'Hong Kong': ['Cantonese'],
                'Mongolia': ['Mongolian'],
                'Nepal': ['Nepalese', 'Nepali'],
                'Sri Lanka': ['Sri Lankan'],
                'Myanmar': ['Burmese', 'Burma'],
                'Cambodia': ['Cambodian'],
                'Laos': ['Laotian'],
                'Afghanistan': ['Afghan'],
                'Kazakhstan': ['Kazakh', 'Kasachstan'],
                'Uzbekistan': ['Uzbek'],
                'Armenia': ['Armenian'],
                'Georgia': ['Georgian'],
                'Azerbaijan': ['Azerbaijani'],
                
                # Africa
                'South Africa': ['South African'],
                'Nigeria': ['Nigerian'],
                'Kenya': ['Kenyan'],
                'Ethiopia': ['Ethiopian'],
                'Ghana': ['Ghanaian'],
                'Morocco': ['Moroccan'],
                'Algeria': ['Algerian'],
                'Tunisia': ['Tunisian'],
                'Libya': ['Libyan'],
                'Senegal': ['Senegalese'],
                'Tanzania': ['Tanzanian'],
                'Uganda': ['Ugandan'],
                'Angola': ['Angolan'],
                'Mozambique': ['Mozambican'],
                'Zimbabwe': ['Zimbabwean'],
                'Cameroon': ['Cameroonian'],
                'Madagascar': ['Malagasy'],
                
                # Oceania
                'Australia': ['Australian'],
                'New Zealand': ['New Zealander', 'Kiwi'],
            }
            
            # Add variations if available
            if country_name in country_variations:
                search_terms.extend(country_variations[country_name])
            
            # Build query variations
            query = Q()
            for term in search_terms:
                query |= Q(country__name__icontains=term)
                query |= Q(country_description__icontains=term)
            
            # Use direct filter on country fields - no joins needed, so no duplicates
            queryset = queryset.filter(query)

        # Ordering (default + search-relevance handling) is owned by
        # NullsLastOrderingFilter, so no manual order_by here.
        return queryset

    def _apply_era_filter(self, queryset):
        """?eras=romantic,modern — composers tagged with ANY of the given eras.

        OR within the param, AND with every other filter: the standard facet
        contract, and the encompassing reading (Romantic + Modern = either, not both).
        """
        from .eras import parse_era_filter

        raw = self.request.query_params.get('eras')
        if not raw:
            return queryset

        slugs = parse_era_filter(raw)
        if not slugs:
            # Param present but no slug survived parsing. Per the rule in
            # resolve_instrumentation_filter — a junk filter returns nothing rather
            # than everything — this is an empty result, not an absent filter.
            return queryset.none()

        from django.db.models import Exists, OuterRef
        matching_eras = ComposerEra.objects.filter(
            composer=OuterRef('pk'), era__in=slugs
        )
        return queryset.filter(Exists(matching_eras))

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ComposerDetailSerializer
        return ComposerListSerializer

    @action(detail=False, methods=['get'])
    def era_facets(self, request):
        """Composer count per era under the currently-applied *other* filters.

        Lets the UI render "Romantic (784)" / "Baroque (0)" on the chips, so a
        conflict between the era chips and the birth-year slider — which are two
        views of one underlying axis, since era tags are derived from birth years —
        is visible before the click instead of an empty table after it.

        The era filter is deliberately excluded from its own counts: were it applied,
        selecting Romantic would drive every other chip to (0) and the facet would
        destroy itself.
        """
        from .eras import era_windows, implied_birth_range

        composers = self.filter_queryset(
            self._apply_filters(Composer.objects.all(), include_eras=False)
        )
        counts = dict(
            ComposerEra.objects
            .filter(composer_id__in=composers.values('pk'))
            .values_list('era')
            # order_by() clears any ordering inherited from the composer queryset;
            # otherwise Django folds the ordering field into the GROUP BY and the
            # counts come back per-composer instead of per-era.
            .order_by()
            .annotate(count=Count('composer_id', distinct=True))
        )

        facets = []
        for slug, label, start, end in era_windows():
            # implied_birth_* is served rather than derived client-side so the
            # creative-age/lifespan constants live in exactly one place; the UI needs
            # them to offer "widen birth years to match Baroque".
            birth_min, birth_max = implied_birth_range(slug)
            facets.append({
                'slug': slug,
                'label': label,
                'start_year': start,
                'end_year': end,
                'implied_birth_min': birth_min,
                'implied_birth_max': birth_max,
                'count': counts.get(slug, 0),
            })
        return Response(facets)

    @action(detail=False, methods=['get'])
    def by_period(self, request):
        """Get composers grouped by period"""
        period = request.query_params.get('period')
        if not period:
            return Response(
                {'error': 'Period parameter required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        composers = self.get_queryset().filter(period=period)
        serializer = self.get_serializer(composers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_country(self, request):
        """Get composers by country"""
        country_id = request.query_params.get('country_id')
        if not country_id:
            return Response(
                {'error': 'Country ID parameter required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        composers = self.get_queryset().filter(country_id=country_id)
        serializer = self.get_serializer(composers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def works(self, request, pk=None):
        """Get all works by a specific composer"""
        composer = self.get_object()
        works = Work.objects.filter(
            composer=composer,
            is_public=True
        ).select_related('instrumentation_category').order_by('title_sort_key')

        # Add pagination for better performance
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 50  # Limit to 50 works per page
        paginated_works = paginator.paginate_queryset(works, request)

        serializer = ComposerWorkSerializer(paginated_works, many=True)
        return paginator.get_paginated_response(serializer.data)


class WorkViewSet(viewsets.ModelViewSet):
    """
    API endpoint for musical works.
    
    list: Get all works (lightweight)
    retrieve: Get detailed work information
    create: Create new work (admin only)
    update: Update work (admin only)
    destroy: Delete work (admin only)
    search: Full-text search works (uses PostgreSQL trigram similarity for fuzzy matching)
    by_instrumentation: Filter by instrumentation category
    by_difficulty: Filter by difficulty level
    """
    # No .distinct(): none of the list filters join across a to-many relation
    # (instrumentation/composer_country are forward FK joins), so DISTINCT only added a
    # needless sort on the hot path.
    queryset = Work.objects.select_related(
        'composer', 'instrumentation_category'
    ).filter(is_public=True)
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, TrigramSearchFilter, NullsLastOrderingFilter]
    search_fields = ['title', 'title_normalized', 'composer__full_name', 'opus_number']
    ordering_fields = [
        'title',
        'title_sort_key',
        'composition_year',
        'difficulty_level',
        'view_count',
        # `composer__full_name` kept for back-compat with already-shared ?sort= links;
        # the UI now sorts the Composer column by last/first name to match /composers.
        'composer__full_name',
        'composer__last_name',
        'composer__first_name',
        'instrumentation_category__name'
    ]
    filterset_fields = [
        'composer', 'instrumentation_category',
        'difficulty_level', 'is_verified'
    ]
    # Default browse order: the maintained alphabetical sort key. Skipped while
    # searching (see NullsLastOrderingFilter) so relevance ranking survives.
    ordering = ['title_sort_key']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkDetailSerializer
        return WorkListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()

        # Add prefetch for detail views only (tags + bespoke links needed there)
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('work_tags__tag', 'links').select_related('data_source')

        return self._apply_filters(queryset)

    def _apply_filters(self, queryset, include_eras=True):
        """The hand-rolled range/name filters, mirroring ComposerViewSet.

        `include_eras=False` is for the era_facets action, which counts each era
        against every *other* filter but not against the era selection itself.
        """
        # Ordering (default title_sort_key + search-relevance handling) is owned by
        # NullsLastOrderingFilter, so no manual order_by here.

        # Filter by instrumentation. The term is resolved to exactly one canonical
        # category and matched on that. This previously OR'd `name__icontains` over a
        # list of loose variations, which matched *other* categories by substring —
        # Duo's 'guitar and' variation pulled in every "Guitar and X" work (23.5k rows
        # against Duo's real 4.6k).
        instrumentation = self.request.query_params.get('instrumentation')
        if instrumentation:
            from .models import WorkInstrumentation
            from .utils import resolve_instrumentation_filter

            category_name = resolve_instrumentation_filter(instrumentation)
            if not category_name:
                queryset = queryset.none()
            else:
                # Match the primary instrumentation *or* an alternate realization: a
                # work written for guitar and tape but playable by 5 guitars belongs in
                # both buckets, and someone filtering Quintet wants it.
                #
                # EXISTS rather than a join + .distinct(), following the same call in
                # ComposerViewSet ("avoid duplicates and distinct() issues"). It matters
                # more here: `ordering_fields` includes instrumentation_category__name,
                # and an ORDER BY across a multi-valued join duplicates rows and inflates
                # the paginated count. A correlated subquery adds nothing to the outer
                # query, so the sort stays honest.
                queryset = queryset.filter(
                    Q(instrumentation_category__name=category_name)
                    | Q(Exists(WorkInstrumentation.objects.filter(
                        work=OuterRef('pk'), category__name=category_name)))
                )

        # Arrangements. The UI is a single "Include arrangements" checkbox, default ON,
        # which sends *no param* when checked — so the common case costs nothing and the
        # default URL stays clean. Unchecking sends is_arrangement=false to hide them.
        #
        # A plain WHERE on an indexed boolean, deliberately: no join, so
        # `ORDER BY instrumentation_category__name` still sees one row per work and the
        # paginated count stays honest (cf. works-column-sort-ordering-fix).
        is_arrangement = self.request.query_params.get('is_arrangement')
        if is_arrangement is not None:
            wanted = is_arrangement.strip().lower()
            if wanted in ('true', '1'):
                queryset = queryset.filter(is_arrangement=True)
            elif wanted in ('false', '0'):
                queryset = queryset.filter(is_arrangement=False)
            # Anything else is ignored rather than 400'd: a junk value should degrade to
            # "no filter", not break the page.

        # Filter by composer country
        composer_country = self.request.query_params.get('composer_country')
        if composer_country:
            queryset = queryset.filter(
                composer__country__name=composer_country
            )

        if include_eras:
            queryset = self._apply_era_filter(queryset)

        # Filter by composition year range
        year_min = self.request.query_params.get('composition_year_min')
        year_max = self.request.query_params.get('composition_year_max')

        if year_min:
            queryset = queryset.filter(composition_year__gte=year_min)
        if year_max:
            queryset = queryset.filter(composition_year__lte=year_max)

        # Filter by composer birth year range
        composer_birth_min = self.request.query_params.get('composer_birth_year_min')
        composer_birth_max = self.request.query_params.get('composer_birth_year_max')

        if composer_birth_min:
            queryset = queryset.filter(composer__birth_year__gte=composer_birth_min)
        if composer_birth_max:
            queryset = queryset.filter(composer__birth_year__lte=composer_birth_max)

        # Combined year range: match on composer birth year, falling back to the work's
        # composition year when the composer has no birth year on record. This keeps the
        # composer-era semantic for the catalogue that has composer dates while still
        # surfacing works whose composer birth year is unknown (e.g. living commission
        # composers) by their composition year.
        combined_min = self.request.query_params.get('year_min')
        combined_max = self.request.query_params.get('year_max')

        if combined_min or combined_max:
            lo = int(combined_min) if combined_min else -32768
            hi = int(combined_max) if combined_max else 32767
            queryset = queryset.filter(
                Q(composer__birth_year__gte=lo, composer__birth_year__lte=hi) |
                Q(composer__birth_year__isnull=True,
                  composition_year__gte=lo, composition_year__lte=hi)
            )

        # Filter by difficulty range
        difficulty_min = self.request.query_params.get('difficulty_min')
        difficulty_max = self.request.query_params.get('difficulty_max')
        
        if difficulty_min:
            queryset = queryset.filter(difficulty_level__gte=difficulty_min)
        if difficulty_max:
            queryset = queryset.filter(difficulty_level__lte=difficulty_max)

        return queryset

    def _apply_era_filter(self, queryset):
        """?composer_eras=romantic,modern — works whose composer holds ANY of them.

        Same OR-within/AND-across contract as /composers/?eras=; named for the
        relation it crosses, matching composer_country / composer_birth_year_*.
        """
        from .eras import parse_era_filter

        raw = self.request.query_params.get('composer_eras')
        if not raw:
            return queryset

        slugs = parse_era_filter(raw)
        if not slugs:
            # Present but unparseable — no works, not every work. Same rule as an
            # unrecognised ?instrumentation= term.
            return queryset.none()

        matching_eras = ComposerEra.objects.filter(
            composer=OuterRef('composer_id'), era__in=slugs
        )
        return queryset.filter(Exists(matching_eras))

    @action(detail=False, methods=['get'])
    def era_facets(self, request):
        """**Work** count per era under the currently-applied other filters.

        Deliberately not the composer counts /composers/era_facets/ returns: above a
        table of works, "Baroque 50" would read as 50 works when it means 50
        composers. Same shape, different unit — the chips are counting whatever the
        table below them lists.

        As on /composers/, the era filter is excluded from its own counts, or picking
        one era would drive every other chip to (0).
        """
        from .eras import era_windows, implied_birth_range

        works = self.filter_queryset(
            self._apply_filters(
                Work.objects.filter(is_public=True), include_eras=False
            )
        )
        # One row per (era, work) pair for the filtered set, counted per era. Grouping
        # on the join table directly — a values('eras__era') on Work would need a
        # to-many join in the outer query, which inflates any ordering already applied.
        # Count works, grouped by their composer's era(s). A work whose composer holds
        # two eras counts under both, matching the filter's OR semantics.
        #
        # Counted off Work (pk__in against the filtered set) rather than off
        # ComposerEra: filtering and annotating across the same to-many relation makes
        # the two share a join, so a Count('composer__works') there silently depends on
        # that coupling. Counting the rows the table below actually lists is exact.
        counts = dict(
            Work.objects.filter(pk__in=works.values('pk'))
            .values_list('composer__eras__era')
            # order_by() clears the inherited ordering; otherwise Django folds the
            # ordering field into the GROUP BY and counts come back per-row.
            .order_by()
            .annotate(count=Count('pk', distinct=True))
        )

        facets = []
        for slug, label, start, end in era_windows():
            birth_min, birth_max = implied_birth_range(slug)
            facets.append({
                'slug': slug,
                'label': label,
                'start_year': start,
                'end_year': end,
                'implied_birth_min': birth_min,
                'implied_birth_max': birth_max,
                'count': counts.get(slug, 0),
            })
        return Response(facets)

    def retrieve(self, request, *args, **kwargs):
        """Increment view count when retrieving a work"""
        instance = self.get_object()
        # Increment view count
        Work.objects.filter(pk=instance.pk).update(
            view_count=instance.view_count + 1
        )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Advanced search with relevance scoring.
        Searches in title, composer name, and description.
        """
        query = request.query_params.get('q', '')
        
        if not query:
            return Response(
                {'error': 'Search query (q) parameter required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build search query
        works = self.get_queryset().filter(
            Q(title__icontains=query) |
            Q(composer__full_name__icontains=query) |
            Q(description__icontains=query) |
            Q(opus_number__icontains=query)
        ).select_related('composer', 'instrumentation_category')
        
        # Convert to search result format
        results = []
        for work in works[:50]:  # Limit to 50 results
            results.append({
                'id': work.id,
                'title': work.title,
                'composer_name': work.composer.full_name,
                'composer_id': work.composer.id,
                'composition_year': work.composition_year,
                'instrumentation': work.instrumentation_category.name if work.instrumentation_category else None,
                'difficulty_level': work.difficulty_level,
            })
        
        serializer = WorkSearchSerializer(results, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_instrumentation(self, request):
        """Get works by instrumentation category"""
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response(
                {'error': 'Category ID parameter required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        works = self.get_queryset().filter(instrumentation_category_id=category_id)
        serializer = WorkListSerializer(works, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most viewed works"""
        limit = int(request.query_params.get('limit', 20))
        works = self.get_queryset().order_by('-view_count')[:limit]
        serializer = WorkListSerializer(works, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently added works"""
        limit = int(request.query_params.get('limit', 20))
        works = self.get_queryset().order_by('-created_at')[:limit]
        serializer = WorkListSerializer(works, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def highlighted(self, request):
        """
        Get today's highlighted work — a deterministic daily pick.
        Uses the current date as a seed so every visitor sees the same work
        on the same day, but the pick changes daily.
        """
        from django.core.cache import cache
        import math

        cache_key = 'highlighted_work_today'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        today = __import__('datetime').date.today()
        seed = today.year * 10000 + today.month * 100 + today.day

        total = self.get_queryset().count()
        if total == 0:
            return Response(
                {'error': 'No works available'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Deterministic index from date seed
        rand = math.sin(seed) * 10000
        index = int((rand - math.floor(rand)) * total)

        work = self.get_queryset().prefetch_related('work_tags__tag', 'links').select_related(
            'composer__country', 'instrumentation_category', 'data_source'
        )[index]

        serializer = WorkDetailSerializer(work)
        data = serializer.data

        # Cache until midnight (max 24 h)
        import datetime
        now = datetime.datetime.now()
        seconds_until_midnight = (
            datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time.min) - now
        ).seconds
        cache.set(cache_key, data, seconds_until_midnight)

        return Response(data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for tags.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'usage_count']
    ordering = ['name']
    filterset_fields = ['category']
    
    @action(detail=True, methods=['get'])
    def works(self, request, pk=None):
        """Get all works with a specific tag"""
        tag = self.get_object()
        work_tags = tag.work_tags.select_related('work__composer', 'work__instrumentation_category')
        works = [wt.work for wt in work_tags if wt.work.is_public]
        
        serializer = WorkListSerializer(works, many=True)
        return Response(serializer.data)


class StatsViewSet(viewsets.ViewSet):
    """
    API endpoint for database statistics.
    """
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get database summary statistics (cached for 1 hour)"""
        from django.core.cache import cache

        cache_key = 'stats_summary'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        stats = {
            'total_composers': Composer.objects.count(),
            'total_works': Work.objects.filter(is_public=True).count(),
            'total_countries': Country.objects.count(),
            'composers_by_period': self._composers_by_period(),
            'works_by_instrumentation': self._works_by_instrumentation(),
            'living_composers': Composer.objects.filter(is_living=True).count(),
        }
        cache.set(cache_key, stats, 3600)
        return Response(stats)
    
    def _composers_by_period(self):
        """Count composers by period"""
        return dict(
            Composer.objects.values('period')
            .annotate(count=Count('id'))
            .values_list('period', 'count')
        )
    
    def _works_by_instrumentation(self):
        """Count works by instrumentation category, primary *and* alternate.

        The count has to follow the filter: ?instrumentation=Quintet returns works
        merely playable as a quintet, so a Quintet count that ignored alternates would
        understate its own result set.

        Consequence, and it is intended: these counts no longer sum to total_works. A
        work written for guitar and tape but playable by 5 guitars genuinely occupies
        two buckets and is counted in both. Don't "fix" that by dropping the union.
        """
        from .models import WorkInstrumentation

        counts = Counter(dict(
            Work.objects.filter(is_public=True)
            .values('instrumentation_category__name')
            .annotate(count=Count('id'))
            .values_list('instrumentation_category__name', 'count')
        ))
        counts.update(dict(
            WorkInstrumentation.objects.filter(work__is_public=True)
            # Exclude the degenerate case where an alternate duplicates the primary;
            # the backfill already refuses to write those, but a manual/suggested row
            # could, and double-counting one work in one bucket is just wrong.
            .exclude(category=F('work__instrumentation_category'))
            .values('category__name')
            .annotate(count=Count('work', distinct=True))
            .values_list('category__name', 'count')
        ))
        return dict(counts)


class UserSuggestionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user suggestions.
    
    Public users can create suggestions (POST).
    Admin can view, update, and delete suggestions.
    """
    queryset = UserSuggestion.objects.all()
    serializer_class = UserSuggestionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'suggestion_type']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        Anyone can create suggestions.
        Only admin can list, update, or delete.
        """
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [IsCognitoAdmin()]
    
    @method_decorator(csrf_exempt, name='dispatch')
    def create(self, request, *args, **kwargs):
        """Public suggestion creation — CSRF exempt since no auth required."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)
            print("Request data:", request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['post'], permission_classes=[IsCognitoAdmin])
    def approve(self, request, pk=None):
        """Approve a suggestion"""
        from django.utils import timezone
        
        suggestion = self.get_object()
        suggestion.status = 'approved'
        suggestion.reviewed_at = timezone.now()
        suggestion.save()
        
        serializer = self.get_serializer(suggestion)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsCognitoAdmin])
    def reject(self, request, pk=None):
        """Reject a suggestion"""
        from django.utils import timezone
        
        suggestion = self.get_object()
        suggestion.status = 'rejected'
        suggestion.admin_notes = request.data.get('admin_notes', '')
        suggestion.reviewed_at = timezone.now()
        suggestion.save()
        
        serializer = self.get_serializer(suggestion)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsCognitoAdmin])
    def mark_merged(self, request, pk=None):
        """Mark a suggestion as merged into the database"""
        from django.utils import timezone

        suggestion = self.get_object()
        suggestion.status = 'merged'
        suggestion.reviewed_at = timezone.now()
        suggestion.save()

        serializer = self.get_serializer(suggestion)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsCognitoAdmin])
    def apply(self, request, pk=None):
        """
        Apply a suggestion to the database (see music.suggestion_apply):
        - edit_work: write the edit-form fields + proposed links onto the work.
        - new_work / new_composer: resolve the composer with a smart compare and,
          unless the admin passes composer_id (reuse) or create_new_composer=true,
          respond 409 with the match candidates so the UI can confirm — the
          guardrail against duplicate composers.
        """
        from .suggestion_apply import apply_suggestion, NeedsConfirmation, UnsupportedSuggestion

        suggestion = self.get_object()
        try:
            result = apply_suggestion(
                suggestion,
                composer_id=request.data.get('composer_id'),
                create_new_composer=bool(request.data.get('create_new_composer')),
            )
        except NeedsConfirmation as exc:
            return Response(exc.payload, status=status.HTTP_409_CONFLICT)
        except UnsupportedSuggestion as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'applied',
            **result,
            'suggestion': self.get_serializer(suggestion).data,
        })
