"""Alternate realizations: splitting "(or ...)" out of instrumentation detail.

A detail string can describe more than one way to play a work. `split_realizations`
separates the notated (primary) realization from the alternates so each resolves on
its own — which fixes the primary *and* earns the alternate a category of its own.

The bug being pinned here is real and was measured across the catalogue: 360 works
(19.6% of the 1,833 carrying an alternate) were filed under their *alternate's*
bucket because the resolver read the whole string at once.

See SDD: alternate-work-instrumentations.
"""
import pytest

from music.models import InstrumentationCategory, Work
from music.utils import (
    UNCATEGORIZED_INSTRUMENTATION,
    alternate_instrumentation_names,
    canonical_instrumentation,
    primary_instrumentation,
    split_realizations,
)
from .factories import WorkFactory


# --- split_realizations ------------------------------------------------------

def test_no_parenthetical_leaves_the_string_alone():
    """~71k works carry no alternate. They must not touch this code path's output."""
    assert split_realizations('Chamber Music: flute, guitar') == (
        'Chamber Music: flute, guitar', [])
    assert split_realizations('Solo') == ('Solo', [])


def test_blank_detail():
    assert split_realizations('') == ('', [])
    assert split_realizations(None) == ('', [])


def test_alternate_substitutes_the_instrument_it_follows():
    primary, alternates = split_realizations('guitar, violin (or flute)')
    assert primary == 'guitar, violin'
    assert alternates == ['guitar, flute']


def test_two_word_instrument_name_is_substituted_whole():
    """"bass guitar (or double bass)" swaps the instrument, not just its last word."""
    primary, alternates = split_realizations('mandolin, bass guitar (or double bass)')
    assert primary == 'mandolin, bass guitar'
    assert alternates == ['mandolin, double bass']


def test_unparseable_shape_yields_no_alternate_rather_than_a_guess():
    """"guitar (4) (or clarinet, guitar)" has a parenthetical between the instrument
    and the alternate, so the substitution can't be read. Emit nothing — a wrong
    alternate is worse than a missing one."""
    primary, alternates = split_realizations('Quartet: guitar (4) (or clarinet, guitar)')
    assert primary == 'Quartet: guitar (4)'
    assert alternates == []


# --- the 360-work bug: the alternate outranked the primary -------------------

@pytest.mark.parametrize('detail, expected_primary, blob_answer', [
    # (detail, correct primary, what reading the whole blob used to return)
    ('guitar, violin (or flute)', 'Guitar and Violin', 'Guitar and Flute'),
    ('2 bandurrias (or mandolins), guitar', 'Duo', 'Guitar and Mandolin'),
    ('Quartet: guitar (4) (or clarinet, guitar)', 'Quartet', 'Guitar and Clarinet'),
])
def test_primary_ignores_the_alternate(detail, expected_primary, blob_answer):
    assert primary_instrumentation(detail) == expected_primary
    # Pin the old behaviour too, so this test explains itself if it ever regresses.
    assert canonical_instrumentation(detail) == blob_answer


# --- alternate_instrumentation_names: deliberately conservative --------------

def test_alternate_earns_its_own_category():
    assert alternate_instrumentation_names('guitar, violin (or flute)') == ['Guitar and Flute']


def test_alternate_in_the_same_bucket_is_dropped():
    """Two-thirds of real alternates resolve to the primary's own bucket. A second
    category identical to the first is noise in the facet and a lie in the UI."""
    detail = 'Guitar with Fixed Media: guitar - tape (or keyboard synthesizer)'
    assert primary_instrumentation(detail) == 'Guitar with Electronics'
    assert alternate_instrumentation_names(detail) == []


def test_alternate_that_leaves_guitar_repertoire_is_dropped():
    """"soprano - guitar (or piano)" played the alternate way is a piano song. It is
    not guitar repertoire and must not earn a bucket in a guitar catalogue."""
    detail = 'Chamber Music: soprano - guitar (or piano)'
    assert primary_instrumentation(detail) == 'Guitar and Voice'
    assert alternate_instrumentation_names(detail) == []


def test_alternate_never_derives_into_other():
    """'Other' is the "we failed" bucket. A junk parse must produce no row."""
    detail = 'guitar, violin (or zzzznonsense qqqq)'
    assert UNCATEGORIZED_INSTRUMENTATION not in alternate_instrumentation_names(detail)


def test_work_without_alternates_has_none():
    assert alternate_instrumentation_names('Chamber Music: flute, guitar') == []
    assert alternate_instrumentation_names('') == []


# --- the driving work --------------------------------------------------------

def test_in_realms_of_passing_dreams():
    """The work this design came from: guitar + tape, or 5 guitars. Both realizations
    derive with no human input. See work 604946 (Chase, Jordan)."""
    detail = 'Guitar and Tape (or 5 Guitars)'
    assert primary_instrumentation(detail) == 'Guitar with Electronics'
    assert alternate_instrumentation_names(detail) == ['Quintet']


# --- Work.save() applies the primary fix ------------------------------------

@pytest.mark.django_db
def test_save_files_the_work_under_its_primary_not_its_alternate():
    work = WorkFactory(instrumentation_detail='guitar, violin (or flute)')
    assert work.instrumentation_category.name == 'Guitar and Violin'


@pytest.mark.django_db
def test_save_still_derives_when_there_is_no_alternate():
    work = WorkFactory(instrumentation_detail='Chamber Music: flute, guitar')
    assert work.instrumentation_category.name == 'Guitar and Flute'
