import { useEffect, useMemo, useState } from "react";

import { getLeadConversionMetrics, getOperationalDashboard, login } from "../lib/api";

export default function MetricsPage() {
  const [token, setToken] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [days, setDays] = useState(7);
  const [metrics, setMetrics] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");

  const totals = useMemo(() => metrics?.totals || {}, [metrics]);
  const invoiceSummary = useMemo(() => dashboard?.invoice_summary || {}, [dashboard]);
  const overdueInvoices = useMemo(() => dashboard?.overdue_invoices || {}, [dashboard]);
  const agingBuckets = useMemo(() => overdueInvoices.aging_buckets || {}, [overdueInvoices]);
  const prioritizedAgingBuckets = useMemo(
    () => [
      { key: "days_31_plus", label: "31 Plus Days", topAction: true },
      { key: "days_15_30", label: "15 To 30 Days", topAction: true },
      { key: "days_8_14", label: "8 To 14 Days" },
      { key: "days_1_7", label: "1 To 7 Days" },
      { key: "current_not_due", label: "Current Not Due" },
    ],
    [],
  );

  function money(value) {
    const amount = Number(value || 0);
    return `$${amount.toFixed(2)}`;
  }

  function bucketCount(key) {
    return agingBuckets?.[key]?.count ?? 0;
  }

  function bucketAmount(key) {
    return money(agingBuckets?.[key]?.amount ?? 0);
  }

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
      const [metricsData, dashboardData] = await Promise.all([
        getLeadConversionMetrics({ token, days }),
        getOperationalDashboard({ token }),
      ]);
      setMetrics(metricsData);
      setDashboard(dashboardData);
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
              <h2>Collections Snapshot</h2>
              <p>Unpaid exposure and overdue aging buckets in highest-risk-first order.</p>
            </header>
            <div className="results-grid">
              <article className="panel">
                <h3>Unpaid Total</h3>
                <p>{money(invoiceSummary.unpaid_total_amount)}</p>
              </article>
              <article className="panel">
                <h3>Overdue Count</h3>
                <p>{invoiceSummary.overdue_count ?? 0}</p>
              </article>
            </div>
            <div className="results-grid collections-aging-grid">
              {prioritizedAgingBuckets.map((bucket) => (
                <article className="panel" key={bucket.key}>
                  <h3>
                    {bucket.label}
                    {bucket.topAction ? " (Top Action)" : ""}
                  </h3>
                  <p>{bucketCount(bucket.key)}</p>
                  <small>{bucketAmount(bucket.key)}</small>
                </article>
              ))}
            </div>
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
