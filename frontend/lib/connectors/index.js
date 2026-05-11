import { toCanonicalPayload, validateCanonicalPayload, getValidProviders } from "./schema";
import { ZapierConnector } from "./zapier";
import { GoogleCalendarConnector } from "./google-calendar";
import { GBPConnector } from "./gbp";
import { JobberConnector } from "./jobber";
import { HousecallProConnector } from "./housecall-pro";
import { ServiceTitanConnector } from "./servicetitan";

export class ConnectorRegistry {
  constructor() {
    this.providers = new Map();
  }

  register(provider, connector) {
    this.providers.set(provider, connector);
  }

  get(provider) {
    return this.providers.get(provider);
  }

  list() {
    return Array.from(this.providers.entries()).map(([provider, connector]) => ({
      provider,
      status: connector.status,
    }));
  }
}

export class UniversalConnector {
  constructor(registry) {
    this.registry = registry;
  }

  async dispatch(input, context = {}) {
    const payload = toCanonicalPayload(input);
    const validation = validateCanonicalPayload(payload);
    if (!validation.ok) {
      return {
        ok: false,
        payload,
        errors: validation.errors,
      };
    }

    const connector = this.registry.get(payload.provider);
    if (!connector) {
      return {
        ok: false,
        payload,
        errors: [`No connector registered for provider: ${payload.provider}`],
      };
    }

    const result = await connector.send(payload, context);
    return {
      ok: Boolean(result.delivered),
      payload,
      result,
    };
  }
}

export function normalizeRetellWebhook(body = {}) {
  const args = body?.call?.args || body?.args || {};
  const transcript = body?.call?.transcript || body?.transcript || "";
  const provider = String(args.provider || body.provider || "zapier").trim().toLowerCase();

  return {
    provider,
    source: "retell",
    eventType: "lead.captured",
    timestamp: new Date().toISOString(),
    contact: {
      name: args.name || body.name || "",
      phone: args.phone || body.phone || "",
      email: args.email || body.email || "",
      address: args.address || body.address || "",
    },
    job: {
      service: args.service || body.service || "",
      description: args.description || transcript || body.description || "",
      preferredTime: args.preferredTime || body.preferredTime || "",
      urgency: args.urgency || body.urgency || "medium",
    },
    meta: {
      externalId: body?.call?.call_id || body.call_id || "",
      organizationId: args.organizationId || body.organizationId || "",
      raw: body,
    },
  };
}

const registry = new ConnectorRegistry();
registry.register("zapier", new ZapierConnector());
registry.register("google-calendar", new GoogleCalendarConnector());
registry.register("gbp", new GBPConnector());
registry.register("jobber", new JobberConnector());
registry.register("housecall-pro", new HousecallProConnector());
registry.register("servicetitan", new ServiceTitanConnector());

export const connectorRegistry = registry;
export const universalConnector = new UniversalConnector(registry);

export { toCanonicalPayload, validateCanonicalPayload, getValidProviders };
