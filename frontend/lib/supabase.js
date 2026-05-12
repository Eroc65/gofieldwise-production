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

/**
 * Upsert a minimal Supabase organizations row keyed on stripe_customer_id.
 * Safe to call multiple times -- uses ignoreDuplicates so it never overwrites
 * an existing row's name or other fields.
 *
 * Call this in checkout.js immediately after stripe.customers.create() so the
 * row exists before the webhook fires. The webhook's updateOrgSubscription also
 * has a safety-net call for customers created before this was deployed.
 */
export async function bootstrapSupabaseOrg(stripeCustomerId, { ownerEmail, fastapiOrgId } = {}) {
  if (!stripeCustomerId) return;
  const supabase = getAdminClient();
  const name =
    ownerEmail
      ? `Org (${ownerEmail})`
      : fastapiOrgId
      ? `org_${fastapiOrgId}`
      : `org_stripe_${stripeCustomerId}`;
  const row = {
    name,
    stripe_customer_id: stripeCustomerId,
    owner_email: ownerEmail || null,
    billing_email: ownerEmail || null,
  };
  const { error } = await supabase
    .from("organizations")
    .upsert(row, { onConflict: "stripe_customer_id", ignoreDuplicates: true });
  if (error) {
    // Non-fatal: log and continue. The safety-net in updateOrgSubscription will
    // attempt another bootstrap when the webhook arrives.
    console.error("[supabase] bootstrapSupabaseOrg error:", error.message);
  }
}

export async function updateOrgSubscription(orgOrId, patch) {
  const supabase = getAdminClient();
  let orgId = await resolveOrgId({
    orgId: typeof orgOrId === "string" ? orgOrId : orgOrId?.id,
    stripeCustomerId: patch?.stripeCustomerId,
  });

  // Safety net: if the Supabase row was never bootstrapped (e.g., the customer
  // was created before bootstrapSupabaseOrg was added to checkout.js, or the
  // bootstrap call failed silently), create it now using the stripe_customer_id
  // as the unique anchor. Then re-resolve the UUID.
  if (!orgId && patch?.stripeCustomerId) {
    await bootstrapSupabaseOrg(patch.stripeCustomerId, {});
    const org = await getOrgByStripeCustomer(patch.stripeCustomerId);
    orgId = org?.id || null;
  }

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

  // Upsert on stripe_event_id so Stripe retries are idempotent.
  // The unique index is WHERE stripe_event_id IS NOT NULL, so null values
  // (e.g. manual debug rows) still insert as new rows.
  const { error } = await supabase
    .from("subscription_events")
    .upsert(row, { onConflict: "stripe_event_id", ignoreDuplicates: true });
  if (error) {
    // Do not fail webhook processing if the event table is unavailable.
    return { ok: false, error: error.message };
  }
  return { ok: true };
}
