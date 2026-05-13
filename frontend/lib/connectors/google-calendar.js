import { BaseConnector } from "./base";

export class GoogleCalendarConnector extends BaseConnector {
  constructor(options = {}) {
    super("google-calendar", options);
  }

  get status() {
    return "live";
  }

  async send(payload) {
    const webhookUrl =
      this.options.webhookUrl || process.env.GOOGLE_CALENDAR_WEBHOOK_URL || process.env.GCAL_CONNECTOR_WEBHOOK_URL;
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
