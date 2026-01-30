from django.db import models
from django.utils.text import slugify


class Country(models.Model):
    """Countries lookup table for composer origins"""
    name = models.CharField(max_length=100, unique=True)
    iso_code = models.CharField(max_length=2, null=True, blank=True)
    region = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'countries'
        verbose_name_plural = 'Countries'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='idx_country_name'),
            models.Index(fields=['iso_code'], name='idx_country_code'),
        ]

    def __str__(self):
        return self.name


class InstrumentationCategory(models.Model):
    """Categories for instrument groupings (Solo Guitar, Duo, Ensemble, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'instrumentation_categories'
        verbose_name_plural = 'Instrumentation Categories'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['name'], name='idx_instrumentation_name'),
        ]

    def __str__(self):
        return self.name


class DataSource(models.Model):
    """Track data sources (Sheerpluck, IMSLP, manual entry)"""
    name = models.CharField(max_length=50, unique=True)
    url = models.URLField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'data_sources'
        verbose_name_plural = 'Data Sources'
        ordering = ['name']

    def __str__(self):
        return self.name


class Composer(models.Model):
    """Composers of classical guitar music"""
    
    PERIOD_CHOICES = [
        ('Renaissance', 'Renaissance'),
        ('Baroque', 'Baroque'),
        ('Classical', 'Classical'),
        ('Romantic', 'Romantic'),
        ('Modern', 'Modern'),
        ('Contemporary', 'Contemporary'),
    ]
    
    # Basic Info
    full_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    name_normalized = models.CharField(max_length=255, help_text="Lowercase, accents removed for search")
    
    # Dates
    birth_year = models.SmallIntegerField(null=True, blank=True)
    death_year = models.SmallIntegerField(null=True, blank=True)
    is_living = models.BooleanField(default=False, null=True, blank=True)
    
    # Location
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    country_description = models.TextField(null=True, blank=True, 
                                          help_text="For complex origins like 'American composer of Brazilian origin'")
    
    # Biography
    biography = models.TextField(null=True, blank=True)
    period = models.CharField(max_length=50, choices=PERIOD_CHOICES, null=True, blank=True)
    
    # Metadata
    data_source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    external_id = models.CharField(max_length=100, null=True, blank=True,
                                   help_text="Original ID from source")
    imslp_url = models.URLField(max_length=255, null=True, blank=True)
    wikipedia_url = models.URLField(max_length=255, null=True, blank=True)
    
    # Admin
    is_verified = models.BooleanField(default=False)
    needs_review = models.BooleanField(default=False)
    admin_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'composers'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name'], name='idx_composer_last_name'),
            models.Index(fields=['full_name'], name='idx_composer_full_name'),
            models.Index(fields=['name_normalized'], name='idx_composer_normalized'),
            models.Index(fields=['country'], name='idx_composer_country'),
            models.Index(fields=['birth_year'], name='idx_composer_birth_year'),
            models.Index(fields=['death_year'], name='idx_composer_death_year'),
            models.Index(fields=['period'], name='idx_composer_period'),
            models.Index(fields=['is_living'], name='idx_composer_living'),
            models.Index(fields=['is_verified'], name='idx_composer_verified'),
        ]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        # Auto-generate normalized name if not set
        if not self.name_normalized:
            import unicodedata
            self.name_normalized = unicodedata.normalize('NFKD', self.full_name).encode('ascii', 'ignore').decode('utf-8').lower()
        super().save(*args, **kwargs)


class ComposerAlias(models.Model):
    """Composer name variants for handling different spellings"""
    
    ALIAS_TYPE_CHOICES = [
        ('birth_name', 'Birth Name'),
        ('stage_name', 'Stage Name'),
        ('alternate_spelling', 'Alternate Spelling'),
        ('pseudonym', 'Pseudonym'),
        ('translation', 'Translation'),
    ]
    
    composer = models.ForeignKey(Composer, on_delete=models.CASCADE, related_name='aliases')
    alias_name = models.CharField(max_length=255)
    alias_type = models.CharField(max_length=20, choices=ALIAS_TYPE_CHOICES, default='alternate_spelling')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'composer_aliases'
        verbose_name_plural = 'Composer Aliases'
        indexes = [
            models.Index(fields=['composer'], name='idx_alias_composer'),
            models.Index(fields=['alias_name'], name='idx_alias_name'),
        ]

    def __str__(self):
        return f"{self.alias_name} ({self.composer.full_name})"


class Work(models.Model):
    """Musical works in the classical guitar repertoire"""
    
    # Relationships
    composer = models.ForeignKey(Composer, on_delete=models.CASCADE, related_name='works')
    
    # Work Info
    title = models.CharField(max_length=500)
    title_normalized = models.CharField(max_length=500, help_text="Lowercase, accents removed for search")
    subtitle = models.TextField(null=True, blank=True)
    opus_number = models.CharField(max_length=50, null=True, blank=True)
    catalog_number = models.CharField(max_length=100, null=True, blank=True)
    
    # Composition details
    composition_year = models.SmallIntegerField(null=True, blank=True)
    composition_year_approx = models.BooleanField(default=False)
    duration_minutes = models.SmallIntegerField(null=True, blank=True)
    
    # Instrumentation
    instrumentation_category = models.ForeignKey(InstrumentationCategory, on_delete=models.SET_NULL, 
                                                 null=True, blank=True)
    instrumentation_detail = models.TextField(null=True, blank=True,
                                             help_text="Original instrumentation string from source")
    difficulty_level = models.SmallIntegerField(null=True, blank=True,
                                               help_text="1-10 scale")
    
    # Content
    description = models.TextField(null=True, blank=True)
    movements = models.TextField(null=True, blank=True,
                                help_text="JSON array or delimited list")
    key_signature = models.CharField(max_length=50, null=True, blank=True)
    
    # External Resources
    imslp_url = models.URLField(max_length=255, null=True, blank=True)
    youtube_url = models.URLField(max_length=255, null=True, blank=True)
    score_url = models.URLField(max_length=255, null=True, blank=True)
    
    # Metadata
    data_source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    external_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Admin
    is_verified = models.BooleanField(default=False)
    needs_review = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)
    admin_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'works'
        ordering = ['title']
        indexes = [
            models.Index(fields=['composer'], name='idx_work_composer'),
            models.Index(fields=['title'], name='idx_work_title'),
            models.Index(fields=['title_normalized'], name='idx_work_normalized'),
            models.Index(fields=['instrumentation_category'], name='idx_work_instrumentation'),
            models.Index(fields=['composition_year'], name='idx_work_year'),
            models.Index(fields=['difficulty_level'], name='idx_work_difficulty'),
            models.Index(fields=['is_public'], name='idx_work_public'),
            models.Index(fields=['is_verified'], name='idx_work_is_verified'),
            models.Index(fields=['view_count'], name='idx_work_views'),
            models.Index(fields=['composer', 'is_public'], name='idx_work_comp_public'),
            models.Index(fields=['composer', 'is_verified'], name='idx_work_comp_verified'),
            models.Index(fields=['instrumentation_category', 'is_public'], name='idx_work_inst_public'),
        ]

    def __str__(self):
        return f"{self.title} - {self.composer.full_name}"

    def save(self, *args, **kwargs):
        # Auto-generate normalized title if not set
        if not self.title_normalized:
            import unicodedata
            self.title_normalized = unicodedata.normalize('NFKD', self.title).encode('ascii', 'ignore').decode('utf-8').lower()
        super().save(*args, **kwargs)


class Tag(models.Model):
    """Tags for flexible categorization of works"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=50, null=True, blank=True,
                               help_text="'genre', 'style', 'technique', 'form', etc.")
    description = models.TextField(null=True, blank=True)
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tags'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='idx_tag_name'),
            models.Index(fields=['slug'], name='idx_tag_slug'),
            models.Index(fields=['category'], name='idx_tag_category'),
            models.Index(fields=['usage_count'], name='idx_tag_usage'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class WorkTag(models.Model):
    """Many-to-many relationship between works and tags"""
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name='work_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='work_tags')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'work_tags'
        unique_together = ('work', 'tag')
        indexes = [
            models.Index(fields=['work'], name='idx_work_tags_work'),
            models.Index(fields=['tag'], name='idx_work_tags_tag'),
        ]

    def __str__(self):
        return f"{self.work.title} - {self.tag.name}"


class WorkSearchIndex(models.Model):
    """Denormalized table for ultra-fast search combining composer and work data"""
    work = models.OneToOneField(Work, on_delete=models.CASCADE, related_name='search_index')
    
    # Denormalized data for fast search
    composer_full_name = models.CharField(max_length=255)
    composer_last_name = models.CharField(max_length=100)
    composer_country = models.CharField(max_length=100, null=True, blank=True)
    composer_birth_year = models.SmallIntegerField(null=True, blank=True)
    composer_death_year = models.SmallIntegerField(null=True, blank=True)
    
    work_title = models.CharField(max_length=500)
    work_instrumentation = models.CharField(max_length=200, null=True, blank=True)
    work_year = models.SmallIntegerField(null=True, blank=True)
    
    # Combined search field
    search_text = models.TextField(help_text="Combines all searchable fields")
    
    # Boost/ranking factors
    popularity_score = models.FloatField(default=0.0)
    last_viewed = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'work_search_index'
        indexes = [
            models.Index(fields=['composer_last_name'], name='idx_search_composer_last'),
            models.Index(fields=['composer_full_name'], name='idx_search_composer_full'),
            models.Index(fields=['work_title'], name='idx_search_work_title'),
            models.Index(fields=['work_instrumentation'], name='idx_search_instrumentation'),
            models.Index(fields=['work_year'], name='idx_search_year'),
            models.Index(fields=['popularity_score'], name='idx_search_popularity'),
        ]

    def __str__(self):
        return f"Search Index: {self.work.title}"

