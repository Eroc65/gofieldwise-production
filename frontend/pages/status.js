import { useEffect, useState } from "react";

import { getPublicStatus } from "../lib/api";

export default function StatusPage() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const out = await getPublicStatus();
        if (mounted) setStatus(out);
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err.message : String(err));
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">System Status</p>
        <h1>FrontDesk Pro Platform Health</h1>
        <p>Public operational summary for API and platform feature availability.</p>
      </section>

      {error ? <section className="dispatch-card"><p className="submit-error">{error}</p></section> : null}

      {status ? (
        <section className="dispatch-card">
          <h2>Current Status: {status.status}</h2>
          <p>Service: {status.service}</p>
          <ul>
            {Object.entries(status.features || {}).map(([key, value]) => (
              <li key={key}>{key}: {String(value)}</li>
            ))}
          </ul>
          <div className="hero-actions">
            <a className="ghost-link" href="/platform">Open Platform Console</a>
            <a className="ghost-link" href="/">Back to Site</a>
          </div>
        </section>
      ) : null}
    </main>
  );
}
