import { BaseConnector } from "./base";

export class GBPConnector extends BaseConnector {
  constructor(options = {}) {
    super("gbp", options);
  }

  get status() {
    return "beta";
  }

  async send(payload) {
    const webhookUrl = this.options.webhookUrl || process.env.GBP_WEBHOOK_URL;
    const result = await this.postJson(webhookUrl, payload);
    return {
      provider: this.provider,
      status: this.status,
      delivered: result.ok,
      responseStatus: result.status,
      warning: "GBP connector is in beta",
      error: result.error || null,
    };
  }
}
