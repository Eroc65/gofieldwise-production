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
        const org = await getOrgByStripeCustomer(session.customer);
        orgId = org?.id || null;

        const planActive =
          subscription.status === "active" || subscription.status === "trialing";

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

        // Sync is_active to FastAPI Postgres
        await syncFastapiOrgActive({
          orgId: session.metadata?.organization_id,
          isActive: planActive,
          subscriptionStatus: subscription.status,
        });
        break;
      }

      case "customer.subscription.updated":
      case "customer.subscription.deleted": {
        const subscription = event.data.object;
        const org = await getOrgByStripeCustomer(subscription.customer);
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
        const org = await getOrgByStripeCustomer(invoice.customer);
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
