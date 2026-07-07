"""IsAdminOrReadOnly: anonymous can read, anonymous cannot write."""
import pytest

from .factories import ComposerFactory

pytestmark = pytest.mark.django_db


def test_anonymous_can_read_composers(api):
    assert api.get('/api/composers/').status_code == 200


def test_anonymous_can_read_works(api):
    assert api.get('/api/works/').status_code == 200


def test_anonymous_cannot_create_composer(api):
    res = api.post('/api/composers/', {'full_name': 'Nope', 'last_name': 'Nope'}, format='json')
    assert res.status_code in (401, 403)


def test_anonymous_cannot_delete_composer(api):
    composer = ComposerFactory()
    res = api.delete(f'/api/composers/{composer.id}/')
    assert res.status_code in (401, 403)
