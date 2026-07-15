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

# Guard: admin login is Cognito, and its config must be compiled into the bundle.
# A bundle without it still builds green but renders "Admin login isn't configured
# yet" in prod (bit us 2026-07-14). Fail here rather than ship a broken login.
echo "▶ Verifying Cognito config is baked into the bundle…"
if ! grep -rq "$COGNITO_USER_POOL_ID" frontend/dist/assets/ 2>/dev/null; then
  echo "✗ Cognito pool id ($COGNITO_USER_POOL_ID) is NOT in the built bundle." >&2
  echo "  Admin login would show \"isn't configured yet\". Aborting deploy." >&2
  echo "  Fix: frontend/src/lib/amplify.ts must define the pool/client defaults." >&2
  exit 1
fi
echo "  ✓ Cognito config present"

echo "▶ Syncing hashed assets (immutable, long cache)…"
aws s3 sync frontend/dist/ "s3://$FRONTEND_BUCKET" --delete \
  --exclude index.html \
  --cache-control "public, max-age=31536000, immutable" \
  --region "$AWS_REGION"

echo "▶ Uploading index.html (no-cache entrypoint)…"
aws s3 cp frontend/dist/index.html "s3://$FRONTEND_BUCKET/index.html" \
  --content-type text/html --cache-control "no-cache" --region "$AWS_REGION"

echo "▶ Invalidating CloudFront /index.html…"
# Use --invalidation-batch (JSON) rather than --paths "/index.html": on Git Bash
# (Windows) MSYS rewrites a leading-slash argument into a Windows path and
# CloudFront rejects it ("InvalidArgument"). A JSON arg starts with '{', so it is
# never path-converted, and this is identical on Linux/macOS. (Don't "fix" it with
# MSYS_NO_PATHCONV/MSYS2_ARG_CONV_EXCL — those break the venv's `aws` shim.)
inv="$(aws cloudfront create-invalidation --distribution-id "$CLOUDFRONT_DIST_ID" \
  --invalidation-batch "{\"Paths\":{\"Quantity\":1,\"Items\":[\"/index.html\"]},\"CallerReference\":\"deploy-$(date +%s)\"}" \
  --query 'Invalidation.Id' --output text)"
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
