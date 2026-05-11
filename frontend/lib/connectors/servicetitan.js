import { BaseConnector } from "./base";

export class ServiceTitanConnector extends BaseConnector {
  constructor(options = {}) {
    super("servicetitan", options);
  }

  get status() {
    return "roadmap";
  }

  async send() {
    return {
      provider: this.provider,
      status: this.status,
      delivered: false,
      error: "ServiceTitan connector is a roadmap stub and is not live yet",
    };
  }
}
