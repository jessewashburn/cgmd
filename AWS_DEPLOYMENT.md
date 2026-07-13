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

The host has no git and is populated by copying code in, then rebuilding the `web` image
(`build: .`). Its container entrypoint runs `migrate --noinput` + `collectstatic` on start.

**Host-only files that must NOT be clobbered:** `.env`, `Caddyfile`, `docker-compose.prod.yml`,
`backup.sh`. Ship only application code.

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

## Frontend deploy (S3 + CloudFront)

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

## Useful commands

```bash
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
