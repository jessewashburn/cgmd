"""Instrumentation categorisation and the ?instrumentation= filter.

`Work.instrumentation_category` is derived from the free-text
`Work.instrumentation_detail`; these pin that mapping, the write paths that apply
it, and the filter that reads it.
"""
import pytest

from music.models import InstrumentationCategory, UserSuggestion, Work
from music.suggestion_apply import apply_suggestion
from music.utils import (
    CANONICAL_INSTRUMENTATION_CATEGORIES,
    canonical_instrumentation,
    resolve_instrumentation_filter,
)
from .factories import ComposerFactory, WorkFactory


# --- canonical_instrumentation ----------------------------------------------

@pytest.mark.parametrize('text, expected', [
    # Verbatim category names round-trip.
    ('Octet', 'Octet'),
    ('Guitar and Piano', 'Guitar and Piano'),
    # Phrasings that the old exact-equality matcher dropped on the floor (-> NULL).
    ('Solo Guitar', 'Solo'),
    ('Guitar Solo', 'Solo'),
    ('guitar (8)', 'Octet'),
    ('Solo: Renaissance guitar', 'Solo'),
    ('Duo: electric guitar (2)', 'Duo'),
    ('Chamber Music: flute, guitar', 'Guitar and Flute'),
    # Bare instrument names (real prod values that were all sitting in 'Other').
    ('guitar', 'Solo'),
    ('Guitar', 'Solo'),
    ('classical guitar', 'Solo'),
    ('guitar / piano', 'Guitar and Piano'),
    # Player counts, including with a qualifier between number and noun.
    ('8 guitars', 'Octet'),
    ('eight guitars', 'Octet'),
    ('two guitars', 'Duo'),
    ('2 guitars', 'Duo'),
    ('4 guitars', 'Quartet'),
    ('2 acoustic guitars', 'Duo'),
    ('three acoustic guitars', 'Trio'),
    # Misspellings and non-English spellings.
    ('Octett', 'Octet'),
    ('Quartett', 'Quartet'),
    ('Quatuor', 'Quartet'),
    ('Duett', 'Duo'),
    ('Gitarre solo', 'Solo'),
    ('Klavier, guitar', 'Guitar and Piano'),
    ('Flauto, guitar', 'Guitar and Flute'),
    # Genre prefixes still beat instrument detection.
    ('Stage Work: opera', 'Stage Work'),
    ('Dance/Ballet: guitar', 'Dance/Ballet'),
    # Unrecognised text is bucketed, not guessed at.
    ('zzzz qqqq', 'Other'),
])
def test_canonical_instrumentation(text, expected):
    assert canonical_instrumentation(text) == expected


def test_blank_instrumentation_has_no_category():
    """Blank text means "unknown", which is a NULL category rather than 'Other'."""
    assert canonical_instrumentation('') is None
    assert canonical_instrumentation('   ') is None
    assert canonical_instrumentation(None) is None


def test_every_category_name_resolves_to_itself():
    """The dropdown sends category names back as filter terms, so each must be a
    fixed point — otherwise picking a filter returns the wrong bucket."""
    for name in CANONICAL_INSTRUMENTATION_CATEGORIES:
        assert canonical_instrumentation(name) == name


def test_player_count_survives_fuzzy_matching():
    """"2 acoustic guitars" is one cheap edit from the "acoustic guitar" alias, so a
    fuzzy match silently demoted a duo to a solo. Counts must win."""
    assert canonical_instrumentation('2 acoustic guitars') == 'Duo'
    assert canonical_instrumentation('acoustic guitar') == 'Solo'


def test_canonical_instrumentation_only_returns_known_categories():
    samples = ['Solo Guitar', 'guitar (8)', 'Klavier, guitar', 'zzzz', 'Octett',
               'Chamber Music: flute, guitar', 'soprano - guitar', 'lute']
    for text in samples:
        assert canonical_instrumentation(text) in CANONICAL_INSTRUMENTATION_CATEGORIES


# --- resolve_instrumentation_filter -----------------------------------------

def test_filter_term_resolution():
    assert resolve_instrumentation_filter('Octet') == 'Octet'
    assert resolve_instrumentation_filter('Solo Guitar') == 'Solo'


def test_unrecognised_filter_term_does_not_fall_into_other():
    """A junk term must match nothing. Reusing canonical_instrumentation here would
    resolve it to 'Other' and silently return the whole uncategorised bucket."""
    assert resolve_instrumentation_filter('zzzznonsense') is None
    assert resolve_instrumentation_filter('') is None
    # ...but 'Other' is still reachable when asked for by name.
    assert resolve_instrumentation_filter('Other') == 'Other'


# --- Work.save() derives the category ---------------------------------------

@pytest.mark.django_db
def test_work_save_derives_category_from_detail():
    work = WorkFactory(instrumentation_detail='Octet')
    assert work.instrumentation_category.name == 'Octet'


@pytest.mark.django_db
def test_editing_detail_recategorises_the_work():
    """The Firelight regression: an edit that rewrote instrumentation_detail left a
    stale/NULL category behind, dropping the work out of ?instrumentation=."""
    work = WorkFactory(instrumentation_detail='Solo')
    assert work.instrumentation_category.name == 'Solo'

    work.instrumentation_detail = 'Octet'
    work.save()
    work.refresh_from_db()
    assert work.instrumentation_category.name == 'Octet'


@pytest.mark.django_db
def test_blank_detail_leaves_an_explicit_category_alone():
    """Nothing should wipe a category that was set deliberately when there is no
    detail text to re-derive it from."""
    category = InstrumentationCategory.objects.create(name='Solo')
    work = WorkFactory(instrumentation_detail='', instrumentation_category=category)
    work.refresh_from_db()
    assert work.instrumentation_category == category


@pytest.mark.django_db
def test_save_reuses_the_existing_category_row():
    existing = InstrumentationCategory.objects.create(name='Octet')
    work = WorkFactory(instrumentation_detail='guitar (8)')
    assert work.instrumentation_category_id == existing.id
    assert InstrumentationCategory.objects.filter(name='Octet').count() == 1


# --- the filter itself ------------------------------------------------------

@pytest.mark.django_db
def test_instrumentation_filter_matches_one_category_only(api):
    """Duo's old variation list contained the fragment 'guitar and', so an icontains
    OR matched every "Guitar and X" category — Duo returned 23.5k works instead of
    4.6k in prod."""
    WorkFactory(title='Real Duo', instrumentation_detail='Duo')
    WorkFactory(title='Piano Work', instrumentation_detail='Chamber Music: piano, guitar')
    WorkFactory(title='Flute Work', instrumentation_detail='Chamber Music: flute, guitar')
    WorkFactory(title='Orchestral', instrumentation_detail='guitar - orchestra')

    res = api.get('/api/works/', {'instrumentation': 'Duo'})
    titles = [w['title'] for w in res.data['results']]
    assert titles == ['Real Duo']


@pytest.mark.django_db
def test_instrumentation_filter_finds_work_added_via_free_text(api):
    """?inst=Octet must find a work whose detail text is 'Octet' — the reported bug."""
    composer = ComposerFactory(full_name='Gainey, Christopher', last_name='Gainey')
    WorkFactory(title='Firelight', composer=composer, instrumentation_detail='Octet')

    res = api.get('/api/works/', {'instrumentation': 'Octet'})
    assert [w['title'] for w in res.data['results']] == ['Firelight']


@pytest.mark.django_db
def test_instrumentation_filter_accepts_a_variant_term(api):
    WorkFactory(title='Solo Work', instrumentation_detail='Solo: Renaissance guitar')
    res = api.get('/api/works/', {'instrumentation': 'Solo Guitar'})
    assert [w['title'] for w in res.data['results']] == ['Solo Work']


@pytest.mark.django_db
def test_unrecognised_instrumentation_filter_returns_nothing(api):
    WorkFactory(title='Some Work', instrumentation_detail='Duo')
    res = api.get('/api/works/', {'instrumentation': 'zzzznonsense'})
    assert res.data['results'] == []


@pytest.mark.django_db
def test_composer_instrumentation_filter_matches_one_category_only(api):
    duo = ComposerFactory(full_name='Duo Writer', last_name='Duo')
    piano = ComposerFactory(full_name='Piano Writer', last_name='Piano')
    WorkFactory(composer=duo, instrumentation_detail='Duo')
    WorkFactory(composer=piano, instrumentation_detail='Chamber Music: piano, guitar')

    res = api.get('/api/composers/', {'instrumentation': 'Duo'})
    names = [c['full_name'] for c in res.data['results']]
    assert names == ['Duo Writer']


# --- the curated category list ----------------------------------------------

@pytest.mark.django_db
def test_curated_list_reports_each_category_with_its_own_id(api):
    """Resolving ids by icontains handed "Guitar and Voice" the Bass Guitar row's id."""
    WorkFactory(instrumentation_detail='soprano - guitar')
    WorkFactory(instrumentation_detail='bass guitar solo')

    res = api.get('/api/instrumentations/')
    by_name = {row['name']: row['id'] for row in res.data}
    assert set(by_name) == {'Guitar and Voice', 'Bass Guitar'}
    for name, category_id in by_name.items():
        assert InstrumentationCategory.objects.get(pk=category_id).name == name


@pytest.mark.django_db
def test_curated_list_omits_categories_with_no_works(api):
    InstrumentationCategory.objects.create(name='Octet')
    WorkFactory(instrumentation_detail='Duo')

    res = api.get('/api/instrumentations/')
    assert [row['name'] for row in res.data] == ['Duo']


@pytest.mark.django_db
def test_curated_list_is_in_canonical_display_order(api):
    for detail in ['Chamber Music: piano, guitar', 'Duo', 'Solo', 'Octet']:
        WorkFactory(instrumentation_detail=detail)

    res = api.get('/api/instrumentations/')
    names = [row['name'] for row in res.data]
    assert names == ['Solo', 'Duo', 'Octet', 'Guitar and Piano']


# --- the cleanup_instrumentations backfill ----------------------------------

@pytest.mark.django_db
def test_cleanup_command_backfills_missing_categories():
    """The backfill for works written before Work.save() derived the category."""
    from django.core.management import call_command

    stale = InstrumentationCategory.objects.create(name='Some Old Junk Category')
    work = WorkFactory(title='Firelight', instrumentation_detail='Octet',
                       instrumentation_category=stale)
    # Simulate the pre-fix state: detail text present, category wrong/NULL.
    Work.objects.filter(pk=work.pk).update(instrumentation_category=None)

    call_command('cleanup_instrumentations', verbosity=0)

    work.refresh_from_db()
    assert work.instrumentation_category.name == 'Octet'
    # Categories left with no works are dropped.
    assert not InstrumentationCategory.objects.filter(pk=stale.pk).exists()


@pytest.mark.django_db
def test_cleanup_command_dry_run_changes_nothing():
    from django.core.management import call_command

    work = WorkFactory(title='Firelight', instrumentation_detail='Octet')
    Work.objects.filter(pk=work.pk).update(instrumentation_category=None)

    call_command('cleanup_instrumentations', '--dry-run', verbosity=0)

    work.refresh_from_db()
    assert work.instrumentation_category is None


@pytest.mark.django_db
def test_cleanup_command_is_idempotent():
    from django.core.management import call_command

    WorkFactory(title='A', instrumentation_detail='Octet')
    WorkFactory(title='B', instrumentation_detail='Chamber Music: flute, guitar')

    call_command('cleanup_instrumentations', verbosity=0)
    first = {w.title: w.instrumentation_category.name for w in Work.objects.all()}
    call_command('cleanup_instrumentations', verbosity=0)
    second = {w.title: w.instrumentation_category.name for w in Work.objects.all()}

    assert first == second == {'A': 'Octet', 'B': 'Guitar and Flute'}


# --- end-to-end reproduction of the reported bug ----------------------------

@pytest.mark.django_db
def test_reported_url_end_to_end(api):
    """Reproduce prod exactly: Firelight added via suggestions with instrumentation
    arriving on a later edit, then fetched with the user's real URL params
    (?inst=Octet&sort=title_sort_key -> ?instrumentation=Octet&ordering=title_sort_key).
    """
    # Some other works so the filter has something to exclude.
    WorkFactory(title='Aria', instrumentation_detail='Solo')
    WorkFactory(title='Zephyr', instrumentation_detail='Chamber Music: piano, guitar')
    # An existing Octet work, to prove ordering across >1 result.
    WorkFactory(title='Zzz Octet Work', instrumentation_detail='guitar (8)')

    # 1. new_work suggestion, submitted WITHOUT instrumentation (as happened in prod).
    composer = ComposerFactory(full_name='Gainey, Christopher', last_name='Gainey')
    new_work = UserSuggestion.objects.create(
        suggestion_type='new_work', title='New work: Firelight', description='',
        suggested_data={'composer_name': 'Chris Gainey', 'work_title': 'Firelight'},
    )
    result = apply_suggestion(new_work, composer_id=composer.id)
    work = Work.objects.get(pk=result['work']['id'])
    assert work.instrumentation_category is None  # nothing to derive from yet

    # 2. edit_work suggestion adds the instrumentation text later.
    edit = UserSuggestion.objects.create(
        suggestion_type='edit_work', title='Add instrumentation', description='',
        suggested_data={'instrumentation_detail': 'Octet'}, related_work=work,
    )
    apply_suggestion(edit)

    # 3. The user's URL.
    res = api.get('/api/works/', {'instrumentation': 'Octet', 'ordering': 'title_sort_key'})
    titles = [w['title'] for w in res.data['results']]

    assert titles == ['Firelight', 'Zzz Octet Work']
    firelight = res.data['results'][0]
    assert firelight['instrumentation_category']['name'] == 'Octet'
    assert firelight['instrumentation_detail'] == 'Octet'
