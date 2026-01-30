from django.contrib import admin
from .models import (
    Country, InstrumentationCategory, DataSource, 
    Composer, ComposerAlias, Work, Tag, WorkTag, WorkSearchIndex
)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'iso_code', 'region']
    search_fields = ['name', 'iso_code']
    list_filter = ['region']


@admin.register(InstrumentationCategory)
class InstrumentationCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order']
    search_fields = ['name']
    ordering = ['sort_order', 'name']


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'last_sync']
    list_filter = ['is_active']
    search_fields = ['name']


class ComposerAliasInline(admin.TabularInline):
    model = ComposerAlias
    extra = 1


@admin.register(Composer)
class ComposerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'birth_year', 'death_year', 'country', 'period', 'is_verified', 'needs_review']
    list_filter = ['period', 'is_living', 'is_verified', 'needs_review', 'country']
    search_fields = ['full_name', 'last_name', 'first_name', 'name_normalized']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('full_name', 'first_name', 'last_name', 'name_normalized')
        }),
        ('Dates', {
            'fields': ('birth_year', 'death_year', 'is_living')
        }),
        ('Location', {
            'fields': ('country', 'country_description')
        }),
        ('Biography', {
            'fields': ('biography', 'period')
        }),
        ('External Links', {
            'fields': ('imslp_url', 'wikipedia_url')
        }),
        ('Metadata', {
            'fields': ('data_source', 'external_id')
        }),
        ('Administration', {
            'fields': ('is_verified', 'needs_review', 'admin_notes', 'created_at', 'updated_at')
        }),
    )
    inlines = [ComposerAliasInline]


@admin.register(ComposerAlias)
class ComposerAliasAdmin(admin.ModelAdmin):
    list_display = ['alias_name', 'composer', 'alias_type']
    list_filter = ['alias_type']
    search_fields = ['alias_name', 'composer__full_name']


class WorkTagInline(admin.TabularInline):
    model = WorkTag
    extra = 1


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ['title', 'composer', 'composition_year', 'difficulty_level', 'is_public', 'is_verified', 'view_count']
    list_filter = ['is_public', 'is_verified', 'needs_review', 'instrumentation_category', 'difficulty_level']
    search_fields = ['title', 'title_normalized', 'composer__full_name', 'opus_number', 'catalog_number']
    readonly_fields = ['created_at', 'updated_at', 'view_count']
    fieldsets = (
        ('Work Information', {
            'fields': ('composer', 'title', 'title_normalized', 'subtitle', 'opus_number', 'catalog_number')
        }),
        ('Composition Details', {
            'fields': ('composition_year', 'composition_year_approx', 'duration_minutes', 'key_signature')
        }),
        ('Instrumentation', {
            'fields': ('instrumentation_category', 'instrumentation_detail', 'difficulty_level')
        }),
        ('Content', {
            'fields': ('description', 'movements')
        }),
        ('External Resources', {
            'fields': ('imslp_url', 'youtube_url', 'score_url')
        }),
        ('Metadata', {
            'fields': ('data_source', 'external_id')
        }),
        ('Administration', {
            'fields': ('is_public', 'is_verified', 'needs_review', 'view_count', 'admin_notes', 'created_at', 'updated_at')
        }),
    )
    inlines = [WorkTagInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'category', 'usage_count']
    list_filter = ['category']
    search_fields = ['name', 'slug']
    readonly_fields = ['usage_count']


@admin.register(WorkTag)
class WorkTagAdmin(admin.ModelAdmin):
    list_display = ['work', 'tag', 'created_at']
    list_filter = ['tag__category']
    search_fields = ['work__title', 'tag__name']


@admin.register(WorkSearchIndex)
class WorkSearchIndexAdmin(admin.ModelAdmin):
    list_display = ['work', 'composer_full_name', 'work_title', 'popularity_score']
    search_fields = ['composer_full_name', 'work_title', 'search_text']
    readonly_fields = ['work', 'composer_full_name', 'composer_last_name', 'composer_country',
                      'composer_birth_year', 'composer_death_year', 'work_title', 
                      'work_instrumentation', 'work_year', 'search_text', 'created_at', 'updated_at']
    
    def has_add_permission(self, request):
        return False  # Search index entries are created automatically

