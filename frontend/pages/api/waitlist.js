const allowedIntegrations = new Set([
  "gbp",
  "google_business_profile",
  "jobber",
  "housecall",
  "housecall_pro",
  "servicetitan",
  "service_titan",
]);

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function normalizeIntegration(value) {
  if (!value || typeof value !== "string") return "";
  return value.trim().toLowerCase().replace(/[^a-z0-9_]+/g, "_");
}

async function forwardToWebhook(payload) {
  const webhookUrl = process.env.WAITLIST_WEBHOOK_URL || process.env.ZAPIER_WAITLIST_WEBHOOK_URL;
  if (!webhookUrl) {
    return { configured: false, forwarded: false };
  }

  const response = await fetch(webhookUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return { configured: true, forwarded: response.ok, status: response.status };
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false, error: "Method not allowed" });
  }

  const email = typeof req.body?.email === "string" ? req.body.email.trim().toLowerCase() : "";
  const name = typeof req.body?.name === "string" ? req.body.name.trim() : "";
  const integration = normalizeIntegration(req.body?.integration);

  if (!isValidEmail(email)) {
    return res.status(400).json({ ok: false, error: "Valid email is required" });
  }

  if (!allowedIntegrations.has(integration)) {
    return res.status(400).json({ ok: false, error: "Valid integration is required" });
  }

  const payload = {
    email,
    name,
    integration,
    source: "integrations_page",
    received_at: new Date().toISOString(),
  };

  try {
    const webhook = await forwardToWebhook(payload);
    return res.status(200).json({
      ok: true,
      persisted: webhook.configured ? webhook.forwarded : false,
      storage: webhook.configured ? "webhook" : "not_configured",
    });
  } catch (error) {
    return res.status(502).json({
      ok: false,
      error: "Waitlist webhook failed",
    });
  }
}
