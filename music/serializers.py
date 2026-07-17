"""
Serializers for the Classical Guitar Music Database API.
"""

from rest_framework import serializers
from .eras import era_label, sort_era_slugs
from .models import (
    Country, InstrumentationCategory, DataSource,
    Composer, ComposerAlias, Work, Tag, WorkTag, WorkLink, UserSuggestion
)
from .publishers import cta_for, resolve_link


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


def _era_labels(composer):
    """Chronologically ordered era labels for a composer.

    Reads `composer.eras.all()` so a prefetch is used when the caller set one up —
    the composer list would otherwise fire a query per row. Sorting happens in Python
    for the same reason: an .order_by() here would defeat the prefetch.
    """
    return [
        era_label(slug)
        for slug in sort_era_slugs(era.era for era in composer.eras.all())
    ]


class ComposerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for composer lists"""
    country_name = serializers.CharField(source='country.name', read_only=True)
    work_count = serializers.IntegerField(read_only=True)  # Use annotated field
    eras = serializers.SerializerMethodField()

    class Meta:
        model = Composer
        fields = [
            'id', 'full_name', 'birth_year', 'death_year',
            'is_living', 'country_name', 'period', 'work_count', 'eras'
        ]

    def get_eras(self, obj):
        # Flat array of display strings, as WorkListSerializer does for tags.
        return _era_labels(obj)


class ComposerDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual composer view"""
    country = CountrySerializer(read_only=True)
    data_source = DataSourceSerializer(read_only=True)
    aliases = ComposerAliasSerializer(many=True, read_only=True)
    work_count = serializers.IntegerField(read_only=True)  # Use annotated field
    eras = serializers.SerializerMethodField()

    class Meta:
        model = Composer
        fields = [
            'id', 'full_name', 'first_name', 'last_name',
            'birth_year', 'death_year', 'is_living',
            'country', 'country_description', 'biography', 'period', 'eras',
            'imslp_url', 'wikipedia_url',
            'data_source', 'is_verified', 'work_count', 'aliases',
            'created_at', 'updated_at'
        ]

    def get_eras(self, obj):
        return _era_labels(obj)


class WorkListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for work lists - optimized for speed"""
    composer = serializers.SerializerMethodField()
    instrumentation_category = serializers.SerializerMethodField()
    
    class Meta:
        model = Work
        fields = [
            'id', 'title', 'composer', 'catalog_number',
            'composition_year', 'instrumentation_category', 'instrumentation_detail',
            'duration_minutes', 'difficulty_level',
            # The list renders an "Arrangement" badge from this. It is what makes an
            # arrangement row legible: the title is the *original* work's title, so
            # without the badge "Violin Partita No.2" just looks misfiled in a guitar
            # catalog.
            'is_arrangement',
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
    alternate_instrumentations = serializers.SerializerMethodField()
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
            'alternate_instrumentations',
            'is_arrangement',
            'difficulty_level', 'description', 'movements',
            'imslp_url', 'sheerpluck_url', 'youtube_url', 'score_url',
            'links',
            'data_source', 'is_verified', 'view_count',
            'tags', 'created_at', 'updated_at'
        ]

    def get_alternate_instrumentations(self, obj):
        """Other ways this work can be played. Detail view only — the Works table's
        instrumentation column means the *primary*, which is what it sorts by."""
        return [
            {'id': alt.category_id, 'name': alt.category.name, 'note': alt.note}
            for alt in obj.alternate_instrumentations.select_related('category')
        ]

    def get_tags(self, obj):
        work_tags = obj.work_tags.select_related('tag')
        return [wt.tag.name for wt in work_tags]

    @staticmethod
    def _link_entry(url, default_type, default_label, link_id, sort_order):
        """One link, with its CTA derived from the host rather than from stored text."""
        resolved = resolve_link(url)
        if resolved:
            link_type, source = resolved
        else:
            # Unrecognised host. Keep rendering it — this is pre-existing data a human
            # entered, and silently hiding their link is worse than showing it — but
            # claim no source, and fall back to the stored label.
            link_type, source = default_type, None
        return {
            'id': link_id,
            'label': cta_for(link_type, default_label),
            'url': url,
            'link_type': link_type,
            'source': source,
            'sort_order': sort_order,
        }

    def get_links(self, obj):
        """Unified list merging the fixed legacy URL columns and bespoke WorkLink rows.

        The label is *derived from the host* (music/publishers), never authored, which is
        what stops a hundred bespoke names accumulating. Consequence worth knowing: a work
        carrying both an IMSLP and a Mutopia score renders two buttons both reading
        "View Score" — `source` is what tells them apart, so the UI must show it.
        """
        merged = []
        legacy = [
            (obj.imslp_url, 'imslp', 'View on IMSLP'),
            (obj.sheerpluck_url, 'sheerpluck', 'View on SheerPluck'),
            (obj.youtube_url, 'youtube', 'Watch on YouTube'),
            (obj.score_url, 'score', 'View Score'),
        ]
        for url, default_type, default_label in legacy:
            if url:
                merged.append(self._link_entry(url, default_type, default_label,
                                               link_id=None, sort_order=-1))
        for wl in obj.links.all():
            merged.append(self._link_entry(wl.url, wl.link_type, wl.label,
                                           link_id=wl.id, sort_order=wl.sort_order))
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
