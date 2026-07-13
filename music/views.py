"""
API views for the Classical Guitar Music Database.
"""

from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Value
from django.db.models.functions import Length, Replace, Lower
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.postgres.search import TrigramSimilarity
from .models import (
    Country, InstrumentationCategory, DataSource,
    Composer, Work, Tag, UserSuggestion
)
from .serializers import (
    CountrySerializer, InstrumentationCategorySerializer,
    DataSourceSerializer, ComposerListSerializer, ComposerDetailSerializer,
    WorkListSerializer, WorkDetailSerializer, TagSerializer,
    WorkSearchSerializer, UserSuggestionSerializer, ComposerWorkSerializer
)
from .permissions import IsAdminOrReadOnly, IsHardcodedAdmin


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

        q_objects = Q()
        for search_field in search_fields:
            field = search_field.lstrip('^=@')
            annotation_name = f'{field.replace("__", "_")}_similarity'
            # Annotate similarity for RANKING only (computed on the filtered subset).
            queryset = queryset.annotate(
                **{annotation_name: TrigramSimilarity(field, search_param)}
            )
            # FILTER with the `%` operator (trigram_similar lookup) so the GIN trigram
            # indexes are used. Using `similarity() > 0.3` here instead forces a full
            # sequential scan. The `%` operator matches when similarity >=
            # pg_trgm.similarity_threshold (default 0.3, our intended value).
            if '__' in field:
                # A related-model field (e.g. works.composer__full_name). Matching it
                # directly puts the `%` on the *joined* table, so the OR spans the join
                # and can't use a single-table index. Resolving it to an inline subquery
                # doesn't help either — a SubPlan inside an OR blocks bitmap index scans,
                # forcing a seq scan of this table. So resolve the related rows to a
                # literal id list FIRST (cheap, index-backed on the related table); a
                # literal `IN (...)` list CAN be bitmap-OR'd with the trigram indexes.
                relation, subfield = field.split('__', 1)
                related_model = queryset.model._meta.get_field(relation).related_model
                related_ids = list(
                    related_model.objects.filter(
                        **{f'{subfield}__trigram_similar': search_param}
                    ).values_list('pk', flat=True)[:2000]
                )
                if related_ids:
                    q_objects |= Q(**{f'{relation}__in': related_ids})
            else:
                q_objects |= Q(**{f'{field}__trigram_similar': search_param})
        
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
        
        # Return curated, ordered categories
        from .utils import get_instrumentation_variations
        
        # Define display order
        ordered_categories = [
            'Solo',
            'Duo', 
            'Trio',
            'Quartet',
            'Quintet',
            'Sextet',
            'Septet',
            'Octet',
            'Guitar and Orchestra',
            'Guitar Orchestra',
            'Guitar and Voice',
            'Guitar and Flute',
            'Guitar and Violin',
            'Guitar and Viola',
            'Guitar and Cello',
            'Guitar and Piano',
            'Guitar and Strings',
            'Guitar and Clarinet',
            'Guitar and Saxophone',
            'Guitar and Harp',
            'Guitar and Percussion',
            'Guitar and Marimba',
            'Guitar and Mandolin',
            'Guitar and Trumpet',
            'Guitar and Oboe',
            'Guitar and Recorder',
            'Guitar and Gamelan',
            'Electric Guitar',
            'Bass Guitar',
            '12-String Guitar',
            'Chamber Music',
            'Guitar with Electronics',
            'Ensemble',
            'Mixed Ensemble',
        ]
        
        # Get variations to check which categories actually exist in database
        instrumentation_variations = get_instrumentation_variations()
        
        # Build result with only categories that have works
        results = []
        for category in ordered_categories:
            if category in instrumentation_variations:
                # Check if any variation exists in database
                variations = instrumentation_variations[category]
                query = Q()
                for variation in variations:
                    query |= Q(name__icontains=variation)  # Changed from iexact to icontains
                
                if InstrumentationCategory.objects.filter(query).exists():
                    # Find the first matching DB entry to get the ID
                    db_entry = InstrumentationCategory.objects.filter(query).first()
                    results.append({
                        'id': db_entry.id,
                        'name': category,
                        'sort_order': db_entry.sort_order if hasattr(db_entry, 'sort_order') else 0
                    })
        
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
    queryset = Composer.objects.select_related('country', 'data_source').annotate(
        work_count=Count('works', filter=Q(works__is_public=True))
    )
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, TrigramSearchFilter, filters.OrderingFilter]
    search_fields = ['full_name', 'last_name', 'first_name', 'name_normalized']
    ordering_fields = [
        'last_name', 
        'first_name', 
        'birth_year', 
        'death_year',
        'country__name',
        'work_count'
    ]
    # Default ordering only when not searching - similarity search has its own ordering
    def get_ordering(self):
        """Override ordering to let search results use similarity ranking"""
        search_param = self.request.query_params.get('search', '')
        if search_param:
            return None  # Let TrigramSearchFilter handle ordering
        return ['last_name', 'first_name']  # Default alphabetical ordering
    filterset_fields = ['period', 'country', 'is_living', 'is_verified']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by instrumentation (composers who have works with this instrumentation)
        # Handles variations like "solo" matching "Solo Guitar", "Guitar Solo", etc.
        instrumentation = self.request.query_params.get('instrumentation')
        if instrumentation:
            from .utils import get_instrumentation_variations
            
            # Map common instrumentation names to their variations
            search_terms = [instrumentation]
            instrumentation_variations = get_instrumentation_variations()
            
            # Add variations if available
            if instrumentation in instrumentation_variations:
                search_terms.extend(instrumentation_variations[instrumentation])
            
            # Build query with all variations
            query = Q()
            for term in search_terms:
                query |= Q(instrumentation_category__name__icontains=term)
            
            # Use exists subquery to avoid duplicates and distinct() issues
            from django.db.models import Exists, OuterRef
            matching_works = Work.objects.filter(
                composer=OuterRef('pk'),
                is_public=True
            ).filter(query)
            queryset = queryset.filter(Exists(matching_works))
        
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
        
        # Force ordering after all filters, but only when not searching
        # When searching, let TrigramSearchFilter handle similarity-based ordering
        search_param = self.request.query_params.get('search', '')
        if not search_param:
            ordering = self.request.query_params.get('ordering', 'last_name,first_name')
            order_fields = [f.strip() for f in ordering.split(',')]
            return queryset.order_by(*order_fields)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ComposerDetailSerializer
        return ComposerListSerializer
    
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
    filter_backends = [DjangoFilterBackend, TrigramSearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'title_normalized', 'composer__full_name', 'opus_number']
    ordering_fields = [
        'title', 
        'title_sort_key', 
        'composition_year', 
        'difficulty_level', 
        'view_count',
        'composer__full_name',
        'instrumentation_category__name'
    ]
    filterset_fields = [
        'composer', 'instrumentation_category', 
        'difficulty_level', 'is_verified'
    ]
    
    def get_ordering(self):
        """Override ordering to let search results use similarity ranking"""
        search_param = self.request.query_params.get('search', '')
        if search_param:
            return None  # Let TrigramSearchFilter handle ordering
        return ['title_sort_key']  # Default alphabetical ordering
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkDetailSerializer
        return WorkListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Add prefetch for detail views only (tags + bespoke links needed there)
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related('work_tags__tag', 'links').select_related('data_source')
        
        # Get the requested ordering parameter, but only apply when not searching
        search_param = self.request.query_params.get('search', '')
        ordering_param = self.request.query_params.get('ordering', 'title')
        
        # If sorting by title (default or explicit) and not searching, use title_normalized for better performance
        if not search_param and (ordering_param == 'title' or ordering_param == '-title'):
            # Use title_normalized which has leading symbols stripped and is indexed
            queryset = queryset.order_by('title_normalized' if ordering_param == 'title' else '-title_normalized')
        
        # Filter by instrumentation (using instrumentation name)
        # Handles variations like "solo" matching "Solo Guitar", "Guitar Solo", etc.
        instrumentation = self.request.query_params.get('instrumentation')
        if instrumentation:
            from .utils import get_instrumentation_variations
            
            # Map common instrumentation names to their variations
            search_terms = [instrumentation]
            instrumentation_variations = get_instrumentation_variations()
            
            # Add variations if available
            if instrumentation in instrumentation_variations:
                search_terms.extend(instrumentation_variations[instrumentation])
            
            # Build query with all variations
            query = Q()
            for term in search_terms:
                query |= Q(instrumentation_category__name__icontains=term)
            
            queryset = queryset.filter(query)
        
        # Filter by composer country
        composer_country = self.request.query_params.get('composer_country')
        if composer_country:
            queryset = queryset.filter(
                composer__country__name=composer_country
            )
        
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
        """Count works by instrumentation category"""
        return dict(
            Work.objects.filter(is_public=True)
            .values('instrumentation_category__name')
            .annotate(count=Count('id'))
            .values_list('instrumentation_category__name', 'count')
        )


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
        return [IsHardcodedAdmin()]
    
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
    
    @action(detail=True, methods=['post'], permission_classes=[IsHardcodedAdmin])
    def approve(self, request, pk=None):
        """Approve a suggestion"""
        from django.utils import timezone
        
        suggestion = self.get_object()
        suggestion.status = 'approved'
        suggestion.reviewed_at = timezone.now()
        suggestion.save()
        
        serializer = self.get_serializer(suggestion)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsHardcodedAdmin])
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
    
    @action(detail=True, methods=['post'], permission_classes=[IsHardcodedAdmin])
    def mark_merged(self, request, pk=None):
        """Mark a suggestion as merged into the database"""
        from django.utils import timezone
        
        suggestion = self.get_object()
        suggestion.status = 'merged'
        suggestion.reviewed_at = timezone.now()
        suggestion.save()
        
        serializer = self.get_serializer(suggestion)
        return Response(serializer.data)
