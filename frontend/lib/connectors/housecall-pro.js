import { BaseConnector } from "./base";

export class HousecallProConnector extends BaseConnector {
  constructor(options = {}) {
    super("housecall-pro", options);
  }

  get status() {
    return "roadmap";
  }

  async send() {
    return {
      provider: this.provider,
      status: this.status,
      delivered: false,
      error: "Housecall Pro connector is a roadmap stub and is not live yet",
    };
  }
}
