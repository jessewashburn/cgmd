"""?instrumentation= matches primary *or* alternate, without breaking the table.

The filter widening is easy; the two things that could go wrong are subtle and are
what these tests actually guard:

  1. Matching a multi-valued relation with a join duplicates rows, which corrupts the
     paginated count *and* the sortable instrumentation column (`ordering_fields`
     includes instrumentation_category__name). Hence EXISTS.
  2. A facet count that ignores alternates would understate its own filter's results.

See SDD: alternate-work-instrumentations.
"""
import pytest

from music.models import InstrumentationCategory, WorkInstrumentation
from .factories import ComposerFactory, WorkFactory

pytestmark = pytest.mark.django_db


def alt(work, name, basis='derived'):
    category, _ = InstrumentationCategory.objects.get_or_create(name=name)
    return WorkInstrumentation.objects.create(work=work, category=category, basis=basis)


def test_filter_finds_a_work_by_its_alternate(api):
    """The driving case: written for guitar and tape, playable by 5 guitars. Someone
    filtering Quintet wants it."""
    work = WorkFactory(title='In Realms of Passing Dreams',
                       instrumentation_detail='Guitar and Tape (or 5 Guitars)')
    assert work.instrumentation_category.name == 'Guitar with Electronics'
    alt(work, 'Quintet')

    res = api.get('/api/works/', {'instrumentation': 'Quintet'})
    assert [w['title'] for w in res.data['results']] == ['In Realms of Passing Dreams']


def test_filter_still_finds_it_by_its_primary(api):
    work = WorkFactory(title='Realms', instrumentation_detail='Guitar and Tape (or 5 Guitars)')
    alt(work, 'Quintet')

    res = api.get('/api/works/', {'instrumentation': 'Guitar with Electronics'})
    assert [w['title'] for w in res.data['results']] == ['Realms']


def test_a_work_matching_both_ways_appears_once(api):
    """The row-duplication regression EXISTS exists to prevent. A join + .distinct()
    here would still inflate `count` under an ORDER BY on the joined column."""
    work = WorkFactory(title='Both', instrumentation_detail='Solo')
    alt(work, 'Solo')  # degenerate: alternate == primary

    res = api.get('/api/works/', {'instrumentation': 'Solo'})
    assert res.data['count'] == 1
    assert [w['title'] for w in res.data['results']] == ['Both']


def test_sorting_by_instrumentation_is_not_duplicated_by_alternates(api):
    """`ordering=instrumentation_category__name` over a multi-valued join returns a
    row per join match. One work must stay one row."""
    work = WorkFactory(title='Multi', instrumentation_detail='Solo')
    alt(work, 'Quintet')
    alt(work, 'Quartet')
    WorkFactory(title='Plain', instrumentation_detail='Duo')

    res = api.get('/api/works/', {'ordering': 'instrumentation_category__name'})
    titles = [w['title'] for w in res.data['results']]
    assert sorted(titles) == ['Multi', 'Plain']
    assert res.data['count'] == 2


def test_unknown_filter_term_still_matches_nothing(api):
    work = WorkFactory(title='Anything', instrumentation_detail='Solo')
    alt(work, 'Quintet')

    res = api.get('/api/works/', {'instrumentation': 'zzzznonsense'})
    assert res.data['count'] == 0


def test_composer_filter_follows_alternates(api):
    """/composers/?instrumentation= must agree with /works/ — a composer whose work is
    merely *playable* as a quintet still belongs in the result."""
    composer = ComposerFactory(full_name='Chase, Jordan', last_name='Chase',
                               first_name='Jordan')
    work = WorkFactory(title='Realms', composer=composer,
                       instrumentation_detail='Guitar and Tape (or 5 Guitars)')
    alt(work, 'Quintet')
    other = ComposerFactory(full_name='Someone, Else', last_name='Someone')
    WorkFactory(title='Unrelated', composer=other, instrumentation_detail='Duo')

    res = api.get('/api/composers/', {'instrumentation': 'Quintet'})
    assert [c['full_name'] for c in res.data['results']] == ['Chase, Jordan']


def test_detail_serializer_exposes_alternates(api):
    work = WorkFactory(title='Realms', instrumentation_detail='Guitar and Tape (or 5 Guitars)')
    alt(work, 'Quintet')

    res = api.get(f'/api/works/{work.id}/')
    names = [a['name'] for a in res.data['alternate_instrumentations']]
    assert names == ['Quintet']
    # The primary is unchanged and still the work's own category.
    assert res.data['instrumentation_category']['name'] == 'Guitar with Electronics'


def test_work_without_alternates_serializes_an_empty_list(api):
    work = WorkFactory(title='Plain', instrumentation_detail='Solo')
    res = api.get(f'/api/works/{work.id}/')
    assert res.data['alternate_instrumentations'] == []
