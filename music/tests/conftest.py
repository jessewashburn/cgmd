import pytest
from django.core.cache import cache
from django.db import connection
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _clear_cache():
    """LocMemCache lives for the whole process, so a cached response (e.g. the
    curated instrumentation list) would otherwise leak between tests."""
    cache.clear()
    yield
    cache.clear()

# Guard trigram-only assertions: on SQLite the filter uses the ILIKE fallback,
# so typo-tolerance / similarity-ranking assertions don't apply.
requires_postgres = pytest.mark.skipif(
    connection.vendor != 'postgresql',
    reason='Trigram similarity requires PostgreSQL; SQLite uses the ILIKE fallback.',
)


@pytest.fixture
def api():
    return APIClient()
