import Head from "next/head";
import { useEffect, useMemo, useState } from "react";

import {
  adminLogin,
  getAdminMonitoringSummary,
  getJobberTokenExpiryStatus,
  requestAdminPasswordReset,
  resetAdminPassword,
  refreshExpiringJobberTokens,
  runAdminSystemHealthcheck,
} from "../lib/api";

const ADMIN_TOKEN_KEY = "gofieldwise.admin.token";
const ADMIN_USERNAME_KEY = "gofieldwise.admin.username";
const ADMIN_RESET_EMAIL = "erock004@gmail.com";

const fallbackSummary = {
  overall_status: "yellow",
  generated_at: null,
  landing_page_health: [
    { name: "Demo Form Loads", status: "green", detail: "Frontend route is included in the production build.", latency_ms: null, last_checked: null },
    { name: "Form Validation Working", status: "green", detail: "Required fields are enforced before submit.", latency_ms: null, last_checked: null },
    { name: "Adrian Callable", status: "yellow", detail: "Waiting for backend health response.", latency_ms: null, last_checked: null },
    { name: "Transcript Stream", status: "yellow", detail: "Waiting for backend health response.", latency_ms: null, last_checked: null },
    { name: "Post-Call SMS Sending", status: "yellow", detail: "Waiting for backend health response.", latency_ms: null, last_checked: null },
    { name: "Extraction Working", status: "yellow", detail: "Waiting for backend health response.", latency_ms: null, last_checked: null },
    { name: "Ads Pixel Firing", status: "yellow", detail: "Pixel monitoring is queued.", latency_ms: null, last_checked: null },
    { name: "API Health", status: "yellow", detail: "Waiting for backend health response.", latency_ms: null, last_checked: null },
  ],
  feature_board: [],
  system_health: {
    status: "yellow",
    healthy: false,
    red_count: 0,
    yellow_count: 8,
    green_count: 0,
    summary: "Waiting for live systems healthcheck.",
  },
  troubleshooting_flows: [],
  demo_metrics: {
    demo_clicks_7d: 0,
    call_success_rate: 0,
    completion_rate: 0,
    avg_call_duration_seconds: 0,
    post_call_sms_delivery_rate: 0,
    form_abandonment_rate: 0,
  },
  visitor_analytics: {
    pageviews_7d: 0,
    unique_visitors: 0,
    bounce_rate: 0,
    avg_time_on_site_seconds: 0,
    top_sources: ["Direct", "Organic", "Referral", "Meta"],
    device_mix: { desktop: 0, mobile: 0 },
  },
  business_health: {
    tenant_count: 0,
    estimated_mrr: 0,
    warm_leads: 0,
    jobs_dispatched: 0,
    open_invoice_total: 0,
    pending_followups: 0,
  },
};

const liveSections = [
  { title: "Call Logs", status: "Live", body: "Demo and live calls, transcripts, quality scores, extraction data." },
  { title: "Warm Leads", status: "#661429", body: "Captured leads, recovery status tracking, dead lead auto-recovery." },
  { title: "Ads Performance", status: "#660447", body: "Traffic attribution, cost per lead, UTM breakdown." },
  { title: "Outreach", status: "#665034", body: "Oklahoma business scraper for plumbing, HVAC, electrical, roofing contacts." },
  { title: "AI Receptionist Settings", status: "Live", body: "Business profile config, Adrian sync, intake rules." },
  { title: "Support Chatbot", status: "#644210", body: "AI chat logs, customer Q&A, article suggestions." },
];

const healthTables = [
  { name: "demo_interactions", purpose: "Tracks form submit to call completion and summary SMS." },
  { name: "visitor_pageviews", purpose: "Session analytics, route, scroll depth, source, device, time on page." },
  { name: "feature_health_checks", purpose: "Automated test results, latency, status, and error details." },
];

const backgroundJobs = [
  "Every 5 min: test demo form endpoint and Adrian call configuration.",
  "Every 15 min: run a real test call and verify transcript, extraction, and SMS.",
  "Every 1 min: health check API, database, and external delivery paths.",
];

const leadSignals = [
  { label: "Urgency", value: "Active leak beats someday remodel", score: 92 },
  { label: "Completeness", value: "Name, phone, address, service captured", score: 81 },
  { label: "Engagement", value: "Call duration and SMS replies", score: 74 },
];

const adrianInsights = [
  "Caller hang-up point by question",
  "Extraction hit rate by field",
  "Average call duration by outcome",
  "Top unanswered customer questions",
];

const alertRules = [
  { rule: "Health check turns red", channel: "Push or SMS", severity: "Critical" },
  { rule: "Completion rate under 60%", channel: "Daily digest plus alert", severity: "High" },
  { rule: "Extraction rate drops", channel: "Owner notification", severity: "High" },
  { rule: "All systems green", channel: "Daily digest", severity: "Info" },
];

const tenantConfig = [
  "Business hours editor",
  "Custom Adrian responses",
  "Service area map",
  "SMS template editor",
  "Emergency routing rules",
  "Pricing and booking notes",
];

function statusLabel(status) {
  if (status === "green") return "Healthy";
  if (status === "red") return "Failing";
  return "Watch";
}

function formatMoney(value) {
  return `$${Number(value || 0).toLocaleString()}`;
}

function formatDateTime(value) {
  if (!value) return "Not checked yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function MiniBars({ values }) {
  const max = Math.max(...values, 1);
  return (
    <div className="mini-bars" aria-label="7 day trend">
      {values.map((value, index) => (
        <span key={`${value}-${index}`} style={{ height: `${Math.max(12, (value / max) * 100)}%` }} />
      ))}
    </div>
  );
}

export default function AdminDashboard() {
  const [summary, setSummary] = useState(fallbackSummary);
  const [token, setToken] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [authenticating, setAuthenticating] = useState(false);
  const [error, setError] = useState("");
  const [authError, setAuthError] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [resetPassword, setResetPassword] = useState("");
  const [resetConfirm, setResetConfirm] = useState("");
  const [resetMessage, setResetMessage] = useState("");
  const [resetBusy, setResetBusy] = useState(false);
  const [jobberStatus, setJobberStatus] = useState({ total: 0, items: [] });
  const [jobberError, setJobberError] = useState("");
  const [jobberLoading, setJobberLoading] = useState(false);
  const [jobberRefreshRunning, setJobberRefreshRunning] = useState(false);
  const [jobberRefreshMessage, setJobberRefreshMessage] = useState("");
  const [warningSeconds, setWarningSeconds] = useState(3600);
  const [criticalSeconds, setCriticalSeconds] = useState(900);
  const [healthcheckRunning, setHealthcheckRunning] = useState(false);
  const [healthcheckError, setHealthcheckError] = useState("");

  async function loadJobberRisk() {
    if (!token) return;
    setJobberLoading(true);
    try {
      const payload = await getJobberTokenExpiryStatus({
        token,
        warningSeconds,
        criticalSeconds,
      });
      setJobberStatus(payload);
      setJobberError("");
    } catch (err) {
      setJobberError(err instanceof Error ? err.message : "Could not load Jobber token risk.");
    } finally {
      setJobberLoading(false);
    }
  }

  useEffect(() => {
    const savedToken = window.localStorage.getItem(ADMIN_TOKEN_KEY) || "";
    const savedUsername = window.localStorage.getItem(ADMIN_USERNAME_KEY) || "";
    const query = new URLSearchParams(window.location.search);
    const queryResetToken = query.get("reset") || "";
    if (queryResetToken) setResetToken(queryResetToken);
    if (savedUsername) setUsername(savedUsername);
    if (savedToken) setToken(savedToken);
    setLoading(false);
  }, []);

  useEffect(() => {
    let active = true;

    async function load() {
      if (!token) return;
      try {
        const payload = await getAdminMonitoringSummary({ token });
        if (active) {
          setSummary({ ...fallbackSummary, ...payload });
          setHealthcheckError("");
          setError("");
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Could not load live monitoring.");
          if (String(err instanceof Error ? err.message : err).includes("401") || String(err instanceof Error ? err.message : err).includes("403")) {
            setToken("");
            window.localStorage.removeItem(ADMIN_TOKEN_KEY);
          }
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    const timer = setInterval(load, 300000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [token]);

  useEffect(() => {
    let active = true;

    async function load() {
      if (!token) return;
      try {
        const payload = await getJobberTokenExpiryStatus({
          token,
          warningSeconds,
          criticalSeconds,
        });
        if (active) {
          setJobberStatus(payload);
          setJobberError("");
        }
      } catch (err) {
        if (active) {
          setJobberError(err instanceof Error ? err.message : "Could not load Jobber token risk.");
        }
      }
    }

    setJobberLoading(true);
    load().finally(() => {
      if (active) setJobberLoading(false);
    });
    return () => {
      active = false;
    };
  }, [token, warningSeconds, criticalSeconds]);

  async function onRefreshJobberNow() {
    if (!token) return;
    setJobberRefreshRunning(true);
    setJobberRefreshMessage("");
    try {
      const result = await refreshExpiringJobberTokens({
        token,
        thresholdSeconds: criticalSeconds,
      });
      setJobberRefreshMessage(
        `Refreshed ${result.refreshed || 0} of ${result.checked || 0} checked (failed: ${result.failed || 0}).`
      );
      await loadJobberRisk();
    } catch (err) {
      setJobberRefreshMessage(err instanceof Error ? err.message : "Refresh failed.");
    } finally {
      setJobberRefreshRunning(false);
    }
  }

  async function onRunSystemHealthcheck() {
    if (!token) return;
    setHealthcheckRunning(true);
    setHealthcheckError("");
    try {
      const payload = await runAdminSystemHealthcheck({ token });
      setSummary((current) => ({
        ...current,
        generated_at: payload.generated_at || current.generated_at,
        overall_status: payload.overall_status || current.overall_status,
        system_health: payload.system_health || current.system_health,
        landing_page_health: payload.checks || current.landing_page_health,
        troubleshooting_flows: payload.troubleshooting_flows || current.troubleshooting_flows,
      }));
    } catch (err) {
      setHealthcheckError(err instanceof Error ? err.message : "System healthcheck failed.");
    } finally {
      setHealthcheckRunning(false);
    }
  }

  async function onLogin(event) {
    event.preventDefault();
    setAuthError("");
    const normalizedUsername = username.trim();
    setAuthenticating(true);
    try {
      const result = await adminLogin({ username: normalizedUsername, password });
      if (!result.access_token) {
        throw new Error("Login succeeded but no access token was returned.");
      }
      window.localStorage.setItem(ADMIN_TOKEN_KEY, result.access_token);
      window.localStorage.setItem(ADMIN_USERNAME_KEY, result.username || normalizedUsername);
      setToken(result.access_token);
      setUsername(result.username || normalizedUsername);
      setPassword("");
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Admin login failed.");
    } finally {
      setAuthenticating(false);
    }
  }

  function onSignOut() {
    setToken("");
    setSummary(fallbackSummary);
    window.localStorage.removeItem(ADMIN_TOKEN_KEY);
  }

  async function onRequestReset(event) {
    event.preventDefault();
    setResetBusy(true);
    setAuthError("");
    setResetMessage("");
    try {
      await requestAdminPasswordReset({ username: username.trim() });
      setResetMessage(`If that admin username is valid, a reset link was sent to ${ADMIN_RESET_EMAIL}.`);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Could not request password reset.");
    } finally {
      setResetBusy(false);
    }
  }

  async function onResetPassword(event) {
    event.preventDefault();
    setResetBusy(true);
    setAuthError("");
    setResetMessage("");
    if (resetPassword !== resetConfirm) {
      setAuthError("Passwords do not match.");
      setResetBusy(false);
      return;
    }
    try {
      const result = await resetAdminPassword({ token: resetToken, password: resetPassword });
      window.localStorage.setItem(ADMIN_TOKEN_KEY, result.access_token);
      window.localStorage.setItem(ADMIN_USERNAME_KEY, result.username || username);
      setToken(result.access_token);
      setUsername(result.username || username);
      setResetToken("");
      setResetPassword("");
      setResetConfirm("");
      setResetMessage("Password reset. Admin session opened.");
      window.history.replaceState({}, document.title, "/admin");
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Could not reset password.");
    } finally {
      setResetBusy(false);
    }
  }

  const business = summary.business_health || fallbackSummary.business_health;
  const metrics = summary.demo_metrics || fallbackSummary.demo_metrics;
  const analytics = summary.visitor_analytics || fallbackSummary.visitor_analytics;
  const health = summary.landing_page_health || [];
  const systemHealth = summary.system_health || fallbackSummary.system_health;
  const troubleshootingFlows = summary.troubleshooting_flows || [];
  const featureBoard = summary.feature_board?.length ? summary.feature_board : fallbackSummary.landing_page_health.map((item) => ({
    feature: item.name,
    status: item.status,
    last_tested: "pending",
    result: item.detail,
  }));
  const trend = useMemo(() => [2, 4, 3, 6, 7, 5, 9], []);

  return (
    <>
      <Head>
        <title>GoFieldwise Admin Monitoring</title>
        <meta name="robots" content="noindex" />
      </Head>

      <main className="admin-shell">
        {!token ? (
          <section className="login-card">
            <p className="eyebrow">Restricted admin</p>
            <h1>GoFieldwise admin portal.</h1>
            <p>Sign in with the admin username and password configured in your backend environment.</p>
            {resetToken ? (
              <form onSubmit={onResetPassword}>
                <label>
                  New password
                  <input
                    type="password"
                    value={resetPassword}
                    onChange={(event) => setResetPassword(event.target.value)}
                    autoComplete="new-password"
                  />
                </label>
                <label>
                  Confirm password
                  <input
                    type="password"
                    value={resetConfirm}
                    onChange={(event) => setResetConfirm(event.target.value)}
                    autoComplete="new-password"
                  />
                </label>
                <button type="submit" disabled={resetBusy || !resetPassword || !resetConfirm}>
                  {resetBusy ? "Resetting..." : "Reset Password"}
                </button>
                <button type="button" className="link-button" onClick={() => setResetToken("")}>
                  Back to login
                </button>
              </form>
            ) : (
              <>
                <form onSubmit={onLogin}>
                  <label>
                    Admin username
                    <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
                  </label>
                  <label>
                    Password
                    <input
                      type="password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      autoComplete="current-password"
                    />
                  </label>
                  <button type="submit" disabled={authenticating || !username || !password}>
                    {authenticating ? "Checking access..." : "Open Admin Portal"}
                  </button>
                </form>
                <form className="reset-form" onSubmit={onRequestReset}>
                  <p>Forgot the admin password? A reset link can be sent to {ADMIN_RESET_EMAIL}.</p>
                  <button type="submit" disabled={resetBusy || !username}>
                    {resetBusy ? "Sending..." : "Send Reset Link"}
                  </button>
                </form>
              </>
            )}
            {authError ? <p className="auth-error">{authError}</p> : null}
            {resetMessage ? <p className="reset-message">{resetMessage}</p> : null}
          </section>
        ) : (
          <>
        <section className="admin-hero">
          <div>
            <p className="eyebrow">GoFieldwise admin</p>
            <h1>System health, demo performance, tenants, leads, and Adrian quality in one command center.</h1>
            <p>
              Built for owner visibility before paid traffic and tenants scale. Auto-refreshes every 5 minutes when the
              backend monitoring endpoint is available.
            </p>
          </div>
          <aside className={`overall ${summary.overall_status || "yellow"}`}>
            <span>Overall status</span>
            <strong>{statusLabel(summary.overall_status)}</strong>
            <small>{loading ? "Checking live systems..." : error || "Live monitoring connected"}</small>
            <button type="button" onClick={onRunSystemHealthcheck} disabled={healthcheckRunning}>
              {healthcheckRunning ? "Running healthcheck..." : "Run Systems Healthcheck"}
            </button>
            <button type="button" onClick={onSignOut}>Sign out</button>
          </aside>
        </section>

        <section className={`panel system-health-panel ${systemHealth.status || "yellow"}`}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Systems indicator</p>
              <h2>{systemHealth.healthy ? "All Systems Healthy" : `Systems ${statusLabel(systemHealth.status)}`}</h2>
            </div>
            <button
              type="button"
              className="healthcheck-button"
              onClick={onRunSystemHealthcheck}
              disabled={healthcheckRunning}
            >
              {healthcheckRunning ? "Checking..." : "Run healthcheck"}
            </button>
          </div>
          <div className="system-health-body">
            <div className={`health-orb ${systemHealth.status || "yellow"}`} aria-hidden="true" />
            <div>
              <p>{systemHealth.summary}</p>
              <small>Last checked: {formatDateTime(summary.generated_at)}</small>
              {healthcheckError ? <p className="auth-error">{healthcheckError}</p> : null}
            </div>
            <div className="health-counts">
              <span><b>{systemHealth.green_count || 0}</b> healthy</span>
              <span><b>{systemHealth.yellow_count || 0}</b> watch</span>
              <span><b>{systemHealth.red_count || 0}</b> failing</span>
            </div>
          </div>
        </section>

        <section className="kpi-grid">
          <article>
            <span>Estimated MRR</span>
            <strong>{formatMoney(business.estimated_mrr)}</strong>
            <p>{business.tenant_count} active tenant record(s)</p>
          </article>
          <article>
            <span>Warm leads</span>
            <strong>{business.warm_leads}</strong>
            <p>Ready for scoring and follow-up priority</p>
          </article>
          <article>
            <span>Jobs dispatched</span>
            <strong>{business.jobs_dispatched}</strong>
            <p>Tenant operations signal</p>
          </article>
          <article>
            <span>Open invoices</span>
            <strong>{formatMoney(business.open_invoice_total)}</strong>
            <p>{business.pending_followups} pending follow-up(s)</p>
          </article>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Jobber token risk</p>
              <h2>Token Expiry Watch</h2>
            </div>
            <div className="jobber-controls">
              <label>
                Warning(s)
                <input
                  type="number"
                  min={60}
                  value={warningSeconds}
                  onChange={(event) => setWarningSeconds(Number(event.target.value) || 3600)}
                />
              </label>
              <label>
                Critical(s)
                <input
                  type="number"
                  min={60}
                  value={criticalSeconds}
                  onChange={(event) => setCriticalSeconds(Number(event.target.value) || 900)}
                />
              </label>
              <button
                type="button"
                className="jobber-refresh"
                onClick={onRefreshJobberNow}
                disabled={jobberRefreshRunning || !token}
              >
                {jobberRefreshRunning ? "Refreshing..." : "Refresh now"}
              </button>
            </div>
          </div>
          {jobberError ? <p className="auth-error">{jobberError}</p> : null}
          {jobberRefreshMessage ? <p className="jobber-refresh-msg">{jobberRefreshMessage}</p> : null}
          <div className="jobber-meta">
            <span>{jobberLoading ? "Refreshing..." : `Configs tracked: ${jobberStatus.total || 0}`}</span>
          </div>
          <div className="jobber-table">
            {(jobberStatus.items || []).map((item) => (
              <article key={`${item.organization_id}-${item.config_id}`} className={`risk-${item.risk || "unknown"}`}>
                <b>{item.name || `Config ${item.config_id}`}</b>
                <span>Org {item.organization_id}</span>
                <span>Risk: {item.risk || "unknown"}</span>
                <span>Expires: {item.expires_at || "n/a"}</span>
                <span>Remaining: {item.seconds_remaining != null ? `${item.seconds_remaining}s` : "n/a"}</span>
              </article>
            ))}
            {!jobberLoading && !(jobberStatus.items || []).length ? (
              <article className="risk-unknown">
                <b>No Jobber configs found</b>
                <span>Create a Jobber OAuth config to monitor token expiry risk.</span>
              </article>
            ) : null}
          </div>
        </section>

        <section className="panel landing-health">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Section 1</p>
              <h2>Landing Page Health Status</h2>
            </div>
            <span>Auto-refresh: 5 min</span>
          </div>
          <div className="health-grid">
            {health.map((item) => (
              <article key={item.name} className={`health-card ${item.status}`}>
                <div>
                  <b>{item.name}</b>
                  <span>{statusLabel(item.status)}</span>
                </div>
                <p>{item.detail}</p>
                <small>{item.latency_ms != null ? `${item.latency_ms}ms` : "Latest check"}</small>
              </article>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">AI helper</p>
              <h2>Troubleshooting Flows</h2>
            </div>
            <span>{troubleshootingFlows.length} process playbooks</span>
          </div>
          <div className="troubleshooting-grid">
            {troubleshootingFlows.map((flow) => (
              <article key={flow.id}>
                <div className="flow-heading">
                  <b>{flow.name}</b>
                  <span>{(flow.systems || []).slice(0, 2).join(" + ")}</span>
                </div>
                <p>{flow.trigger}</p>
                <ol>
                  {(flow.steps || []).slice(0, 4).map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
                <small>Healthy signal: {flow.healthy_signal}</small>
              </article>
            ))}
            {!troubleshootingFlows.length ? (
              <article>
                <div className="flow-heading">
                  <b>Waiting for live flows</b>
                  <span>Pending</span>
                </div>
                <p>Run the systems healthcheck to load AI troubleshooting playbooks.</p>
              </article>
            ) : null}
          </div>
        </section>

        <section className="split-grid">
          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Section 2</p>
                <h2>Demo Engagement Metrics</h2>
              </div>
            </div>
            <MiniBars values={trend} />
            <div className="metric-list">
              <span>Demo clicks: {metrics.demo_clicks_7d}</span>
              <span>Call success: {metrics.call_success_rate}%</span>
              <span>Completion: {metrics.completion_rate}%</span>
              <span>Avg duration: {metrics.avg_call_duration_seconds}s</span>
              <span>SMS delivery: {metrics.post_call_sms_delivery_rate}%</span>
              <span>Form abandonment: {metrics.form_abandonment_rate}%</span>
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Section 3</p>
                <h2>Visitor Analytics</h2>
              </div>
            </div>
            <div className="analytics-grid">
              <span><b>{analytics.pageviews_7d}</b> page views</span>
              <span><b>{analytics.unique_visitors}</b> unique visitors</span>
              <span><b>{analytics.bounce_rate}%</b> bounce rate</span>
              <span><b>{analytics.avg_time_on_site_seconds}s</b> avg time</span>
            </div>
            <div className="source-row">
              {(analytics.top_sources || []).map((source) => (
                <span key={source}>{source}</span>
              ))}
            </div>
          </article>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Section 4</p>
              <h2>Feature Status Board</h2>
            </div>
          </div>
          <div className="feature-board">
            {featureBoard.map((item) => (
              <article key={item.feature} className={item.status}>
                <span>{item.feature}</span>
                <strong>{statusLabel(item.status)}</strong>
                <p>{item.result}</p>
                <small>Last checked {item.last_tested}</small>
              </article>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Already shipped</p>
              <h2>Admin Dashboard Sections</h2>
            </div>
          </div>
          <div className="status-table">
            {liveSections.map((section) => (
              <article key={section.title}>
                <b>{section.title}</b>
                <span>{section.status}</span>
                <p>{section.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="split-grid">
          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Priority 1</p>
                <h2>Revenue and Tenant Health</h2>
              </div>
            </div>
            <div className="tenant-list">
              <span>MRR tracker: active tenants x plan value</span>
              <span>Tenant health cards: calls, jobs, last activity</span>
              <span>Trial to paid funnel: demo, call, trial, subscribed</span>
              <span>Churn risk: tenant quiet for 7 days</span>
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Priority 2</p>
                <h2>Lead Scoring</h2>
              </div>
            </div>
            <div className="score-list">
              {leadSignals.map((signal) => (
                <div key={signal.label}>
                  <span>{signal.label}</span>
                  <b>{signal.score}</b>
                  <p>{signal.value}</p>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="split-grid">
          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Priority 3</p>
                <h2>Adrian Performance Analytics</h2>
              </div>
            </div>
            <div className="check-list">
              {adrianInsights.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Priority 4</p>
                <h2>Alerts and Notifications</h2>
              </div>
            </div>
            <div className="alert-table">
              {alertRules.map((item) => (
                <div key={item.rule}>
                  <b>{item.rule}</b>
                  <span>{item.severity}</span>
                  <p>{item.channel}</p>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="split-grid">
          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Priority 5</p>
                <h2>Tenant Self-Service Config</h2>
              </div>
            </div>
            <div className="pill-grid">
              {tenantConfig.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Data and jobs</p>
                <h2>Monitoring Build Plan</h2>
              </div>
            </div>
            <div className="schema-list">
              {healthTables.map((table) => (
                <div key={table.name}>
                  <b>{table.name}</b>
                  <p>{table.purpose}</p>
                </div>
              ))}
            </div>
            <div className="job-list">
              {backgroundJobs.map((job) => (
                <span key={job}>{job}</span>
              ))}
            </div>
          </article>
        </section>
          </>
        )}
      </main>

      <style jsx>{`
        .admin-shell {
          min-height: 100vh;
          background: var(--paper);
          color: var(--ink);
          padding: 24px;
        }

        .admin-hero,
        .kpi-grid,
        .login-card,
        .panel,
        .split-grid {
          max-width: 1180px;
          margin: 0 auto;
        }

        .login-card {
          max-width: 520px;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          box-shadow: var(--shadow);
          padding: 24px;
        }

        .login-card .eyebrow {
          color: var(--accent-dark);
        }

        .login-card h1 {
          color: var(--navy);
          font-size: clamp(2rem, 5vw, 3rem);
        }

        .login-card p {
          color: #35505b;
          line-height: 1.6;
        }

        .login-card form {
          display: grid;
          gap: 14px;
          margin-top: 20px;
        }

        .login-card label {
          display: grid;
          gap: 6px;
          color: var(--navy);
          font-weight: 850;
        }

        .login-card input {
          min-height: 48px;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 0 12px;
          font-size: 1rem;
        }

        .login-card button,
        .overall button,
        .healthcheck-button {
          min-height: 44px;
          border: 0;
          border-radius: 8px;
          background: linear-gradient(120deg, var(--navy-deep), var(--navy-light));
          color: #fffdf8;
          font-weight: 850;
          cursor: pointer;
        }

        .login-card .link-button,
        .reset-form button {
          background: transparent;
          color: var(--navy);
          border: 1px solid var(--line);
        }

        .reset-form {
          margin-top: 14px;
          border-top: 1px solid var(--line);
          padding-top: 14px;
        }

        .reset-form p,
        .reset-message {
          margin: 0;
          color: #35505b;
          line-height: 1.55;
          font-weight: 750;
        }

        .reset-message {
          margin-top: 14px;
          color: #247a4d;
        }

        .overall button:disabled,
        .healthcheck-button:disabled {
          cursor: wait;
          opacity: 0.7;
        }

        .login-card button:disabled {
          cursor: wait;
          opacity: 0.7;
        }

        .auth-error {
          margin-top: 14px;
          color: var(--error);
          font-weight: 850;
        }

        .admin-hero {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 320px;
          gap: 20px;
          align-items: stretch;
          border-radius: 8px;
          background: linear-gradient(120deg, var(--navy), var(--navy-light));
          color: #fffdf8;
          padding: 30px;
        }

        .eyebrow {
          margin: 0 0 8px;
          color: #ffd9ae;
          font-size: 0.76rem;
          font-weight: 900;
          letter-spacing: 0.12em;
          text-transform: uppercase;
        }

        h1,
        h2,
        h3,
        p {
          overflow-wrap: anywhere;
        }

        h1 {
          max-width: 840px;
          margin: 0;
          font-size: clamp(2.3rem, 5vw, 4rem);
          line-height: 1.02;
        }

        .admin-hero p:not(.eyebrow) {
          max-width: 760px;
          color: #f7efe1;
          line-height: 1.65;
        }

        .overall,
        .kpi-grid article,
        .panel {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          box-shadow: var(--shadow);
        }

        .overall {
          color: var(--ink);
          padding: 20px;
          display: grid;
          align-content: center;
          gap: 8px;
        }

        .overall span,
        .kpi-grid span,
        .panel-heading > span {
          color: #4e6a74;
          font-size: 0.8rem;
          font-weight: 900;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .overall strong {
          color: var(--navy);
          font-size: 2rem;
        }

        .overall.green {
          border-top: 5px solid #247a4d;
        }

        .overall.yellow {
          border-top: 5px solid var(--accent);
        }

        .overall.red {
          border-top: 5px solid var(--error);
        }

        .kpi-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 12px;
          margin-top: 18px;
        }

        .kpi-grid article {
          padding: 18px;
        }

        .kpi-grid strong {
          display: block;
          margin: 8px 0;
          color: var(--navy);
          font-size: 2rem;
          line-height: 1;
        }

        .kpi-grid p,
        .health-card p,
        .feature-board p,
        .status-table p,
        .schema-list p,
        .alert-table p,
        .score-list p {
          margin: 0;
          color: #35505b;
          line-height: 1.5;
        }

        .panel,
        .split-grid {
          margin-top: 18px;
        }

        .panel {
          padding: 20px;
        }

        .panel-heading {
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: start;
          margin-bottom: 18px;
        }

        .panel h2 {
          margin: 0;
          color: var(--navy);
          font-size: 1.7rem;
          line-height: 1.12;
        }

        .system-health-panel {
          border-top: 6px solid var(--accent);
        }

        .system-health-panel.green {
          border-top-color: #247a4d;
        }

        .system-health-panel.red {
          border-top-color: var(--error);
        }

        .system-health-body {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr) auto;
          gap: 18px;
          align-items: center;
        }

        .system-health-body p {
          margin: 0 0 4px;
          color: #35505b;
          font-weight: 850;
        }

        .system-health-body small {
          color: #4e6a74;
          font-weight: 750;
        }

        .health-orb {
          width: 54px;
          height: 54px;
          border-radius: 50%;
          background: var(--accent);
          box-shadow: 0 0 0 10px rgba(212, 124, 43, 0.12);
        }

        .health-orb.green {
          background: #247a4d;
          box-shadow: 0 0 0 10px rgba(36, 122, 77, 0.12);
        }

        .health-orb.red {
          background: var(--error);
          box-shadow: 0 0 0 10px rgba(176, 58, 46, 0.12);
        }

        .health-counts {
          display: grid;
          grid-template-columns: repeat(3, auto);
          gap: 8px;
        }

        .health-counts span {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fff8ee;
          color: #35505b;
          font-weight: 850;
          padding: 10px 12px;
          text-align: center;
        }

        .health-counts b {
          display: block;
          color: var(--navy);
          font-size: 1.4rem;
        }

        .health-grid,
        .feature-board,
        .status-table,
        .pill-grid,
        .troubleshooting-grid {
          display: grid;
          gap: 12px;
        }

        .health-grid {
          grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .health-card,
        .feature-board article,
        .status-table article {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fffdf8;
          padding: 14px;
        }

        .health-card {
          border-top: 5px solid var(--accent);
          display: grid;
          gap: 10px;
        }

        .health-card.green,
        .feature-board .green {
          border-top-color: #247a4d;
        }

        .health-card.red,
        .feature-board .red {
          border-top-color: var(--error);
        }

        .health-card div {
          display: flex;
          justify-content: space-between;
          gap: 10px;
        }

        .health-card b,
        .feature-board strong,
        .status-table b,
        .schema-list b,
        .alert-table b {
          color: var(--navy);
        }

        .health-card span,
        .feature-board small,
        .health-card small {
          color: #4e6a74;
          font-weight: 800;
        }

        .split-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 18px;
        }

        .mini-bars {
          height: 150px;
          display: grid;
          grid-template-columns: repeat(7, 1fr);
          gap: 8px;
          align-items: end;
          margin-bottom: 16px;
          border-bottom: 1px solid var(--line);
        }

        .mini-bars span {
          display: block;
          border-radius: 6px 6px 0 0;
          background: linear-gradient(180deg, var(--accent), #ffe4ad);
        }

        .metric-list,
        .analytics-grid,
        .tenant-list,
        .check-list,
        .job-list,
        .source-row,
        .pill-grid {
          display: grid;
          gap: 10px;
        }

        .metric-list,
        .analytics-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .metric-list span,
        .analytics-grid span,
        .source-row span,
        .tenant-list span,
        .check-list span,
        .job-list span,
        .pill-grid span {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fff8ee;
          padding: 12px;
          color: var(--navy);
          font-weight: 800;
        }

        .analytics-grid b {
          display: block;
          font-size: 1.5rem;
        }

        .source-row {
          grid-template-columns: repeat(4, minmax(0, 1fr));
          margin-top: 14px;
        }

        .feature-board {
          grid-template-columns: repeat(6, minmax(0, 1fr));
        }

        .feature-board article {
          border-top: 5px solid var(--accent);
          display: grid;
          gap: 8px;
        }

        .feature-board span,
        .status-table span,
        .alert-table span,
        .score-list span {
          color: #4e6a74;
          font-size: 0.78rem;
          font-weight: 900;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .status-table {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .status-table article {
          display: grid;
          gap: 8px;
        }

        .troubleshooting-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .troubleshooting-grid article {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fffdf8;
          padding: 14px;
          display: grid;
          gap: 10px;
        }

        .flow-heading {
          display: grid;
          gap: 4px;
        }

        .flow-heading b {
          color: var(--navy);
          font-size: 1rem;
        }

        .flow-heading span,
        .troubleshooting-grid small {
          color: #4e6a74;
          font-weight: 800;
          line-height: 1.45;
        }

        .troubleshooting-grid p {
          margin: 0;
          color: #35505b;
          line-height: 1.55;
        }

        .troubleshooting-grid ol {
          margin: 0;
          padding-left: 18px;
          color: #233d49;
          line-height: 1.55;
        }

        .troubleshooting-grid li {
          margin-bottom: 5px;
        }

        .jobber-controls {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }

        .jobber-controls label {
          display: grid;
          gap: 4px;
          font-size: 0.78rem;
          font-weight: 800;
          color: var(--navy);
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .jobber-controls input {
          min-height: 36px;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 0 10px;
          width: 140px;
          font-size: 0.95rem;
        }

        .jobber-refresh {
          min-height: 36px;
          border: 0;
          border-radius: 8px;
          background: linear-gradient(120deg, var(--navy-deep), var(--navy-light));
          color: #fffdf8;
          font-weight: 850;
          cursor: pointer;
          padding: 0 12px;
          align-self: end;
        }

        .jobber-refresh:disabled {
          opacity: 0.7;
          cursor: wait;
        }

        .jobber-refresh-msg {
          margin: 0 0 8px;
          color: #35505b;
          font-weight: 800;
        }

        .jobber-meta {
          margin-bottom: 12px;
          color: #4e6a74;
          font-weight: 800;
        }

        .jobber-table {
          display: grid;
          gap: 10px;
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .jobber-table article {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fffdf8;
          padding: 12px;
          display: grid;
          gap: 6px;
        }

        .jobber-table article b {
          color: var(--navy);
        }

        .jobber-table article span {
          color: #35505b;
          font-size: 0.9rem;
        }

        .risk-ok {
          border-top: 5px solid #247a4d;
        }

        .risk-warning {
          border-top: 5px solid var(--accent);
        }

        .risk-critical {
          border-top: 5px solid var(--error);
        }

        .risk-unknown {
          border-top: 5px solid #94a3b8;
        }

        .score-list,
        .alert-table,
        .schema-list {
          display: grid;
          gap: 12px;
        }

        .score-list div,
        .alert-table div,
        .schema-list div {
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 14px;
          background: #fffdf8;
        }

        .score-list b {
          display: block;
          color: var(--accent-dark);
          font-size: 2rem;
          line-height: 1;
          margin: 6px 0;
        }

        .alert-table div {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 6px 12px;
        }

        .alert-table p {
          grid-column: 1 / -1;
        }

        .pill-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .schema-list {
          margin-bottom: 14px;
        }

        @media (max-width: 980px) {
          .admin-hero,
          .split-grid {
            grid-template-columns: 1fr;
          }

          .kpi-grid,
          .health-grid,
          .feature-board,
          .status-table,
          .troubleshooting-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .jobber-table {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 640px) {
          .admin-shell {
            padding: 12px;
          }

          .admin-hero,
          .panel {
            padding: 16px;
          }

          .system-health-body {
            grid-template-columns: 1fr;
          }

          .health-counts {
            grid-template-columns: 1fr;
          }

          .kpi-grid,
          .health-grid,
          .metric-list,
          .analytics-grid,
          .source-row,
          .feature-board,
          .status-table,
          .pill-grid,
          .troubleshooting-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </>
  );
}
