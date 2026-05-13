import {
  connectorRegistry,
  universalConnector,
  normalizeRetellWebhook,
  getValidProviders,
} from "../../../lib/connectors";
import { requireSubscription } from "../../../lib/middleware/requireSubscription";

async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false, error: "Method not allowed" });
  }

  try {
    const isRetell =
      req.headers["x-retell-signature"] ||
      req.body?.source === "retell" ||
      req.body?.call ||
      req.body?.call_id;

    const input = isRetell ? normalizeRetellWebhook(req.body || {}) : req.body || {};
    const result = await universalConnector.dispatch(input, {
      requestId: req.headers["x-request-id"] || "",
    });

    if (!result.ok) {
      return res.status(400).json({
        ok: false,
        errors: result.errors || ["Connector dispatch failed"],
        supportedProviders: getValidProviders(),
      });
    }

    return res.status(200).json({
      ok: true,
      provider: result.payload.provider,
      providerStatus: connectorRegistry.get(result.payload.provider)?.status || "unknown",
      delivered: result.result.delivered,
      responseStatus: result.result.responseStatus || null,
      warning: result.result.warning || null,
      error: result.result.error || null,
    });
  } catch (error) {
    return res.status(500).json({
      ok: false,
      error: "Connector dispatch failed unexpectedly",
      detail: String(error?.message || error),
    });
  }
}

export default requireSubscription(handler);
