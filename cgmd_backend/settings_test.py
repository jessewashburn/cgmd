"""
Test settings.

Local default: in-memory SQLite — fast and requires no external DB. This
exercises the TrigramSearchFilter's non-PostgreSQL ILIKE fallback path.
Production is the `db` PostgreSQL 17 container on the EC2 host (see
AWS_DEPLOYMENT.md); tests must NEVER run against it.

CI (or anyone wanting the real trigram path) sets USE_POSTGRES_TEST=1 and the
TEST_DB_* env vars to point at a throwaway local Postgres. Trigram-only
assertions are guarded by the `requires_postgres` marker so the suite still
passes end-to-end under SQLite.
"""
import os

from .settings import *  # noqa: F401,F403

if os.getenv('USE_POSTGRES_TEST') == '1':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('TEST_DB_NAME', 'cgmd_test'),
            'USER': os.getenv('TEST_DB_USER', 'postgres'),
            'PASSWORD': os.getenv('TEST_DB_PASSWORD', 'postgres'),
            'HOST': os.getenv('TEST_DB_HOST', 'localhost'),
            'PORT': os.getenv('TEST_DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

# Speed: cheap hasher, no debug.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
DEBUG = False

# DEBUG = False makes Django enforce ALLOWED_HOSTS, and `runserver` refuses to boot when
# it's empty: "CommandError: You must set settings.ALLOWED_HOSTS if DEBUG is False."
#
# Base settings only ever populate ALLOWED_HOSTS from the environment, and settings.py
# calls load_dotenv(), so a developer's .env silently supplied it locally while CI — which
# has no .env — got [] and could not start the E2E web server. Test settings must not
# depend on a machine's .env to be runnable, so pin it here, next to the DEBUG that
# requires it.
#
# 'testserver' is the host Django's own test client sends.
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'testserver']
