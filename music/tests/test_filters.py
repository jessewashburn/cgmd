"""Filter param contract — pins the exact query-param names the frontend sends."""
import pytest

from .factories import ComposerFactory, WorkFactory, CountryFactory

pytestmark = pytest.mark.django_db


def test_composer_country_name_filter(api):
    spain = CountryFactory(name='Spain')
    france = CountryFactory(name='France')
    ComposerFactory(full_name='Spanish One', last_name='Uno', country=spain)
    ComposerFactory(full_name='French One', last_name='Deux', country=france)

    res = api.get('/api/composers/', {'country_name': 'Spain'})
    names = [c['full_name'] for c in res.data['results']]
    assert 'Spanish One' in names
    assert 'French One' not in names


def test_composer_birth_year_range_filter(api):
    ComposerFactory(full_name='Old Master', last_name='Old', birth_year=1700)
    ComposerFactory(full_name='Romantic', last_name='Mid', birth_year=1850)

    res = api.get('/api/composers/', {'birth_year_min': 1800, 'birth_year_max': 1900})
    names = [c['full_name'] for c in res.data['results']]
    assert 'Romantic' in names
    assert 'Old Master' not in names


def test_works_composer_country_and_birth_year_contract(api):
    spain = CountryFactory(name='Spain')
    france = CountryFactory(name='France')
    spanish = ComposerFactory(last_name='Sp', country=spain, birth_year=1852)
    french = ComposerFactory(last_name='Fr', country=france, birth_year=1700)
    WorkFactory(title='Spanish Work', composer=spanish)
    WorkFactory(title='French Work', composer=french)

    res = api.get('/api/works/', {
        'composer_country': 'Spain',
        'composer_birth_year_min': 1800,
        'composer_birth_year_max': 1900,
    })
    titles = [w['title'] for w in res.data['results']]
    assert 'Spanish Work' in titles
    assert 'French Work' not in titles


def test_works_combined_year_filter_falls_back_to_composition_year(api):
    """year_min/year_max match composer birth year, falling back to composition
    year only when the composer has no birth year on record."""
    no_birth = ComposerFactory(last_name='NoDob', birth_year=None)
    born_1850 = ComposerFactory(last_name='Old', birth_year=1850)
    born_1950 = ComposerFactory(last_name='Living', birth_year=1950)

    # Included via composition-year fallback (composer birth year unknown).
    WorkFactory(title='Fallback Hit', composer=no_birth, composition_year=2006)
    # Excluded: composer born 1850 is primary; 2006 composition year is ignored.
    WorkFactory(title='Birth Year Wins', composer=born_1850, composition_year=2006)
    # Included on birth year even though composed long before the range.
    WorkFactory(title='Birth In Range', composer=born_1950, composition_year=1600)
    # Excluded: fallback composition year out of range.
    WorkFactory(title='Fallback Miss', composer=no_birth, composition_year=1600)

    res = api.get('/api/works/', {'year_min': 1900, 'year_max': 2007})
    titles = [w['title'] for w in res.data['results']]
    assert 'Fallback Hit' in titles
    assert 'Birth In Range' in titles
    assert 'Birth Year Wins' not in titles
    assert 'Fallback Miss' not in titles
