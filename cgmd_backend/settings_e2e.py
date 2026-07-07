"""
Settings for Playwright E2E runs.

Local default: a SQLite *file* (not :memory:) so the seed command, the Django
server process, and the tests all share one database. CI sets USE_POSTGRES_TEST=1
(and TEST_DB_* env) to run against a throwaway Postgres for full trigram parity.
"""
import os

from .settings_test import *  # noqa: F401,F403
from .settings import BASE_DIR  # noqa: E402

if os.getenv('USE_POSTGRES_TEST') != '1':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db_e2e.sqlite3'),
        }
    }

# The E2E frontend runs on the Vite dev server.
CORS_ALLOW_ALL_ORIGINS = True
