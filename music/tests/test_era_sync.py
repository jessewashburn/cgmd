"""Materialising era tags: the post_save signal, basis ownership, and the backfill
command.

The derivation itself is covered by test_eras.py; this file is about the rows.
"""
import pytest
from django.core.management import call_command
from io import StringIO

from music.models import ComposerEra, sync_composer_eras

from .factories import ComposerFactory, DataSourceFactory

pytestmark = pytest.mark.django_db


def eras_of(composer):
    return set(composer.eras.values_list('era', flat=True))


# --- the signal keeps tags honest -------------------------------------------

def test_saving_a_composer_creates_its_era_tags():
    composer = ComposerFactory(birth_year=1885, death_year=1944)
    assert eras_of(composer) == {'romantic', 'modern'}


def test_editing_a_birth_year_reclassifies():
    """The bug this signal exists to prevent: dates change, tags quietly lie."""
    composer = ComposerFactory(birth_year=1885, death_year=1944)
    assert eras_of(composer) == {'romantic', 'modern'}

    composer.birth_year = 1600
    composer.death_year = 1660
    composer.save()

    assert eras_of(composer) == {'baroque'}


def test_clearing_dates_retracts_derived_tags():
    composer = ComposerFactory(birth_year=1885, death_year=1944)
    composer.birth_year = None
    composer.death_year = None
    composer.save()
    assert eras_of(composer) == set()


def test_composer_with_no_dates_gets_no_tags():
    composer = ComposerFactory(birth_year=None, death_year=None)
    assert eras_of(composer) == set()


def test_save_with_unrelated_update_fields_skips_the_resync():
    """Bulk paths opt out by naming their fields; only date fields trigger work."""
    composer = ComposerFactory(birth_year=1885, death_year=1944)
    ComposerEra.objects.filter(composer=composer).delete()

    composer.full_name = 'Renamed'
    composer.save(update_fields=['full_name'])
    assert eras_of(composer) == set()  # untouched

    composer.birth_year = 1885
    composer.save(update_fields=['birth_year'])
    assert eras_of(composer) == {'romantic', 'modern'}


def test_sync_is_idempotent():
    composer = ComposerFactory(birth_year=1885, death_year=1944)
    before = set(ComposerEra.objects.filter(composer=composer).values_list('id', flat=True))

    sync_composer_eras(composer)
    sync_composer_eras(composer)

    after = set(ComposerEra.objects.filter(composer=composer).values_list('id', flat=True))
    assert before == after, 'resyncing churned rows that should have been left alone'


# --- basis ownership ---------------------------------------------------------

def test_manual_tags_survive_resync():
    composer = ComposerFactory(birth_year=1950, death_year=None, is_living=True)
    ComposerEra.objects.create(composer=composer, era='baroque', basis='manual')

    sync_composer_eras(composer)

    assert 'baroque' in eras_of(composer), 'an admin override was stomped by re-derivation'
    assert eras_of(composer) == {'baroque', 'modern', '21st-century'}


def test_source_inferred_tags_survive_while_the_composer_stays_undated():
    composer = ComposerFactory(birth_year=None, death_year=None)
    ComposerEra.objects.create(composer=composer, era='modern', basis='source')

    sync_composer_eras(composer)

    assert eras_of(composer) == {'modern'}


def test_real_dates_supersede_a_source_guess():
    composer = ComposerFactory(birth_year=None, death_year=None)
    ComposerEra.objects.create(composer=composer, era='modern', basis='source')
    ComposerEra.objects.create(composer=composer, era='21st-century', basis='source')

    composer.birth_year = 1600
    composer.death_year = 1660
    composer.save()

    assert eras_of(composer) == {'baroque'}, 'stale source guesses outlived the dates'


def test_a_guess_confirmed_by_dates_is_promoted_not_duplicated():
    composer = ComposerFactory(birth_year=None, death_year=None)
    ComposerEra.objects.create(composer=composer, era='modern', basis='source')

    composer.birth_year = 1950
    composer.save()

    rows = ComposerEra.objects.filter(composer=composer, era='modern')
    assert rows.count() == 1
    assert rows.first().basis == 'dates'


# --- the backfill command ----------------------------------------------------

def test_backfill_tags_existing_composers():
    composers = [
        ComposerFactory(birth_year=1885, death_year=1944),
        ComposerFactory(birth_year=1600, death_year=1660),
    ]
    ComposerEra.objects.all().delete()  # simulate rows created before the feature

    call_command('backfill_composer_eras', stdout=StringIO())

    assert eras_of(composers[0]) == {'romantic', 'modern'}
    assert eras_of(composers[1]) == {'baroque'}


def test_backfill_dry_run_writes_nothing():
    ComposerFactory(birth_year=1885, death_year=1944)
    ComposerEra.objects.all().delete()

    out = StringIO()
    call_command('backfill_composer_eras', '--dry-run', stdout=out)

    assert ComposerEra.objects.count() == 0
    assert 'DRY RUN' in out.getvalue()


def test_backfill_is_idempotent():
    ComposerFactory(birth_year=1885, death_year=1944)
    call_command('backfill_composer_eras', stdout=StringIO())
    first = ComposerEra.objects.count()

    call_command('backfill_composer_eras', stdout=StringIO())

    assert ComposerEra.objects.count() == first


def test_infer_undated_is_opt_in_and_only_touches_the_named_source():
    sheerpluck = DataSourceFactory(name='Sheerpluck')
    imslp = DataSourceFactory(name='IMSLP')
    undated_sp = ComposerFactory(birth_year=None, death_year=None, data_source=sheerpluck)
    undated_imslp = ComposerFactory(birth_year=None, death_year=None, data_source=imslp)

    # Without the flag: nothing is guessed.
    call_command('backfill_composer_eras', stdout=StringIO())
    assert eras_of(undated_sp) == set()

    call_command('backfill_composer_eras', '--infer-undated', stdout=StringIO())

    assert eras_of(undated_sp) == {'modern', '21st-century'}
    assert ComposerEra.objects.filter(composer=undated_sp).first().basis == 'source'
    # IMSLP spans every era, so its undated composers imply nothing.
    assert eras_of(undated_imslp) == set()


def test_infer_undated_leaves_dated_composers_alone():
    sheerpluck = DataSourceFactory(name='Sheerpluck')
    dated = ComposerFactory(birth_year=1600, death_year=1660, data_source=sheerpluck)

    call_command('backfill_composer_eras', '--infer-undated', stdout=StringIO())

    assert eras_of(dated) == {'baroque'}


def test_infer_undated_is_reversible():
    """The escape hatch that makes guessing at thousands of rows acceptable."""
    sheerpluck = DataSourceFactory(name='Sheerpluck')
    undated = ComposerFactory(birth_year=None, death_year=None, data_source=sheerpluck)
    call_command('backfill_composer_eras', '--infer-undated', stdout=StringIO())

    ComposerEra.objects.filter(basis='source').delete()

    assert eras_of(undated) == set()
