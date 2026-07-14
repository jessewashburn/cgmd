# AGENTS.md

This repo's dev history lives in PromptRoot under tenant `solmu`.

Coding agents (Claude Code, Cursor, Continue, Cline, Jules) use that tenant
for SDD search and authoring. The MCP server resolves the tenant
automatically from the `.promptroot-tenant` file in this repo, so no
per-call configuration is needed.

## Quick start for agents

- Read SDDs: `promptroot_search_sdds` / `promptroot_get_sdd`.
- Create new SDDs: `promptroot_create_sdd` (frontmatter + body).
- Update an SDD: `promptroot_update_sdd` (writes a new version).

If no MCP server is configured, fall back to:

    POST https://us-central1-promptroot-b02a2.cloudfunctions.net/ragQuery
    {
      "query": "<question>",
      "topK": 5,
      "tenantId": "solmu"
    }

## Deploying (prod is all AWS)

**Before any deploy, read [`AWS_DEPLOYMENT.md`](AWS_DEPLOYMENT.md).** It is the single
source of truth — do **not** SSH-probe the prod box to rediscover the topology; it's
already documented there and in the [[deployment-process-and-docs]] SDD.

Topology in one line:
- **Frontend** — static Vite build in **S3** (`cgmd-frontend-1770139819`) behind
  **CloudFront** (`E23JJN25WLB1B9`), private via OAC.
- **Backend + DB** — one **EC2 t4g.micro** (`52.205.65.184`, us-east-1) running a
  Docker Compose stack: `cgmd-web-1` (Django/gunicorn), `cgmd-db-1` (PostgreSQL 17,
  volume `pgdata`), `cgmd-caddy-1` (TLS/reverse-proxy). No Elastic Beanstalk, no RDS,
  no Supabase.

One command per tier (safety — backup, health-gate — is built in):

    scripts/deploy-backend.sh     # archive HEAD → rebuild web → migrate → health check
    scripts/deploy-frontend.sh    # build → s3 sync (cache headers) → CloudFront invalidate

**Django migrations run automatically when `web` starts, and a failed migration
crash-loops the container and takes `/api` down.** See the "Database migrations in
prod" section of `AWS_DEPLOYMENT.md` before shipping any migration.
