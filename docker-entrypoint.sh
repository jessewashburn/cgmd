#!/bin/sh
# Container entrypoint: wait for Postgres, apply migrations (creates schema, the
# pg_trgm extension, and GIN trigram indexes via migration 0004), collect static,
# then hand off to gunicorn (the image CMD).
set -e

echo "Waiting for database at ${DB_HOST:-db}:${DB_PORT:-5432}..."
python - <<'PY'
import os, sys, time
import psycopg2

cfg = dict(
    host=os.getenv("DB_HOST", "db"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "postgres"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", ""),
)
for _ in range(60):
    try:
        psycopg2.connect(connect_timeout=3, **cfg).close()
        print("Database is up.")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001 - any connection error means "not ready yet"
        print(f"  ...not ready ({exc.__class__.__name__}); retrying in 2s")
        time.sleep(2)
print("Database did not become ready in time.", file=sys.stderr)
sys.exit(1)
PY

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

exec "$@"
