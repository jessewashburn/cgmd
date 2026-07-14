"""Cognito JWT authentication + admins-group authorization.

Mocks the pool JWKS with a local RSA keypair so we can mint tokens and assert the
authenticator/permission behavior without hitting AWS. Token *validation* is tested
against the authenticator directly; *authorization* (admins group) is tested through
a protected endpoint.
"""
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from music.cognito_auth import CognitoJWTAuthentication
from music.models import UserSuggestion, WorkLink
from .factories import WorkFactory

pytestmark = pytest.mark.django_db

ISSUER = 'https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TESTPOOL'
CLIENT_ID = 'test-client-id'

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeKey:
    def __init__(self, key):
        self.key = key


class _FakeJWKClient:
    """Stand-in for PyJWKClient returning our test public key for any token."""
    def get_signing_key_from_jwt(self, token):
        return _FakeKey(_PRIVATE_KEY.public_key())


@pytest.fixture(autouse=True)
def _cognito_settings_and_jwks(monkeypatch):
    monkeypatch.setattr(
        CognitoJWTAuthentication, '_get_jwk_client',
        classmethod(lambda cls: _FakeJWKClient()),
    )
    with override_settings(
        COGNITO_USER_POOL_ID='us-east-1_TESTPOOL',
        COGNITO_APP_CLIENT_ID=CLIENT_ID,
        COGNITO_ISSUER=ISSUER,
    ):
        yield


def mint(groups=('admins',), **overrides):
    now = int(time.time())
    claims = {
        'sub': 'user-123',
        'iss': ISSUER,
        'client_id': CLIENT_ID,
        'token_use': 'access',
        'username': 'admin@example.com',
        'cognito:groups': list(groups),
        'iat': now,
        'exp': now + 3600,
    }
    claims.update(overrides)
    return jwt.encode(claims, _PRIVATE_KEY, algorithm='RS256')


def _authenticate(token):
    request = APIRequestFactory().get('/', HTTP_AUTHORIZATION=f'Bearer {token}')
    return CognitoJWTAuthentication().authenticate(request)


# --- authenticator parses a valid token ------------------------------------

def test_valid_token_yields_user_and_groups():
    user, claims = _authenticate(mint(groups=['admins']))
    assert user.username == 'admin@example.com'
    assert user.groups == ['admins']
    assert claims['sub'] == 'user-123'


def test_no_bearer_is_anonymous():
    request = APIRequestFactory().get('/')
    assert CognitoJWTAuthentication().authenticate(request) is None


# --- token validation failures ---------------------------------------------

@pytest.mark.parametrize('token_kwargs', [
    {'exp': int(time.time()) - 10},        # expired
    {'client_id': 'someone-else'},         # wrong app client
    {'token_use': 'id'},                   # must be an access token
])
def test_invalid_tokens_rejected(token_kwargs):
    with pytest.raises(AuthenticationFailed):
        _authenticate(mint(**token_kwargs))


def test_garbage_token_rejected():
    with pytest.raises(AuthenticationFailed):
        _authenticate('not-a-jwt')


# --- admin-gated action requires the admins group --------------------------

def _make_suggestion():
    return UserSuggestion.objects.create(
        suggestion_type='edit_work', title='t', description='d',
    )


def _approve(api, token=None):
    s = _make_suggestion()
    if token:
        api.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return api.post(f'/api/suggestions/{s.id}/approve/'), s


def test_admin_can_approve_suggestion(api):
    res, s = _approve(api, mint(groups=['admins']))
    assert res.status_code == 200
    s.refresh_from_db()
    assert s.status == 'approved'


def test_non_admin_cannot_approve(api):
    res, _ = _approve(api, mint(groups=['viewers']))
    assert res.status_code == 403


def test_anonymous_cannot_approve(api):
    res, _ = _approve(api)
    assert res.status_code in (401, 403)


# --- apply action: edit_work suggestions update fields + create links -------

def _edit_work_suggestion(work, **suggested):
    return UserSuggestion.objects.create(
        suggestion_type='edit_work', title='edit', description='',
        related_work=work, suggested_data=suggested,
    )


def test_apply_updates_fields_and_creates_links(api):
    work = WorkFactory(title='Old Title', composition_year=None)
    s = _edit_work_suggestion(
        work,
        title='New Title',
        composition_year=2001,
        links=[{'label': 'BCGS Commission', 'url': 'https://bcgs.org', 'link_type': 'commission'}],
    )
    api.credentials(HTTP_AUTHORIZATION=f'Bearer {mint(groups=["admins"])}')
    res = api.post(f'/api/suggestions/{s.id}/apply/')

    assert res.status_code == 200
    assert res.data['links_added'] == 1
    work.refresh_from_db()
    assert work.title == 'New Title'
    assert work.composition_year == 2001
    assert work.links.filter(url='https://bcgs.org', link_type='commission').exists()
    s.refresh_from_db()
    assert s.status == 'merged'


def test_apply_is_idempotent_on_links(api):
    work = WorkFactory()
    s = _edit_work_suggestion(work, links=[{'label': 'X', 'url': 'https://x.com'}])
    api.credentials(HTTP_AUTHORIZATION=f'Bearer {mint(groups=["admins"])}')
    api.post(f'/api/suggestions/{s.id}/apply/')
    second = api.post(f'/api/suggestions/{s.id}/apply/')
    assert second.data['links_added'] == 0
    assert WorkLink.objects.filter(work=work, url='https://x.com').count() == 1


def test_apply_rejects_new_work(api):
    s = UserSuggestion.objects.create(
        suggestion_type='new_work', title='n', description='', suggested_data={'links': []},
    )
    api.credentials(HTTP_AUTHORIZATION=f'Bearer {mint(groups=["admins"])}')
    res = api.post(f'/api/suggestions/{s.id}/apply/')
    assert res.status_code == 400


def test_apply_requires_admin(api):
    work = WorkFactory()
    s = _edit_work_suggestion(work, links=[{'label': 'X', 'url': 'https://x.com'}])
    api.credentials(HTTP_AUTHORIZATION=f'Bearer {mint(groups=["viewers"])}')
    res = api.post(f'/api/suggestions/{s.id}/apply/')
    assert res.status_code == 403
