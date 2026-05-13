import { BaseConnector } from "./base";

export class JobberConnector extends BaseConnector {
  constructor(options = {}) {
    super("jobber", options);
  }

  get status() {
    return "roadmap";
  }

  async send() {
    return {
      provider: this.provider,
      status: this.status,
      delivered: false,
      error: "Jobber connector is a roadmap stub and is not live yet",
    };
  }
}
