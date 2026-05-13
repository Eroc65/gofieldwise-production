import Stripe from "stripe";
import { bootstrapSupabaseOrg } from "../../../lib/supabase";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "", {
  apiVersion: "2025-04-30.basil",
});

const BACKEND_API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "https://backend-npkg.onrender.com";

function getBearerToken(req) {
  const authHeader = req.headers.authorization || req.headers.Authorization;
  if (!authHeader || Array.isArray(authHeader)) return null;
  if (!String(authHeader).toLowerCase().startsWith("bearer ")) return null;
  return String(authHeader).slice(7).trim();
}

async function resolveIdentity(req) {
  const token = getBearerToken(req);
  if (!token) return null;

  try {
    const response = await fetch(`${BACKEND_API_BASE}/api/auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) return null;
    const payload = await response.json();
    return {
      email: payload?.email || null,
      organizationId: payload?.organization_id ? String(payload.organization_id) : null,
    };
  } catch {
    return null;
  }
}

async function resolveStripeCustomerId({ customerId, customerEmail, organizationId }) {
  if (customerId) return String(customerId);
  if (!customerEmail) return null;

  const customerList = await stripe.customers.list({ email: customerEmail, limit: 10 });
  if (!customerList.data?.length) return null;

  if (organizationId) {
    const orgMatched = customerList.data.find((row) => row.metadata?.organization_id === String(organizationId));
    if (orgMatched?.id) return orgMatched.id;
  }

  return customerList.data[0]?.id || null;
}

function getAppUrl(req) {
  const envUrl = process.env.NEXT_PUBLIC_APP_URL;
  if (envUrl) return envUrl.replace(/\/$/, "");
  const proto = req.headers["x-forwarded-proto"] || "http";
  const host = req.headers.host || "localhost:3000";
  return `${proto}://${host}`;
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false, error: "Method not allowed" });
  }

  if (!process.env.STRIPE_SECRET_KEY || !process.env.STRIPE_PRICE_ID) {
    return res.status(500).json({ ok: false, error: "Stripe env vars are not configured" });
  }

  const requestedAction = req.body?.action || req.body?.mode || "checkout";
  const action = String(requestedAction).toLowerCase();
  const appUrl = getAppUrl(req);
  const identity = await resolveIdentity(req);

  try {
    if (action === "portal") {
      const customerIdFromBody = req.body?.customerId;
      const resolvedCustomerId = await resolveStripeCustomerId({
        customerId: customerIdFromBody,
        customerEmail: identity?.email || null,
        organizationId: identity?.organizationId || null,
      });

      if (!resolvedCustomerId) {
        return res.status(400).json({
          ok: false,
          error: "No Stripe customer found for this account. Start checkout first.",
        });
      }

      const portal = await stripe.billingPortal.sessions.create({
        customer: resolvedCustomerId,
        return_url: `${appUrl}/billing`,
      });
      return res.status(200).json({ ok: true, url: portal.url });
    }

    if (action !== "checkout") {
      return res.status(400).json({
        ok: false,
        error: "Unsupported action. Use action/mode: checkout or portal",
      });
    }

    const successUrl = req.body?.successUrl || `${appUrl}/billing?checkout=success`;
    const cancelUrl = req.body?.cancelUrl || `${appUrl}/billing?checkout=cancel`;
    const customerEmail = req.body?.customerEmail || identity?.email || null;

    let resolvedCustomerId = await resolveStripeCustomerId({
      customerId: req.body?.customerId,
      customerEmail,
      organizationId: identity?.organizationId || null,
    });

    if (!resolvedCustomerId && customerEmail) {
      const createdCustomer = await stripe.customers.create({
        email: customerEmail,
        metadata: {
          organization_id: identity?.organizationId || "",
          source: "gofieldwise_checkout",
        },
      });
      resolvedCustomerId = createdCustomer.id;

      // Bootstrap the Supabase org row now so the webhook's
      // getOrgByStripeCustomer() lookup succeeds when it fires.
      // Non-fatal: updateOrgSubscription has a safety-net fallback.
      await bootstrapSupabaseOrg(createdCustomer.id, {
        fastapiOrgId: identity?.organizationId || null,
        ownerEmail: customerEmail || null,
      }).catch((err) =>
        console.error("[checkout] bootstrapSupabaseOrg failed:", err?.message)
      );
    }

    const metadata = {
      ...(req.body?.metadata || {}),
      organization_id: identity?.organizationId || "",
      user_email: identity?.email || customerEmail || "",
    };

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      line_items: [{ price: process.env.STRIPE_PRICE_ID, quantity: 1 }],
      success_url: successUrl,
      cancel_url: cancelUrl,
      ...(resolvedCustomerId ? { customer: resolvedCustomerId } : {}),
      ...(!resolvedCustomerId && customerEmail ? { customer_email: customerEmail } : {}),
      allow_promotion_codes: true,
      metadata,
    });

    return res.status(200).json({ ok: true, url: session.url, id: session.id });
  } catch (error) {
    return res.status(500).json({
      ok: false,
      error: "Stripe checkout action failed",
      detail: String(error?.message || error),
    });
  }
}
