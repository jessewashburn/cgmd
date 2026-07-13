# syntax=docker/dockerfile:1
# Consolidated API image: Django + gunicorn, served behind nginx/CloudFront in prod.
# Postgres runs as a separate container (see docker-compose.yml), co-located on the
# same host so the DB round trip is localhost instead of cross-region.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=cgmd_backend.settings

WORKDIR /app

# curl is used by the compose healthcheck; psycopg2-binary bundles libpq so no build deps.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/docker-entrypoint.sh \
    && adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/staticfiles \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
# 3 gunicorn workers suits a 2-vCPU t4g.small; tune via GUNICORN_WORKERS if needed.
CMD ["sh", "-c", "gunicorn cgmd_backend.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout 60"]
