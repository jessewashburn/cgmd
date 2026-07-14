#!/usr/bin/env bash
# Deploy the backend to the EC2 Docker host: ship committed HEAD, rebuild the web
# container (its entrypoint runs migrate + collectstatic), and health-gate the result.
#
#   scripts/deploy-backend.sh              # backup DB, ship, rebuild, verify
#   SKIP_BACKUP=1 scripts/deploy-backend.sh  # skip the pre-deploy DB backup (code-only, no migrations)
#
# Ships committed HEAD only (deterministic + LF-safe via .gitattributes). Commit first.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=deploy/config.sh
source "$ROOT/deploy/config.sh"
cd "$ROOT"
require git; require ssh

if [ -n "$(git status --porcelain)" ]; then
  echo "⚠  Working tree is dirty — deploying committed HEAD only; uncommitted changes will NOT ship."
fi
REV="$(git rev-parse --short HEAD)"
echo "▶ Deploying backend @ $REV → $PROD_USER@$PROD_HOST:$PROD_APP_DIR"

# 1) Safety backup (default on; skip only for code-only deploys you're sure about).
if [ "${SKIP_BACKUP:-0}" = "1" ]; then
  echo "▶ Skipping DB backup (SKIP_BACKUP=1)."
else
  "$ROOT/scripts/backup-db.sh"
fi

# 2) Ship committed application code (git archive skips untracked/__pycache__, emits LF).
echo "▶ Shipping code (git archive HEAD)…"
git archive --format=tar HEAD "${BACKEND_SHIP_PATHS[@]}" \
  | ssh_prod "tar -xf - -C '$PROD_APP_DIR'"

# 3) Rebuild + restart web (db/caddy keep running; entrypoint applies migrations).
echo "▶ Rebuilding + restarting web…"
ssh_prod "cd '$PROD_APP_DIR' && docker compose -f '$PROD_COMPOSE' up -d --build web"

# 4) Health gate — poll gunicorn inside the container (curl ships in the web image).
echo "▶ Waiting for web to serve HTTP 200…"
ok=0
for _ in $(seq 1 30); do
  code="$(ssh_prod "docker exec cgmd-web-1 curl -s -o /dev/null -w '%{http_code}' 'http://127.0.0.1:8000/api/works/?page_size=1'" 2>/dev/null || true)"
  if [ "$code" = "200" ]; then ok=1; break; fi
  sleep 3
done

if [ "$ok" != "1" ]; then
  echo ""
  echo "✗ web did not return 200 within ~90s. Recent logs:"
  ssh_prod "docker logs cgmd-web-1 --tail 40" || true
  cat <<'HINT'

── Rollback / fixes (see AWS_DEPLOYMENT.md → Rollback) ─────────────────────────
 • Migration error (crash-loop): the failed migration rolled back (DB unchanged).
   Fix/split the migration locally, commit, and re-run this script.
   Reminder: never mix RunPython DML + schema ALTER in one migration; backfills
   must .order_by('pk').
 • CRLF entrypoint ("exec …: no such file or directory"):
   ssh -i ~/.ssh/cgmd-prod.pem ec2-user@52.205.65.184 \
     "sed -i 's/\r$//' /home/ec2-user/cgmd/docker-entrypoint.sh && \
      cd /home/ec2-user/cgmd && docker compose -f docker-compose.prod.yml up -d --build web"
────────────────────────────────────────────────────────────────────────────────
HINT
  exit 1
fi

echo "✓ Backend deployed @ $REV — API serving (HTTP 200)."
echo "▶ Applied migrations (music, tail):"
ssh_prod "docker exec cgmd-web-1 python manage.py showmigrations music | tail -3" || true
