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
    """
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'iso_code']
    ordering_fields = ['name']
    ordering = ['name']


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
        
        # Filter by composition year range
        year_min = self.request.query_params.get('year_min')
        year_max = self.request.query_params.get('year_max')
        
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
