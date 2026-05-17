import { useEffect, useMemo, useState } from "react";
import {
  getConnectSettings,
  getCurrentUser,
  getPublicStatus,
  runConnectTestCall,
  updateConnectSettings,
} from "../lib/api";

const TOKEN_KEYS = ["fdp.dispatch.token", "access_token", "token"];

const STEPS = [
  { id: "business", label: "Business profile" },
  { id: "trade", label: "Trade type" },
  { id: "service_area", label: "Service area" },
  { id: "hours", label: "Business hours" },
  { id: "owner_phone", label: "Owner notification phone" },
  { id: "backup", label: "Backup contact" },
  { id: "emergency", label: "Emergency rules" },
  { id: "after_hours", label: "After-hours message" },
  { id: "workflow", label: "Workflow mode" },
  { id: "crm", label: "CRM destination" },
  { id: "test_call", label: "Test AI call" },
];

const DEFAULT_SETTINGS = {
  business_name: "",
  owner_name: "",
  public_phone: "",
  trade_type: "HVAC",
  service_area: "",
  business_hours: "Monday-Friday 8:00 AM-5:00 PM",
  owner_notification_phone: "",
  backup_contact_name: "",
  backup_contact_phone: "",
  emergency_rules: "",
  after_hours_message: "",
  workflow_mode: "hybrid",
  crm_destination: "email",
  crm_destination_detail: "",
  test_call_phone: "",
  test_customer_name: "Test Customer",
  test_customer_phone: "",
  test_call_confirmed: false,
  test_call_result: null,
};

function readToken() {
  if (typeof window === "undefined") return "";
  for (const key of TOKEN_KEYS) {
    const value = window.localStorage.getItem(key);
    if (value) return value;
  }
  return "";
}

function completionFor(settings) {
  const required = [
    "business_name",
    "owner_name",
    "public_phone",
    "trade_type",
    "service_area",
    "business_hours",
    "owner_notification_phone",
    "backup_contact_name",
    "backup_contact_phone",
    "emergency_rules",
    "after_hours_message",
    "workflow_mode",
    "crm_destination",
    "test_call_phone",
  ];
  const filled = required.filter((key) => String(settings[key] || "").trim()).length;
  const test = settings.test_call_confirmed ? 1 : 0;
  return Math.round(((filled + test) / (required.length + 1)) * 100);
}

function isComplete(settings) {
  return completionFor(settings) === 100;
}

function Field({ label, children, hint }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint ? <small>{hint}</small> : null}
      <style jsx>{`
        .field {
          display: grid;
          gap: 7px;
          color: #10231e;
          font-weight: 900;
        }
        .field :global(input),
        .field :global(select),
        .field :global(textarea) {
          width: 100%;
          border: 1px solid rgba(19, 35, 31, 0.18);
          border-radius: 10px;
          background: #fffdf8;
          color: #13231f;
          font: inherit;
          padding: 12px;
          box-sizing: border-box;
        }
        .field :global(textarea) {
          min-height: 98px;
          resize: vertical;
          line-height: 1.55;
        }
        small {
          color: #63766f;
          font-weight: 600;
          line-height: 1.45;
        }
      `}</style>
    </label>
  );
}

export default function ConnectCenterPage() {
  const [token, setToken] = useState("");
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState(null);
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [savedAt, setSavedAt] = useState("");
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [runningTest, setRunningTest] = useState(false);
  const [message, setMessage] = useState("Checking your operator session...");
  const [error, setError] = useState("");

  const progress = useMemo(() => completionFor(settings), [settings]);
  const completed = isComplete(settings);
  const step = STEPS[activeStep];

  useEffect(() => {
    const storedToken = readToken();
    setToken(storedToken);

    if (!storedToken) {
      setLoading(false);
      setMessage("No operator session found. Complete operator setup first.");
      return;
    }

    (async () => {
      try {
        const [me, publicStatus, connect] = await Promise.all([
          getCurrentUser({ token: storedToken }),
          getPublicStatus().catch(() => null),
          getConnectSettings({ token: storedToken }),
        ]);
        const loaded = { ...DEFAULT_SETTINGS, ...(connect?.settings || {}) };
        setUser(me);
        setStatus(publicStatus);
        setSettings(loaded);
        setSavedAt(connect?.updated_at || "");
        setMessage(connect?.completed ? "Connect setup complete." : "Connect setup in progress.");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load Connect Center.");
        setMessage("Connect Center could not be loaded.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function updateField(key, value) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  async function save(nextSettings = settings, nextStep = activeStep) {
    if (!token) return false;
    setSaving(true);
    setError("");
    try {
      const payload = await updateConnectSettings({
        token,
        settings: nextSettings,
        completed: isComplete(nextSettings),
      });
      setSavedAt(payload?.updated_at || new Date().toISOString());
      setMessage(isComplete(nextSettings) ? "Connect setup complete." : "Progress saved.");
      setActiveStep(nextStep);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save Connect settings.");
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function nextStep() {
    await save(settings, Math.min(activeStep + 1, STEPS.length - 1));
  }

  async function previousStep() {
    await save(settings, Math.max(activeStep - 1, 0));
  }

  async function markTestCallComplete() {
    const next = { ...settings, test_call_confirmed: true };
    setSettings(next);
    await save(next, activeStep);
  }

  async function runTestCall() {
    if (!token) return;
    const customerName = settings.test_customer_name || "Test Customer";
    const customerPhone = settings.test_customer_phone || settings.test_call_phone;
    const preSave = {
      ...settings,
      test_customer_name: customerName,
      test_customer_phone: customerPhone,
      test_call_phone: customerPhone,
    };
    setRunningTest(true);
    setError("");
    try {
      await save(preSave, activeStep);
      const result = await runConnectTestCall({ token, customerName, customerPhone });
      const next = {
        ...preSave,
        test_call_confirmed: Boolean(result?.lead_id),
        test_call_result: result,
      };
      setSettings(next);
      await save(next, activeStep);
      setMessage(result?.message || "Connect test activation completed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not run Connect test call.");
    } finally {
      setRunningTest(false);
    }
  }

  function signOut() {
    TOKEN_KEYS.forEach((key) => window.localStorage.removeItem(key));
    window.localStorage.removeItem("gofieldwise_user");
    window.localStorage.removeItem("gofieldwise_org");
    window.location.href = "/operator/setup";
  }

  function renderStep() {
    switch (step.id) {
      case "business":
        return (
          <div className="formGrid">
            <Field label="Business name">
              <input value={settings.business_name} onChange={(event) => updateField("business_name", event.target.value)} placeholder="Example Plumbing LLC" />
            </Field>
            <Field label="Owner name">
              <input value={settings.owner_name} onChange={(event) => updateField("owner_name", event.target.value)} placeholder="Eric Hicks" />
            </Field>
            <Field label="Public business phone">
              <input value={settings.public_phone} onChange={(event) => updateField("public_phone", event.target.value)} placeholder="405-555-0100" inputMode="tel" />
            </Field>
          </div>
        );
      case "trade":
        return (
          <Field label="Primary trade">
            <select value={settings.trade_type} onChange={(event) => updateField("trade_type", event.target.value)}>
              {["HVAC", "Plumbing", "Electrical", "Cleaning", "Roofing", "Landscaping", "Other"].map((trade) => (
                <option key={trade} value={trade}>{trade}</option>
              ))}
            </select>
          </Field>
        );
      case "service_area":
        return (
          <Field label="Service area" hint="List the cities, neighborhoods, or counties your team serves.">
            <textarea value={settings.service_area} onChange={(event) => updateField("service_area", event.target.value)} placeholder="Tulsa, Broken Arrow, Jenks, Bixby, Owasso" />
          </Field>
        );
      case "hours":
        return (
          <Field label="Business hours" hint="Include weekend or emergency availability if it applies.">
            <textarea value={settings.business_hours} onChange={(event) => updateField("business_hours", event.target.value)} />
          </Field>
        );
      case "owner_phone":
        return (
          <Field label="Owner notification phone" hint="Where GoFieldWise should send urgent lead and missed-call alerts.">
            <input value={settings.owner_notification_phone} onChange={(event) => updateField("owner_notification_phone", event.target.value)} placeholder="405-555-0100" inputMode="tel" />
          </Field>
        );
      case "backup":
        return (
          <div className="formGrid">
            <Field label="Backup contact name">
              <input value={settings.backup_contact_name} onChange={(event) => updateField("backup_contact_name", event.target.value)} placeholder="Dispatch manager" />
            </Field>
            <Field label="Backup contact phone">
              <input value={settings.backup_contact_phone} onChange={(event) => updateField("backup_contact_phone", event.target.value)} placeholder="918-555-0100" inputMode="tel" />
            </Field>
          </div>
        );
      case "emergency":
        return (
          <Field label="Emergency rules" hint="Tell the AI what should count as urgent and who should be alerted.">
            <textarea value={settings.emergency_rules} onChange={(event) => updateField("emergency_rules", event.target.value)} placeholder="Burst pipes, no heat below 40 degrees, electrical burning smell, active water leaks. Text owner immediately." />
          </Field>
        );
      case "after_hours":
        return (
          <Field label="After-hours customer message">
            <textarea value={settings.after_hours_message} onChange={(event) => updateField("after_hours_message", event.target.value)} placeholder="Thanks for calling. We received your request and will follow up first thing in the morning. If this is an emergency, reply EMERGENCY." />
          </Field>
        );
      case "workflow":
        return (
          <div className="choiceGrid">
            {[
              ["standalone", "Standalone", "AI handles intake and customer response as the front office."],
              ["sidecar", "Sidecar", "AI watches for missed calls and drafts follow-up while your team stays primary."],
              ["hybrid", "Hybrid", "AI handles routine intake and escalates urgent or uncertain cases to a person."],
            ].map(([value, title, detail]) => (
              <button key={value} type="button" className={settings.workflow_mode === value ? "choice active" : "choice"} onClick={() => updateField("workflow_mode", value)}>
                <strong>{title}</strong>
                <span>{detail}</span>
              </button>
            ))}
          </div>
        );
      case "crm":
        return (
          <div className="formGrid">
            <Field label="CRM destination">
              <select value={settings.crm_destination} onChange={(event) => updateField("crm_destination", event.target.value)}>
                <option value="email">Email summary</option>
                <option value="jobber">Jobber</option>
                <option value="housecall_pro">Housecall Pro</option>
                <option value="google_sheet">Google Sheet</option>
                <option value="other">Other</option>
              </select>
            </Field>
            <Field label="Destination detail" hint="Add the email address, CRM notes, or destination your team should use.">
              <input value={settings.crm_destination_detail} onChange={(event) => updateField("crm_destination_detail", event.target.value)} placeholder="dispatch@example.com" />
            </Field>
          </div>
        );
      case "test_call":
        const result = settings.test_call_result;
        const card = (label, ok, detail) => (
          <div className={ok ? "statusCard good" : "statusCard muted"}>
            <strong>{label}</strong>
            <span>{detail}</span>
          </div>
        );
        return (
          <div className="testBox">
            <div className="formGrid">
              <Field label="Test customer name">
                <input value={settings.test_customer_name} onChange={(event) => updateField("test_customer_name", event.target.value)} placeholder="Jane Customer" />
              </Field>
              <Field label="Test customer phone" hint="The number used for the test AI call and customer confirmation SMS.">
                <input value={settings.test_customer_phone || settings.test_call_phone} onChange={(event) => { updateField("test_customer_phone", event.target.value); updateField("test_call_phone", event.target.value); }} placeholder="405-555-0100" inputMode="tel" />
              </Field>
            </div>
            <button type="button" className="secondaryAction" onClick={runTestCall} disabled={saving || runningTest || !(settings.test_customer_phone || settings.test_call_phone)}>
              {runningTest ? "Running test..." : "Run Test AI Call"}
            </button>
            {result ? (
              <div className="statusGrid">
                {card("Lead draft created", Boolean(result.lead_id), result.lead_id ? `Lead #${result.lead_id}` : "No lead returned")}
                {card("Owner SMS sent", Boolean(result.owner_sms_sent), result.owner_sms_sent ? "Owner notification processed" : result.errors?.owner_sms || "Not sent")}
                {card("Customer confirmation sent", Boolean(result.customer_sms_sent), result.customer_sms_sent ? "Customer confirmation processed" : result.errors?.customer_sms || "Not sent")}
                {card("AI call started/simulated", Boolean(result.call_started), result.call_started ? `Call ${result.call_id || "started"}` : result.errors?.call || "Simulated safely")}
              </div>
            ) : (
              <div className="statusGrid">
                {card("Lead draft created", false, "Waiting for test")}
                {card("Owner SMS sent", false, "Waiting for test")}
                {card("Customer confirmation sent", false, "Waiting for test")}
                {card("AI call started/simulated", false, "Waiting for test")}
              </div>
            )}
            <Field label="Phone to use for legacy test status" hint="Kept for compatibility with saved setup progress.">
              <input value={settings.test_call_phone} onChange={(event) => updateField("test_call_phone", event.target.value)} placeholder="405-555-0100" inputMode="tel" />
            </Field>
            <button type="button" className="secondaryAction" onClick={markTestCallComplete} disabled={saving || !settings.test_call_phone}>
              {settings.test_call_confirmed ? "Test call marked complete" : "Mark test call ready"}
            </button>
          </div>
        );
      default:
        return null;
    }
  }

  return (
    <main className="connectShell">
      <section className="hero">
        <p className="eyebrow">GoFieldWise Connect Center</p>
        <h1>{completed ? "Your AI front office setup is ready." : "Let’s set up your AI front office step by step."}</h1>
        <p className="intro">
          {completed
            ? "Place a test call to confirm the experience, then keep this page as your setup command center."
            : "Answer each setup step once. Your progress saves as you move through the wizard."}
        </p>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>{user ? "Connect activation" : "Operator session"}</h2>
            <p>{loading ? "Loading Connect Center..." : message}</p>
          </div>
          {token ? <span className="badge success">JWT detected</span> : <span className="badge danger">No token</span>}
        </div>

        {error ? <p className="error">{error}</p> : null}

        {!user && !loading ? (
          <div className="empty">
            <p>Complete operator setup with your one-time key to access Connect Center.</p>
            <a href="/operator/setup">Go to operator setup</a>
          </div>
        ) : null}

        {user ? (
          <>
            <div className="topGrid">
              <article>
                <span>Email</span>
                <strong>{user.email}</strong>
              </article>
              <article>
                <span>Role</span>
                <strong>{user.role}</strong>
              </article>
              <article>
                <span>API</span>
                <strong>{status?.ok === false ? "Needs attention" : "Reachable"}</strong>
              </article>
            </div>

            <div className="progressBlock">
              <div>
                <strong>{progress}% setup complete</strong>
                <span>{savedAt ? `Last saved ${new Date(savedAt).toLocaleString()}` : "Not saved yet"}</span>
              </div>
              <div className="progressTrack" aria-label="Setup progress">
                <div style={{ width: `${progress}%` }} />
              </div>
            </div>

            <div className="wizard">
              <nav className="steps" aria-label="Connect setup steps">
                {STEPS.map((item, index) => (
                  <button key={item.id} type="button" onClick={() => setActiveStep(index)} className={activeStep === index ? "step active" : "step"}>
                    <span>{index + 1}</span>
                    {item.label}
                  </button>
                ))}
              </nav>

              <div className="stepPanel">
                <p className="stepCount">Step {activeStep + 1} of {STEPS.length}</p>
                <h3>{step.label}</h3>
                {renderStep()}

                <div className="wizardActions">
                  <button type="button" className="ghost" onClick={previousStep} disabled={saving || activeStep === 0}>Back</button>
                  <button type="button" className="ghost" onClick={() => save()} disabled={saving}>{saving ? "Saving..." : "Save"}</button>
                  {activeStep < STEPS.length - 1 ? (
                    <button type="button" onClick={nextStep} disabled={saving}>{saving ? "Saving..." : "Save & continue"}</button>
                  ) : (
                    <button type="button" onClick={() => save(settings, activeStep)} disabled={saving}>{completed ? "Setup complete" : "Save test call step"}</button>
                  )}
                </div>
              </div>
            </div>

            {completed ? (
              <div className="completeBox">
                <strong>Your AI front office setup is ready.</strong>
                <p>Place a test call to confirm the experience. If something feels off, email support@gofieldwise.com and include the business name and test-call phone number.</p>
              </div>
            ) : null}

            <div className="actions">
              <a href="mailto:support@gofieldwise.com">Contact support@gofieldwise.com</a>
              <a href="/leads">Lead center</a>
              <a href="/metrics">Metrics</a>
              <button type="button" onClick={signOut}>Sign out</button>
            </div>
          </>
        ) : null}
      </section>

      <style jsx>{`
        .connectShell {
          min-height: 100vh;
          background: #f5f1e8;
          color: #13231f;
          padding: 44px 20px;
        }
        .hero,
        .panel {
          width: min(1120px, 100%);
          margin: 0 auto;
        }
        .hero {
          margin-bottom: 24px;
        }
        .eyebrow {
          color: #a66f00;
          font-size: 12px;
          font-weight: 900;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          margin: 0 0 10px;
        }
        h1 {
          color: #10231e;
          font-size: clamp(38px, 7vw, 72px);
          line-height: 0.95;
          margin: 0 0 12px;
          max-width: 880px;
        }
        .intro,
        .panel p,
        .empty p {
          color: #4f625c;
          line-height: 1.6;
        }
        .panel {
          background: #fff;
          border: 1px solid rgba(20, 35, 31, 0.12);
          border-radius: 18px;
          padding: clamp(20px, 4vw, 34px);
          box-shadow: 0 24px 70px rgba(24, 38, 35, 0.14);
        }
        .panelHeader {
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: flex-start;
          margin-bottom: 18px;
        }
        h2,
        h3 {
          margin: 0 0 4px;
          color: #10231e;
        }
        h3 {
          font-size: 28px;
          margin-bottom: 18px;
        }
        .badge {
          border-radius: 999px;
          padding: 7px 11px;
          font-size: 12px;
          font-weight: 900;
          white-space: nowrap;
        }
        .success {
          background: #eef9f1;
          color: #135c2d;
        }
        .danger {
          background: #fff1ee;
          color: #9d2f19;
        }
        .error {
          background: #fff1ee;
          border: 1px solid rgba(157, 47, 25, 0.2);
          border-radius: 12px;
          color: #9d2f19;
          font-weight: 800;
          padding: 12px 14px;
        }
        .topGrid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
          margin: 20px 0;
        }
        article {
          background: #fffdf8;
          border: 1px solid rgba(19, 35, 31, 0.14);
          border-radius: 12px;
          padding: 14px;
          min-width: 0;
        }
        article span,
        .progressBlock span,
        .stepCount {
          display: block;
          color: #667a73;
          font-size: 12px;
          font-weight: 800;
          margin-bottom: 5px;
        }
        article strong {
          color: #10231e;
          overflow-wrap: anywhere;
        }
        .progressBlock {
          display: grid;
          gap: 10px;
          background: #f7fbf9;
          border: 1px solid rgba(19, 35, 31, 0.12);
          border-radius: 14px;
          padding: 14px;
          margin-bottom: 18px;
        }
        .progressTrack {
          height: 9px;
          background: #e1ebe7;
          border-radius: 999px;
          overflow: hidden;
        }
        .progressTrack div {
          height: 100%;
          background: #17643a;
          border-radius: 999px;
          transition: width 0.2s ease;
        }
        .wizard {
          display: grid;
          grid-template-columns: 260px 1fr;
          gap: 18px;
          align-items: start;
        }
        .steps {
          display: grid;
          gap: 7px;
        }
        .step {
          display: flex;
          align-items: center;
          gap: 8px;
          text-align: left;
          background: #fffdf8;
          color: #3f544e;
          border: 1px solid rgba(19, 35, 31, 0.12);
          border-radius: 10px;
          padding: 9px 10px;
          font-weight: 800;
        }
        .step span {
          width: 22px;
          height: 22px;
          border-radius: 999px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          background: #edf3ef;
          font-size: 12px;
          flex: 0 0 auto;
        }
        .step.active {
          background: #13231f;
          color: #fff;
        }
        .step.active span {
          background: rgba(255, 255, 255, 0.18);
        }
        .stepPanel {
          border: 1px solid rgba(19, 35, 31, 0.14);
          border-radius: 14px;
          padding: 18px;
          background: #fffdf8;
        }
        .formGrid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
        }
        .formGrid :global(label:first-child:last-child),
        .formGrid :global(label:nth-child(3)) {
          grid-column: 1 / -1;
        }
        .choiceGrid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 10px;
        }
        .choice {
          min-height: 130px;
          align-items: flex-start;
          background: #fff;
          border: 1px solid rgba(19, 35, 31, 0.16);
          color: #13231f;
          display: grid;
          gap: 8px;
          text-align: left;
        }
        .choice span {
          color: #5b7069;
          font-weight: 600;
          line-height: 1.45;
        }
        .choice.active {
          border-color: #17643a;
          background: #eef9f1;
        }
        .testBox {
          display: grid;
          gap: 14px;
        }
        .statusGrid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
        }
        .statusCard {
          border: 1px solid rgba(19, 35, 31, 0.14);
          border-radius: 12px;
          background: #fff;
          padding: 12px;
          display: grid;
          gap: 4px;
        }
        .statusCard.good {
          background: #eef9f1;
          border-color: rgba(19, 92, 45, 0.22);
        }
        .statusCard.muted {
          background: #f7f3eb;
        }
        .statusCard span {
          color: #5b7069;
          font-size: 12px;
          font-weight: 700;
          line-height: 1.45;
        }
        .completeBox {
          margin-top: 18px;
          background: #eef9f1;
          border: 1px solid rgba(19, 92, 45, 0.2);
          color: #135c2d;
          border-radius: 14px;
          padding: 15px;
        }
        .completeBox p {
          color: #285c3e;
          margin-bottom: 0;
        }
        .wizardActions,
        .actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          margin-top: 20px;
        }
        a,
        button {
          border: 0;
          border-radius: 10px;
          background: #13231f;
          color: #fff;
          cursor: pointer;
          display: inline-flex;
          font: inherit;
          font-weight: 900;
          padding: 11px 14px;
          text-decoration: none;
        }
        button:disabled {
          cursor: not-allowed;
          opacity: 0.6;
        }
        .ghost,
        .secondaryAction,
        .actions button {
          background: #fff4de;
          color: #13231f;
          border: 1px solid #e5c17b;
        }
        .empty {
          background: #fffdf8;
          border: 1px dashed rgba(19, 35, 31, 0.22);
          border-radius: 14px;
          padding: 18px;
        }
        @media (max-width: 900px) {
          .wizard,
          .topGrid,
          .formGrid,
          .choiceGrid {
            grid-template-columns: 1fr;
          }
          .statusGrid {
            grid-template-columns: 1fr;
          }
          .steps {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .panelHeader {
            display: grid;
          }
        }
        @media (max-width: 560px) {
          .steps {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </main>
  );
}
