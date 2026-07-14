"""
DRF authentication for AWS Cognito access tokens.

The React admin app signs in against a Cognito user pool (in-app SRP via Amplify)
and sends the resulting access token as ``Authorization: Bearer <token>``. This
authenticator validates the token's RS256 signature against the pool's JWKS and
checks issuer / expiry / token_use / client_id. Group-based authorization
(``admins``) lives in music.permissions.

No token → returns None (anonymous), so public read endpoints keep working.
"""
import jwt
from jwt import PyJWKClient
from django.conf import settings
from rest_framework import authentication, exceptions


class CognitoUser:
    """Lightweight authenticated principal built from validated token claims."""

    is_authenticated = True
    is_active = True

    def __init__(self, claims):
        self.claims = claims
        self.sub = claims.get('sub')
        self.username = claims.get('username') or claims.get('sub')
        self.groups = claims.get('cognito:groups', []) or []

    def __str__(self):
        return self.username or 'cognito-user'


class CognitoJWTAuthentication(authentication.BaseAuthentication):
    """Validate a Cognito access token from the Authorization: Bearer header."""

    keyword = 'Bearer'
    _jwk_client = None

    @classmethod
    def _get_jwk_client(cls):
        # PyJWKClient caches signing keys in-process; reuse one instance.
        if cls._jwk_client is None:
            cls._jwk_client = PyJWKClient(settings.COGNITO_JWKS_URL, cache_keys=True)
        return cls._jwk_client

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            return None  # No bearer token → anonymous; public reads still work.
        if len(header) != 2:
            raise exceptions.AuthenticationFailed('Invalid Authorization header.')

        token = header[1].decode()
        claims = self._verify(token)
        return (CognitoUser(claims), claims)

    def _verify(self, token):
        if not settings.COGNITO_USER_POOL_ID or not settings.COGNITO_APP_CLIENT_ID:
            raise exceptions.AuthenticationFailed('Cognito authentication is not configured.')
        try:
            signing_key = self._get_jwk_client().get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=['RS256'],
                issuer=settings.COGNITO_ISSUER,
                # Cognito *access* tokens have no `aud`; identity is `client_id` (checked below).
                options={'verify_aud': False},
            )
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed(f'Invalid token: {exc}')

        if claims.get('token_use') != 'access':
            raise exceptions.AuthenticationFailed('Wrong token_use (expected "access").')
        if claims.get('client_id') != settings.COGNITO_APP_CLIENT_ID:
            raise exceptions.AuthenticationFailed('Token client_id mismatch.')
        return claims

    def authenticate_header(self, request):
        return self.keyword
