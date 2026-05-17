import Stripe from "stripe";
import {
  getOrgByStripeCustomer,
  updateOrgSubscription,
  logSubscriptionEvent,
} from "../../../lib/supabase";

export const config = {
  api: { bodyParser: false },
};

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "", {
  apiVersion: "2025-04-30.basil",
});

const BACKEND_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://backend-npkg.onrender.com";

async function getRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

/**
 * After updating Supabase, notify FastAPI so it can flip org.is_active in its
 * own Postgres. Non-fatal: a failure here is logged but never throws, so the
 * webhook always returns 200 to Stripe.
 */
async function syncFastapiOrgActive({ orgId, isActive, subscriptionStatus }) {
  const secret = process.env.BILLING_SYNC_SECRET;
  if (!secret || !orgId) return;

  try {
    const res = await fetch(`${BACKEND_API_BASE}/api/billing/sync`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Billing-Sync-Secret": secret,
      },
      body: JSON.stringify({
        org_id: Number(orgId),
        is_active: Boolean(isActive),
        subscription_status: subscriptionStatus ?? null,
      }),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error(`[stripe/webhook] billing sync returned ${res.status}: ${text}`);
    }
  } catch (err) {
    console.error("[stripe/webhook] billing sync fetch failed:", err?.message);
  }
}

/**
 * Provision the one-time operator setup key after checkout. This stays separate
 * from billing sync so onboarding logic does not get tangled into subscription
 * state updates.
 */
async function provisionOperatorInvite({
  organizationId,
  email,
  ownerName,
  businessName,
  phone,
  stripeCustomerId,
  stripeSubscriptionId,
}) {
  const secret = process.env.OPERATOR_INVITE_SYNC_SECRET || process.env.BILLING_SYNC_SECRET;
  if (!secret || !organizationId) return null;

  try {
    const res = await fetch(`${BACKEND_API_BASE}/api/operator/invite/provision`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Billing-Sync-Secret": secret,
      },
      body: JSON.stringify({
        organization_id: Number(organizationId),
        email: email || null,
        owner_name: ownerName || null,
        business_name: businessName || null,
        phone: phone || null,
        source: "stripe_checkout",
        stripe_customer_id: stripeCustomerId || null,
        stripe_subscription_id: stripeSubscriptionId || null,
        expires_hours: 72,
        setup_base_url: process.env.NEXT_PUBLIC_APP_URL || "https://gofieldwise.com",
      }),
    });

    const payload = await res.json().catch(() => null);
    if (!res.ok) {
      console.error(`[stripe/webhook] operator invite provision returned ${res.status}:`, payload);
      return null;
    }

    console.log(
      `[stripe/webhook] operator invite provisioned: invite_id=${payload?.invite_id}, org=${payload?.organization_id}`
    );
    return payload;
  } catch (err) {
    console.error("[stripe/webhook] operator invite provision failed:", err?.message);
    return null;
  }
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getSetupEmailText({ setupUrl, organizationName, expiresAt, supportEmail }) {
  const accountName = organizationName || "your GoFieldWise account";
  const expiration = expiresAt
    ? `This setup link expires on ${new Date(expiresAt).toLocaleString("en-US", {
        timeZone: "America/Chicago",
        dateStyle: "medium",
        timeStyle: "short",
      })} Central.`
    : "This setup link expires in 72 hours.";

  return [
    "Your GoFieldWise Connect account is ready.",
    "",
    `Account: ${accountName}`,
    "",
    "Create your operator login here:",
    setupUrl,
    "",
    expiration,
    "",
    `Need help? Contact ${supportEmail}.`,
    "",
    "GoFieldWise Team",
  ].join("\n");
}

function getSetupEmailHtml({ setupUrl, organizationName, expiresAt, supportEmail }) {
  const accountName = escapeHtml(organizationName || "your GoFieldWise account");
  const expiration = expiresAt
    ? `This setup link expires on ${escapeHtml(
        new Date(expiresAt).toLocaleString("en-US", {
          timeZone: "America/Chicago",
          dateStyle: "medium",
          timeStyle: "short",
        })
      )} Central.`
    : "This setup link expires in 72 hours.";

  return `
    <div style="font-family:Arial,sans-serif;line-height:1.6;color:#10212b;max-width:620px;margin:0 auto">
      <p style="font-size:14px;color:#536b76;margin:0 0 16px">GoFieldWise Connect</p>
      <h1 style="font-size:26px;line-height:1.2;margin:0 0 14px;color:#0b2633">Your operator dashboard is ready.</h1>
      <p style="font-size:16px;margin:0 0 12px">Create your GoFieldWise operator login for <strong>${accountName}</strong>.</p>
      <p style="font-size:16px;margin:0 0 24px">${escapeHtml(expiration)}</p>
      <p style="margin:0 0 28px">
        <a href="${escapeHtml(setupUrl)}" style="display:inline-block;background:#0b2633;color:#fff;text-decoration:none;font-weight:700;padding:13px 18px;border-radius:8px">
          Create Operator Login
        </a>
      </p>
      <p style="font-size:13px;color:#536b76;margin:0 0 8px">If the button does not work, paste this link into your browser:</p>
      <p style="font-size:13px;word-break:break-all;margin:0 0 24px"><a href="${escapeHtml(setupUrl)}">${escapeHtml(setupUrl)}</a></p>
      <hr style="border:0;border-top:1px solid #e4edf0;margin:24px 0" />
      <p style="font-size:13px;color:#536b76;margin:0">Need help? Contact <a href="mailto:${escapeHtml(supportEmail)}">${escapeHtml(supportEmail)}</a>.</p>
    </div>
  `;
}

async function sendOperatorSetupEmail({
  to,
  setupUrl,
  organizationName,
  expiresAt,
  inviteId,
}) {
  const resendApiKey = process.env.RESEND_API_KEY;
  const supportEmail = process.env.SUPPORT_EMAIL || "support@gofieldwise.com";
  const from = process.env.SETUP_EMAIL_FROM || `GoFieldWise <${supportEmail}>`;

  if (!to || !setupUrl) {
    console.warn(`[stripe/webhook] setup email skipped: invite_id=${inviteId || "unknown"}, reason=missing_recipient_or_url`);
    return { sent: false, reason: "missing_recipient_or_url" };
  }

  if (!resendApiKey) {
    console.warn(`[stripe/webhook] setup email skipped: invite_id=${inviteId || "unknown"}, reason=resend_not_configured`);
    return { sent: false, reason: "resend_not_configured" };
  }

  try {
    const emailPayload = {
      from,
      to,
      subject: "Set up your GoFieldWise Operator Dashboard",
      text: getSetupEmailText({ setupUrl, organizationName, expiresAt, supportEmail }),
      html: getSetupEmailHtml({ setupUrl, organizationName, expiresAt, supportEmail }),
    };

    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${resendApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(emailPayload),
    });

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      console.error(
        `[stripe/webhook] setup email failed: invite_id=${inviteId || "unknown"}, status=${response.status}, message=${payload?.message || payload?.error || "unknown"}`
      );
      return { sent: false, reason: "resend_error" };
    }

    console.log(
      `[stripe/webhook] setup email queued: invite_id=${inviteId || "unknown"}, email_id=${payload?.id || "unknown"}`
    );
    return { sent: true, id: payload?.id || null };
  } catch (err) {
    console.error(
      `[stripe/webhook] setup email request failed: invite_id=${inviteId || "unknown"}, message=${err?.message || "unknown"}`
    );
    return { sent: false, reason: "request_failed" };
  }
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  if (!process.env.STRIPE_SECRET_KEY || !process.env.STRIPE_WEBHOOK_SECRET) {
    return res.status(500).json({ error: "Stripe webhook env vars are not configured" });
  }

  const rawBody = await getRawBody(req);
  const sig = req.headers["stripe-signature"];

  let event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, sig, process.env.STRIPE_WEBHOOK_SECRET);
  } catch (error) {
    return res.status(400).json({ error: `Webhook error: ${error.message}` });
  }

  let orgId = null;
  let eventErr = null;

  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object;
        if (session.mode !== "subscription") break;

        const subscription = await stripe.subscriptions.retrieve(session.subscription);

        // Supabase lookup is best-effort — don't let it abort the FastAPI sync
        let org = null;
        try {
          org = await getOrgByStripeCustomer(session.customer);
        } catch (supabaseErr) {
          console.error(
            `[stripe/webhook] getOrgByStripeCustomer failed (non-fatal):`,
            supabaseErr?.message
          );
        }
        orgId = org?.id || null;

        const planActive =
          subscription.status === "active" || subscription.status === "trialing";

        try {
          await updateOrgSubscription(orgId || session.metadata?.organization_id, {
            stripeCustomerId: session.customer,
            stripeSubscriptionId: subscription.id,
            status: subscription.status,
            planActive,
            currentPeriodEnd: subscription.current_period_end
              ? new Date(subscription.current_period_end * 1000).toISOString()
              : null,
            trialEndsAt: subscription.trial_end
              ? new Date(subscription.trial_end * 1000).toISOString()
              : null,
          });
        } catch (supabaseUpdateErr) {
          console.error(
            `[stripe/webhook] updateOrgSubscription failed (non-fatal):`,
            supabaseUpdateErr?.message
          );
        }

        // Sync is_active to FastAPI Postgres — always runs regardless of Supabase state
        await syncFastapiOrgActive({
          orgId: session.metadata?.organization_id,
          isActive: planActive,
          subscriptionStatus: subscription.status,
        });

        if (planActive && session.metadata?.organization_id) {
          const invite = await provisionOperatorInvite({
            organizationId: session.metadata.organization_id,
            email: session.customer_details?.email || session.customer_email || null,
            ownerName: session.customer_details?.name || session.metadata?.owner_name || null,
            businessName:
              session.metadata?.business_name ||
              session.metadata?.organization_name ||
              session.customer_details?.name ||
              null,
            phone: session.customer_details?.phone || session.metadata?.phone || null,
            stripeCustomerId: session.customer,
            stripeSubscriptionId: subscription.id,
          });

          if (invite?.setup_url) {
            console.log(
              `[stripe/webhook] Operator invite ready for org ${session.metadata.organization_id}: invite_id=${invite.invite_id}`
            );
            await sendOperatorSetupEmail({
              to: session.customer_details?.email || session.customer_email || null,
              setupUrl: invite.setup_url,
              organizationName: invite.organization_name,
              expiresAt: invite.expires_at,
              inviteId: invite.invite_id,
            });
          }
        }
        break;
      }

      case "customer.subscription.updated":
      case "customer.subscription.deleted": {
        const subscription = event.data.object;
        let org = null;
        try {
          org = await getOrgByStripeCustomer(subscription.customer);
        } catch (supabaseErr) {
          console.error(
            `[stripe/webhook] getOrgByStripeCustomer failed (non-fatal):`,
            supabaseErr?.message
          );
        }
        orgId = org?.id || null;

        const planActive =
          subscription.status === "active" || subscription.status === "trialing";

        // Pass stripeCustomerId so updateOrgSubscription can resolve (and
        // bootstrap if needed) even when orgId is null.
        await updateOrgSubscription(orgId, {
          stripeCustomerId: subscription.customer,
          stripeSubscriptionId: subscription.id,
          status: subscription.status,
          planActive,
          currentPeriodEnd: subscription.current_period_end
            ? new Date(subscription.current_period_end * 1000).toISOString()
            : null,
          trialEndsAt: subscription.trial_end
            ? new Date(subscription.trial_end * 1000).toISOString()
            : null,
        });

        // Sync is_active to FastAPI Postgres via Supabase org row → metadata
        // The Supabase org row doesn't store fastapi_org_id yet, so we rely on
        // the org having been bootstrapped with organization_id in metadata.
        // This is a best-effort call; failures are logged, not re-thrown.
        if (org?.owner_email) {
          // owner_email stored on bootstrap; FastAPI billing/sync requires org_id int.
          // Without the fastapi_org_id we skip the sync here — it will be caught
          // on the next checkout.session.completed which does carry organization_id.
          console.log(
            `[stripe/webhook] subscription.updated for org ${org.id} (${org.owner_email}) — ` +
            `FastAPI sync skipped (no fastapi_org_id on Supabase row yet)`
          );
        }
        break;
      }

      case "invoice.paid":
      case "invoice.payment_failed": {
        const invoice = event.data.object;
        let org = null;
        try {
          org = await getOrgByStripeCustomer(invoice.customer);
        } catch (supabaseErr) {
          console.error(
            `[stripe/webhook] getOrgByStripeCustomer failed (non-fatal):`,
            supabaseErr?.message
          );
        }
        orgId = org?.id || null;

        if (event.type === "invoice.payment_failed" && orgId) {
          await updateOrgSubscription(orgId, {
            status: "past_due",
            planActive: false,
          });
        }
        break;
      }

      default:
        break;
    }
  } catch (error) {
    eventErr = error.message;
    console.error(`[stripe/webhook] handler error for ${event.type}:`, error.message);
  }

  await logSubscriptionEvent({
    stripeEventId: event.id,
    eventType: event.type,
    orgId,
    payload: event.data.object,
    error: eventErr,
  });

  return res.status(200).json({ received: true, type: event.type });
}
