import { useEffect, useState } from "react";

import {
  bookLead,
  getCurrentUser,
  getLeadActivity,
  getLeadConversionMetrics,
  listLeads,
  listTechnicians,
  login,
  qualifyLead,
  updateLeadStatus,
} from "../lib/api";

function toLocalInputValue(date) {
  const d = date instanceof Date ? date : new Date(date);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function prettyDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function LeadInboxPage() {
  const [token, setToken] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [leads, setLeads] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [leadActivity, setLeadActivity] = useState([]);
  const [conversionSummary, setConversionSummary] = useState(null);
  const [selectedLeadId, setSelectedLeadId] = useState("");
  const [serviceCategory, setServiceCategory] = useState("");
  const [scheduledTime, setScheduledTime] = useState(toLocalInputValue(new Date(Date.now() + 2 * 60 * 60 * 1000)));
  const [bookTechId, setBookTechId] = useState("");
  const [actionResult, setActionResult] = useState("");
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");

  useEffect(() => {
    const savedToken = window.localStorage.getItem("fdp.dispatch.token") || "";
    const savedEmail = window.localStorage.getItem("fdp.dispatch.email") || "";
    if (savedToken) setToken(savedToken);
    if (savedEmail) setAuthEmail(savedEmail);
  }, []);

  useEffect(() => {
    if (token) {
      window.localStorage.setItem("fdp.dispatch.token", token);
      void refreshInbox();
    }
  }, [token]);

  async function withAction(name, fn) {
    setError("");
    setActionResult("");
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
      if (!authEmail || !authPassword) {
        throw new Error("Email and password are required for login.");
      }
      const result = await login({ email: authEmail, password: authPassword });
      if (!result.access_token) {
        throw new Error("Login succeeded but no access token was returned.");
      }
      setToken(result.access_token);
    });
  }

  async function refreshInbox() {
    await withAction("refresh", async () => {
      const [leadRows, techRows, me] = await Promise.all([
        listLeads({ token }),
        listTechnicians({ token }),
        getCurrentUser({ token }),
      ]);
      setLeads(Array.isArray(leadRows) ? leadRows : []);
      setTechnicians(Array.isArray(techRows) ? techRows : []);
      setCurrentUser(me || null);
      if (!selectedLeadId && Array.isArray(leadRows) && leadRows.length > 0) {
        setSelectedLeadId(String(leadRows[0].id));
      }
      if (!bookTechId && Array.isArray(techRows) && techRows.length > 0) {
        setBookTechId(String(techRows[0].id));
      }

      try {
        const summary = await getLeadConversionMetrics({ token, days: 7 });
        setConversionSummary(summary);
      } catch {
        setConversionSummary(null);
      }

      const activeLeadId = Number(selectedLeadId || leadRows?.[0]?.id || 0);
      if (activeLeadId > 0) {
        try {
          const events = await getLeadActivity({ token, leadId: activeLeadId });
          setLeadActivity(Array.isArray(events) ? events : []);
        } catch {
          setLeadActivity([]);
        }
      } else {
        setLeadActivity([]);
      }
    });
  }

  useEffect(() => {
    if (!token || !selectedLeadId) {
      return;
    }
    let cancelled = false;
    async function loadLeadTimeline() {
      try {
        const events = await getLeadActivity({ token, leadId: Number(selectedLeadId) });
        if (!cancelled) {
          setLeadActivity(Array.isArray(events) ? events : []);
        }
      } catch {
        if (!cancelled) {
          setLeadActivity([]);
        }
      }
    }
    void loadLeadTimeline();
    return () => {
      cancelled = true;
    };
  }, [token, selectedLeadId]);

  const role = String(currentUser?.role || "owner").toLowerCase();
  const canQualify = ["owner", "admin", "dispatcher"].includes(role);
  const canBook = ["owner", "admin", "dispatcher"].includes(role);

  async function onMarkContacted() {
    await withAction("contacted", async () => {
      if (!selectedLeadId) throw new Error("Select a lead first.");
      const updated = await updateLeadStatus({ token, leadId: Number(selectedLeadId), status: "contacted" });
      await refreshInbox();
      setActionResult(`Lead #${updated.id} moved to contacted.`);
    });
  }

  async function onQualifyLead() {
    await withAction("qualify", async () => {
      if (!selectedLeadId) throw new Error("Select a lead first.");
      const result = await qualifyLead({
        token,
        leadId: Number(selectedLeadId),
        emergency: true,
        budgetConfirmed: true,
        requestedWithin48h: true,
        serviceCategory,
      });
      await refreshInbox();
      setActionResult(`Lead #${result.lead.id} qualified with score ${result.lead.priority_score ?? "n/a"}.`);
    });
  }

  async function onBookLead() {
    await withAction("book", async () => {
      if (!selectedLeadId) throw new Error("Select a lead first.");
      if (!bookTechId) throw new Error("Pick a technician for booking.");
      const result = await bookLead({
        token,
        leadId: Number(selectedLeadId),
        technicianId: Number(bookTechId),
        scheduledTime: new Date(scheduledTime).toISOString(),
      });
      await refreshInbox();
      setActionResult(`Lead booked. Job #${result.job_id} scheduled ${prettyDate(result.scheduled_time)}.`);
    });
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Lead Inbox</p>
        <h1>Review, Qualify, And Book New Leads Fast</h1>
        <p>Single-screen operator workflow to move inbound leads from new to booked without context switching.</p>
        <div className="hero-actions">
          <a className="ghost-link" href="/metrics">Open Metrics</a>
        </div>
      </section>

      <section className="dispatch-card">
        <header className="dispatch-head">
          <h2>Operator Access</h2>
          <p>Use an existing account from your organization. Current role: <strong>{currentUser?.role || "unknown"}</strong></p>
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
          <label className="span-2">
            Bearer Token
            <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Paste JWT access token" />
          </label>
        </div>

        <div className="actions">
          <button type="button" onClick={onLogin} disabled={busyAction !== "" || !authEmail || !authPassword}>
            {busyAction === "auth" ? "Authorizing..." : "Login"}
          </button>
          <button type="button" onClick={refreshInbox} disabled={busyAction !== "" || !token}>
            {busyAction === "refresh" ? "Refreshing..." : "Refresh Inbox"}
          </button>
        </div>
      </section>

      <section className="dispatch-card">
        <header className="dispatch-head">
          <h2>Lead Actions</h2>
          <p>Quickly move selected lead toward dispatch.</p>
        </header>

        {conversionSummary ? (
          <>
            <div className="panel">
              <h3>Recommended Next Action</h3>
              <p>{conversionSummary.recommended_next_action || "No recommendation available yet."}</p>
            </div>
            <div className="results-grid">
              <article className="panel">
                <h3>7 Day Intakes</h3>
                <p>{conversionSummary.totals?.intakes ?? 0}</p>
              </article>
              <article className="panel">
                <h3>7 Day Qualified</h3>
                <p>{conversionSummary.totals?.qualified ?? 0}</p>
              </article>
              <article className="panel">
                <h3>7 Day Booked</h3>
                <p>{conversionSummary.totals?.booked ?? 0}</p>
              </article>
              <article className="panel">
                <h3>Qualification Rate</h3>
                <p>{conversionSummary.totals?.qualification_rate ?? 0}%</p>
              </article>
              <article className="panel">
                <h3>Booking Rate</h3>
                <p>{conversionSummary.totals?.booking_rate ?? 0}%</p>
              </article>
            </div>
          </>
        ) : null}

        <div className="form-grid">
          <label>
            Pick Lead
            <select value={selectedLeadId} onChange={(e) => setSelectedLeadId(e.target.value)}>
              <option value="">Select a lead</option>
              {leads.map((lead) => (
                <option key={lead.id} value={String(lead.id)}>
                  #{lead.id} {lead.name || lead.phone || "Unnamed"} ({lead.status})
                </option>
              ))}
            </select>
          </label>

          <label>
            Service Category
            <input value={serviceCategory} onChange={(e) => setServiceCategory(e.target.value)} placeholder="plumbing, hvac, dental..." />
          </label>

          <label>
            Booking Technician
            <select value={bookTechId} onChange={(e) => setBookTechId(e.target.value)}>
              <option value="">Select a technician</option>
              {technicians.map((tech) => (
                <option key={tech.id} value={String(tech.id)}>#{tech.id} {tech.name}</option>
              ))}
            </select>
          </label>

          <label>
            Booking Time
            <input type="datetime-local" value={scheduledTime} onChange={(e) => setScheduledTime(e.target.value)} />
          </label>
        </div>

        <div className="actions">
          <button type="button" onClick={onMarkContacted} disabled={busyAction !== "" || !token || !selectedLeadId}>
            {busyAction === "contacted" ? "Updating..." : "Mark Contacted"}
          </button>
          <button type="button" onClick={onQualifyLead} disabled={busyAction !== "" || !token || !selectedLeadId || !canQualify}>
            {busyAction === "qualify" ? "Qualifying..." : "Qualify Lead"}
          </button>
          <button type="button" onClick={onBookLead} disabled={busyAction !== "" || !token || !selectedLeadId || !bookTechId || !canBook}>
            {busyAction === "book" ? "Booking..." : "Book Lead"}
          </button>
        </div>

        {!canQualify || !canBook ? (
          <div className="panel error">
            <p>Your role has limited lead-action permissions. Contact an owner/admin if you need qualification or booking access.</p>
          </div>
        ) : null}

        {actionResult ? <div className="panel"><p>{actionResult}</p></div> : null}
        {error ? <div className="panel error">{error}</div> : null}
      </section>

      <section className="dispatch-card">
        <header className="dispatch-head">
          <h2>Live Queue</h2>
          <p>Newest leads first.</p>
        </header>

        <div className="lead-list">
          {leads.length === 0 ? (
            <p>No leads loaded yet.</p>
          ) : (
            leads.map((lead) => (
              <article key={lead.id} className="panel">
                <h3>#{lead.id} {lead.name || "Unnamed Lead"}</h3>
                <ul>
                  <li>Status: {lead.status}</li>
                  <li>Phone: {lead.phone || "-"}</li>
                  <li>Email: {lead.email || "-"}</li>
                  <li>Source: {lead.source}</li>
                  <li>Priority: {lead.priority_score ?? "-"}</li>
                  <li>Created: {prettyDate(lead.created_at)}</li>
                </ul>
              </article>
            ))
          )}
        </div>
      </section>

      <section className="dispatch-card">
        <header className="dispatch-head">
          <h2>Lead Activity Timeline</h2>
          <p>Audit trail for the currently selected lead.</p>
        </header>
        <div className="lead-list">
          {leadActivity.length === 0 ? (
            <p>No activity available for this lead yet.</p>
          ) : (
            leadActivity.map((event) => (
              <article key={event.id} className="panel">
                <h3>{event.action}</h3>
                <ul>
                  <li>From: {event.from_status || "-"}</li>
                  <li>To: {event.to_status}</li>
                  <li>Actor User ID: {event.actor_user_id ?? "system"}</li>
                  <li>When: {prettyDate(event.created_at)}</li>
                  <li>Note: {event.note || "-"}</li>
                </ul>
              </article>
            ))
          )}
        </div>
      </section>
    </main>
  );
}
