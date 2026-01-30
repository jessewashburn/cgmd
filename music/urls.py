"""
URL configuration for the music API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CountryViewSet, InstrumentationCategoryViewSet, DataSourceViewSet,
    ComposerViewSet, WorkViewSet, TagViewSet, StatsViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'instrumentations', InstrumentationCategoryViewSet, basename='instrumentation')
router.register(r'sources', DataSourceViewSet, basename='source')
router.register(r'composers', ComposerViewSet, basename='composer')
router.register(r'works', WorkViewSet, basename='work')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'stats', StatsViewSet, basename='stats')

urlpatterns = [
    path('', include(router.urls)),
]
