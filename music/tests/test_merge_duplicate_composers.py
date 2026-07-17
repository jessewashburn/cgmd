"""Merging composer rows that are one human split by a missing birth year.

Every case below is a real shape from production, not a hypothetical.
"""
import pytest
from django.core.management import call_command

from music.models import Composer, UserSuggestion, Work
from .factories import ComposerFactory, CountryFactory, WorkFactory

pytestmark = pytest.mark.django_db


def _dupe(name='Adams, Chris', **kw):
    return ComposerFactory(full_name=name, last_name=name.split(',')[0],
                           name_normalized=name.lower(), **kw)


# --------------------------------------------------------------------------
# The safe case
# --------------------------------------------------------------------------

def test_merges_a_dated_and_an_undated_row():
    """prod: adams, chris  b-(4w) | b1979(1w). A missing birth year is not evidence of a
    different person."""
    undated = _dupe(birth_year=None)
    dated = _dupe(birth_year=1979)
    WorkFactory(composer=undated, title='Undated Work')
    WorkFactory(composer=dated, title='Dated Work')

    call_command('merge_duplicate_composers', apply=True)

    assert Composer.objects.filter(name_normalized='adams, chris').count() == 1
    survivor = Composer.objects.get(name_normalized='adams, chris')
    assert survivor.id == dated.id           # the row carrying the identity wins
    assert survivor.birth_year == 1979
    assert survivor.works.count() == 2       # both works, none lost


def test_works_are_moved_before_the_loser_is_deleted():
    """Work.composer is CASCADE. Deleting a loser with works still attached would delete
    the works — the worst possible outcome of a 'cleanup'."""
    undated = _dupe(birth_year=None)
    dated = _dupe(birth_year=1979)
    for i in range(4):
        WorkFactory(composer=undated, title=f'Fragile Work {i}')

    call_command('merge_duplicate_composers', apply=True)

    assert Work.objects.filter(title__startswith='Fragile Work').count() == 4
    assert Composer.objects.get(pk=dated.pk).works.count() == 4


def test_fills_gaps_on_the_winner_from_the_loser():
    undated = _dupe(birth_year=None, biography='A useful biography')
    _dupe(birth_year=1979, biography=None)

    call_command('merge_duplicate_composers', apply=True)

    survivor = Composer.objects.get(name_normalized='adams, chris')
    assert survivor.birth_year == 1979
    assert survivor.biography == 'A useful biography'
    assert not Composer.objects.filter(pk=undated.pk).exists()


def test_pending_suggestions_follow_the_winner():
    """related_composer is SET_NULL, so a suggestion would silently detach on delete."""
    undated = _dupe(birth_year=None)
    dated = _dupe(birth_year=1979)
    s = UserSuggestion.objects.create(suggestion_type='edit_composer', title='x',
                                      description='y', related_composer=undated)

    call_command('merge_duplicate_composers', apply=True)

    s.refresh_from_db()
    assert s.related_composer_id == dated.id


# --------------------------------------------------------------------------
# The cases that must NOT merge
# --------------------------------------------------------------------------

def test_refuses_two_different_people_with_the_same_name():
    """prod: anelli, giuseppe  b1787/d1865 | b1873/d1926.

    Two humans. Merging them is the single worst thing this command could do, and the
    'same name = same person' shortcut is exactly what would cause it.
    """
    a = _dupe('Anelli, Giuseppe', birth_year=1787, death_year=1865)
    b = _dupe('Anelli, Giuseppe', birth_year=1873, death_year=1926)
    WorkFactory(composer=a, title='Elder Work')
    WorkFactory(composer=b, title='Younger Work')

    call_command('merge_duplicate_composers', apply=True)

    assert Composer.objects.filter(name_normalized='anelli, giuseppe').count() == 2
    assert Composer.objects.get(pk=a.pk).works.count() == 1
    assert Composer.objects.get(pk=b.pk).works.count() == 1


def test_refuses_a_merge_that_would_produce_impossible_dates():
    """prod: beischer-matyo, tamas  b1972/d- | b-/d1972.

    Without --repair this stays refused: unioning the fields would record him as born and
    dead in 1972.
    """
    _dupe('Beischer-Matyo, Tamas', birth_year=1972, death_year=None, is_living=True)
    _dupe('Beischer-Matyo, Tamas', birth_year=None, death_year=1972)

    call_command('merge_duplicate_composers', apply=True)

    assert Composer.objects.filter(name_normalized='beischer-matyo, tamas').count() == 2


def test_refuses_an_undated_row_when_several_people_could_own_it():
    """prod: diaz, rafael  b-(17w) | b1943(15w) | b1965(1w).

    Two real people plus an undated row. Without evidence, which one owns the 17 works is
    not decidable, and guessing would misattribute them.
    """
    _dupe('Nodata, Ambiguous', birth_year=None)
    _dupe('Nodata, Ambiguous', birth_year=1943)
    _dupe('Nodata, Ambiguous', birth_year=1965)

    call_command('merge_duplicate_composers', apply=True)

    assert Composer.objects.filter(name_normalized='nodata, ambiguous').count() == 3


def test_merges_rows_that_share_a_birth_year_and_leaves_a_third_person_alone():
    """Three rows, two of them one person: bucket by birth year and merge within buckets,
    never across them."""
    a = _dupe('Trio, Test', birth_year=1943)
    b = _dupe('Trio, Test', birth_year=1943)
    other = _dupe('Trio, Test', birth_year=1965)
    WorkFactory(composer=a, title='A work')
    WorkFactory(composer=b, title='B work')
    WorkFactory(composer=other, title='Other work')

    call_command('merge_duplicate_composers', apply=True)

    rows = Composer.objects.filter(name_normalized='trio, test')
    assert rows.count() == 2                               # 1943 pair merged, 1965 kept
    assert Composer.objects.get(pk=other.pk).works.count() == 1
    assert rows.get(birth_year=1943).works.count() == 2


# --------------------------------------------------------------------------
# --repair
# --------------------------------------------------------------------------

def test_repair_fixes_a_birth_year_parsed_into_death_year_then_merges():
    """prod: kan-no shigeru b1959/Japan/living(16w) | b-/d1959(7w).

    The other row says he is ALIVE, so 1959 cannot be a death year — it's his birth year
    in the wrong column. Derived from the data, not from recognising the name.
    """
    living = _dupe('Kan-no, Shigeru', birth_year=1959, death_year=None, is_living=True)
    broken = _dupe('Kan-no, Shigeru', birth_year=None, death_year=1959)
    WorkFactory(composer=living, title='Live Work')
    WorkFactory(composer=broken, title='Misparsed Work')

    call_command('merge_duplicate_composers', apply=True, repair=True)

    survivors = Composer.objects.filter(name_normalized='kan-no, shigeru')
    assert survivors.count() == 1
    s = survivors.get()
    assert s.birth_year == 1959
    assert s.death_year is None, 'the misparsed death year must be cleared, not merged in'
    assert s.works.count() == 2


def test_repair_does_not_resurrect_a_genuinely_dead_composer():
    """The rule requires the other row to say is_living. A real death year that happens to
    equal another row's birth year must not be wiped."""
    _dupe('Dead, Composer', birth_year=1900, death_year=None, is_living=False)
    _dupe('Dead, Composer', birth_year=None, death_year=1900)

    call_command('merge_duplicate_composers', apply=True, repair=True)

    assert Composer.objects.filter(name_normalized='dead, composer').count() == 2


def test_repair_applies_the_researched_llobet_correction():
    """prod: llobet, miguel b1878/d1938(9w) | b1875/d1938(12w). 1878 is correct."""
    right = _dupe('Llobet, Miguel', birth_year=1878, death_year=1938)
    wrong = _dupe('Llobet, Miguel', birth_year=1875, death_year=1938)
    WorkFactory(composer=right, title='IMSLP Llobet')
    WorkFactory(composer=wrong, title='Sheerpluck Llobet')

    call_command('merge_duplicate_composers', apply=True, repair=True)

    survivors = Composer.objects.filter(name_normalized='llobet, miguel')
    assert survivors.count() == 1
    assert survivors.get().birth_year == 1878
    assert survivors.get().works.count() == 2


def test_repair_attaches_diaz_undated_works_to_the_spaniard_only():
    """The undated 'Letra B/I/X' are movements of the b.1943 Spaniard's 'Abecedario'.
    The b.1965 Chilean is a different person and must survive untouched.

    Mirrors prod: the undated row is IMSLP's (no country), the dated ones are
    Sheerpluck's (country set) — so the better-identified row wins.
    """
    spain = CountryFactory(name='Spain')
    chile = CountryFactory(name='Chile')
    # ComposerFactory gives every composer a country by default, so the IMSLP row has to
    # opt out to match prod — that emptiness is precisely what makes it the loser.
    undated = _dupe('Diaz, Rafael', birth_year=None, country=None, first_name=None)
    spaniard = _dupe('Diaz, Rafael', birth_year=1943, country=spain)
    chilean = _dupe('Diaz, Rafael', birth_year=1965, country=chile)
    WorkFactory(composer=undated, title='Letra X')
    WorkFactory(composer=spaniard, title='Abecedario para Guitarra')
    WorkFactory(composer=chilean, title='Chilean Work')

    call_command('merge_duplicate_composers', apply=True, repair=True)

    rows = Composer.objects.filter(name_normalized='diaz, rafael')
    assert rows.count() == 2
    # The Spaniard's row survives — it identifies the person; the undated row didn't.
    assert Composer.objects.get(pk=spaniard.pk).works.count() == 2
    assert Composer.objects.get(pk=chilean.pk).works.count() == 1
    assert not Composer.objects.filter(pk=undated.pk).exists()


def test_repair_still_refuses_two_different_people():
    """--repair must not become a licence to merge Anelli 1787 into Anelli 1873."""
    _dupe('Anelli, Giuseppe', birth_year=1787, death_year=1865)
    _dupe('Anelli, Giuseppe', birth_year=1873, death_year=1926)

    call_command('merge_duplicate_composers', apply=True, repair=True)

    assert Composer.objects.filter(name_normalized='anelli, giuseppe').count() == 2


def test_refuses_when_neither_row_has_dates():
    """Nothing distinguishes them — but nothing identifies them either."""
    _dupe('Nameless, Pair', birth_year=None)
    _dupe('Nameless, Pair', birth_year=None)

    call_command('merge_duplicate_composers', apply=True)

    assert Composer.objects.filter(name_normalized='nameless, pair').count() == 2


# --------------------------------------------------------------------------
# Safety
# --------------------------------------------------------------------------

def test_dry_run_is_the_default_and_writes_nothing():
    undated = _dupe(birth_year=None)
    _dupe(birth_year=1979)
    WorkFactory(composer=undated, title='Still Here')

    call_command('merge_duplicate_composers')   # no --apply

    assert Composer.objects.filter(name_normalized='adams, chris').count() == 2
    assert Work.objects.filter(title='Still Here').exists()


def test_is_idempotent():
    _dupe(birth_year=None)
    _dupe(birth_year=1979)

    call_command('merge_duplicate_composers', apply=True)
    call_command('merge_duplicate_composers', apply=True)

    assert Composer.objects.filter(name_normalized='adams, chris').count() == 1
