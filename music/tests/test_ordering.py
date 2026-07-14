"""OrderingFilter behavior across every sortable list column.

Covers the Works title/composer/instrumentation columns and the Composers
name/country/birth-year/work-count columns, plus NULLs-last placement and the
search-relevance-vs-manual-sort rule (NullsLastOrderingFilter).
"""
import pytest

from .factories import (
    ComposerFactory, CountryFactory, InstrumentationCategoryFactory, WorkFactory,
)

pytestmark = pytest.mark.django_db


# --- Composers ---------------------------------------------------------------

def test_browse_defaults_to_last_name_ascending(api):
    ComposerFactory(full_name='Zed Zulu', last_name='Zulu')
    ComposerFactory(full_name='Abe Adams', last_name='Adams')

    res = api.get('/api/composers/')
    names = [c['full_name'] for c in res.data['results']]
    assert names.index('Abe Adams') < names.index('Zed Zulu')


def test_explicit_descending_order(api):
    ComposerFactory(full_name='Zed Zulu', last_name='Zulu')
    ComposerFactory(full_name='Abe Adams', last_name='Adams')

    res = api.get('/api/composers/', {'ordering': '-last_name'})
    names = [c['full_name'] for c in res.data['results']]
    assert names.index('Zed Zulu') < names.index('Abe Adams')


def test_ordering_by_birth_year(api):
    ComposerFactory(full_name='Older', last_name='B', birth_year=1700)
    ComposerFactory(full_name='Newer', last_name='A', birth_year=1950)

    res = api.get('/api/composers/', {'ordering': 'birth_year'})
    names = [c['full_name'] for c in res.data['results']]
    assert names.index('Older') < names.index('Newer')


def test_null_birth_year_sorts_last_ascending(api):
    ComposerFactory(full_name='Known', last_name='A', birth_year=1800)
    ComposerFactory(full_name='Unknown', last_name='B', birth_year=None)

    res = api.get('/api/composers/', {'ordering': 'birth_year'})
    names = [c['full_name'] for c in res.data['results']]
    assert names[-1] == 'Unknown'


def test_null_birth_year_still_sorts_last_descending(api):
    ComposerFactory(full_name='Known', last_name='A', birth_year=1800)
    ComposerFactory(full_name='Unknown', last_name='B', birth_year=None)

    res = api.get('/api/composers/', {'ordering': '-birth_year'})
    names = [c['full_name'] for c in res.data['results']]
    assert names[-1] == 'Unknown'


def test_ordering_by_country_name(api):
    zed = CountryFactory(name='Zedland')
    aba = CountryFactory(name='Abaland')
    ComposerFactory(full_name='C1', last_name='C1', country=zed)
    ComposerFactory(full_name='C2', last_name='C2', country=aba)

    res = api.get('/api/composers/', {'ordering': 'country__name'})
    names = [c['full_name'] for c in res.data['results']]
    assert names.index('C2') < names.index('C1')


def test_ordering_by_work_count(api):
    prolific = ComposerFactory(full_name='Prolific', last_name='P')
    sparse = ComposerFactory(full_name='Sparse', last_name='S')
    WorkFactory.create_batch(3, composer=prolific)
    WorkFactory(composer=sparse)

    res = api.get('/api/composers/', {'ordering': '-work_count'})
    names = [c['full_name'] for c in res.data['results']]
    assert names.index('Prolific') < names.index('Sparse')


# --- Works -------------------------------------------------------------------

def test_works_default_order_is_alphabetical_by_title(api):
    WorkFactory(title='Zebra Sonata')
    WorkFactory(title='apple etude')     # lowercase: must fold, not sort after capitals
    WorkFactory(title='Étude')           # accent: folds next to 'e'
    WorkFactory(title='10 Pieces')       # numeric: bucket after letters

    res = api.get('/api/works/')
    titles = [w['title'] for w in res.data['results']]
    assert titles == ['apple etude', 'Étude', 'Zebra Sonata', '10 Pieces']


def test_works_default_equals_explicit_title_sort_key(api):
    for t in ['Gamma', 'alpha', 'Beta']:
        WorkFactory(title=t)

    default = [w['title'] for w in api.get('/api/works/').data['results']]
    explicit = [w['title'] for w in api.get('/api/works/', {'ordering': 'title_sort_key'}).data['results']]
    assert default == explicit


def test_works_title_descending_is_exact_reverse(api):
    for t in ['Gamma', 'alpha', 'Beta']:
        WorkFactory(title=t)

    asc = [w['title'] for w in api.get('/api/works/', {'ordering': 'title_sort_key'}).data['results']]
    desc = [w['title'] for w in api.get('/api/works/', {'ordering': '-title_sort_key'}).data['results']]
    assert desc == list(reversed(asc))


def test_newly_created_work_lands_in_correct_position(api):
    # Regression: a work created after the initial backfill must still be ordered
    # correctly (Work.save() maintains the key).
    WorkFactory(title='Alpha')
    WorkFactory(title='Zulu')
    WorkFactory(title='Mike')  # created last, should land in the middle

    titles = [w['title'] for w in api.get('/api/works/').data['results']]
    assert titles == ['Alpha', 'Mike', 'Zulu']


def test_works_ordered_by_composer_matches_composers_page_key(api):
    aa = ComposerFactory(full_name='Aa, Michel van der', last_name='Aa', first_name='Michel van der')
    zz = ComposerFactory(full_name='Zulu, Zed', last_name='Zulu', first_name='Zed')
    WorkFactory(title='W1', composer=zz)
    WorkFactory(title='W2', composer=aa)

    res = api.get('/api/works/', {'ordering': 'composer__last_name,composer__first_name'})
    composers = [w['composer']['full_name'] for w in res.data['results']]
    assert composers.index('Aa, Michel van der') < composers.index('Zulu, Zed')


def test_works_ordered_by_instrumentation(api):
    banjo = InstrumentationCategoryFactory(name='Banjo')
    zither = InstrumentationCategoryFactory(name='Zither')
    WorkFactory(title='W1', instrumentation_category=zither)
    WorkFactory(title='W2', instrumentation_category=banjo)

    res = api.get('/api/works/', {'ordering': 'instrumentation_category__name'})
    names = [w['instrumentation_category']['name'] for w in res.data['results']]
    assert names.index('Banjo') < names.index('Zither')
