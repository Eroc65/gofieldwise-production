import { useEffect, useMemo, useState } from "react";

import { getLeadConversionMetrics, login } from "../lib/api";

export default function MetricsPage() {
  const [token, setToken] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [days, setDays] = useState(7);
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");

  const totals = useMemo(() => metrics?.totals || {}, [metrics]);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("fdp.dispatch.token") || "";
    const savedEmail = window.localStorage.getItem("fdp.dispatch.email") || "";
    if (savedToken) setToken(savedToken);
    if (savedEmail) setAuthEmail(savedEmail);
  }, []);

  async function withAction(name, fn) {
    setError("");
    setBusyAction(name);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyAction("");
    }
  }

  async function onLogin() {
    await withAction("auth", async () => {
      const result = await login({ email: authEmail, password: authPassword });
      if (!result.access_token) {
        throw new Error("Login succeeded but no access token was returned.");
      }
      setToken(result.access_token);
      window.localStorage.setItem("fdp.dispatch.token", result.access_token);
    });
  }

  async function onLoadMetrics() {
    await withAction("metrics", async () => {
      if (!token) throw new Error("Login first to load metrics.");
      const data = await getLeadConversionMetrics({ token, days });
      setMetrics(data);
    });
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Operator Metrics</p>
        <h1>Lead Conversion Dashboard</h1>
        <p>Track daily intake, qualification, and booking conversion over time.</p>
      </section>

      <section className="dispatch-card">
        <header className="dispatch-head">
          <h2>Access</h2>
          <p>Authenticate with your organization user.</p>
        </header>

        <div className="form-grid">
          <label>
            Auth Email
            <input value={authEmail} onChange={(e) => setAuthEmail(e.target.value)} placeholder="owner@shop.com" />
          </label>
          <label>
            Auth Password
            <input type="password" value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} placeholder="password" />
          </label>
          <label>
            Days
            <input type="number" min={1} max={30} value={days} onChange={(e) => setDays(Number(e.target.value))} />
          </label>
        </div>

        <div className="actions">
          <button type="button" onClick={onLogin} disabled={busyAction !== "" || !authEmail || !authPassword}>
            {busyAction === "auth" ? "Authorizing..." : "Login"}
          </button>
          <button type="button" onClick={onLoadMetrics} disabled={busyAction !== "" || !token}>
            {busyAction === "metrics" ? "Loading..." : "Load Metrics"}
          </button>
          <a className="ghost-link" href="/leads">Open Lead Inbox</a>
          <a className="ghost-link" href="/platform">Platform Console</a>
          <a className="ghost-link" href="/status">Status</a>
        </div>
      </section>

      {error ? <div className="panel error">{error}</div> : null}

      {metrics ? (
        <>
          <section className="dispatch-card">
            <header className="dispatch-head">
              <h2>Recommended Next Action</h2>
              <p>{metrics.recommended_next_action || "No recommendation available yet."}</p>
            </header>
          </section>

          <section className="results-grid">
            <article className="panel">
              <h3>Intakes</h3>
              <p>{totals.intakes ?? 0}</p>
            </article>
            <article className="panel">
              <h3>Qualified</h3>
              <p>{totals.qualified ?? 0}</p>
            </article>
            <article className="panel">
              <h3>Booked</h3>
              <p>{totals.booked ?? 0}</p>
            </article>
            <article className="panel">
              <h3>Qualification Rate</h3>
              <p>{totals.qualification_rate ?? 0}%</p>
            </article>
            <article className="panel">
              <h3>Booking Rate</h3>
              <p>{totals.booking_rate ?? 0}%</p>
            </article>
          </section>

          <section className="dispatch-card">
            <header className="dispatch-head">
              <h2>Daily Timeline</h2>
              <p>Most recent conversion activity by day.</p>
            </header>
            <div className="metric-table-wrap">
              <table className="metric-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Intakes</th>
                    <th>Qualified</th>
                    <th>Booked</th>
                    <th>Qual %</th>
                    <th>Book %</th>
                  </tr>
                </thead>
                <tbody>
                  {(metrics.timeline || []).map((row) => (
                    <tr key={row.date}>
                      <td>{row.date}</td>
                      <td>{row.intakes}</td>
                      <td>{row.qualified}</td>
                      <td>{row.booked}</td>
                      <td>{row.qualification_rate}%</td>
                      <td>{row.booking_rate}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}
