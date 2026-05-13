const VALID_PROVIDERS = new Set([
  "zapier",
  "google-calendar",
  "gbp",
  "jobber",
  "housecall-pro",
  "servicetitan",
]);

function normalizeString(value) {
  return typeof value === "string" ? value.trim() : "";
}

function normalizeEmail(value) {
  const email = normalizeString(value).toLowerCase();
  if (!email) return "";
  const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  return isValid ? email : "";
}

function normalizePhone(value) {
  const phone = normalizeString(value);
  if (!phone) return "";
  return phone.replace(/[^\d+]/g, "");
}

export function toCanonicalPayload(input = {}) {
  const provider = normalizeString(input.provider).toLowerCase();
  const now = new Date().toISOString();

  return {
    provider,
    source: normalizeString(input.source) || "unknown",
    eventType: normalizeString(input.eventType) || "lead.created",
    timestamp: normalizeString(input.timestamp) || now,
    contact: {
      name: normalizeString(input.contact?.name || input.name),
      phone: normalizePhone(input.contact?.phone || input.phone),
      email: normalizeEmail(input.contact?.email || input.email),
      address: normalizeString(input.contact?.address || input.address),
    },
    job: {
      service: normalizeString(input.job?.service || input.service),
      description: normalizeString(input.job?.description || input.description),
      preferredTime: normalizeString(input.job?.preferredTime || input.preferredTime),
      urgency: normalizeString(input.job?.urgency || input.urgency) || "medium",
    },
    meta: {
      externalId: normalizeString(input.meta?.externalId || input.externalId),
      organizationId: normalizeString(input.meta?.organizationId || input.organizationId),
      raw: input.meta?.raw || input.raw || null,
    },
  };
}

export function validateCanonicalPayload(payload = {}) {
  const errors = [];

  if (!VALID_PROVIDERS.has(payload.provider)) {
    errors.push("provider must be one of: " + Array.from(VALID_PROVIDERS).join(", "));
  }

  if (!payload.contact?.name && !payload.contact?.phone && !payload.contact?.email) {
    errors.push("at least one contact field (name, phone, email) is required");
  }

  if (!payload.job?.service && !payload.job?.description) {
    errors.push("at least one job field (service or description) is required");
  }

  return {
    ok: errors.length === 0,
    errors,
  };
}

export function getValidProviders() {
  return Array.from(VALID_PROVIDERS);
}
