"""
API views for the Classical Guitar Music Database.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from .models import (
    Country, InstrumentationCategory, DataSource,
    Composer, Work, Tag
)
from .serializers import (
    CountrySerializer, InstrumentationCategorySerializer,
    DataSourceSerializer, ComposerListSerializer, ComposerDetailSerializer,
    WorkListSerializer, WorkDetailSerializer, TagSerializer,
    WorkSearchSerializer
)


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
    """
    queryset = InstrumentationCategory.objects.all()
    serializer_class = InstrumentationCategorySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'sort_order']
    ordering = ['sort_order', 'name']


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for data sources.
    """
    queryset = DataSource.objects.filter(is_active=True)
    serializer_class = DataSourceSerializer
    ordering = ['name']


class ComposerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for composers.
    
    list: Get all composers (lightweight)
    retrieve: Get detailed composer information
    search: Full-text search composers
    by_period: Filter composers by period
    by_country: Filter composers by country
    """
    queryset = Composer.objects.select_related('country', 'data_source').all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['last_name', 'birth_year', 'death_year']
    ordering = ['last_name', 'first_name']
    filterset_fields = ['period', 'country', 'is_living', 'is_verified']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Implement fuzzy search using the normalized name field
        search_query = self.request.query_params.get('search')
        if search_query:
            # Normalize the search query
            import unicodedata
            normalized_query = unicodedata.normalize('NFKD', search_query).encode('ascii', 'ignore').decode('utf-8').lower()
            
            # Search in both regular fields and normalized field for fuzzy matching
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(name_normalized__icontains=normalized_query)
            )
        
        # Filter by instrumentation (composers who have works with this instrumentation)
        instrumentation = self.request.query_params.get('instrumentation')
        if instrumentation:
            queryset = queryset.filter(
                works__instrumentation_category__name=instrumentation
            ).distinct()
        
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
                'Kazakhstan': ['Kazakh'],
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
            
            # Build query with all variations
            query = Q()
            for term in search_terms:
                query |= Q(country__name__icontains=term)
                query |= Q(country_description__icontains=term)
            
            queryset = queryset.filter(query).distinct()
        
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
        ).select_related('instrumentation_category')
        
        serializer = WorkListSerializer(works, many=True)
        return Response(serializer.data)


class WorkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for musical works.
    
    list: Get all works (lightweight)
    retrieve: Get detailed work information
    search: Full-text search works
    by_instrumentation: Filter by instrumentation category
    by_difficulty: Filter by difficulty level
    """
    queryset = Work.objects.select_related(
        'composer', 'instrumentation_category', 'data_source'
    ).filter(is_public=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'title_normalized', 'composer__full_name', 'opus_number']
    ordering_fields = ['title', 'composition_year', 'difficulty_level', 'view_count']
    ordering = ['title']
    filterset_fields = [
        'composer', 'instrumentation_category', 
        'difficulty_level', 'is_verified'
    ]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkDetailSerializer
        return WorkListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by instrumentation (using instrumentation name)
        instrumentation = self.request.query_params.get('instrumentation')
        if instrumentation:
            queryset = queryset.filter(
                instrumentation_category__name=instrumentation
            )
        
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
        """Get database summary statistics"""
        stats = {
            'total_composers': Composer.objects.count(),
            'total_works': Work.objects.filter(is_public=True).count(),
            'total_countries': Country.objects.count(),
            'composers_by_period': self._composers_by_period(),
            'works_by_instrumentation': self._works_by_instrumentation(),
            'living_composers': Composer.objects.filter(is_living=True).count(),
        }
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
