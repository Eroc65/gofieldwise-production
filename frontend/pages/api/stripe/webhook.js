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
  apiVersion: "2024-06-20",
});

async function getRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
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

        await updateOrgSubscription(orgId || session.metadata?.org_id, {
          stripeCustomerId: session.customer,
          stripeSubscriptionId: subscription.id,
          status: subscription.status,
          planActive: subscription.status === "active" || subscription.status === "trialing",
          currentPeriodEnd: new Date(subscription.current_period_end * 1000).toISOString(),
          trialEndsAt: subscription.trial_end
            ? new Date(subscription.trial_end * 1000).toISOString()
            : null,
        });
        break;
      }

      case "customer.subscription.updated":
      case "customer.subscription.deleted": {
        const subscription = event.data.object;
        const org = await getOrgByStripeCustomer(subscription.customer);
        orgId = org?.id || null;

        if (orgId) {
          await updateOrgSubscription(orgId, {
            stripeCustomerId: subscription.customer,
            stripeSubscriptionId: subscription.id,
            status: subscription.status,
            planActive: subscription.status === "active" || subscription.status === "trialing",
            currentPeriodEnd: new Date(subscription.current_period_end * 1000).toISOString(),
            trialEndsAt: subscription.trial_end
              ? new Date(subscription.trial_end * 1000).toISOString()
              : null,
          });
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
