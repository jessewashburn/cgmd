"""Merging composer rows that are one human split by a missing birth year.

Every case below is a real shape from production, not a hypothetical.
"""
import pytest
from django.core.management import call_command

from music.models import Composer, UserSuggestion, Work
from .factories import ComposerFactory, WorkFactory

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

    Same person — his birth year was parsed into death_year on one row. But unioning the
    fields would record him as born and dead in 1972. A parse error, not an identity
    question; a human should fix the row.
    """
    _dupe('Beischer-Matyo, Tamas', birth_year=1972, death_year=None)
    _dupe('Beischer-Matyo, Tamas', birth_year=None, death_year=1972)

    call_command('merge_duplicate_composers', apply=True)

    assert Composer.objects.filter(name_normalized='beischer-matyo, tamas').count() == 2


def test_refuses_three_way_groups():
    """prod: diaz, rafael  b-(17w) | b1943(15w) | b1965(1w).

    Two real people plus an undated row. Which of them owns the 17 undated works is not
    decidable from the data, so guessing would misattribute them.
    """
    _dupe('Diaz, Rafael', birth_year=None)
    _dupe('Diaz, Rafael', birth_year=1943)
    _dupe('Diaz, Rafael', birth_year=1965)

    call_command('merge_duplicate_composers', apply=True)

    assert Composer.objects.filter(name_normalized='diaz, rafael').count() == 3


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
