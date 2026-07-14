# CLAUDE.md

Guidance for Claude Code (and other coding agents) working in this repo.

## Dev history / SDDs
This repo's design history lives in **PromptRoot**, tenant `solmu` (see [AGENTS.md](AGENTS.md)).
Search before you build: `promptroot_search_sdds` / `promptroot_get_sdd`.

## Deploying — read the runbook, don't probe prod
Production is **entirely on AWS**. **Before any deploy, read [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)** —
it documents the live environment, exact commands, and the gotchas. Do **not** SSH into the prod
box to rediscover how it's laid out; it's already written down (this rule exists because an agent
once rebuilt the whole topology by probing the host — see the `deployment-process-and-docs` SDD).

- **Frontend:** S3 (`cgmd-frontend-1770139819`) + CloudFront (`E23JJN25WLB1B9`), private via OAC.
- **Backend + DB:** one EC2 t4g.micro (`52.205.65.184`, us-east-1), Docker Compose stack —
  `cgmd-web-1` (Django/gunicorn), `cgmd-db-1` (PostgreSQL 17), `cgmd-caddy-1` (TLS). No EB, RDS, or Supabase.

One command per tier, safety built in:

    scripts/deploy-backend.sh      # archive HEAD → rebuild web → migrate → health-gate (auto DB backup if migrations pending)
    scripts/deploy-frontend.sh     # build → s3 sync (cache headers) → CloudFront invalidate → verify

## Database migrations in prod — hazard
`web`'s entrypoint runs `migrate` on **every start**, and `set -e` means a failed migration
**crash-loops the container and takes `/api` down**. Before shipping a migration:
- Never mix `RunPython` data changes with a schema `ALTER` on the same table in one migration
  (Postgres "pending trigger events"). Split backfill and schema change into separate migrations.
- Batch backfills must `.order_by('pk')` — titles/names aren't unique; unordered slices skip rows.
- Back up first (`scripts/backup-db.sh`), verify row counts + a spot ordering query after.

See the "Database migrations in prod" section of [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) for details.

## Tests
- Backend: `pytest` (from repo root). Frontend: `cd frontend && npm test`. E2E: `cd frontend && npm run test:e2e`.
- CI (`.github/workflows/ci.yml`) runs all three on every PR. CI does **not** deploy.
