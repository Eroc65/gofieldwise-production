import { BaseConnector } from "./base";

export class ZapierConnector extends BaseConnector {
  constructor(options = {}) {
    super("zapier", options);
  }

  get status() {
    return "live";
  }

  async send(payload) {
    const webhookUrl =
      this.options.webhookUrl || process.env.ZAPIER_WEBHOOK_URL || process.env.ZAPIER_CONNECTOR_WEBHOOK_URL;
    const result = await this.postJson(webhookUrl, payload);
    return {
      provider: this.provider,
      status: this.status,
      delivered: result.ok,
      responseStatus: result.status,
      error: result.error || null,
    };
  }
}
