export class BaseConnector {
  constructor(provider, options = {}) {
    this.provider = provider;
    this.options = options;
  }

  get status() {
    return "unknown";
  }

  async send(_payload, _context = {}) {
    throw new Error(`send() not implemented for provider ${this.provider}`);
  }

  async health() {
    return {
      provider: this.provider,
      status: this.status,
      ok: this.status === "live" || this.status === "beta",
    };
  }

  async postJson(url, payload, headers = {}) {
    if (!url) {
      return {
        ok: false,
        status: 0,
        error: "target URL is not configured",
      };
    }

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...headers,
        },
        body: JSON.stringify(payload),
      });

      let data = null;
      try {
        data = await response.json();
      } catch {
        data = null;
      }

      return {
        ok: response.ok,
        status: response.status,
        data,
      };
    } catch (error) {
      return {
        ok: false,
        status: 0,
        error: String(error?.message || error),
      };
    }
  }
}
