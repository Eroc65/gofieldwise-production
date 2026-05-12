import { createClient } from "@supabase/supabase-js";

function getAdminClient() {
  const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceRoleKey) {
    throw new Error("Supabase env vars missing: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required");
  }
  return createClient(url, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

export async function getOrgByStripeCustomer(stripeCustomerId) {
  if (!stripeCustomerId) return null;
  const supabase = getAdminClient();
  const { data, error } = await supabase
    .from("organizations")
    .select("*")
    .eq("stripe_customer_id", stripeCustomerId)
    .maybeSingle();
  if (error) throw new Error(`getOrgByStripeCustomer failed: ${error.message}`);
  return data;
}

async function resolveOrgId({ orgId, stripeCustomerId }) {
  if (orgId) return orgId;
  const org = await getOrgByStripeCustomer(stripeCustomerId);
  return org?.id || null;
}

export async function updateOrgSubscription(orgOrId, patch) {
  const supabase = getAdminClient();
  const orgId = await resolveOrgId({
    orgId: typeof orgOrId === "string" ? orgOrId : orgOrId?.id,
    stripeCustomerId: patch?.stripeCustomerId,
  });
  if (!orgId) throw new Error("updateOrgSubscription failed: could not resolve organization");

  const orgUpdate = {
    stripe_customer_id: patch.stripeCustomerId ?? null,
    stripe_subscription_id: patch.stripeSubscriptionId ?? null,
    subscription_status: patch.status ?? "inactive",
    is_active: Boolean(patch.planActive),
    updated_at: new Date().toISOString(),
  };

  const { error: orgError } = await supabase
    .from("organizations")
    .update(orgUpdate)
    .eq("id", orgId);
  if (orgError) throw new Error(`organizations update failed: ${orgError.message}`);

  if (patch.stripeSubscriptionId) {
    const subRow = {
      organization_id: orgId,
      provider: "stripe",
      provider_subscription_id: patch.stripeSubscriptionId,
      provider_customer_id: patch.stripeCustomerId ?? null,
      status: patch.status ?? "inactive",
      current_period_end: patch.currentPeriodEnd ?? null,
      metadata: {
        trial_ends_at: patch.trialEndsAt ?? null,
      },
      updated_at: new Date().toISOString(),
    };

    const { error: subError } = await supabase
      .from("subscriptions")
      .upsert(subRow, { onConflict: "provider,provider_subscription_id" });
    if (subError) throw new Error(`subscriptions upsert failed: ${subError.message}`);
  }
}

export async function logSubscriptionEvent(eventRow) {
  const supabase = getAdminClient();
  const row = {
    stripe_event_id: eventRow?.stripeEventId ?? null,
    event_type: eventRow?.eventType ?? null,
    org_id: eventRow?.orgId ?? null,
    payload: eventRow?.payload ?? {},
    error: eventRow?.error ?? null,
    created_at: new Date().toISOString(),
  };

  const { error } = await supabase.from("subscription_events").insert(row);
  if (error) {
    // Do not fail webhook processing if debug event table is missing or unavailable.
    return { ok: false, error: error.message };
  }
  return { ok: true };
}

