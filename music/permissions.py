"""
Custom permissions for admin operations.

Admin access is granted to authenticated Cognito users who are members of the
``admins`` group (see music.cognito_auth). Reads remain public.
"""
from rest_framework import permissions

ADMIN_GROUP = 'admins'


def is_cognito_admin(request):
    """True if the request carries a valid Cognito token in the ``admins`` group."""
    user = getattr(request, 'user', None)
    return bool(
        user
        and getattr(user, 'is_authenticated', False)
        and ADMIN_GROUP in getattr(user, 'groups', [])
    )


class IsCognitoAdmin(permissions.BasePermission):
    """Allow only authenticated Cognito users in the ``admins`` group."""

    def has_permission(self, request, view):
        return is_cognito_admin(request)


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    - Read access (GET, HEAD, OPTIONS): anyone
    - Write access (POST, PUT, PATCH, DELETE): Cognito ``admins`` group only
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_cognito_admin(request)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_cognito_admin(request)
