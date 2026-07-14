"""
URL configuration for the music API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CountryViewSet, InstrumentationCategoryViewSet, DataSourceViewSet,
    ComposerViewSet, WorkViewSet, TagViewSet, StatsViewSet, UserSuggestionViewSet
)
from .admin_views import update_all_is_living

# Create router and register viewsets
router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'instrumentations', InstrumentationCategoryViewSet, basename='instrumentation')
router.register(r'sources', DataSourceViewSet, basename='source')
router.register(r'composers', ComposerViewSet, basename='composer')
router.register(r'works', WorkViewSet, basename='work')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'stats', StatsViewSet, basename='stats')
router.register(r'suggestions', UserSuggestionViewSet, basename='suggestion')

urlpatterns = [
    # Auth is handled entirely by Cognito in the SPA (bearer tokens validated
    # per-request via CognitoJWTAuthentication); no backend auth endpoints.

    # Admin maintenance endpoints
    path('admin/update-is-living/', update_all_is_living, name='update-is-living'),
    
    # API endpoints
    path('', include(router.urls)),
]
