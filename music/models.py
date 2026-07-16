from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify

from .eras import ERA_CHOICES, eras_for_composer


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
    name = models.CharField(max_length=1000, unique=True)
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


class ComposerEra(models.Model):
    """A composer's membership in one musical era.

    Multi-valued by design: a composer's active span can overlap several era windows
    (Barrios, 1885-1944, is Romantic *and* Modern). Rows are derived from birth/death
    years by `music.eras` — materialised here so the era filter can hit an index
    rather than recompute arithmetic over 16k composers per request.

    Kept in sync by the post_save signal below plus the idempotent
    `backfill_composer_eras` command. There is no `Era` lookup table: the vocabulary
    is closed and its windows must live in code anyway (the derivation needs them),
    so a table would buy a join and a seed migration and nothing else.
    """

    BASIS_CHOICES = [
        ('dates', 'Derived from birth/death years'),
        ('source', 'Inferred from data source (no dates available)'),
        ('manual', 'Set by an admin'),
    ]

    composer = models.ForeignKey(Composer, on_delete=models.CASCADE, related_name='eras')
    era = models.CharField(max_length=20, choices=ERA_CHOICES)
    # How this row was arrived at. Re-derivation rewrites 'dates'/'source' rows but
    # never touches 'manual' ones, so an admin correction survives the next backfill;
    # it also makes "show me every era we guessed" a one-line query.
    basis = models.CharField(max_length=10, choices=BASIS_CHOICES, default='dates')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'composer_eras'
        unique_together = ('composer', 'era')
        indexes = [
            models.Index(fields=['composer'], name='idx_composer_eras_composer'),
            # (era, composer) not (era): the era filter is an EXISTS correlated on
            # composer_id, so the composite serves it index-only.
            models.Index(fields=['era', 'composer'], name='idx_composer_eras_era'),
        ]

    def __str__(self):
        return f"{self.composer.full_name} - {self.get_era_display()}"


def sync_composer_eras(composer) -> set:
    """Rewrite `composer`'s date-derived era rows to match its birth/death years.

    Idempotent; returns the set of era slugs the dates imply. Shared by the post_save
    signal and the `backfill_composer_eras` command so there is exactly one
    definition of "what this composer's eras should be".

    Row ownership by `basis`, which is what makes re-running safe:
      - 'dates'  — owned here; freely created and deleted.
      - 'source' — a guess made for a composer with no dates. Left alone while the
                   composer still has no dates; replaced the moment real dates arrive.
      - 'manual' — an admin's word. Never touched.

    Known limitation: a manual row is *additive*. An admin can add an era the dates
    miss, but can't subtract one the dates imply — deleting it just means the next
    sync puts it back. Suppression would need an exclusion row; nothing needs it yet.
    """
    desired = set(eras_for_composer(
        composer.birth_year, composer.death_year, bool(composer.is_living)
    ))
    rows = {row.era: row for row in composer.eras.all()}

    if desired:
        # Real dates supersede guesses: drop any non-manual row the dates don't back,
        # including 'source' rows that were only ever a stand-in for missing dates.
        for era, row in rows.items():
            if era not in desired and row.basis != 'manual':
                row.delete()
        for era in desired:
            row = rows.get(era)
            if row is None:
                ComposerEra.objects.create(composer=composer, era=era, basis='dates')
            elif row.basis == 'source':
                # Same era, but we now know it rather than guess it.
                row.basis = 'dates'
                row.save(update_fields=['basis'])
    else:
        # Dates were removed or never existed: retract only what dates justified,
        # leaving any 'source' fallback and 'manual' overrides standing.
        for row in rows.values():
            if row.basis == 'dates':
                row.delete()

    return desired


@receiver(post_save, sender=Composer)
def _sync_eras_on_composer_save(sender, instance, created, update_fields=None, **kwargs):
    """Keep era tags honest when a composer's dates change.

    Staleness is the classic failure of materialised tags: edit a birth year in admin
    and the tags quietly lie. (`is_living` has exactly this bug today — it's only
    recomputed by a command someone has to remember to run. Don't copy that.)

    Bulk paths are unaffected: bulk_create/bulk_update don't emit post_save, and a
    save() that names unrelated update_fields skips the work.
    """
    if update_fields is not None and not {
        'birth_year', 'death_year', 'is_living'
    } & set(update_fields):
        return
    sync_composer_eras(instance)


class Work(models.Model):
    """Musical works in the classical guitar repertoire"""

    # Follows ComposerEra/WorkInstrumentation's `basis` precedent.
    ARRANGEMENT_BASIS_CHOICES = [
        ('derived', 'Derived'),      # from IMSLP's own (arr) categories
        ('suggested', 'Suggested'),  # from a user suggestion an admin applied
        ('manual', 'Manual'),        # set by hand
    ]

    # Relationships
    composer = models.ForeignKey(Composer, on_delete=models.CASCADE, related_name='works')
    
    # Work Info
    title = models.CharField(max_length=1000)
    title_normalized = models.CharField(max_length=1000, help_text="Lowercase, accents removed for search")
    title_sort_key = models.CharField(max_length=1000, db_index=True, default='', blank=True,
                                     help_text="Normalized title for alphabetical sorting")
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

    # Arrangement provenance
    #
    # True when the entry is in this guitar catalog *because a guitar arrangement of it
    # exists and is linkable* — Bach's violin Chaconne, a vihuela fantasia — rather than
    # because it was written for the modern guitar. The title stays the original work's
    # title (IMSLP files arrangements under the original work), so this flag is what
    # makes such a row legible: without it a violin partita just looks misfiled.
    #
    # Deliberately no `arranger` column. One IMSLP page hosts up to five different guitar
    # arrangements (BWV 1007 has Dada, Gazoni, Reyne, Shorter, Tavares), so a single
    # CharField would misrepresent it, and we don't filter by arranger. Per-arranger
    # attribution, if ever wanted, is a side table like WorkInstrumentation.
    is_arrangement = models.BooleanField(default=False, db_index=True,
                                        help_text="Arranged/transcribed for guitar rather than "
                                                  "originally written for it")
    arrangement_basis = models.CharField(max_length=10, choices=ARRANGEMENT_BASIS_CHOICES,
                                        default='manual', blank=True,
                                        help_text="Where is_arrangement came from. Re-running the "
                                                  "importer rewrites 'derived' only, so a human's "
                                                  "call survives every backfill.")

    # Content
    description = models.TextField(null=True, blank=True)
    movements = models.TextField(null=True, blank=True,
                                help_text="JSON array or delimited list")
    key_signature = models.CharField(max_length=50, null=True, blank=True)
    
    # External Resources
    imslp_url = models.URLField(max_length=1000, null=True, blank=True)
    sheerpluck_url = models.URLField(max_length=1000, null=True, blank=True)
    youtube_url = models.URLField(max_length=1000, null=True, blank=True)
    score_url = models.URLField(max_length=1000, null=True, blank=True)
    
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
        ordering = ['title_sort_key']
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
        # Keep the derived title columns in lockstep with `title` on every save so an
        # edit fixes them too. `title_normalized` powers search; `title_sort_key` powers
        # the alphabetical browse order (default sort). Historically only
        # `title_normalized` was maintained here, leaving `title_sort_key` NULL on any
        # work created/edited outside the one-off `update_sort_keys` command — which
        # broke the Works default ordering.
        import unicodedata
        from .utils import generate_title_sort_key, resolve_instrumentation_category

        title = self.title or ''
        self.title_normalized = (
            unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('utf-8').lower()
        )
        self.title_sort_key = generate_title_sort_key(title)

        # `instrumentation_category` is derived from `instrumentation_detail` for the
        # same reason, and had the same bug: nothing in the UI sets the category
        # directly, so a work whose detail text was written by any path other than the
        # importer kept a NULL category and vanished from the ?instrumentation= filter.
        # Only derive when there IS detail text — a blank detail leaves an explicitly
        # assigned category alone rather than wiping it.
        if (self.instrumentation_detail or '').strip():
            self.instrumentation_category = resolve_instrumentation_category(
                self.instrumentation_detail
            )
        super().save(*args, **kwargs)


class WorkInstrumentation(models.Model):
    """An *additional* way a work can be played, beyond its notated instrumentation.

    "In Realms of Passing Dreams" is written for guitar and tape but is also playable
    by 5 guitars; it belongs in both Guitar with Electronics and Quintet. Rows here
    are derived from the "(or ...)" alternates our sources already write into
    `Work.instrumentation_detail` (see `utils.split_realizations`), by the idempotent
    `backfill_alternate_instrumentations` command, or proposed by users through the
    suggestion flow.

    `Work.instrumentation_category` stays the *primary* and is untouched by this
    table — deliberately. It is what the Works column shows, what the table sorts by
    and what the facet totals are keyed on, none of which have honest semantics over a
    multi-valued join (an ORDER BY across one duplicates rows). Only the filter reads
    both. There is no `is_primary` flag here: the FK is the primary, one source of
    truth.

    See SDD: alternate-work-instrumentations.
    """

    BASIS_CHOICES = [
        ('derived', 'Derived from the detail text'),
        ('suggested', 'Proposed by a user and approved by an admin'),
        ('manual', 'Set by an admin'),
    ]

    work = models.ForeignKey(Work, on_delete=models.CASCADE,
                             related_name='alternate_instrumentations')
    category = models.ForeignKey(InstrumentationCategory, on_delete=models.CASCADE,
                                 related_name='alternate_works')
    # As on ComposerEra: re-derivation rewrites 'derived' rows but never touches
    # 'suggested'/'manual' ones, so a human's call survives the next backfill — and
    # "show me every alternate we guessed" stays a one-line query. The parse is a
    # crude substitution and is wrong sometimes; this is what makes that acceptable.
    basis = models.CharField(max_length=10, choices=BASIS_CHOICES, default='derived')
    note = models.CharField(max_length=200, blank=True,
                            help_text="e.g. 'playable as 5 guitars'")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'work_instrumentations'
        unique_together = ('work', 'category')
        indexes = [
            models.Index(fields=['work'], name='idx_work_inst_work'),
            # (category, work) not (category): the filter is an EXISTS correlated on
            # work_id, so the composite serves it index-only.
            models.Index(fields=['category', 'work'], name='idx_work_inst_category'),
        ]

    def __str__(self):
        return f"{self.work.title} - also {self.category.name}"


def sync_work_alternate_instrumentations(work) -> set:
    """Refresh a work's *derived* alternates from its detail text. Returns the set of
    category names now on the work.

    Leaves 'suggested'/'manual' rows alone. Idempotent, so the backfill and any future
    save-time hook can both call it safely.
    """
    from .utils import alternate_instrumentation_names

    names = set(alternate_instrumentation_names(work.instrumentation_detail))
    kept = set(
        WorkInstrumentation.objects
        .filter(work=work).exclude(basis='derived')
        .values_list('category__name', flat=True)
    )
    # Never derive a row a human already owns, and never duplicate the primary.
    wanted = names - kept

    WorkInstrumentation.objects.filter(work=work, basis='derived').exclude(
        category__name__in=wanted).delete()
    for name in wanted:
        category, _ = InstrumentationCategory.objects.get_or_create(name=name)
        WorkInstrumentation.objects.get_or_create(
            work=work, category=category, defaults={'basis': 'derived'})
    return wanted | kept


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


class WorkLink(models.Model):
    """Arbitrary labeled external links for a work (bespoke links).

    Complements the fixed URL columns on Work (imslp_url, sheerpluck_url,
    youtube_url, score_url) for any link that doesn't fit those buckets.
    """

    LINK_TYPE_CHOICES = [
        ('imslp', 'IMSLP'),
        ('sheerpluck', 'SheerPluck'),
        ('youtube', 'YouTube'),
        ('score', 'Score'),
        ('publisher', 'Publisher'),
        ('recording', 'Recording'),
        ('commission', 'Commission / Program'),
        ('other', 'Other'),
    ]

    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name='links')
    label = models.CharField(max_length=200, help_text="Display text, e.g. 'BCGS Commission'")
    url = models.URLField(max_length=1000)
    link_type = models.CharField(max_length=20, choices=LINK_TYPE_CHOICES, default='other',
                                 help_text="Drives the icon / CTA styling; label is the shown text")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'work_links'
        ordering = ['sort_order', 'id']
        unique_together = ('work', 'url')
        indexes = [
            models.Index(fields=['work'], name='idx_work_links_work'),
            models.Index(fields=['link_type'], name='idx_work_links_type'),
        ]

    def __str__(self):
        return f"{self.label} -> {self.work.title}"


class WorkSearchIndex(models.Model):
    """Denormalized table for ultra-fast search combining composer and work data"""
    work = models.OneToOneField(Work, on_delete=models.CASCADE, related_name='search_index')
    
    # Denormalized data for fast search
    composer_full_name = models.CharField(max_length=255)
    composer_last_name = models.CharField(max_length=100)
    composer_country = models.CharField(max_length=100, null=True, blank=True)
    composer_birth_year = models.SmallIntegerField(null=True, blank=True)
    composer_death_year = models.SmallIntegerField(null=True, blank=True)
    
    work_title = models.CharField(max_length=1000)
    work_instrumentation = models.CharField(max_length=1000, null=True, blank=True)
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


class UserSuggestion(models.Model):
    """Store user suggestions for database changes/additions"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('merged', 'Merged'),
    ]
    
    SUGGESTION_TYPE_CHOICES = [
        ('new_composer', 'New Composer'),
        ('new_work', 'New Work'),
        ('edit_composer', 'Edit Composer'),
        ('edit_work', 'Edit Work'),
        ('correction', 'Correction'),
        ('other', 'Other'),
    ]
    
    # Submission info
    suggestion_type = models.CharField(max_length=20, choices=SUGGESTION_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # User contact
    submitter_name = models.CharField(max_length=100, blank=True)
    submitter_email = models.EmailField(blank=True)
    
    # Suggestion content
    title = models.CharField(max_length=200)
    description = models.TextField()
    suggested_data = models.JSONField(null=True, blank=True, help_text="Structured data for the suggestion")
    
    # References
    related_composer = models.ForeignKey(Composer, on_delete=models.SET_NULL, null=True, blank=True)
    related_work = models.ForeignKey(Work, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Admin notes
    admin_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_suggestions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='idx_suggestion_status'),
            models.Index(fields=['created_at'], name='idx_suggestion_created'),
            models.Index(fields=['suggestion_type'], name='idx_suggestion_type'),
        ]
    
    def __str__(self):
        return f"{self.get_suggestion_type_display()}: {self.title}"

