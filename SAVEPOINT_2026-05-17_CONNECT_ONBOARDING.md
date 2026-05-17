# Savepoint: GoFieldWise Connect Onboarding

Created: 2026-05-17 04:44:39 -05:00

Git commit at savepoint: `df45365 Add Connect Center onboarding wizard`

## Completed

- Stripe checkout end-to-end path proven in production test mode.
- Vercel Stripe webhook provisions operator invites through Render FastAPI.
- Operator setup links are delivered by Resend email.
- `/operator/setup` verifies and redeems one-time setup keys.
- Operator redemption creates a dashboard login and returns a FastAPI JWT.
- Operators redirect to `/connect-center` after setup.
- `/connect-center` is now a first-run activation wizard.
- Connect onboarding saves authenticated progress through `/api/connect/settings`.
- Returning operators load saved Connect settings.
- Completion progress is visible.
- Completed setup state shows: “Your AI front office setup is ready. Place a test call to confirm the experience.”
- Help CTA uses `support@gofieldwise.com`.
- “Book Setup Call” is not used.
- Supabase missing-table webhook warnings are suppressed as quiet skips when optional Supabase mirror tables are absent.

## Connect Wizard Steps

- Business profile
- Trade type
- Service area
- Business hours
- Owner notification phone
- Backup contact
- Emergency rules
- After-hours customer message
- Workflow mode: standalone, sidecar, hybrid
- CRM destination
- Test AI call

## Verification

- Backend focused tests passed: `8 passed`.
- Frontend production build passed.
- Vercel frontend deployed and aliased to production.
- Render backend deployed live.
- Live authenticated smoke test passed:
  - signup: `200`
  - GET `/api/connect/settings`: `200`
  - PATCH `/api/connect/settings`: `200`
- Live `/connect-center` returned `200`.

## Recent Important Commits

- `df45365 Add Connect Center onboarding wizard`
- `35cad40 Email operator setup links after checkout`
- `bdce6b6 Add operator connect center landing page`
- `8992fa7 Secure operator invite provisioning logs`
- `c88311b Provision operator invite after Stripe checkout`

## Current Production Notes

- Vercel Stripe environment was restored to live mode after test-mode validation.
- Test Stripe subscription from validation was canceled.
- Temporary Stripe test webhook endpoint was deleted.
- Resend setup email delivery was confirmed by inbox receipt.
- The pasted test setup key should be treated as burned and not reused.
