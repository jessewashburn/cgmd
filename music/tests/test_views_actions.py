"""Endpoint smoke tests: list/detail, subresources, and custom @actions."""
import pytest

from .factories import ComposerFactory, WorkFactory

pytestmark = pytest.mark.django_db


def test_composers_list(api):
    ComposerFactory()
    res = api.get('/api/composers/')
    assert res.status_code == 200
    assert 'results' in res.data


def test_works_list(api):
    WorkFactory()
    res = api.get('/api/works/')
    assert res.status_code == 200
    assert 'results' in res.data


def test_composer_detail(api):
    composer = ComposerFactory(full_name='Detail Composer')
    res = api.get(f'/api/composers/{composer.id}/')
    assert res.status_code == 200
    assert res.data['full_name'] == 'Detail Composer'


def test_work_detail(api):
    work = WorkFactory(title='Detail Work')
    res = api.get(f'/api/works/{work.id}/')
    assert res.status_code == 200
    assert res.data['title'] == 'Detail Work'


def test_composer_works_subresource(api):
    composer = ComposerFactory()
    WorkFactory(composer=composer, title='Sub Work')
    res = api.get(f'/api/composers/{composer.id}/works/')
    assert res.status_code == 200


def test_composers_by_period(api):
    ComposerFactory(period='Romantic')
    res = api.get('/api/composers/by_period/', {'period': 'Romantic'})
    assert res.status_code == 200


def test_works_popular(api):
    WorkFactory()
    res = api.get('/api/works/popular/')
    assert res.status_code == 200


def test_works_recent(api):
    WorkFactory()
    res = api.get('/api/works/recent/')
    assert res.status_code == 200


def test_work_search_action(api):
    WorkFactory(title='Searchable Work')
    res = api.get('/api/works/search/', {'q': 'Searchable'})
    assert res.status_code == 200
