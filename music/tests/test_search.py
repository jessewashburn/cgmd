"""TrigramSearchFilter tests — both the PostgreSQL similarity path and the
SQLite ILIKE fallback. Trigram-only (typo tolerance) is guarded by `requires_postgres`."""
import pytest

from .factories import ComposerFactory, WorkFactory
from .conftest import requires_postgres

pytestmark = pytest.mark.django_db


def test_composer_search_matches_by_normalized_name(api):
    # name_normalized strips accents, so an ASCII query finds the accented name on both backends.
    ComposerFactory(full_name='Francisco Tárrega', last_name='Tárrega', first_name='Francisco')
    ComposerFactory(full_name='Fernando Sor', last_name='Sor', first_name='Fernando')

    res = api.get('/api/composers/', {'search': 'Tarrega'})
    assert res.status_code == 200
    names = [c['full_name'] for c in res.data['results']]
    assert 'Francisco Tárrega' in names
    assert 'Fernando Sor' not in names


def test_work_search_matches_title(api):
    composer = ComposerFactory(full_name='Isaac Albéniz', last_name='Albéniz')
    WorkFactory(title='Asturias (Leyenda)', composer=composer)
    WorkFactory(title='Recuerdos de la Alhambra', composer=composer)

    res = api.get('/api/works/', {'search': 'alhambra'})
    assert res.status_code == 200
    titles = [w['title'] for w in res.data['results']]
    assert 'Recuerdos de la Alhambra' in titles
    assert 'Asturias (Leyenda)' not in titles


def test_search_without_manual_ordering_returns_matches(api):
    # With a search term and no ordering param, the viewset returns None ordering and
    # lets the filter rank by relevance. We assert the endpoint stays healthy and matches.
    ComposerFactory(full_name='Mauro Giuliani', last_name='Giuliani')
    res = api.get('/api/composers/', {'search': 'Giuliani'})
    assert res.status_code == 200
    assert any(c['full_name'] == 'Mauro Giuliani' for c in res.data['results'])


@requires_postgres
def test_trigram_is_typo_tolerant(api):
    ComposerFactory(full_name='Francisco Tárrega', last_name='Tárrega', first_name='Francisco')
    res = api.get('/api/composers/', {'search': 'Taregas'})  # misspelled
    assert res.status_code == 200
    assert 'Francisco Tárrega' in [c['full_name'] for c in res.data['results']]
