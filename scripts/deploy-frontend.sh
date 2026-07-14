#!/usr/bin/env bash
# Deploy the frontend to S3 + CloudFront: build, sync with correct cache headers,
# invalidate the HTML entrypoint, and verify the live bundle hash.
#
#   scripts/deploy-frontend.sh
#
# Vite bakes VITE_API_URL (https://www.solmuapp.com/api) from frontend/.env.production.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=deploy/config.sh
source "$ROOT/deploy/config.sh"
cd "$ROOT"
require aws; require npm; require curl

echo "▶ Building frontend…"
( cd frontend && npm run build )

echo "▶ Syncing hashed assets (immutable, long cache)…"
aws s3 sync frontend/dist/ "s3://$FRONTEND_BUCKET" --delete \
  --exclude index.html \
  --cache-control "public, max-age=31536000, immutable" \
  --region "$AWS_REGION"

echo "▶ Uploading index.html (no-cache entrypoint)…"
aws s3 cp frontend/dist/index.html "s3://$FRONTEND_BUCKET/index.html" \
  --content-type text/html --cache-control "no-cache" --region "$AWS_REGION"

echo "▶ Invalidating CloudFront /index.html…"
inv="$(aws cloudfront create-invalidation --distribution-id "$CLOUDFRONT_DIST_ID" \
  --paths "/index.html" --query 'Invalidation.Id' --output text)"
echo "  invalidation: $inv"

echo "▶ Verifying bundle hash…"
built="$(grep -o 'index-[A-Za-z0-9_-]*\.js' frontend/dist/index.html | head -1 || true)"
live="$(curl -s "$SITE_URL/" | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1 || true)"
echo "  built=$built  live=$live"
if [ -n "$built" ] && [ "$built" = "$live" ]; then
  echo "✓ Frontend deployed — live bundle matches the build."
else
  echo "✓ Frontend uploaded. Live may lag until the invalidation completes (~1 min); re-check:"
  echo "  curl -s $SITE_URL/ | grep -o 'index-[A-Za-z0-9_-]*\\.js'"
fi
