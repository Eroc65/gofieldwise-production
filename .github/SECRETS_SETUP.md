# GitHub Secrets Setup (Required)

Configure these repository secrets in Settings > Secrets and variables > Actions.

## GitHub CLI (Workspace Ready)
- GitHub CLI is installed in this workspace (`gh 2.89.0`).
- If authentication expires, re-authenticate from this workspace:
	- `gh auth login`
	- choose: `GitHub.com` -> `HTTPS` -> `Login with a web browser`
- Verify:
	- `gh auth status`

## Optional: Set Secrets via CLI
After authentication, you can set secrets directly from terminal:
- `gh secret set RENDER_FRONTEND_DEPLOY_HOOK_URL --body "<value>"`
- `gh secret set RENDER_BACKEND_DEPLOY_HOOK_URL --body "<value>"`
- `gh secret set RENDER_STAGING_FRONTEND_DEPLOY_HOOK_URL --body "<value>"`
- `gh secret set RENDER_STAGING_BACKEND_DEPLOY_HOOK_URL --body "<value>"`
- `gh secret set STAGING_API_BASE_URL --body "<value>"`
- `gh secret set STAGING_SMOKE_EMAIL --body "<value>"`
- `gh secret set STAGING_SMOKE_PASSWORD --body "<value>"`
- `gh secret set PRODUCTION_API_BASE_URL --body "<value>"`
- `gh secret set PRODUCTION_SMOKE_EMAIL --body "<value>"`
- `gh secret set PRODUCTION_SMOKE_PASSWORD --body "<value>"`

## Automation Script (Recommended)
Use `.github/scripts/github-ops.ps1` for repeatable operations.

Examples:
- Check secret health and latest workflow runs:
	- `powershell -ExecutionPolicy Bypass -File .github/scripts/github-ops.ps1 -Action status`
- Check only missing secrets:
	- `powershell -ExecutionPolicy Bypass -File .github/scripts/github-ops.ps1 -Action check-secrets`
- Trigger staging deploy workflow:
	- `powershell -ExecutionPolicy Bypass -File .github/scripts/github-ops.ps1 -Action trigger-staging`
- Trigger production deploy workflow:
	- `powershell -ExecutionPolicy Bypass -File .github/scripts/github-ops.ps1 -Action trigger-production`
- Validate deploy hook secret presence before triggering deploys:
	- `powershell -ExecutionPolicy Bypass -File .github/scripts/github-ops.ps1 -Action validate-hooks`

## Current Status
- Validate live secret health with:
	- `powershell -ExecutionPolicy Bypass -File .github/scripts/github-ops.ps1 -Action check-secrets`
- Validate latest workflow runs with:
	- `powershell -ExecutionPolicy Bypass -File .github/scripts/github-ops.ps1 -Action status`

## Render deploy hooks
- RENDER_FRONTEND_DEPLOY_HOOK_URL
- RENDER_BACKEND_DEPLOY_HOOK_URL
- RENDER_STAGING_FRONTEND_DEPLOY_HOOK_URL
- RENDER_STAGING_BACKEND_DEPLOY_HOOK_URL

Validation behavior:
- Staging and production deploy workflows now fail fast unless each deploy hook matches Render format:
	- `https://api.render.com/deploy/srv-...?...`
- This prevents accidental values like database URLs from silently breaking deploy routing.

## Post-deploy smoke targets (staging)
- STAGING_API_BASE_URL
- STAGING_SMOKE_EMAIL
- STAGING_SMOKE_PASSWORD

## Post-deploy smoke targets (production)
- PRODUCTION_API_BASE_URL
- PRODUCTION_SMOKE_EMAIL
- PRODUCTION_SMOKE_PASSWORD

## Suggested values
- API base URLs should be full HTTPS origins (for example: https://backend-staging.example.com).
- Smoke user should be an owner/admin account in the target organization.
- Deploy hook secrets must be Render deploy hook `https://` URLs. Do not use database URLs (for example `postgresql://...`) in deploy hook secrets.

## Activation Controls
- Optional strict messaging mode:
	- `REQUIRE_REAL_SMS_DELIVERY=true`
	- When enabled, SMS dispatch fails if Twilio credentials are not configured (no simulation fallback).
- Tenant-level communication credentials are managed in the Platform Console (`/platform`) via `Communication Tenant Profile`.

## Live Activation Checklist Script
Run this from `backend/` to verify production readiness for AI guide + comm profile + reactivation:
- `ACTIVATION_API_BASE_URL=<https url> ACTIVATION_EMAIL=<owner/admin email> ACTIVATION_PASSWORD=<password> python scripts/activation_checklist.py`

## Why this file exists
This workspace is GitHub CLI-ready and includes repeatable `gh` operations for secrets and deploy workflow control.
