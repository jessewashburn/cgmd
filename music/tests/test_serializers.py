"""Serializer output-shape / contract tests (the frontend depends on these fields)."""
import pytest

from .factories import ComposerFactory, WorkFactory, CountryFactory, InstrumentationCategoryFactory

pytestmark = pytest.mark.django_db


def test_composer_list_serializer_shape(api):
    spain = CountryFactory(name='Spain')
    composer = ComposerFactory(full_name='Shape Composer', last_name='Shape', country=spain)
    WorkFactory(composer=composer, is_public=True)

    res = api.get('/api/composers/', {'search': 'Shape'})
    row = next(c for c in res.data['results'] if c['full_name'] == 'Shape Composer')

    assert set(row.keys()) == {
        'id', 'full_name', 'birth_year', 'death_year',
        'is_living', 'country_name', 'period', 'work_count',
    }
    assert row['country_name'] == 'Spain'
    assert row['work_count'] == 1  # annotated count of public works


def test_work_list_serializer_shape(api):
    inst = InstrumentationCategoryFactory(name='Guitar solo')
    composer = ComposerFactory(full_name='Work Composer', last_name='WComposer')
    WorkFactory(title='Shape Work', composer=composer, instrumentation_category=inst)

    res = api.get('/api/works/', {'search': 'Shape Work'})
    row = next(w for w in res.data['results'] if w['title'] == 'Shape Work')

    assert set(row.keys()) == {
        'id', 'title', 'composer', 'catalog_number', 'composition_year',
        'instrumentation_category', 'instrumentation_detail',
        'duration_minutes', 'difficulty_level',
    }
    assert row['composer'] == {'id': composer.id, 'full_name': 'Work Composer'}
    assert row['instrumentation_category'] == {'id': inst.id, 'name': 'Guitar solo'}
