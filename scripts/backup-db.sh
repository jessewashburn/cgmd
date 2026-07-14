#!/usr/bin/env bash
# Ad-hoc production DB backup to a user-writable path on the host.
#
# Unlike the nightly backup.sh (root-owned ~/backups, custom -Fc format), this writes a
# plain SQL dump to /home/ec2-user/ (outside the docker build context) that ec2-user can
# create — use it right before a risky deploy/migration. Restore with:
#   docker exec -i cgmd-db-1 psql -U cgmd -d cgmd < pre_deploy_YYYYMMDD_HHMMSS.sql
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=deploy/config.sh
source "$ROOT/deploy/config.sh"
require ssh

TS="$(date +%Y%m%d_%H%M%S)"
echo "▶ Backing up prod DB → ~/pre_deploy_${TS}.sql on $PROD_HOST"
ssh_prod "cd '$PROD_APP_DIR' && set -a && . ./.env && set +a && \
  docker exec -e PGPASSWORD=\"\$DB_PASSWORD\" cgmd-db-1 pg_dump -U \"\$DB_USER\" -d \"\$DB_NAME\" \
    > ~/pre_deploy_${TS}.sql && \
  echo \"✓ backup: ~/pre_deploy_${TS}.sql (\$(du -h ~/pre_deploy_${TS}.sql | cut -f1))\""
