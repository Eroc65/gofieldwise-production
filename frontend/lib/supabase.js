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
 * Safe to call multiple times — uses ignoreDuplicates so it never overwrites
 * an existing row's name or other fields.
 *
 * Call this in checkout.js immediately after stripe.customers.create() so the
 * row exists before the webhook fires. The webhook's updateOrgSubscription also
 * has a safety-net call for customers created before this was deployed.
 *
 * @param {string} stripeCustomerId
 * @param {{ ownerEmail?: string|null, fastapiOrgId?: string|null }} [opts]
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

  if (!