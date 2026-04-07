import { useMemo, useState } from "react";

import {
  getOperationalDashboard,
  getOperatorQueue,
  listLeads,
  listMarketingCampaigns,
  login,
} from "../lib/api";

export default function GrowthPage() {
  const [token, setToken] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [campaigns, setCampaigns] = useState([]);
  const [leads, setLeads] = useState([]);
  const [queue, setQueue] = useState({ items: [] });
  const [dashboard, setDashboard] = useState(null);

  const launchedCampaigns = useMemo(
    () => (campaigns || []).filter((row) => row.status === "launched").length,
    [campaigns],
  );
  const newLeads = useMemo(
    () => (leads || []).filter((row) => row.status === "new").length,
    [leads],
  );

  function money(value) {
    const amount = Number(value || 0);
    return `$${amount.toFixed(2)}`;
  }

  async function withBusy(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onLogin() {
    await withBusy(async () => {
      const response = await login({ email: authEmail, password: authPassword });
      if (!response.access_token) {
        throw new Error("Login succeeded but no access token was returned.");
      }
      setToken(response.access_token);
      window.localStorage.setItem("fdp.dispatch.token", response.access_token);
      window.localStorage.setItem("fdp.dispatch.email", authEmail);
    });
  }

  async function loadControlTower() {
    await withBusy(async () => {
      if (!token) {
        throw new Error("Login first to load growth infrastructure metrics.");
      }
      const [campaignRows, leadRows, queueOut, dashboardOut] = await Promise.all([
        listMarketingCampaigns({ token }),
        listLeads({ token }),
        getOperatorQueue({ token, limit: 5 }),
        getOperationalDashboard({ token }),
      ]);
      setCampaigns(Array.isArray(campaignRows) ? campaignRows : []);
      setLeads(Array.isArray(leadRows) ? leadRows : []);
      setQueue(queueOut || { items: [] });
      setDashboard(dashboardOut || null);
    });
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Growth Infrastructure</p>
        <h1>AI Growth Infrastructure For Modern Businesses</h1>
        <p>
          A premium AI growth control tower that unifies demand generation, digital presence, and revenue operations
          into one measurable operating system.
        </p>
        <div className="hero-actions">
          <a className="ghost-link" href="/">Marketing Site</a>
          <a className="ghost-link" href="/platform">Platform Console</a>
          <a className="ghost-link" href="/metrics">Metrics</a>
          <a className="ghost-link" href="/leads">Lead Inbox</a>
        </div>
      </section>

      <section className="dispatch-card">
        <header className="dispatch-head">
          <h2>Operator Access</h2>
          <p>Authenticate to load live growth and revenue operations data.</p>
        </header>
        <div className="form-grid">
          <label>
            Email
            <input value={authEmail} onChange={(e) => setAuthEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} />
          </label>
        </div>
        <div className="actions">
          <button type="button" onClick={onLogin} disabled={busy || !authEmail || !authPassword}>Login</button>
          <button type="button" onClick={loadControlTower} disabled={busy || !token}>Load Control Tower</button>
        </div>
        {error ? <p className="submit-error">{error}</p> : null}
      </section>

      <section className="results-grid">
        <article className="panel">
          <h3>Campaigns Launched</h3>
          <p>{launchedCampaigns}</p>
        </article>
        <article className="panel">
          <h3>Total Leads</h3>
          <p>{(leads || []).length}</p>
        </article>
        <article className="panel">
          <h3>New Leads</h3>
          <p>{newLeads}</p>
        </article>
        <article className="panel">
          <h3>Priority Queue Items</h3>
          <p>{(queue.items || []).length}</p>
        </article>
        <article className="panel">
          <h3>Unpaid Exposure</h3>
          <p>{money(dashboard?.invoice_summary?.unpaid_total_amount)}</p>
        </article>
        <article className="panel">
          <h3>Overdue Count</h3>
          <p>{dashboard?.invoice_summary?.overdue_count ?? 0}</p>
        </article>
      </section>

      <section className="dispatch-card">
        <header className="dispatch-head">
          <h2>Growth Priorities</h2>
          <p>Top actions from your unified operator queue.</p>
        </header>
        {(queue.items || []).length > 0 ? (
          <div className="metric-table-wrap">
            <table className="metric-table">
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Task</th>
                  <th>Urgency</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {(queue.items || []).map((item, index) => (
                  <tr key={`${item.item_type}-${item.entity_id}`}>
                    <td>#{index + 1} ({item.priority_score})</td>
                    <td>{item.title}</td>
                    <td>{item.urgency}</td>
                    <td>{item.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>No active priority items right now.</p>
        )}
      </section>
    </main>
  );
}
