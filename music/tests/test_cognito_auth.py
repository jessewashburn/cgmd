"""Cognito JWT authentication + admins-group authorization.

Mocks the pool JWKS with a local RSA keypair so we can mint tokens and assert the
authenticator/permission behavior end-to-end without hitting AWS.
"""
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import override_settings

from music.cognito_auth import CognitoJWTAuthentication
from music.models import UserSuggestion

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


def auth(client, token):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


# --- /api/auth/user/ reflects identity + admin status ---------------------

def test_current_user_reports_admin(api):
    res = auth(api, mint(groups=['admins'])).get('/api/auth/user/')
    assert res.status_code == 200
    assert res.data['is_admin'] is True
    assert res.data['username'] == 'admin@example.com'


def test_current_user_non_admin(api):
    res = auth(api, mint(groups=['viewers'])).get('/api/auth/user/')
    assert res.status_code == 200
    assert res.data['is_admin'] is False


def test_current_user_anonymous(api):
    assert api.get('/api/auth/user/').status_code == 401


# --- token validation failures → 401 --------------------------------------

def test_expired_token_rejected(api):
    res = auth(api, mint(exp=int(time.time()) - 10)).get('/api/auth/user/')
    assert res.status_code == 401


def test_wrong_client_id_rejected(api):
    res = auth(api, mint(client_id='someone-else')).get('/api/auth/user/')
    assert res.status_code == 401


def test_id_token_rejected(api):
    # token_use must be "access"
    res = auth(api, mint(token_use='id')).get('/api/auth/user/')
    assert res.status_code == 401


def test_garbage_token_rejected(api):
    res = auth(api, 'not-a-jwt').get('/api/auth/user/')
    assert res.status_code == 401


# --- admin-gated action requires the admins group -------------------------

def _make_suggestion():
    return UserSuggestion.objects.create(
        suggestion_type='edit_work', title='t', description='d',
    )


def test_admin_can_approve_suggestion(api):
    s = _make_suggestion()
    res = auth(api, mint(groups=['admins'])).post(f'/api/suggestions/{s.id}/approve/')
    assert res.status_code == 200
    s.refresh_from_db()
    assert s.status == 'approved'


def test_non_admin_cannot_approve(api):
    s = _make_suggestion()
    res = auth(api, mint(groups=['viewers'])).post(f'/api/suggestions/{s.id}/approve/')
    assert res.status_code == 403


def test_anonymous_cannot_approve(api):
    s = _make_suggestion()
    assert api.post(f'/api/suggestions/{s.id}/approve/').status_code in (401, 403)
