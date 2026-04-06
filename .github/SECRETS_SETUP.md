# GitHub Secrets Setup (Required)

Configure these repository secrets in Settings > Secrets and variables > Actions.

## Render deploy hooks
- RENDER_FRONTEND_DEPLOY_HOOK_URL
- RENDER_BACKEND_DEPLOY_HOOK_URL
- RENDER_STAGING_FRONTEND_DEPLOY_HOOK_URL
- RENDER_STAGING_BACKEND_DEPLOY_HOOK_URL

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

## Why this file exists
This workspace does not currently have GitHub CLI available, so secrets cannot be set directly from automation here.
