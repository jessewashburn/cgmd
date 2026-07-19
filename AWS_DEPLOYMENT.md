# AWS Deployment Guide

> **Architecture (current, as of 2026-07-13):** everything is on AWS. The backend is a
> **Docker Compose stack on a single EC2 instance** (Django + gunicorn, PostgreSQL 17, and
> Caddy for TLS/reverse-proxy — all co-located). The frontend is a **static build in S3 fronted
> by CloudFront**. **Nothing runs on Elastic Beanstalk and there is no Supabase** — both were removed
> (see the `aws-cost-consolidation` SDD). Ignore any `eb ...` commands; `eb status` will say
> "not found". Note the EB *applications* `cgmd`/`cgmd-backend` and their artifact bucket still
> exist as retired rollback material — no environments, no compute cost. `.elasticbeanstalk/config.yml`
> in this repo is stale.

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
| **EBS volume** | `vol-004b267b19eadc38e` — 20 GiB gp3, `us-east-1c`. Holds the DB **and** the local dumps `backup-db.sh` writes. |
| **Elastic IP** | `52.205.65.184` (`eipassoc-0c81a356da6eac31d`). Billed ~$3.60/mo even while attached. |
| **CPU credit mode** | `standard` (**not** `unlimited`) — see [Cost controls](#cost-controls-and-monitoring). |
| **CloudFront pricing plan** | **Free flat-rate plan.** Invisible to the API — see [Cost controls](#cost-controls-and-monitoring). |
| **WAF Web ACL** | `CreatedByCloudFront-14c50cb5` (id `2950a003-6b60-4376-837b-c2217591637d`, scope `CLOUDFRONT`), 3 AWS managed rule groups. Bundled free with the plan — **do not remove**. |
| **HTTP versions** | `http2and3` (QUIC/HTTP-3 enabled 2026-07-19), IPv6 on, compression on. |
| **Origins on the distribution** | **2** — `/` → S3 REST endpoint, `/api/*` → `cgmd-api-box` (`api.solmuapp.com`). A dead Elastic Beanstalk origin was removed 2026-07-19. |
| **Cost-control stack** | CloudFormation `cgmd-cost-controls` — see [Cost controls](#cost-controls-and-monitoring). |

> One CloudFront distribution fronts both origins: `/` → S3 (frontend), `/api` → the EC2 host's
> Caddy → `web:8000`. Bucket name and distribution ID are identifiers, not secrets. Real secrets
> (`SECRET_KEY`, DB password) live in the host-only `/home/ec2-user/cgmd/.env` (gitignored, **never**
> overwrite it during a deploy).

### S3 buckets

| Bucket | Purpose |
|--------|---------|
| `cgmd-frontend-1770139819` | Frontend build. Private, CloudFront OAC only. Lifecycle: noncurrent versions expire 30d, incomplete MPUs 7d. |
| `cgmd-db-backups-429541886989` | **Empty and currently unused** — has a 30-day expiry rule on a `daily/` prefix nothing writes to. See the backup hazard below. |
| `elasticbeanstalk-us-east-1-429541886989` | 46 objects / 78 MB of old EB application bundles. EB *applications* `cgmd` and `cgmd-backend` still exist with 25 registered versions; newest artifact `2026-07-12`, the rollback path from the EC2 migration. Costs ~$0.002/mo — kept deliberately. |
| `crm-events-archive-jw-1766456486` | **Unrelated project** (CRM lead events, Dec 2025). Not cgmd. |

> ⚠️ **Backup hazard.** `scripts/backup-db.sh` writes dumps to `~/pre_deploy_*.sql` on the EC2 host —
> the *same EBS volume as the database*. There is no off-instance backup today, so losing
> `vol-004b267b19eadc38e` loses the data and every backup at once. The `cgmd-db-backups` bucket
> exists for this but nothing ships to it yet.

### IAM identities

| Identity | Use |
|----------|-----|
| `solmu` | Day-to-day deploys. S3, CloudFront, EC2/CloudWatch read, `ec2:ModifyInstanceCreditSpecification`. **Denied** IAM, Budgets, Cost Explorer, Savings Plans, Lambda invoke. |
| `cgmd-admin` | `AdministratorAccess`. Needed for the cost-control stack, Cost Explorer, Budgets, Savings Plans. Use `AWS_PROFILE=cgmd-admin`. |

> Account-level **"IAM access to billing data"** must be enabled by the **root user** in the Billing
> console — there is no API or CLI for it. Without it no IAM principal can read Cost Explorer,
> regardless of policy.

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

> **One command:** `scripts/deploy-frontend.sh` runs the build → **Cognito bundle check** → sync
> → invalidate → verify below. The manual steps follow for reference.

Build locally (Vite bakes `VITE_API_URL=https://www.solmuapp.com/api` from `.env.production`),
sync to S3 with correct cache headers, invalidate only `index.html`.

> ⚠️ **Cognito config must be compiled into the bundle — never pass it only via the shell.**
> (Bit us 2026-07-14: prod admin login showed *"Admin login isn't configured yet."*)
>
> The Cognito **user pool id / app client id are public** (they ship in the client bundle either
> way; the pool is protected by SRP + the `admins` group). They are therefore **hardcoded as
> defaults in [frontend/src/lib/amplify.ts](frontend/src/lib/amplify.ts)** so that *any* build —
> `npm run build`, the deploy script, CI, an agent — bakes them in with **no env setup**.
>
> - **Do NOT** rely on exporting `VITE_COGNITO_*` in your shell. That's how we shipped a green
>   build with a broken login: config that only exists in one shell is not config.
> - `VITE_COGNITO_USER_POOL_ID` / `VITE_COGNITO_APP_CLIENT_ID` still **override** the defaults if
>   you need to point a build at a different pool.
> - Two things enforce this: `scripts/deploy-frontend.sh` **aborts** if the pool id isn't found in
>   `frontend/dist/assets/`, and `frontend/src/lib/amplify.test.ts` fails if the source defaults
>   are removed (it runs with no env set).
> - **If you rotate/recreate the pool**, update the defaults in `amplify.ts` *and*
>   `COGNITO_USER_POOL_ID` / `COGNITO_APP_CLIENT_ID` in [deploy/config.sh](deploy/config.sh)
>   (used only for the deploy assertion).

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
- **Cost/billing work needs `AWS_PROFILE=cgmd-admin`** — `solmu` is denied IAM, Budgets, Cost
  Explorer, Savings Plans and Lambda invoke. See [IAM identities](#iam-identities).
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

## Cost controls and monitoring

> **Read this before "optimising" anything.** The account costs **~$11.70/mo** and roughly $10 of
> that is irreducible. A previous pass priced it from public rate cards (the deploy user is denied
> `ce:GetCostAndUsage`) and invented an **$8/mo WAF charge that does not exist** — 41% of a $19.39
> estimate that was really $11.70. **Read the bill with `cgmd-admin`; never reconstruct one from
> rate cards.** Full history in the `aws-cost-control-hardening` SDD.

### The CloudFront flat-rate pricing plan (the non-obvious bit)

Distribution `E23JJN25WLB1B9` is on the **CloudFront Free flat-rate plan**. This does not appear in
`get-distribution` output and **there are no pricing-plan operations in the CloudFront API** —
it surfaces only as a `CloudFront Flat-Rate Plans` line in Cost Explorer, or in the console.
Consequences:

- **CloudFront, AWS WAF and DDoS protection are bundled at $0.** There is no WAF line item despite
  a Web ACL with 3 managed rule groups being attached.
- **No overage charges, regardless of traffic spikes or attacks.** Sustained overage degrades
  delivery (fewer/more distant edges) instead of billing you.
- **The Web ACL cannot be disassociated** while a plan is active — both `UpdateDistribution` and
  `DisassociateDistributionWebACL` reject it. Cancelling the plan is **console-only**.
- **WAF-blocked traffic doesn't count toward the plan allowance**, so the WAF protects the free
  tier. **Keep it.**
- Do **not** switch to `PriceClass_100`: it drops Asia/South America/Oceania/Africa/India and saves
  **$0**, since CloudFront is already free here.

### Actual spend (June 2026, final)

| Service | $/mo |
|---------|-----:|
| EC2 – Compute (t4g.micro) | 6.13 |
| Amazon VPC (public IPv4) | 3.60 |
| EC2 – Other (EBS gp3 20 GiB) | 1.60 |
| Tax | ~0.34 |
| S3 | ~0.01 |
| CloudFront + WAF + DDoS (Free plan) | **0.00** |
| **Total** | **~11.70** |

```bash
# The only trustworthy source. Requires AWS_PROFILE=cgmd-admin.
aws ce get-cost-and-usage --time-period Start=2026-06-01,End=2026-07-01 \
  --granularity MONTHLY --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE --output table
```

### The `cgmd-cost-controls` stack

Defined in [`deploy/cost-controls.yaml`](deploy/cost-controls.yaml) (15 resources). Deploy with
`cgmd-admin`:

```bash
export AWS_PROFILE=cgmd-admin
aws cloudformation deploy --region us-east-1 \
  --template-file deploy/cost-controls.yaml \
  --stack-name cgmd-cost-controls --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides MonthlyBudgetUSD=25 AlertEmail=jeswashburn@gmail.com
```

| Resource | What it does |
|----------|--------------|
| Budget `cgmd-monthly` | $25/mo; SNS at 60% actual and 100% forecasted. |
| Budget Action + `cgmd-deny-costly-provisioning` | At 100% actual, attaches a deny policy to `solmu` covering `ec2:RunInstances`, NAT/EIP/volume creation, RDS, ElastiCache, Redshift, SageMaker, EMR, new distributions and load balancers. **Deliberately excludes `s3:*` and `cloudfront:CreateInvalidation`, so both deploy scripts keep working.** |
| Alarm `cgmd-cloudfront-egress-runaway` | CloudFront `BytesDownloaded` > 2 GiB/hr (baseline is ~5 MiB/**day**). |
| Lambda `cgmd-egress-breaker` | Disables the distribution when the alarm fires. |
| SNS `cgmd-cost-alerts`, `cgmd-egress-breaker` | Email to the owner; both subscriptions **confirmed**. |
| CE anomaly subscription | Attached to the account's existing `Default-Services-Monitor`, $5 threshold. |

> ⚠️ The egress breaker **takes down the frontend and the API together** (one distribution fronts
> both). Given the flat-rate plan has no overages, it now guards against a cost that cannot occur —
> consider repointing the alarm to `cgmd-cost-alerts` for alert-only behaviour.

### Verify the breaker without an outage

The handler has a permanent dry-run mode. A real SNS alarm event is an envelope with a `Records`
key and no `dry_run`, so it can never take the dry path.

```bash
# Single line on purpose — see the Git Bash gotcha below.
aws lambda invoke --region us-east-1 --function-name cgmd-egress-breaker --cli-binary-format raw-in-base64-out --payload '{"dry_run": true}' breaker-test.json && cat breaker-test.json
# => {"status":"dry-run","distribution":"E23JJN25WLB1B9","enabled":true,"etag":"...","would_disable":true}
```

**If the breaker has fired**, re-enable the distribution:

```bash
aws cloudfront get-distribution-config --id E23JJN25WLB1B9 > /tmp/d.json   # set Enabled=true
aws cloudfront update-distribution --id E23JJN25WLB1B9 --if-match <ETag> --distribution-config file:///tmp/cfg.json
# If the deny policy is attached:
aws iam detach-user-policy --user-name solmu --policy-arn arn:aws:iam::429541886989:policy/cgmd-deny-costly-provisioning
```

### Gotchas hit while building this

- **`AWS::CE::AnomalyMonitor` fails with `AlreadyExists`.** Only one DIMENSIONAL/SERVICE monitor is
  permitted per account, and enabling Cost Explorer auto-creates `Default-Services-Monitor`. The
  template takes its ARN as a parameter instead of creating one.
- **Git Bash: `/dev/stdout` fails** with `[Errno 2] No such file or directory: '/proc/self/fd/1'`.
  Write CLI output to a real file. Same family as the CloudFront invalidation path issue below.
- **Git Bash mangles multi-line pastes.** Use single-line commands for anything destructive — a
  garbled `--payload` once nearly fired the breaker for real.
- **T4g `unlimited` credit mode is an uncapped cost vector** (~$58/mo tail on 2 vCPUs). Switched to
  `standard` 2026-07-19; at 2.57% average CPU with credits pinned at 288/288 it never throttles.

## Production checklist
- [x] Backend on EC2 Docker (db + web + caddy) — Elastic Beanstalk removed
- [x] Database is the on-host PostgreSQL 17 container (`cgmd`/`cgmd`) — Supabase removed
- [x] Frontend bucket private + served via CloudFront OAC (2026-07-07)
- [x] `*.sh` pinned to LF via `.gitattributes` (prevents entrypoint crash-loop)
- [x] Cost controls deployed — `cgmd-cost-controls` stack, budget + alerts + breaker (2026-07-19)
- [x] EC2 CPU credit mode `standard`, not `unlimited` (closes a ~$58/mo tail)
- [x] SNS cost-alert email subscriptions confirmed (unconfirmed = silent alerts)
- [ ] Off-instance DB backups — dumps currently share the database's EBS volume
- [ ] 1-year Compute Savings Plan on the t4g.micro (~$1.70/mo)
- [ ] `SECRET_KEY` / `DEBUG=False` / `ALLOWED_HOSTS` / DB creds set in host `.env`
- [ ] Frontend `VITE_API_URL` → `https://www.solmuapp.com/api`
