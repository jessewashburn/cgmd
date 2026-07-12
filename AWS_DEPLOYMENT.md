# AWS Elastic Beanstalk Deployment Guide

## Live environment (fill-ins for the commands below)

| Thing | Value |
|-------|-------|
| Site domain | `www.solmuapp.com` / `solmuapp.com` |
| CloudFront distribution ID | `E23JJN25WLB1B9` |
| CloudFront domain | `djow2c4ppl2zz.cloudfront.net` |
| Frontend S3 bucket | `cgmd-frontend-1770139819` |
| Backend (EB) env | `cgmd-production` (region `us-east-1`) |
| Backend origin | `cgmd-production.eba-u32mituc.us-east-1.elasticbeanstalk.com` |

> One CloudFront distribution fronts both origins: `/` → S3 (frontend), `/api` → Elastic Beanstalk (backend).
> The bucket name and distribution ID are **identifiers, not secrets** — safe to keep here. Real
> secrets (AWS keys, DB password, `SECRET_KEY`) live in `~/.aws/`, EB env vars, and the gitignored `.env`.

## Quick redeploy (frontend)

```bash
cd frontend && npm run build && cd ..

# 1) Hashed assets — long-lived immutable cache (everything except index.html)
aws s3 sync frontend/dist/ s3://cgmd-frontend-1770139819 --delete \
  --exclude index.html --cache-control "public, max-age=31536000, immutable"

# 2) index.html — never cache the entrypoint, so new asset hashes are picked up instantly
aws s3 cp frontend/dist/index.html s3://cgmd-frontend-1770139819/index.html \
  --content-type text/html --cache-control "no-cache"

# 3) Invalidate only the HTML (assets are content-hashed + immutable — no need to invalidate them)
aws cloudfront create-invalidation --distribution-id E23JJN25WLB1B9 --paths "/index.html"
```

Because assets are content-hashed and marked `immutable`, browsers and CloudFront cache them
indefinitely and only ever refetch `index.html` (`no-cache`) — fast repeat visits, and you only
invalidate `/index.html` per deploy. **Do not** drop the `--cache-control` flags: without them S3
stores no caching directive and every asset is needlessly revalidated. Status:

```bash
aws cloudfront get-invalidation --distribution-id E23JJN25WLB1B9 --id <INVALIDATION_ID> --query "Invalidation.Status"
```

## Prerequisites
1. AWS Account with Free Tier eligible
2. AWS CLI installed
3. EB CLI installed

## Installation

### 1. Install AWS CLI
```bash
# Windows (using MSI installer)
Download from: https://awscli.amazonaws.com/AWSCLIV2.msi

# Or via pip
pip install awscli
```

### 2. Install EB CLI
```bash
pip install awsebcli
```

### 3. Configure AWS Credentials
```bash
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-east-1 (or your preferred region)
# - Default output format: json
```

## Backend Deployment (Elastic Beanstalk)

### 1. Initialize Elastic Beanstalk
```bash
cd c:/Users/jesse/cgmd
eb init

# Choose:
# - Region: us-east-1 (or your preferred)
# - Application name: cgmd-backend
# - Platform: Python 3.12
# - CodeCommit: No
# - SSH: Yes (for debugging)
```

### 2. Create Environment
```bash
eb create cgmd-production

# This will:
# - Create an EC2 instance (t3.micro - FREE tier)
# - Install Python 3.12
# - Install dependencies from requirements.txt
# - Run migrations
# - Collect static files
```

### 3. Set Environment Variables
```bash
eb setenv \
  SECRET_KEY="your-secret-key-here-generate-a-new-one" \
  DEBUG=False \
  ALLOWED_HOSTS=".elasticbeanstalk.com" \
  DATABASE_URL="postgresql://postgres.yosugfmarodnempvvbru:YOUR-PASSWORD@aws-0-us-west-2.pooler.supabase.com:5432/postgres" \
  CORS_ALLOWED_ORIGINS="https://your-cloudfront-url.cloudfront.net"
```

### 4. Deploy
```bash
eb deploy
```

### 5. Get Backend URL
```bash
eb status
# Look for "CNAME" - this is your backend URL
# Example: cgmd-production.us-east-1.elasticbeanstalk.com
```

## Frontend Deployment (S3 + CloudFront)

### 1. Build Frontend
```bash
cd frontend
npm install
npm run build
```

### 2. Create S3 Bucket
```bash
# Replace 'your-unique-bucket-name' with something unique
aws s3 mb s3://cgmd-frontend-bucket --region us-east-1

# Enable static website hosting
aws s3 website s3://cgmd-frontend-bucket --index-document index.html --error-document index.html
```

### 3. Configure Bucket Policy (Public Access)
Create a file `s3-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::cgmd-frontend-bucket/*"
    }
  ]
}
```

Apply policy:
```bash
aws s3api put-bucket-policy --bucket cgmd-frontend-bucket --policy file://s3-policy.json
```

### 4. Upload Frontend Files
```bash
aws s3 sync frontend/dist/ s3://cgmd-frontend-bucket --delete
```

### 5. Create CloudFront Distribution (CDN)
```bash
aws cloudfront create-distribution \
  --origin-domain-name cgmd-frontend-bucket.s3.amazonaws.com \
  --default-root-object index.html
```

Or create via AWS Console:
1. Go to CloudFront console
2. Create Distribution
3. Origin: Your S3 bucket
4. Default root object: `index.html`
5. Error pages: Add custom error response for 404 → /index.html (for React routing)

### 6. Update Frontend Environment Variable
Update `frontend/.env.production`:
```
VITE_API_URL=https://cgmd-production.us-east-1.elasticbeanstalk.com/api
```

Rebuild and redeploy:
```bash
npm run build
aws s3 sync frontend/dist/ s3://cgmd-frontend-bucket --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR-DIST-ID --paths "/*"
```

## Useful Commands

### Backend (EB)
```bash
eb status                  # Check environment status
eb logs                    # View logs
eb ssh                     # SSH into instance
eb deploy                  # Deploy new version
eb setenv KEY=value        # Set environment variable
eb open                    # Open app in browser
eb terminate              # Delete environment (careful!)
```

### Frontend (S3)
```bash
# Sync new files
aws s3 sync frontend/dist/ s3://cgmd-frontend-1770139819 --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id E23JJN25WLB1B9 --paths "/*"
```

## Cost Estimate
- **EB t3.micro**: FREE (first year) → $8-10/month
- **S3**: ~$0.50/month (for storage)
- **CloudFront**: ~$1/month (first 1TB free)
- **Data Transfer**: Included in free tier
- **Total**: FREE first year, then ~$10/month

## Monitoring
- EB Health: `eb health`
- CloudWatch Logs: AWS Console → CloudWatch
- S3 Usage: AWS Console → S3 → Metrics

## Troubleshooting
```bash
# View recent logs
eb logs --stream

# SSH into instance
eb ssh

# Check Django logs
sudo cat /var/log/eb-engine.log
sudo cat /var/log/web.stdout.log
```

## Hardening: CloudFront OAC + private bucket — ✅ APPLIED (2026-07-07)

**Current state:** the frontend bucket is **private** and served **only** through CloudFront via
**Origin Access Control** (OAC id `E3MZSI8QOW4DL1`). Block Public Access is ON, the public bucket
policy is removed (see [s3-policy.json](s3-policy.json) for the applied OAC policy), and S3 static
website hosting is disabled. The distribution's frontend origin is the S3 **REST** endpoint
(`cgmd-frontend-1770139819.s3.us-east-1.amazonaws.com`), and SPA deep links work via CloudFront
custom error responses (403/404 → `/index.html`, 200). Direct S3 access now returns 403/404.

> Verified: `www.solmuapp.com/` and `/api/*` → 200; direct S3 REST/website endpoints → 403/404.

The migration steps below are retained for reference / disaster recovery.

Migration outline (do in this order; test in the CloudFront console first):

1. **Create an OAC** (CloudFront console → Security → Origin access) of type "S3", signing = SigV4.
2. **Switch the origin** on distribution `E23JJN25WLB1B9`: change the frontend origin from the S3
   *website* endpoint to the S3 *REST* endpoint (`cgmd-frontend-1770139819.s3.us-east-1.amazonaws.com`)
   and attach the OAC. Keep the SPA fallback by configuring a **custom error response**:
   403/404 → `/index.html` (200), since a private bucket returns 403 for missing keys.
3. **Replace the public bucket policy** with an OAC policy that allows only this distribution:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Sid": "AllowCloudFrontOAC",
       "Effect": "Allow",
       "Principal": { "Service": "cloudfront.amazonaws.com" },
       "Action": "s3:GetObject",
       "Resource": "arn:aws:s3:::cgmd-frontend-1770139819/*",
       "Condition": {
         "StringEquals": { "AWS:SourceArn": "arn:aws:cloudfront::<ACCOUNT_ID>:distribution/E23JJN25WLB1B9" }
       }
     }]
   }
   ```
4. **Turn off public access**: bucket → Permissions → Block Public Access = **On**; remove the old
   public-read policy. You can also disable S3 "Static website hosting" (OAC uses the REST endpoint).
5. **Invalidate** (`/*`) and verify: `https://www.solmuapp.com` works; the raw
   `*.s3-website-*` / `*.s3.amazonaws.com` URLs now return **403**.

Deploy commands are unchanged — you still `aws s3 sync` + invalidate; only *how CloudFront reads the
bucket* changes.

## Production Checklist
- [ ] SECRET_KEY set (new, random value)
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS configured
- [ ] DATABASE_URL points to Supabase
- [ ] CORS_ALLOWED_ORIGINS includes CloudFront URL
- [ ] Frontend VITE_API_URL points to EB backend
- [ ] SSL/HTTPS enabled (EB provides this automatically)
- [ ] Migrations run successfully
- [ ] Static files collected
- [ ] CloudFront error pages configured for SPA routing
- [x] Frontend bucket private + served via CloudFront OAC (applied 2026-07-07) — see "Hardening" above
