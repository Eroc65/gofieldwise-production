import { useEffect, useState } from "react";

import {
  createCoachingSnippet,
  createHelpArticle,
  getAIGuideSettings,
  getCommProfile,
  listCoachingSnippets,
  listHelpArticles,
  listMarketingServicePackages,
  login,
  runReactivationEngine,
  updateAIGuideSettings,
  updateCommProfile,
} from "../lib/api";

export default function PlatformPage() {
  const [token, setToken] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState("");

  const [aiGuide, setAiGuide] = useState({ enabled: false, stage: "onboarding" });
  const [helpArticles, setHelpArticles] = useState([]);
  const [coachingSnippets, setCoachingSnippets] = useState([]);
  const [servicePackages, setServicePackages] = useState([]);
  const [commProfile, setCommProfile] = useState({ active: false });

  const [helpForm, setHelpForm] = useState({ slug: "", title: "", category: "general", context_key: "general", body: "" });
  const [coachForm, setCoachForm] = useState({ title: "", trade: "general", issue_pattern: "", senior_tip: "", checklist: "" });

  useEffect(() => {
    const savedToken = window.localStorage.getItem("fdp.dispatch.token") || "";
    const savedEmail = window.localStorage.getItem("fdp.dispatch.email") || "";
    if (savedToken) setToken(savedToken);
    if (savedEmail) setAuthEmail(savedEmail);
  }, []);

  async function withBusy(fn) {
    setBusy(true);
    setError("");
    setResult("");
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
      setToken(response.access_token);
      window.localStorage.setItem("fdp.dispatch.token", response.access_token);
      window.localStorage.setItem("fdp.dispatch.email", authEmail);
    });
  }

  async function refreshAll() {
    await withBusy(async () => {
      const [guide, help, coach, packs, comm] = await Promise.all([
        getAIGuideSettings({ token }),
        listHelpArticles({ token }),
        listCoachingSnippets({ token }),
        listMarketingServicePackages({ token }),
        getCommProfile({ token }),
      ]);
      setAiGuide(guide);
      setHelpArticles(Array.isArray(help) ? help : []);
      setCoachingSnippets(Array.isArray(coach) ? coach : []);
      setServicePackages(Array.isArray(packs) ? packs : []);
      setCommProfile(comm || { active: false });
    });
  }

  async function saveAIGuide() {
    await withBusy(async () => {
      const out = await updateAIGuideSettings({ token, enabled: aiGuide.enabled, stage: aiGuide.stage });
      setAiGuide(out);
      setResult("AI Guide settings updated.");
    });
  }

  async function addHelpArticle() {
    await withBusy(async () => {
      await createHelpArticle({ token, payload: helpForm });
      const rows = await listHelpArticles({ token });
      setHelpArticles(Array.isArray(rows) ? rows : []);
      setResult("Help article created.");
    });
  }

  async function addCoachingSnippet() {
    await withBusy(async () => {
      await createCoachingSnippet({ token, payload: coachForm });
      const rows = await listCoachingSnippets({ token });
      setCoachingSnippets(Array.isArray(rows) ? rows : []);
      setResult("Coaching snippet created.");
    });
  }

  async function runReactivation() {
    await withBusy(async () => {
      const run = await runReactivationEngine({ token, lookbackDays: 180, limit: 250, dryRun: false });
      setResult(`Reactivation queued ${run.queued_count} of ${run.candidate_count} candidates.`);
    });
  }

  async function saveCommProfile() {
    await withBusy(async () => {
      const out = await updateCommProfile({ token, payload: commProfile });
      setCommProfile(out);
      setResult("Communication profile saved.");
    });
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Platform Control</p>
        <h1>AI Guide, Contextual Help, Coaching, And Messaging Profiles</h1>
        <p>Use this page to operate the new platform systems without touching the database.</p>
        <div className="hero-actions">
          <a className="ghost-link" href="/">Marketing Site</a>
          <a className="ghost-link" href="/leads">Lead Inbox</a>
          <button type="button" onClick={refreshAll} disabled={!token || busy}>Refresh Platform Data</button>
        </div>
      </section>

      <section className="dispatch-card">
        <header className="dispatch-head">
          <h2>Operator Access</h2>
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
          <button type="button" onClick={onLogin} disabled={busy}>Login</button>
        </div>
        {error ? <p className="submit-error">{error}</p> : null}
        {result ? <p className="submit-note">{result}</p> : null}
      </section>

      <section className="dispatch-card">
        <h2>AI Guide</h2>
        <div className="form-grid">
          <label>
            Enabled
            <select value={aiGuide.enabled ? "yes" : "no"} onChange={(e) => setAiGuide((prev) => ({ ...prev, enabled: e.target.value === "yes" }))}>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </label>
          <label>
            Stage
            <input value={aiGuide.stage || "onboarding"} onChange={(e) => setAiGuide((prev) => ({ ...prev, stage: e.target.value }))} />
          </label>
        </div>
        <div className="actions">
          <button type="button" onClick={saveAIGuide} disabled={!token || busy}>Save AI Guide</button>
        </div>
      </section>

      <section className="dispatch-card">
        <h2>Communication Tenant Profile</h2>
        <div className="form-grid">
          <label>
            Active
            <select value={commProfile.active ? "yes" : "no"} onChange={(e) => setCommProfile((p) => ({ ...p, active: e.target.value === "yes" }))}>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </label>
          <label>
            Twilio Account SID
            <input value={commProfile.twilio_account_sid || ""} onChange={(e) => setCommProfile((p) => ({ ...p, twilio_account_sid: e.target.value }))} />
          </label>
          <label>
            Twilio Auth Token
            <input type="password" value={commProfile.twilio_auth_token || ""} onChange={(e) => setCommProfile((p) => ({ ...p, twilio_auth_token: e.target.value }))} />
          </label>
          <label>
            Messaging Service SID
            <input value={commProfile.twilio_messaging_service_sid || ""} onChange={(e) => setCommProfile((p) => ({ ...p, twilio_messaging_service_sid: e.target.value }))} />
          </label>
          <label>
            Twilio Phone
            <input value={commProfile.twilio_phone_number || ""} onChange={(e) => setCommProfile((p) => ({ ...p, twilio_phone_number: e.target.value }))} />
          </label>
          <label>
            Retell Agent ID
            <input value={commProfile.retell_agent_id || ""} onChange={(e) => setCommProfile((p) => ({ ...p, retell_agent_id: e.target.value }))} />
          </label>
          <label>
            Retell Phone
            <input value={commProfile.retell_phone_number || ""} onChange={(e) => setCommProfile((p) => ({ ...p, retell_phone_number: e.target.value }))} />
          </label>
        </div>
        <div className="actions">
          <button type="button" onClick={saveCommProfile} disabled={!token || busy}>Save Communication Profile</button>
        </div>
      </section>

      <section className="dispatch-card">
        <h2>Contextual Help</h2>
        <div className="form-grid">
          <label>Slug<input value={helpForm.slug} onChange={(e) => setHelpForm((p) => ({ ...p, slug: e.target.value }))} /></label>
          <label>Title<input value={helpForm.title} onChange={(e) => setHelpForm((p) => ({ ...p, title: e.target.value }))} /></label>
          <label>Category<input value={helpForm.category} onChange={(e) => setHelpForm((p) => ({ ...p, category: e.target.value }))} /></label>
          <label>Context Key<input value={helpForm.context_key} onChange={(e) => setHelpForm((p) => ({ ...p, context_key: e.target.value }))} /></label>
          <label className="span-2">Body<textarea rows={3} value={helpForm.body} onChange={(e) => setHelpForm((p) => ({ ...p, body: e.target.value }))} /></label>
        </div>
        <div className="actions">
          <button type="button" onClick={addHelpArticle} disabled={!token || busy}>Create Help Article</button>
        </div>
        <ul>
          {helpArticles.slice(0, 5).map((item) => <li key={item.id}>{item.title} ({item.context_key})</li>)}
        </ul>
      </section>

      <section className="dispatch-card">
        <h2>Tribal Coaching</h2>
        <div className="form-grid">
          <label>Title<input value={coachForm.title} onChange={(e) => setCoachForm((p) => ({ ...p, title: e.target.value }))} /></label>
          <label>Trade<input value={coachForm.trade} onChange={(e) => setCoachForm((p) => ({ ...p, trade: e.target.value }))} /></label>
          <label>Issue Pattern<input value={coachForm.issue_pattern} onChange={(e) => setCoachForm((p) => ({ ...p, issue_pattern: e.target.value }))} /></label>
          <label className="span-2">Senior Tip<textarea rows={3} value={coachForm.senior_tip} onChange={(e) => setCoachForm((p) => ({ ...p, senior_tip: e.target.value }))} /></label>
          <label className="span-2">Checklist<textarea rows={2} value={coachForm.checklist} onChange={(e) => setCoachForm((p) => ({ ...p, checklist: e.target.value }))} /></label>
        </div>
        <div className="actions">
          <button type="button" onClick={addCoachingSnippet} disabled={!token || busy}>Create Coaching Snippet</button>
        </div>
        <ul>
          {coachingSnippets.slice(0, 5).map((item) => <li key={item.id}>{item.trade}: {item.title}</li>)}
        </ul>
      </section>

      <section className="dispatch-card">
        <h2>Growth Packages + Reactivation</h2>
        <div className="actions">
          <button type="button" onClick={runReactivation} disabled={!token || busy}>Run Reactivation Now</button>
        </div>
        <div className="results-grid">
          {servicePackages.map((pkg) => (
            <article className="panel" key={pkg.code}>
              <h3>{pkg.name}</h3>
              <p>${pkg.monthly_price_usd}/mo</p>
              <p>{pkg.summary}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
