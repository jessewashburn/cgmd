"""OrderingFilter + the search-relevance override (get_ordering)."""
import pytest

from .factories import ComposerFactory

pytestmark = pytest.mark.django_db


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
