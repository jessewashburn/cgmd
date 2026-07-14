#!/usr/bin/env bash
# Shared prod deploy identifiers + helpers, sourced by scripts/*.sh.
# NO SECRETS here — these are public identifiers. Real secrets live in the
# host-only, gitignored /home/ec2-user/cgmd/.env. See AWS_DEPLOYMENT.md.

# --- Backend / EC2 host ---
PROD_HOST="52.205.65.184"
PROD_USER="ec2-user"
PROD_SSH_KEY="${PROD_SSH_KEY:-$HOME/.ssh/cgmd-prod.pem}"
PROD_APP_DIR="/home/ec2-user/cgmd"
PROD_COMPOSE="docker-compose.prod.yml"
EC2_INSTANCE_ID="i-07ce6430cf3cdc27b"

# --- Frontend / CDN ---
FRONTEND_BUCKET="cgmd-frontend-1770139819"
CLOUDFRONT_DIST_ID="E23JJN25WLB1B9"
AWS_REGION="us-east-1"
SITE_URL="https://www.solmuapp.com"

# App code shipped on a backend deploy (application only — never .env or host infra).
BACKEND_SHIP_PATHS=(music cgmd_backend requirements.txt Dockerfile docker-entrypoint.sh manage.py)

SSH_OPTS=(-i "$PROD_SSH_KEY" -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new)

# Run a command on the prod host over SSH.
ssh_prod() { ssh "${SSH_OPTS[@]}" "$PROD_USER@$PROD_HOST" "$@"; }

# Run an interactive command on the prod host (allocates a TTY).
ssh_prod_tty() { ssh "${SSH_OPTS[@]}" -t "$PROD_USER@$PROD_HOST" "$@"; }

# Abort if a required tool is missing.
require() { command -v "$1" >/dev/null 2>&1 || { echo "✗ missing required tool: $1" >&2; exit 1; }; }
