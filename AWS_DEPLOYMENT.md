# AWS Deployment Guide

> **Architecture (current, as of 2026-07-13):** everything is on AWS. The backend is a
> **Docker Compose stack on a single EC2 instance** (Django + gunicorn, PostgreSQL 17, and
> Caddy for TLS/reverse-proxy — all co-located). The frontend is a **static build in S3 fronted
> by CloudFront**. **There is no Elastic Beanstalk and no Supabase** — both were removed (see the
> `aws-cost-consolidation` SDD). Ignore any `eb ...` commands; `eb status` will say "not found".

## Live environment

| Thing | Value |
|-------|-------|
| Site domain | `www.solmuapp.com` / `solmuapp.com` |
| CloudFront distribution ID | `E23JJN25WLB1B9` |
| CloudFront domain | `djow2c4ppl2zz.cloudfront.net` |
| Frontend S3 bucket | `cgmd-frontend-1770139819` |
| **Backend EC2 instance** | `cgmd-api` — `i-07ce6430cf3cdc27b`, t4g.micro, **`52.205.65.184`** (`us-east-1`) |
| **SSH** | `ssh -i ~/.ssh/cgmd-prod.pem ec2-user@52.205.65.184` (key name `cgmd-prod`, Amazon Linux) |
| **App dir on host** | `/home/ec2-user/cgmd` — **NOT a git checkout** (git is not installed on the host) |
| **Prod compose file** | `docker-compose.prod.yml` (services: `db` postgres:17, `web`, `caddy`) |
| **Containers** | `cgmd-db-1`, `cgmd-web-1`, `cgmd-caddy-1` |
| **Database** | PostgreSQL 17 **in a container on the host** (`db`/`web` env: `DB_NAME=cgmd`, `DB_USER=cgmd`), volume `pgdata`. Not RDS, not Supabase. |

> One CloudFront distribution fronts both origins: `/` → S3 (frontend), `/api` → the EC2 host's
> Caddy → `web:8000`. Bucket name and distribution ID are identifiers, not secrets. Real secrets
> (`SECRET_KEY`, DB password) live in the host-only `/home/ec2-user/cgmd/.env` (gitignored, **never**
> overwrite it during a deploy).

## Backend deploy (Docker on EC2)

> **One command:** `scripts/deploy-backend.sh` does everything below with a DB backup (when
> migrations are pending), a health gate, and a rollback hint on failure. The manual steps
> follow for reference / debugging.

The host has no git and is populated by copying code in, then rebuilding the `web` image
(`build: .`). Its container entrypoint runs `migrate --noinput` + `collectstatic` on start.

**Never overwrite the host `.env`** during a deploy (real secrets live there). The infra files
`docker-compose.prod.yml`, `Caddyfile`, and `backup.sh` are now committed as the canonical copies;
the default deploy still ships **only application code** and does not push them — update the host
copies deliberately (`scp` + `docker compose up -d`) when they actually change.

```bash
# 1) From the local repo (committed HEAD), ship app code to the host. git archive keeps it
#    deterministic and skips untracked/__pycache__. Add paths as needed.
git archive --format=tar HEAD music cgmd_backend requirements.txt Dockerfile docker-entrypoint.sh \
  | ssh -i ~/.ssh/cgmd-prod.pem ec2-user@52.205.65.184 "tar -xf - -C /home/ec2-user/cgmd"

# 2) Rebuild + restart the web container (db/caddy keep running). The entrypoint migrates.
ssh -i ~/.ssh/cgmd-prod.pem ec2-user@52.205.65.184 \
  "cd /home/ec2-user/cgmd && docker compose -f docker-compose.prod.yml up -d --build web"

# 3) Confirm it came up cleanly (look for 'Applying ... OK' and gunicorn 'Listening at').
ssh -i ~/.ssh/cgmd-prod.pem ec2-user@52.205.65.184 "docker logs cgmd-web-1 --tail 20"
```

> ⚠️ **CRLF gotcha (bit us on 2026-07-13):** if `docker-entrypoint.sh` reaches the host with
> Windows CRLF line endings, the container crash-loops with
> `exec /app/docker-entrypoint.sh: no such file or directory` (the `#!/bin/sh` shebang resolves to
> `/bin/sh\r`) — **and `/api` goes down.** This repo's [.gitattributes](.gitattributes) now pins
> `*.sh` to `eol=lf` so `git archive` emits LF. If you ever see the crash loop anyway, fix in place:
> `sed -i 's/\r$//' docker-entrypoint.sh` on the host, then rebuild.

### Management commands / migrations / DB access (on the host)

```bash
# Run any Django management command against prod:
docker exec cgmd-web-1 python manage.py <command>        # e.g. seed_bcgs_commissions --dry-run
docker exec cgmd-web-1 python manage.py migrate           # (also runs automatically on web start)

# psql into the prod database:
docker exec -it cgmd-db-1 psql -U cgmd -d cgmd
```

## Database migrations in prod

> ⚠️ **`web`'s entrypoint runs `migrate --noinput` on every start, and the entrypoint is
> `set -e`.** A migration that errors therefore **aborts the entrypoint → the container
> crash-loops → `/api` goes down.** Treat every migration as a potential outage and follow
> the rules below. (These bit us shipping the `works-column-sort-ordering-fix`.)

**Rules (learned the hard way):**
1. **Never mix a `RunPython` data change with a schema `ALTER` on the same table in one
   migration.** Postgres rejects it with `cannot ALTER TABLE "…" because it has pending
   trigger events`. **Split it:** do the data backfill in one migration, the
   `AlterField` / `AlterModelOptions` in the *next* one (separate transactions).
2. **Batch backfills must `.order_by('pk')`.** Titles/names aren't unique, so an
   unordered offset slice (`qs[start:start+N]`) silently **skips rows** at batch
   boundaries, leaving them with the column default. Order by the primary key.
3. **Back up first, verify after** (below).

**Safe procedure:**
```bash
# 0) Back up the DB first (writes to a user-writable path — see scripts/backup-db.sh)
scripts/backup-db.sh                       # or run the manual dump in the Rollback section

# 1) Ship code + rebuild (entrypoint applies the migration). Prefer the script:
scripts/deploy-backend.sh                  # rebuilds web, health-gates, prints rollback hint on failure

# 2) Confirm the migration applied and the app is serving
ssh -i ~/.ssh/cgmd-prod.pem ec2-user@52.205.65.184 \
  "docker exec cgmd-web-1 python manage.py showmigrations music | tail -5"
curl -s -o /dev/null -w '%{http_code}\n' https://www.solmuapp.com/api/works/?page_size=1   # expect 200

# 3) Spot-check the data the migration touched (example: a backfilled sort column)
docker exec cgmd-db-1 psql -U cgmd -d cgmd -tAc \
  "SELECT count(*) FILTER (WHERE title_sort_key='') AS empty, count(*) AS total FROM works;"
```

If a backfill missed rows, repair without a new migration by recomputing from the model:
```bash
docker exec -i cgmd-web-1 python manage.py shell <<'PY'
from music.models import Work
from music.utils import generate_title_sort_key
qs = list(Work.objects.filter(title_sort_key=''))
for w in qs: w.title_sort_key = generate_title_sort_key(w.title or '')
Work.objects.bulk_update(qs, ['title_sort_key'], batch_size=500)
print('repaired', len(qs))
PY
```

## Rollback

There is **no instant rollback** (Elastic Beanstalk is gone; see the `aws-cost-consolidation`
SDD). Recovery is fix-forward or rebuild-and-restore, RTO ≈ 30–60 min.

**`web` is crash-looping / `/api` is 502:**
```bash
ssh -i ~/.ssh/cgmd-prod.pem ec2-user@52.205.65.184 "docker logs cgmd-web-1 --tail 40"
```
- `exec /app/docker-entrypoint.sh: no such file or directory` → CRLF line endings; fix in place
  `sed -i 's/\r$//' docker-entrypoint.sh` then rebuild (`.gitattributes` prevents this via `git archive`).
- `cannot ALTER TABLE … pending trigger events` / any migration error → split/fix the migration,
  re-ship. The failed migration rolled back (Django wraps each migration in a transaction), so the
  DB is unchanged and it's safe to retry.

**Restore the database from a dump** (custom `-Fc` format from `backup.sh` / nightly, or plain SQL
from `scripts/backup-db.sh`):
```bash
# custom-format dump:
docker exec -i cgmd-db-1 pg_restore -U cgmd -d cgmd --clean --if-exists < cgmd_YYYYMMDD.dump
# plain SQL dump:
docker exec -i cgmd-db-1 psql -U cgmd -d cgmd < pre_deploy_YYYYMMDD.sql
```
RPO ≈ 24h from the nightly `cgmd-backup.timer`, or **0** if you ran `scripts/backup-db.sh` right
before deploying.

## Frontend deploy (S3 + CloudFront)

> **One command:** `scripts/deploy-frontend.sh` runs the build → sync → invalidate → verify
> below. The manual steps follow for reference.

Build locally (Vite bakes `VITE_API_URL=https://www.solmuapp.com/api` from `.env.production`),
sync to S3 with correct cache headers, invalidate only `index.html`.

```bash
cd frontend && npm run build && cd ..

# 1) Hashed assets — long-lived immutable cache (everything except index.html)
aws s3 sync frontend/dist/ s3://cgmd-frontend-1770139819 --delete \
  --exclude index.html --cache-control "public, max-age=31536000, immutable"

# 2) index.html — never cache the entrypoint, so new asset hashes are picked up instantly
aws s3 cp frontend/dist/index.html s3://cgmd-frontend-1770139819/index.html \
  --content-type text/html --cache-control "no-cache"

# 3) Invalidate only the HTML (assets are content-hashed + immutable)
aws cloudfront create-invalidation --distribution-id E23JJN25WLB1B9 --paths "/index.html"
```

**Do not** drop the `--cache-control` flags. Verify:

```bash
aws cloudfront get-invalidation --distribution-id E23JJN25WLB1B9 --id <INVALIDATION_ID> --query "Invalidation.Status"
# Confirm the live entrypoint references the new bundle hash:
curl -s https://www.solmuapp.com/ | grep -o 'index-[A-Za-z0-9_-]*\.js'
```

## Deploy order

When a change spans both tiers **and** the frontend consumes a new API field, deploy **backend
first, then frontend** — otherwise the new frontend requests a field the old API doesn't return.
(Example: the `WorkLink` `links` array — the new `ExternalLinks` reads `work.links`.)

## Prerequisites / tooling
- AWS CLI + credentials configured locally (IAM user `solmu`, account `429541886989`, region `us-east-1`).
- SSH key `~/.ssh/cgmd-prod.pem` for the EC2 host.
- Docker + Docker Compose v2 are installed on the EC2 host (invoked as `docker compose`).
- Deploy identifiers live in [`deploy/config.sh`](deploy/config.sh); the [`scripts/`](scripts/)
  wrappers source it, so nothing hard-codes the host/bucket/dist id.

### Host `.env` (prod compose variables)
The prod compose (`docker-compose.prod.yml`) reads these from the **host-only, gitignored**
`/home/ec2-user/cgmd/.env` — **never commit or overwrite it during a deploy**:

| Var | Notes |
|-----|-------|
| `SECRET_KEY` | Django secret. |
| `ALLOWED_HOSTS` | `api.solmuapp.com,www.solmuapp.com,solmuapp.com,localhost,127.0.0.1`. |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Postgres creds (`cgmd`/`cgmd`/…). `DB_HOST=db` is set in compose. |
| `DB_CONN_MAX_AGE` | `600` (persistent connections — the latency fix). |
| `CORS_ALLOWED_ORIGINS` | Frontend origins. |
| `GUNICORN_WORKERS` | Defaults to `2` on the t4g.micro. |
| `COGNITO_REGION` / `COGNITO_USER_POOL_ID` / `COGNITO_APP_CLIENT_ID` | Admin auth (see `cognito-admin-auth` SDD). |

## Useful commands

```bash
# One-command deploys (from local; see scripts/README.md)
scripts/deploy-backend.sh     # ship HEAD → rebuild web → migrate → health-gate (+ DB backup)
scripts/deploy-frontend.sh    # build → s3 sync → invalidate → verify
scripts/backup-db.sh          # ad-hoc prod DB dump before a risky change
scripts/prod.sh logs 80       # tail web logs   (also: ps | shell | manage <args> | migrate | psql)

# Backend (on the EC2 host)
docker ps                                              # container status
docker logs cgmd-web-1 --tail 50                       # app logs
docker compose -f docker-compose.prod.yml restart web  # restart without rebuild
docker compose -f docker-compose.prod.yml up -d --build web  # rebuild + restart after code change

# Frontend (from local)
aws s3 sync frontend/dist/ s3://cgmd-frontend-1770139819 --delete
aws cloudfront create-invalidation --distribution-id E23JJN25WLB1B9 --paths "/index.html"
```

## CloudFront OAC + private bucket — ✅ APPLIED (2026-07-07)

The frontend bucket is **private** and served **only** through CloudFront via Origin Access Control
(OAC id `E3MZSI8QOW4DL1`). Block Public Access is ON, the public bucket policy is removed (see
[s3-policy.json](s3-policy.json) for the applied OAC policy), and S3 static website hosting is
disabled. The distribution's frontend origin is the S3 **REST** endpoint
(`cgmd-frontend-1770139819.s3.us-east-1.amazonaws.com`); SPA deep links work via CloudFront custom
error responses (403/404 → `/index.html`, 200). Direct S3 access returns 403/404. Deploy commands
are unchanged — you still `aws s3 sync` + invalidate; only *how CloudFront reads the bucket* changed.

## Production checklist
- [x] Backend on EC2 Docker (db + web + caddy) — Elastic Beanstalk removed
- [x] Database is the on-host PostgreSQL 17 container (`cgmd`/`cgmd`) — Supabase removed
- [x] Frontend bucket private + served via CloudFront OAC (2026-07-07)
- [x] `*.sh` pinned to LF via `.gitattributes` (prevents entrypoint crash-loop)
- [ ] `SECRET_KEY` / `DEBUG=False` / `ALLOWED_HOSTS` / DB creds set in host `.env`
- [ ] Frontend `VITE_API_URL` → `https://www.solmuapp.com/api`
