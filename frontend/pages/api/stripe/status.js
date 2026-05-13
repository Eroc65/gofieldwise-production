import Stripe from "stripe";

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

function mapStatus(subscriptionStatus) {
  if (subscriptionStatus === "active") return "active";
  if (subscriptionStatus === "trialing") return "trialing";
  if (subscriptionStatus === "past_due" || subscriptionStatus === "unpaid") return "past_due";
  return "inactive";
}

function pickSubscription(subscriptions) {
  if (!Array.isArray(subscriptions) || subscriptions.length === 0) return null;

  const priority = ["trialing", "active", "past_due", "unpaid", "incomplete", "canceled"];
  for (const status of priority) {
    const match = subscriptions.find((sub) => sub.status === status);
    if (match) return match;
  }

  return subscriptions[0] || null;
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

export default async function handler(req, res) {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).json({ ok: false, error: "Method not allowed" });
  }

  if (!process.env.STRIPE_SECRET_KEY) {
    return res.status(500).json({ ok: false, error: "Stripe env vars are not configured" });
  }

  const customerIdFromQuery = req.query?.customerId;
  const customerEmailFromQuery = req.query?.customerEmail;

  const customerId = Array.isArray(customerIdFromQuery) ? customerIdFromQuery[0] : customerIdFromQuery;
  const customerEmailFromQueryNormalized = Array.isArray(customerEmailFromQuery)
    ? customerEmailFromQuery[0]
    : customerEmailFromQuery;

  try {
    const identity = await resolveIdentity(req);
    const resolvedCustomerId = await resolveStripeCustomerId({
      customerId,
      customerEmail: customerEmailFromQueryNormalized || identity?.email || null,
      organizationId: identity?.organizationId || null,
    });

    if (!resolvedCustomerId) {
      return res.status(200).json({
        ok: true,
        status: "inactive",
        customerId: null,
        nextBillingDate: null,
        nextAmount: null,
        currency: null,
        interval: null,
      });
    }

    const subscriptions = await stripe.subscriptions.list({
      customer: resolvedCustomerId,
      status: "all",
      limit: 10,
    });

    const selected = pickSubscription(subscriptions.data || []);

    if (!selected) {
      return res.status(200).json({
        ok: true,
        status: "inactive",
        customerId: resolvedCustomerId,
        nextBillingDate: null,
        nextAmount: null,
        currency: null,
        interval: null,
      });
    }

    const rawStatus = selected.status;
    const status = mapStatus(rawStatus);

    const nextBillingDate = selected.current_period_end
      ? new Date(selected.current_period_end * 1000).toISOString()
      : null;

    const firstLine = selected.items?.data?.[0];
    const price = firstLine?.price;

    return res.status(200).json({
      ok: true,
      status,
      rawStatus,
      customerId: resolvedCustomerId,
      nextBillingDate,
      nextAmount: typeof price?.unit_amount === "number" ? price.unit_amount : null,
      currency: price?.currency || null,
      interval: price?.recurring?.interval || null,
    });
  } catch (error) {
    return res.status(500).json({
      ok: false,
      error: "Failed to load Stripe subscription status",
      detail: String(error?.message || error),
    });
  }
}
