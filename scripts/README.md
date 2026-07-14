# Deploy scripts

One command per tier for the all-AWS stack. Full context in
[`../AWS_DEPLOYMENT.md`](../AWS_DEPLOYMENT.md); shared identifiers in
[`../deploy/config.sh`](../deploy/config.sh). Run from anywhere in the repo.

| Script | What it does |
|--------|--------------|
| `deploy-backend.sh` | Backup DB → ship committed `HEAD` → rebuild `web` (entrypoint migrates) → health-gate → rollback hint on failure. `SKIP_BACKUP=1` skips the backup. |
| `deploy-frontend.sh` | `npm run build` → `s3 sync` (immutable assets) → upload `index.html` (no-cache) → CloudFront invalidate → verify live bundle hash. |
| `backup-db.sh` | Ad-hoc plain-SQL prod DB dump to `~/pre_deploy_*.sql` on the host (user-writable, unlike the root-owned nightly `backup.sh`). |
| `prod.sh` | Host helpers: `ps`, `logs [N]`, `shell`, `manage <args>`, `migrate`, `psql`, `ssh [cmd]`. |

**Prereqs:** AWS CLI configured (IAM `solmu`), SSH key at `~/.ssh/cgmd-prod.pem`
(override with `PROD_SSH_KEY`), and — for the backend — a clean commit (scripts ship
`HEAD`, not the working tree).

**Before shipping a migration**, read the "Database migrations in prod" section of
`AWS_DEPLOYMENT.md`: `migrate` runs on `web` start and a failure crash-loops `/api`.
