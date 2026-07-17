"""Test settings must be runnable without a developer's .env.

Regression test for a CI-only failure:

    [WebServer] CommandError: You must set settings.ALLOWED_HOSTS if DEBUG is False.

`settings_test` sets DEBUG = False, which makes Django enforce ALLOWED_HOSTS and makes
`runserver` refuse to start when it is empty. Base settings only populate ALLOWED_HOSTS
from the environment, and `settings.py` calls `load_dotenv()` — so a developer's .env
supplied it locally and the E2E suite passed, while CI (no .env) could not boot the web
server Playwright needs.

The general rule this pins: anything under cgmd_backend/settings_test.py must stand on its
own. A machine-local .env is not part of the contract.
"""
from django.conf import settings


def test_debug_is_off():
    assert settings.DEBUG is False


def test_allowed_hosts_is_populated_without_env():
    """DEBUG=False + empty ALLOWED_HOSTS is exactly what stopped Playwright's Django
    server from starting in CI. This must not depend on the environment."""
    assert settings.ALLOWED_HOSTS, (
        'settings_test sets DEBUG=False, so ALLOWED_HOSTS must be set explicitly there — '
        'relying on the environment means CI (which has no .env) cannot run runserver.'
    )
    assert 'localhost' in settings.ALLOWED_HOSTS
    assert '127.0.0.1' in settings.ALLOWED_HOSTS
    # Django's own test client sends Host: testserver.
    assert 'testserver' in settings.ALLOWED_HOSTS


def test_allowed_hosts_is_not_a_wildcard():
    """'*' would satisfy runserver but disable host validation everywhere the tests run,
    so the suite would stop noticing if the real setting regressed."""
    assert '*' not in settings.ALLOWED_HOSTS
