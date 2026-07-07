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
