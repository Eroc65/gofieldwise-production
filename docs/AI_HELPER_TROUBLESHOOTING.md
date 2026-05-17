# GoFieldWise AI Helper Troubleshooting Playbook

This document is the source playbook for the admin AI helper. Use it to diagnose customer setup, billing, voice, SMS, lead, and integration issues.

Start by matching the user's issue to a trigger, then work the steps in order. Do not expose secrets in logs, chat, screenshots, or customer-facing notes.

## Stripe Checkout To Operator Setup

**Trigger:** Customer paid but did not receive or cannot use operator setup link.

**Systems:** Vercel Stripe webhook, FastAPI billing sync, operator_invites, Render backend

**Steps:**
1. Confirm Stripe has checkout.session.completed for the customer.
2. Check Vercel env has STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, BILLING_SYNC_SECRET, OPERATOR_INVITE_SYNC_SECRET.
3. Check Render backend env has BILLING_SYNC_SECRET and OPERATOR_INVITE_SYNC_SECRET with the same value as Vercel.
4. Confirm /api/billing/sync returned 200 and org.is_active is true.
5. Confirm /api/operator/invite/provision returned 200 and created a pending invite.
6. Send the setup_url again or create a replacement invite if the key expired or was redeemed by mistake.

**Healthy signal:** checkout.session.completed provisions a pending invite and /operator/setup?key=... verifies successfully.

**Escalate if:** Stripe webhook is receiving events but Render returns 401/403/404/5xx for provision.

## Connect Center FastAPI Login

**Trigger:** Connect Center loads but API calls fail with 401/403.

**Systems:** operator setup, FastAPI JWT, frontend localStorage, subscription gate

**Steps:**
1. Confirm the customer redeemed an operator invite and received a FastAPI JWT.
2. Check browser localStorage key fdp.dispatch.token exists.
3. Call /api/auth/me with the bearer token and verify organization_id and role=owner.
4. If response is 402, verify org.is_active and billing sync state.
5. If response is 401, ask customer to log out and redeem/login again.

**Healthy signal:** /api/auth/me returns the owner user and protected Connect Center calls return 200.

**Escalate if:** JWT is valid but protected endpoints still reject the active organization.

## Connect Service Key

**Trigger:** Connect webhook or connector calls fail authorization.

**Systems:** Vercel, Render, CONNECT_SERVICE_KEY

**Steps:**
1. Confirm CONNECT_SERVICE_KEY exists on both Vercel and Render.
2. Confirm the values match without exposing the secret in logs.
3. Redeploy or restart both services after changing the value.
4. Retry the logged-in /connect-center flow.

**Healthy signal:** Connector calls authenticate and return expected Connect settings/status.

**Escalate if:** Both environments match but requests still fail signature or service-key checks.

## Adrian Voice AI Calls

**Trigger:** Demo call or AI receptionist call does not start, drops, or lacks transcript.

**Systems:** Retell, Twilio, lead intake, transcript stream

**Steps:**
1. Confirm RETELL_API_KEY, RETELL_FROM_NUMBER, and RETELL_AGENT_ID are set.
2. Confirm Twilio phone/SMS env vars are set and the number can call outbound.
3. Create a test demo call and capture call_id.
4. Check Retell events are received and transcript stream endpoint is registered.
5. If transcript is missing, inspect Retell event payload and agent configuration.

**Healthy signal:** Demo call starts, transcript events arrive, and lead/intake records are updated.

**Escalate if:** Retell accepts the call request but no webhook or transcript event reaches the backend.

## Post-Call SMS And Follow-Up Reminders

**Trigger:** Customer does not receive SMS or reminders stay pending.

**Systems:** Twilio, Reminder, SmsOptOut, delivery status webhook

**Steps:**
1. Confirm Twilio credentials and from number or messaging service are configured.
2. Check the recipient is not listed in sms_opt_outs.
3. Confirm reminder status, dispatch_attempts, and last_dispatch_error.
4. Check /api/integrations/twilio/status events for delivered/failed state.
5. Retry dispatch after correcting phone number or Twilio credentials.

**Healthy signal:** Reminder transitions to sent/delivered and Twilio status callback is processed.

**Escalate if:** Twilio reports delivered but the customer still receives nothing.

## Lead Intake, Qualification, Booking

**Trigger:** Lead form submits but no lead appears, or qualified lead cannot book.

**Systems:** public intake, Lead, Customer, Job, Technician scheduling

**Steps:**
1. Confirm public intake endpoint returns 201 and creates a Lead.
2. Validate name, email, and phone formatting errors are not blocking intake.
3. Check lead status transition rules: new -> contacted/qualified -> converted.
4. Before booking, confirm technician exists and scheduling conflict check passes.
5. If booking fails, inspect lead activity history and job creation response.

**Healthy signal:** Lead can be created, qualified, converted to customer/job, and dispatched.

**Escalate if:** Valid lead payload creates no database row or activity event.

## Jobber OAuth Token Health

**Trigger:** Jobber sync fails or admin token risk shows warning/critical.

**Systems:** Jobber OAuth config, token refresh, CRM hub

**Steps:**
1. Open Admin -> Jobber Token Expiry Watch.
2. If critical, click Refresh now.
3. Confirm checked/refreshed counts and inspect failed configs.
4. If refresh fails, reconnect Jobber OAuth for that tenant.

**Healthy signal:** Token risk returns ok and seconds_remaining is above warning threshold.

**Escalate if:** Refresh endpoint fails for all tenants or OAuth credentials are missing.

## Billing And Active Subscription Gate

**Trigger:** Paid customer sees subscription required or inactive account.

**Systems:** Stripe, Supabase subscription row, FastAPI Organization.is_active

**Steps:**
1. Confirm Stripe subscription status is active or trialing.
2. Confirm Vercel webhook updated Supabase subscription status.
3. Confirm /api/billing/sync updated FastAPI org.is_active.
4. If org_id metadata is missing, map the Stripe customer to the FastAPI org and re-run sync.

**Healthy signal:** Organization.is_active is true and protected business endpoints do not return 402.

**Escalate if:** Stripe is active but webhook logs show missing organization_id metadata.
