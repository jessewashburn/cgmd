"""
Serializers for the Classical Guitar Music Database API.
"""

from rest_framework import serializers
from .models import (
    Country, InstrumentationCategory, DataSource,
    Composer, ComposerAlias, Work, Tag, WorkTag
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
    work_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Composer
        fields = [
            'id', 'full_name', 'birth_year', 'death_year', 
            'is_living', 'country_name', 'period', 'work_count'
        ]
    
    def get_work_count(self, obj):
        return obj.works.filter(is_public=True).count()


class ComposerDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual composer view"""
    country = CountrySerializer(read_only=True)
    data_source = DataSourceSerializer(read_only=True)
    aliases = ComposerAliasSerializer(many=True, read_only=True)
    work_count = serializers.SerializerMethodField()
    
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
    
    def get_work_count(self, obj):
        return obj.works.filter(is_public=True).count()


class WorkListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for work lists"""
    composer_name = serializers.CharField(source='composer.full_name', read_only=True)
    instrumentation_name = serializers.CharField(
        source='instrumentation_category.name', 
        read_only=True
    )
    
    class Meta:
        model = Work
        fields = [
            'id', 'title', 'composer_name', 'composition_year',
            'instrumentation_name', 'difficulty_level', 'opus_number'
        ]


class WorkDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual work view"""
    composer = ComposerListSerializer(read_only=True)
    instrumentation_category = InstrumentationCategorySerializer(read_only=True)
    data_source = DataSourceSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    
    class Meta:
        model = Work
        fields = [
            'id', 'title', 'subtitle', 'composer',
            'opus_number', 'catalog_number',
            'composition_year', 'composition_year_approx',
            'duration_minutes', 'key_signature',
            'instrumentation_category', 'instrumentation_detail',
            'difficulty_level', 'description', 'movements',
            'imslp_url', 'youtube_url', 'score_url',
            'data_source', 'is_verified', 'view_count',
            'tags', 'created_at', 'updated_at'
        ]
    
    def get_tags(self, obj):
        work_tags = obj.work_tags.select_related('tag')
        return [wt.tag.name for wt in work_tags]


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
