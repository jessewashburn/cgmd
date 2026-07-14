#!/bin/bash
# Nightly production DB backup (run on the EC2 host by the systemd timer
# `cgmd-backup.timer`, as root, 07:00 UTC). Custom-format pg_dump, keep 7 local,
# push to S3 once an instance role is attached. Canonical copy of the host script.
#
# NOTE: writes to /home/ec2-user/backups which is root-owned, so this fails if run
# as ec2-user. For an ad-hoc pre-deploy dump, use scripts/backup-db.sh instead.
set -euo pipefail
BK=/home/ec2-user/backups
BUCKET=cgmd-db-backups-429541886989
mkdir -p "$BK"
TS=$(date +%Y%m%d_%H%M%S)
OUT="$BK/cgmd_${TS}.dump"
cd /home/ec2-user/cgmd
# -Fc custom format is already compressed
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U cgmd -d cgmd -Fc > "$OUT"
# keep last 7 local
ls -1t "$BK"/cgmd_*.dump 2>/dev/null | tail -n +8 | xargs -r rm -f
# off-box copy iff AWS creds/role are available (auto-activates once an instance role is attached)
if command -v aws >/dev/null 2>&1 && aws sts get-caller-identity >/dev/null 2>&1; then
  aws s3 cp "$OUT" "s3://${BUCKET}/daily/" --only-show-errors && echo "s3: uploaded $(basename "$OUT")"
else
  echo "s3: skipped (no AWS creds/role on box yet)"
fi
echo "backup ok: $OUT ($(du -h "$OUT" | cut -f1))"
