"""
Serializers for the Classical Guitar Music Database API.
"""

from rest_framework import serializers
from .models import (
    Country, InstrumentationCategory, DataSource,
    Composer, ComposerAlias, Work, Tag, WorkTag, WorkLink, UserSuggestion
)


class CountrySerializer(serializers.ModelSerializer):
    """Serializer for Country model"""
    
    class Meta:
        model = Country
        fields = ['id', 'name', 'iso_code', 'region']


class InstrumentationCategorySerializer(serializers.ModelSerializer):
    """Serializer for InstrumentationCategory model"""
    
    class Meta:
        model = InstrumentationCategory
        fields = ['id', 'name', 'description', 'sort_order']


class DataSourceSerializer(serializers.ModelSerializer):
    """Serializer for DataSource model"""
    
    class Meta:
        model = DataSource
        fields = ['id', 'name', 'url', 'description', 'is_active']


class ComposerAliasSerializer(serializers.ModelSerializer):
    """Serializer for ComposerAlias model"""
    
    class Meta:
        model = ComposerAlias
        fields = ['id', 'alias_name', 'alias_type']


class ComposerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for composer lists"""
    country_name = serializers.CharField(source='country.name', read_only=True)
    work_count = serializers.IntegerField(read_only=True)  # Use annotated field
    
    class Meta:
        model = Composer
        fields = [
            'id', 'full_name', 'birth_year', 'death_year', 
            'is_living', 'country_name', 'period', 'work_count'
        ]


class ComposerDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual composer view"""
    country = CountrySerializer(read_only=True)
    data_source = DataSourceSerializer(read_only=True)
    aliases = ComposerAliasSerializer(many=True, read_only=True)
    work_count = serializers.IntegerField(read_only=True)  # Use annotated field
    
    class Meta:
        model = Composer
        fields = [
            'id', 'full_name', 'first_name', 'last_name',
            'birth_year', 'death_year', 'is_living',
            'country', 'country_description', 'biography', 'period',
            'imslp_url', 'wikipedia_url',
            'data_source', 'is_verified', 'work_count', 'aliases',
            'created_at', 'updated_at'
        ]


class WorkListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for work lists - optimized for speed"""
    composer = serializers.SerializerMethodField()
    instrumentation_category = serializers.SerializerMethodField()
    
    class Meta:
        model = Work
        fields = [
            'id', 'title', 'composer', 'catalog_number',
            'composition_year', 'instrumentation_category', 'instrumentation_detail',
            'duration_minutes', 'difficulty_level'
        ]
    
    def get_composer(self, obj):
        if obj.composer:
            return {
                'id': obj.composer.id,
                'full_name': obj.composer.full_name
            }
        return None
    
    def get_instrumentation_category(self, obj):
        if obj.instrumentation_category:
            return {
                'id': obj.instrumentation_category.id,
                'name': obj.instrumentation_category.name
            }
        return None


class ComposerWorkSerializer(serializers.ModelSerializer):
    """Minimal serializer for the works nested under a composer row."""
    instrumentation_category = serializers.SerializerMethodField()

    class Meta:
        model = Work
        fields = ['id', 'title', 'instrumentation_category']

    def get_instrumentation_category(self, obj):
        if obj.instrumentation_category:
            return {
                'id': obj.instrumentation_category.id,
                'name': obj.instrumentation_category.name
            }
        return None


class WorkLinkSerializer(serializers.ModelSerializer):
    """Serializer for a bespoke WorkLink row"""

    class Meta:
        model = WorkLink
        fields = ['id', 'label', 'url', 'link_type', 'sort_order']


class WorkDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual work view"""
    composer = ComposerListSerializer(read_only=True)
    instrumentation_category = InstrumentationCategorySerializer(read_only=True)
    data_source = DataSourceSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()

    class Meta:
        model = Work
        fields = [
            'id', 'title', 'subtitle', 'composer',
            'opus_number', 'catalog_number',
            'composition_year', 'composition_year_approx',
            'duration_minutes', 'key_signature',
            'instrumentation_category', 'instrumentation_detail',
            'difficulty_level', 'description', 'movements',
            'imslp_url', 'sheerpluck_url', 'youtube_url', 'score_url',
            'links',
            'data_source', 'is_verified', 'view_count',
            'tags', 'created_at', 'updated_at'
        ]

    def get_tags(self, obj):
        work_tags = obj.work_tags.select_related('tag')
        return [wt.tag.name for wt in work_tags]

    def get_links(self, obj):
        """Unified list merging the fixed legacy URL columns and bespoke WorkLink rows."""
        merged = []
        legacy = [
            (obj.imslp_url, 'View on IMSLP', 'imslp'),
            (obj.sheerpluck_url, 'View on SheerPluck', 'sheerpluck'),
            (obj.youtube_url, 'Watch on YouTube', 'youtube'),
            (obj.score_url, 'View Score', 'score'),
        ]
        for url, label, link_type in legacy:
            if url:
                merged.append({
                    'id': None, 'label': label, 'url': url,
                    'link_type': link_type, 'sort_order': -1,
                })
        for wl in obj.links.all():
            merged.append(WorkLinkSerializer(wl).data)
        return merged


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model"""
    work_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'category', 'description', 'work_count']
    
    def get_work_count(self, obj):
        return obj.work_tags.count()


class WorkSearchSerializer(serializers.Serializer):
    """Serializer for search results"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    composer_name = serializers.CharField()
    composer_id = serializers.IntegerField()
    composition_year = serializers.IntegerField(allow_null=True)
    instrumentation = serializers.CharField(allow_null=True)
    difficulty_level = serializers.IntegerField(allow_null=True)
    relevance_score = serializers.FloatField(required=False)


class UserSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for user suggestions"""
    suggestion_type_display = serializers.CharField(source='get_suggestion_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    related_composer_name = serializers.CharField(source='related_composer.full_name', read_only=True, allow_null=True)
    related_work_title = serializers.CharField(source='related_work.title', read_only=True, allow_null=True)
    
    class Meta:
        model = UserSuggestion
        fields = [
            'id', 'suggestion_type', 'suggestion_type_display', 'status', 'status_display',
            'submitter_name', 'submitter_email', 'title', 'description', 'suggested_data',
            'related_composer', 'related_composer_name', 'related_work', 'related_work_title',
            'admin_notes', 'reviewed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'reviewed_at']
