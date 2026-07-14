"""
Authentication views.

Login is handled entirely by AWS Cognito (in-app SRP via Amplify in the SPA);
the backend is stateless and only validates the bearer token per request
(see music.cognito_auth). This module exposes a single read-only endpoint the
SPA can use to confirm the current token's identity and admin status.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .permissions import ADMIN_GROUP


@api_view(['GET'])
@permission_classes([AllowAny])
def current_user(request):
    """
    Echo the authenticated Cognito user (from the validated bearer token).

    GET /api/auth/user/
    """
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        groups = getattr(user, 'groups', [])
        return Response({
            'username': getattr(user, 'username', None),
            'groups': groups,
            'is_admin': ADMIN_GROUP in groups,
        })
    return Response(
        {'error': 'Not authenticated'},
        status=status.HTTP_401_UNAUTHORIZED,
    )
