import pytest
from django.db import connection
from rest_framework.test import APIClient

# Guard trigram-only assertions: on SQLite the filter uses the ILIKE fallback,
# so typo-tolerance / similarity-ranking assertions don't apply.
requires_postgres = pytest.mark.skipif(
    connection.vendor != 'postgresql',
    reason='Trigram similarity requires PostgreSQL; SQLite uses the ILIKE fallback.',
)


@pytest.fixture
def api():
    return APIClient()
