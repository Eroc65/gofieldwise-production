import { createClient } from "@supabase/supabase-js";

function getSupabaseAdmin() {
  const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error("Supabase env vars missing: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required");
  }
  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

function getOrgIdFromRequest(req) {
  const headerOrgId = req.headers["x-org-id"] || req.headers["x-organization-id"];
  if (typeof headerOrgId === "string" && headerOrgId.trim()) return headerOrgId.trim();
  if (typeof req.body?.org_id === "string" && req.body.org_id.trim()) return req.body.org_id.trim();
  if (typeof req.body?.organizationId === "string" && req.body.organizationId.trim()) {
    return req.body.organizationId.trim();
  }
  if (typeof req.body?.meta?.organizationId === "string" && req.body.meta.organizationId.trim()) {
    return req.body.meta.organizationId.trim();
  }
  if (typeof req.query?.org_id === "string" && req.query.org_id.trim()) return req.query.org_id.trim();
  return null;
}

export async function getSubscriptionStatus(req) {
  const orgId = getOrgIdFromRequest(req);
  if (!orgId) return { active: false, reason: "missing_org_id" };

  const supabase = getSupabaseAdmin();
  const { data, error } = await supabase
    .from("organizations")
    .select("id,is_active,subscription_status")
    .eq("id", orgId)
    .maybeSingle();

  if (error) {
    return { active: false, orgId, reason: "lookup_failed", detail: error.message };
  }
  if (!data) {
    return { active: false, orgId, reason: "org_not_found" };
  }

  const status = String(data.subscription_status || "").toLowerCase();
  const active =
    Boolean(data.is_active) &&
    (status === "active" || status === "trialing");
  return { active, orgId, reason: active ? null : "inactive_subscription" };
}

export function requireSubscription(handler) {
  return async function subscriptionGuard(req, res) {
    const bypass = String(process.env.BYPASS_SUBSCRIPTION_CHECK || "").toLowerCase();
    if (bypass === "1" || bypass === "true" || bypass === "yes" || bypass === "on") {
      return handler(req, res);
    }

    let status;
    try {
      status = await getSubscriptionStatus(req);
    } catch (error) {
      return res.status(500).json({
        ok: false,
        error: "Subscription lookup failed",
        reason: "subscription_lookup_error",
        detail: String(error?.message || error),
      });
    }

    if (status?.reason === "missing_org_id") {
      return res.status(401).json({
        ok: false,
        error: "Organization context required",
        reason: "missing_org_id",
      });
    }

    if (!status?.active) {
      return res.status(402).json({
        ok: false,
        error: "Active subscription required",
        reason: status?.reason || "inactive_subscription",
      });
    }

    return handler(req, res);
  };
}
