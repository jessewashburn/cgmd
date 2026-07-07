"""LargeResultsSetPagination: {count, next, previous, results} shape + page_size."""
import pytest

from .factories import ComposerFactory, WorkFactory

pytestmark = pytest.mark.django_db


def test_pagination_shape_and_page_size(api):
    composer = ComposerFactory()
    WorkFactory.create_batch(60, composer=composer)

    res = api.get('/api/works/', {'page_size': 50})
    assert res.status_code == 200
    assert res.data['count'] == 60
    assert len(res.data['results']) == 50
    assert res.data['next'] is not None
    assert res.data['previous'] is None


def test_second_page(api):
    composer = ComposerFactory()
    WorkFactory.create_batch(60, composer=composer)

    res = api.get('/api/works/', {'page_size': 50, 'page': 2})
    assert res.status_code == 200
    assert len(res.data['results']) == 10
    assert res.data['previous'] is not None
    assert res.data['next'] is None


def test_non_public_works_excluded(api):
    composer = ComposerFactory()
    WorkFactory(title='Public Work', composer=composer, is_public=True)
    WorkFactory(title='Hidden Work', composer=composer, is_public=False)

    res = api.get('/api/works/', {'page_size': 100})
    titles = [w['title'] for w in res.data['results']]
    assert 'Public Work' in titles
    assert 'Hidden Work' not in titles
