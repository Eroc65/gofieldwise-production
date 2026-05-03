import Head from "next/head";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { getDemoTranscriptStreamUrl, startDemoCall } from "../lib/api";

const workflowSteps = [
  {
    title: "Call answered",
    body: "Adrian picks up 24/7, asks trade-smart questions, and captures the job details while you stay on the work.",
  },
  {
    title: "Job booked",
    body: "Service type, urgency, address, and preferred time become a clean job record instead of a missed voicemail.",
  },
  {
    title: "Tech dispatched",
    body: "The right tech gets the work order, customer context, and SMS updates without a front-desk scramble.",
  },
  {
    title: "Invoice sent",
    body: "When the job is done, billing and payment follow-up keep moving without you chasing the customer.",
  },
  {
    title: "Review requested",
    body: "Completion SMS, invoice nudges, and review requests go out automatically so revenue and reputation keep compounding.",
  },
];

const modules = [
  {
    title: "AI Receptionist",
    body: "Adrian answers calls, extracts intake data, routes emergencies, and keeps every lead moving.",
  },
  {
    title: "Dispatch and Scheduling",
    body: "Jobs land on the board with urgency, service type, customer details, and tech-ready notes.",
  },
  {
    title: "Invoicing and Payments",
    body: "Invoices, reminders, and payment follow-up happen while the crew stays focused on the field.",
  },
  {
    title: "Follow-up Engine",
    body: "On-the-way, completion, invoice, review, and reactivation texts run without sticky notes.",
  },
];

const outcomes = [
  { value: "24/7", label: "call answering without adding payroll" },
  { value: "<60s", label: "speed-to-lead target for new calls" },
  { value: "5 steps", label: "call, book, dispatch, invoice, review" },
];

const frontOfficeProblems = [
  {
    title: "Missed calls become missed revenue",
    body: "Most home service buyers call the next company if nobody answers. Adrian picks up, qualifies, and keeps the lead warm.",
  },
  {
    title: "Dispatch notes are too thin",
    body: "A tech should not arrive with 'leak' as the whole job description. GoFieldwise captures urgency, address, access, and trade-specific context.",
  },
  {
    title: "Follow-up dies after the job",
    body: "Invoice nudges, review requests, and reactivation texts keep moving after the truck leaves.",
  },
];

const comparisonPoints = [
  {
    label: "Traditional field service software",
    title: "You manage the software",
    body: "Calendars, invoices, pipelines, automations, add-ons, setup calls, and training still need a human operator.",
  },
  {
    label: "GoFieldwise",
    title: "Adrian runs the workflow",
    body: "The AI answers the call, creates usable intake, triggers dispatch updates, and pushes the next admin step forward.",
  },
];

const integrations = ["Retell AI", "Twilio", "Stripe", "QuickBooks-ready", "Google Business Profile", "Website forms", "SMS follow-ups", "Neon Postgres"];

const growthPlays = [
  "Missed-call rescue and instant SMS follow-up",
  "Review request campaigns after completed work",
  "Dormant customer reactivation for seasonal services",
  "Trade-specific landing pages and offer testing",
  "Google Business Profile and local conversion support",
  "Lead source tracking from call to booked job",
];

const onboardingSteps = [
  { title: "Connect", body: "Point your phone flow, form, and SMS number into GoFieldwise." },
  { title: "Train", body: "Load business hours, service area, emergency rules, pricing notes, and trade scripts." },
  { title: "Launch", body: "Test Adrian live, confirm summary SMS, then send real calls through the workflow." },
];

const faqs = [
  {
    question: "Is this another CRM my team has to manage?",
    answer: "No. GoFieldwise is positioned as an AI operator first. The CRM-style records exist so calls, dispatch, billing, and follow-up have somewhere clean to land.",
  },
  {
    question: "Can customers talk to the same Adrian from the demo?",
    answer: "Yes. The demo is designed to mirror production: Adrian answers, captures job context, displays transcript data, and sends a summary text.",
  },
  {
    question: "Who is this best for?",
    answer: "Owner-led plumbing, HVAC, electrical, roofing, landscaping, and cleaning teams that need office-manager coverage before they are ready to hire a full-time dispatcher.",
  },
  {
    question: "What makes the marketing add-on different?",
    answer: "It is tied to operations. Campaigns are built around answered calls, booked jobs, completed work, reviews, and reactivation instead of disconnected ad spend.",
  },
];

const trades = ["Plumbing", "HVAC", "Electrical", "Roofing", "Landscaping", "Cleaning"];

function normalizeLines(transcript) {
  if (!Array.isArray(transcript)) return [];
  return transcript
    .map((line) => ({
      role: line.role || line.speaker || "agent",
      content: line.content || line.text || "",
    }))
    .filter((line) => line.content);
}

function errorMessage(err) {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;
  try {
    return JSON.stringify(err);
  } catch {
    return "Something went wrong starting the demo call.";
  }
}

export default function Home() {
  const [form, setForm] = useState({ name: "", email: "", phone: "" });
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [callId, setCallId] = useState("");
  const [transcript, setTranscript] = useState([]);
  const [summary, setSummary] = useState(null);
  const streamRef = useRef(null);

  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.close();
    };
  }, []);

  function updateField(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function openTranscriptStream(nextCallId) {
    if (streamRef.current) streamRef.current.close();
    const source = new EventSource(getDemoTranscriptStreamUrl(nextCallId));
    streamRef.current = source;

    source.addEventListener("transcript", (event) => {
      const payload = JSON.parse(event.data);
      setTranscript(normalizeLines(payload.transcript));
    });

    source.addEventListener("call_ended", (event) => {
      const payload = JSON.parse(event.data);
      setSummary(payload.extraction || {});
      setNotice("Call complete. The dispatch summary text is being sent.");
      source.close();
    });

    source.onerror = () => {
      setNotice("Call started. Waiting for Adrian's transcript...");
    };
  }

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setNotice("");
    setError("");
    setCallId("");
    setTranscript([]);
    setSummary(null);

    try {
      const result = await startDemoCall(form);
      if (!result.call_started) {
        throw new Error(result.call_error || result.message || "Demo call could not be started.");
      }
      setCallId(result.call_sid);
      setNotice("Adrian is calling now. Keep this page open to watch the transcript.");
      openTranscriptStream(result.call_sid);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Head>
        <title>GoFieldwise - AI Operations Manager for Home Service Businesses</title>
        <meta
          name="description"
          content="GoFieldwise gives plumbers, HVAC, electrical, and roofing businesses an AI front office. Adrian answers calls, books jobs, dispatches techs, sends invoices, and follows up."
        />
      </Head>

      <main className="landing">
        <section className="hero">
          <div className="hero-inner">
            <div className="hero-copy">
              <p className="eyebrow">AI operations manager for home service teams</p>
              <h1>Get your trade back. Let Adrian run the front office.</h1>
              <p className="hero-lede">
                GoFieldwise answers calls, books jobs, dispatches techs, sends customer updates, and helps you get paid.
                Built for owners who are great at the trade, not stuck chasing phones and invoices.
              </p>
              <div className="hero-actions">
                <a className="primary-action" href="#live-demo">
                  Have Adrian call me
                </a>
                <a className="secondary-action" href="tel:+16029320967">
                  Call Adrian: (602) 932-0967
                </a>
              </div>
              <div className="trust-row" aria-label="Key GoFieldwise facts">
                <span>24/7 call coverage</span>
                <span>Live in under 60 minutes</span>
                <span>$200/mo core plan</span>
              </div>
            </div>

            <aside className="ops-visual" aria-label="GoFieldwise operations board preview">
              <div className="visual-topline">
                <span>Fieldwise Dispatch</span>
                <strong>Live</strong>
              </div>
              <div className="job-board">
                <div className="job-card emergency">
                  <span>Burst pipe</span>
                  <strong>Same-day</strong>
                  <small>Adrian captured address and shutoff note</small>
                </div>
                <div className="job-card">
                  <span>HVAC tune-up</span>
                  <strong>Scheduled</strong>
                  <small>Confirmation SMS sent to customer</small>
                </div>
                <div className="job-card paid">
                  <span>Drain unclog</span>
                  <strong>Paid</strong>
                  <small>Invoice link collected in driveway</small>
                </div>
              </div>
              <div className="phone-preview">
                <p>Adrian</p>
                <strong>"I can help with that leak. What address should I send the tech to?"</strong>
              </div>
            </aside>
          </div>
        </section>

        <section className="outcome-strip" aria-label="GoFieldwise outcomes">
          {outcomes.map((item) => (
            <div key={item.value}>
              <strong>{item.value}</strong>
              <span>{item.label}</span>
            </div>
          ))}
        </section>

        <section className="problem-section">
          <div className="section-heading">
            <p className="eyebrow">Why owners switch</p>
            <h2>The front office is where good trade businesses leak money.</h2>
            <p>
              Competitors sell software to organize the work. GoFieldwise starts one step earlier: the moment a
              customer calls, texts, or fills out a form.
            </p>
          </div>
          <div className="problem-grid">
            {frontOfficeProblems.map((problem) => (
              <article className="problem-card" key={problem.title}>
                <h3>{problem.title}</h3>
                <p>{problem.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="live-demo" className="demo-section">
          <div className="section-heading">
            <p className="eyebrow">The demo is the product</p>
            <h2>Experience exactly what your customers will experience.</h2>
            <p>
              Enter your details, Adrian calls your phone, the call transcript appears live, and a dispatch summary text
              follows after the call.
            </p>
          </div>

          <div className="demo-grid">
            <form className="demo-form" onSubmit={onSubmit}>
              <div className="field">
                <label htmlFor="demo-name">Your name</label>
                <span>Example: John Smith</span>
                <input
                  id="demo-name"
                  value={form.name}
                  onChange={(event) => updateField("name", event.target.value)}
                  placeholder="John Smith"
                  autoComplete="name"
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="demo-email">Email address</label>
                <span>Used only for demo context.</span>
                <input
                  id="demo-email"
                  type="email"
                  value={form.email}
                  onChange={(event) => updateField("email", event.target.value)}
                  placeholder="john@example.com"
                  autoComplete="email"
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="demo-phone">Phone number</label>
                <span>Adrian calls this number from (602) 932-0967.</span>
                <input
                  id="demo-phone"
                  value={form.phone}
                  onChange={(event) => updateField("phone", event.target.value)}
                  placeholder="4055551234"
                  autoComplete="tel"
                  inputMode="tel"
                  required
                />
              </div>
              <button type="submit" disabled={busy}>
                {busy ? "Starting call..." : "Have Adrian call me"}
              </button>
              <a className="call-link" href="tel:+16029320967">
                Call instead: (602) 932-0967
              </a>
              {notice ? <p className="notice">{notice}</p> : null}
              {error ? <p className="form-error">{error}</p> : null}
              {callId ? <p className="call-id">Call ID: {callId}</p> : null}
            </form>

            <div className="transcript-console">
              <div className="console-header">
                <div>
                  <span>Live call console</span>
                  <strong>Adrian extraction feed</strong>
                </div>
                <b>{transcript.length > 0 ? "Connected" : "Ready"}</b>
              </div>
              <div className="transcript-body">
                {transcript.length > 0 ? (
                  transcript.map((line, index) => (
                    <div key={`${line.role}-${index}`} className={line.role === "user" ? "bubble customer" : "bubble"}>
                      <span>{line.role === "user" ? "Customer" : "Adrian"}</span>
                      <p>{line.content}</p>
                    </div>
                  ))
                ) : (
                  <>
                    <div className="bubble">
                      <span>Adrian</span>
                      <p>Fieldwise Demo Services, this is Adrian. How can I help today?</p>
                    </div>
                    <div className="empty-state">
                      The live transcript and extracted dispatch notes will appear here during your demo call.
                    </div>
                  </>
                )}
              </div>
              <div className="summary-preview">
                <h3>Dispatch summary SMS</h3>
                {summary ? (
                  <dl>
                    <dt>Service</dt>
                    <dd>{summary.service_type || "Not captured"}</dd>
                    <dt>Address</dt>
                    <dd>{summary.address || "Not captured"}</dd>
                    <dt>Urgency</dt>
                    <dd>{summary.urgency || "Not captured"}</dd>
                    <dt>Preferred time</dt>
                    <dd>{summary.preferred_time || "Not captured"}</dd>
                  </dl>
                ) : (
                  <p>
                    Thanks for trying GoFieldwise. Adrian captured service type, address, urgency, preferred time, and
                    notes for dispatch.
                  </p>
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="workflow-section">
          <div className="section-heading">
            <p className="eyebrow">From call to cash</p>
            <h2>One clean workflow instead of front-office chaos.</h2>
          </div>
          <div className="workflow">
            {workflowSteps.map((step, index) => (
              <article className="workflow-card" key={step.title}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="positioning-section">
          <div className="section-heading">
            <p className="eyebrow">Different by design</p>
            <h2>Field software records the business. GoFieldwise operates it.</h2>
            <p>
              ServiceTitan, Jobber, Housecall Pro, and Workiz prove the category is real. GoFieldwise wins by making the
              AI operator the front door, not a buried add-on.
            </p>
          </div>
          <div className="comparison-grid">
            {comparisonPoints.map((point) => (
              <article className="comparison-card" key={point.label}>
                <span>{point.label}</span>
                <h3>{point.title}</h3>
                <p>{point.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="trade-section">
          <div className="section-heading">
            <p className="eyebrow">Built for the trades</p>
            <h2>Not generic CRM software. A front office for field businesses.</h2>
            <p>
              GoFieldwise is shaped around urgent calls, rolling trucks, job notes, dispatch handoffs, invoices, and
              customer SMS.
            </p>
          </div>
          <div className="trade-grid">
            {trades.map((trade) => (
              <span key={trade}>{trade}</span>
            ))}
          </div>
        </section>

        <section className="modules-section">
          <div className="section-heading">
            <p className="eyebrow">The digital office</p>
            <h2>Everything an office manager does, without adding payroll.</h2>
          </div>
          <div className="module-grid">
            {modules.map((module) => (
              <article className="module-card" key={module.title}>
                <h3>{module.title}</h3>
                <p>{module.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="integrations-section">
          <div className="section-heading">
            <p className="eyebrow">Connected office stack</p>
            <h2>Voice, SMS, payments, forms, and reporting in one operational loop.</h2>
            <p>
              The promise is not another dashboard. It is a connected path from first call to paid invoice and review.
            </p>
          </div>
          <div className="integration-grid">
            {integrations.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </section>

        <section className="pricing-section">
          <div className="pricing-copy">
            <p className="eyebrow">Simple pricing</p>
            <h2>Start with operations. Add growth when you are ready.</h2>
            <p>
              Core automation starts at $200/month. Teams that want done-for-you marketing can expand into a growth
              package as lead volume becomes the next bottleneck.
            </p>
          </div>
          <div className="pricing-grid">
            <article className="price-card">
              <span>Core Operations</span>
              <strong>$200/mo</strong>
              <p>Adrian, intake, dispatch, customer SMS, invoicing workflows, and the real-time job board.</p>
            </article>
            <article className="price-card growth">
              <span>Growth + Marketing</span>
              <strong>$700-950/mo</strong>
              <p>Everything in core plus done-for-you campaigns, follow-up assets, reactivation, and marketing support.</p>
            </article>
          </div>
        </section>

        <section className="growth-section">
          <div className="growth-copy">
            <p className="eyebrow">Marketing that follows operations</p>
            <h2>The growth add-on is not generic ads. It turns completed work into more work.</h2>
            <p>
              Once the phones, dispatch, and follow-up are clean, GoFieldwise can layer in campaigns that compound from
              the jobs your team already wins.
            </p>
          </div>
          <div className="growth-list">
            {growthPlays.map((play) => (
              <span key={play}>{play}</span>
            ))}
          </div>
        </section>

        <section className="onboarding-section">
          <div className="section-heading">
            <p className="eyebrow">Fast launch</p>
            <h2>No six-month implementation. Start with one working phone flow.</h2>
          </div>
          <div className="onboarding-grid">
            {onboardingSteps.map((step, index) => (
              <article className="onboarding-card" key={step.title}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="proof-section">
          <blockquote>
            "Fieldwise replaces the evening admin work: missed calls, scheduling texts, invoices, and review asks. It
            feels like an office manager that never forgets the next step."
          </blockquote>
          <div className="proof-metrics">
            <span>
              <strong>100%</strong>
              call coverage target
            </span>
            <span>
              <strong>60 sec</strong>
              speed-to-lead goal
            </span>
            <span>
              <strong>1-20</strong>
              tech teams supported
            </span>
          </div>
        </section>

        <section className="faq-section">
          <div className="section-heading">
            <p className="eyebrow">Questions buyers ask</p>
            <h2>Built for the owner who needs leverage before another hire.</h2>
          </div>
          <div className="faq-grid">
            {faqs.map((item) => (
              <article className="faq-card" key={item.question}>
                <h3>{item.question}</h3>
                <p>{item.answer}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="final-cta">
          <h2>Stop wearing six hats. Put Adrian on the phones.</h2>
          <p>
            Your customers get a fast answer. Your techs get clean job details. You get your trade back.
          </p>
          <div className="hero-actions">
            <a className="primary-action" href="#live-demo">
              Try the live call demo
            </a>
            <Link className="secondary-action" href="/platform">
              See the platform
            </Link>
          </div>
        </section>
      </main>

      <style jsx>{`
        .landing {
          background: var(--paper);
          color: var(--ink);
        }

        .hero {
          background: linear-gradient(120deg, var(--navy), var(--navy-light) 62%, #2f6678);
          color: #fffdf8;
          border-radius: 0;
          box-shadow: none;
          padding: 64px 20px 40px;
        }

        .hero-inner,
        .outcome-strip,
        .problem-section,
        .demo-section,
        .workflow-section,
        .positioning-section,
        .trade-section,
        .modules-section,
        .integrations-section,
        .pricing-section,
        .growth-section,
        .onboarding-section,
        .proof-section,
        .faq-section,
        .final-cta {
          max-width: 1120px;
          margin: 0 auto;
        }

        .hero-inner {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 430px;
          gap: 34px;
          align-items: center;
        }

        .eyebrow {
          margin: 0 0 10px;
          color: #ffd9ae;
          font-size: 0.78rem;
          font-weight: 800;
          text-transform: uppercase;
          letter-spacing: 0.12em;
        }

        h1,
        h2,
        h3,
        p {
          overflow-wrap: anywhere;
        }

        h1 {
          margin: 0;
          max-width: 780px;
          font-size: 3.75rem;
          line-height: 1.02;
        }

        .hero-lede {
          max-width: 680px;
          margin: 20px 0 0;
          font-size: 1.18rem;
          line-height: 1.7;
          color: #f7efe1;
        }

        .hero-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-top: 28px;
        }

        .primary-action,
        .secondary-action,
        .call-link,
        .demo-form button {
          min-height: 48px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 8px;
          padding: 0 18px;
          font-weight: 800;
          text-decoration: none;
        }

        .primary-action,
        .demo-form button {
          border: 0;
          background: linear-gradient(120deg, var(--navy-deep), var(--navy-light));
          color: #fffdf8;
          cursor: pointer;
          box-shadow: inset 0 0 0 1px rgba(242, 181, 68, 0.44);
        }

        .primary-action:hover,
        .demo-form button:hover {
          background: var(--accent);
          color: var(--navy-deep);
        }

        .secondary-action,
        .call-link {
          border: 1px solid rgba(255, 217, 174, 0.62);
          color: #fffdf8;
          background: rgba(255, 255, 255, 0.08);
        }

        .trust-row {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin-top: 26px;
        }

        .trust-row span {
          border: 1px solid rgba(255, 255, 255, 0.22);
          border-radius: 999px;
          padding: 8px 11px;
          background: rgba(255, 255, 255, 0.08);
          color: #f7efe1;
          font-weight: 700;
          font-size: 0.92rem;
        }

        .ops-visual {
          border: 1px solid rgba(255, 255, 255, 0.22);
          border-radius: 8px;
          background: #fffdf8;
          color: var(--ink);
          box-shadow: var(--shadow);
          padding: 18px;
        }

        .visual-topline,
        .console-header {
          display: flex;
          justify-content: space-between;
          gap: 14px;
          align-items: center;
        }

        .visual-topline span,
        .console-header span {
          color: #4e6a74;
          font-weight: 800;
          font-size: 0.78rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .visual-topline strong,
        .console-header b {
          border-radius: 999px;
          padding: 6px 10px;
          background: #e8f5ed;
          color: #17643a;
          font-size: 0.78rem;
        }

        .job-board {
          display: grid;
          gap: 10px;
          margin-top: 16px;
        }

        .job-card {
          border: 1px solid var(--line);
          border-left: 5px solid var(--info);
          border-radius: 8px;
          padding: 12px;
          background: #fffcf7;
          display: grid;
          gap: 4px;
        }

        .job-card.emergency {
          border-left-color: var(--accent);
        }

        .job-card.paid {
          border-left-color: #247a4d;
        }

        .job-card span {
          color: #4e6a74;
          font-weight: 700;
        }

        .job-card strong {
          font-size: 1.05rem;
        }

        .job-card small {
          color: #647c84;
          line-height: 1.4;
        }

        .phone-preview {
          margin-top: 14px;
          border-radius: 8px;
          background: #19333c;
          color: #fffdf8;
          padding: 14px;
        }

        .phone-preview p {
          margin: 0 0 6px;
          color: #ffd9ae;
          font-weight: 800;
        }

        .phone-preview strong {
          line-height: 1.45;
        }

        .demo-section,
        .workflow-section,
        .problem-section,
        .positioning-section,
        .trade-section,
        .modules-section,
        .integrations-section,
        .pricing-section,
        .growth-section,
        .onboarding-section,
        .proof-section,
        .faq-section,
        .final-cta {
          padding: 64px 20px;
        }

        .outcome-strip {
          margin-top: -22px;
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
          padding: 0 20px;
          position: relative;
          z-index: 2;
        }

        .outcome-strip div {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          box-shadow: var(--shadow);
          padding: 18px;
          display: grid;
          gap: 5px;
        }

        .outcome-strip strong {
          color: var(--navy);
          font-size: 2rem;
          line-height: 1;
        }

        .outcome-strip span {
          color: #4e6a74;
          font-weight: 750;
          line-height: 1.35;
        }

        .section-heading {
          max-width: 760px;
          margin-bottom: 26px;
        }

        .section-heading h2,
        .pricing-copy h2,
        .final-cta h2 {
          margin: 0;
          font-size: 2.35rem;
          line-height: 1.08;
        }

        .section-heading p,
        .pricing-copy p,
        .final-cta p {
          margin: 12px 0 0;
          color: #35505b;
          font-size: 1.04rem;
          line-height: 1.65;
        }

        .demo-grid {
          display: grid;
          grid-template-columns: 410px minmax(0, 1fr);
          gap: 18px;
          align-items: stretch;
        }

        .demo-form,
        .transcript-console,
        .workflow-card,
        .module-card,
        .price-card,
        .problem-card,
        .comparison-card,
        .onboarding-card,
        .faq-card {
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 8px;
          box-shadow: var(--shadow);
        }

        .problem-grid,
        .comparison-grid,
        .onboarding-grid,
        .faq-grid {
          display: grid;
          gap: 14px;
        }

        .problem-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .comparison-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .faq-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .problem-card,
        .comparison-card,
        .onboarding-card,
        .faq-card {
          padding: 20px;
        }

        .problem-card h3,
        .comparison-card h3,
        .onboarding-card h3,
        .faq-card h3 {
          margin: 0;
          color: var(--navy);
        }

        .problem-card p,
        .comparison-card p,
        .onboarding-card p,
        .faq-card p {
          margin: 12px 0 0;
          color: #35505b;
          line-height: 1.62;
        }

        .comparison-card {
          border-top: 5px solid var(--line);
        }

        .comparison-card:last-child {
          border-top-color: var(--accent);
          background: linear-gradient(160deg, #fffdf8, #fff4de);
        }

        .comparison-card span,
        .onboarding-card span {
          display: block;
          margin-bottom: 10px;
          color: #4e6a74;
          font-size: 0.76rem;
          font-weight: 900;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .demo-form {
          padding: 20px;
          display: grid;
          gap: 14px;
        }

        .field {
          display: grid;
          gap: 6px;
        }

        .field label {
          font-weight: 850;
          display: block;
        }

        .field span {
          color: #607a84;
          font-size: 0.9rem;
        }

        .field input {
          min-height: 48px;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fff;
          padding: 0 12px;
          font-size: 1rem;
        }

        .demo-form button {
          width: 100%;
          font-size: 1rem;
        }

        .demo-form button:disabled {
          cursor: wait;
          opacity: 0.68;
        }

        .call-link {
          color: #183743;
          background: #fff4de;
          border-color: #edc17c;
        }

        .notice,
        .form-error,
        .call-id {
          margin: 0;
          font-weight: 800;
          line-height: 1.45;
        }

        .notice {
          color: #17643a;
        }

        .form-error {
          color: var(--error);
        }

        .call-id {
          color: #607a84;
          font-size: 0.88rem;
        }

        .transcript-console {
          overflow: hidden;
          background: #19333c;
          color: #fffdf8;
          display: grid;
          grid-template-rows: auto 1fr auto;
        }

        .console-header {
          padding: 16px 18px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.16);
        }

        .console-header strong {
          display: block;
          margin-top: 4px;
        }

        .transcript-body {
          padding: 18px;
          display: grid;
          align-content: start;
          gap: 12px;
          min-height: 280px;
        }

        .bubble {
          max-width: 86%;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.12);
          padding: 12px;
        }

        .bubble.customer {
          margin-left: auto;
          background: #fff4de;
          color: #19333c;
        }

        .bubble span {
          display: block;
          margin-bottom: 4px;
          color: #ffd9ae;
          font-weight: 900;
          font-size: 0.82rem;
        }

        .bubble.customer span {
          color: var(--accent);
        }

        .bubble p,
        .empty-state,
        .summary-preview p {
          margin: 0;
          line-height: 1.55;
        }

        .empty-state {
          color: #c5d4d8;
        }

        .summary-preview {
          background: #fffdf8;
          color: var(--ink);
          padding: 16px 18px;
        }

        .summary-preview h3 {
          margin: 0 0 10px;
        }

        .summary-preview dl {
          display: grid;
          grid-template-columns: 120px minmax(0, 1fr);
          gap: 8px 12px;
          margin: 0;
        }

        .summary-preview dt {
          color: #607a84;
          font-weight: 800;
        }

        .summary-preview dd {
          margin: 0;
        }

        .workflow {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 12px;
        }

        .workflow-card,
        .module-card,
        .price-card {
          padding: 18px;
        }

        .workflow-card span {
          color: var(--accent);
          font-weight: 900;
        }

        .workflow-card h3,
        .module-card h3 {
          margin: 10px 0 8px;
          font-size: 1.08rem;
        }

        .workflow-card p,
        .module-card p,
        .price-card p {
          margin: 0;
          color: #35505b;
          line-height: 1.55;
        }

        .trade-section {
          background: #fff8ee;
          max-width: none;
        }

        .trade-section .section-heading,
        .trade-grid {
          max-width: 1120px;
          margin-left: auto;
          margin-right: auto;
        }

        .trade-grid {
          display: grid;
          grid-template-columns: repeat(6, minmax(0, 1fr));
          gap: 10px;
        }

        .trade-grid span {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fffdf8;
          padding: 14px 10px;
          text-align: center;
          font-weight: 850;
          color: #234452;
        }

        .module-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 14px;
        }

        .integrations-section {
          background: #fff8ee;
          max-width: none;
        }

        .integrations-section .section-heading,
        .integration-grid {
          max-width: 1120px;
          margin-left: auto;
          margin-right: auto;
        }

        .integration-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
        }

        .integration-grid span,
        .growth-list span {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          padding: 14px;
          color: var(--navy);
          font-weight: 850;
          line-height: 1.35;
          box-shadow: 0 8px 22px rgba(27, 25, 20, 0.08);
        }

        .pricing-section {
          display: grid;
          grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
          gap: 24px;
          align-items: center;
        }

        .pricing-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
        }

        .price-card {
          display: grid;
          gap: 10px;
          background: #fffdf8;
        }

        .price-card.growth {
          border-color: #98b7bf;
          background: linear-gradient(160deg, #fffdf8, #eef7f8);
        }

        .price-card span {
          color: #4e6a74;
          font-weight: 900;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-size: 0.76rem;
        }

        .price-card strong {
          color: #19333c;
          font-size: 2rem;
          line-height: 1;
        }

        .growth-section {
          display: grid;
          grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
          gap: 24px;
          align-items: center;
          border-top: 1px solid var(--line);
        }

        .growth-copy h2 {
          margin: 0;
          color: var(--navy);
          font-size: 2.35rem;
          line-height: 1.08;
        }

        .growth-copy p {
          color: #35505b;
          line-height: 1.65;
        }

        .growth-list {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
        }

        .onboarding-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .onboarding-card span {
          color: var(--accent-dark);
        }

        .proof-section {
          border-top: 1px solid var(--line);
          border-bottom: 1px solid var(--line);
          display: grid;
          grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
          gap: 24px;
          align-items: center;
        }

        blockquote {
          margin: 0;
          font-size: 1.55rem;
          line-height: 1.35;
          color: #19333c;
          font-weight: 850;
        }

        .proof-metrics {
          display: grid;
          gap: 12px;
        }

        .proof-metrics span {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          padding: 16px;
          display: grid;
          gap: 4px;
          color: #4e6a74;
          font-weight: 700;
        }

        .proof-metrics strong {
          color: var(--accent);
          font-size: 1.6rem;
        }

        .final-cta {
          text-align: center;
        }

        .final-cta .hero-actions {
          justify-content: center;
        }

        .final-cta .secondary-action {
          color: #19333c;
          border-color: var(--line);
          background: #fffdf8;
        }

        @media (max-width: 980px) {
          .hero-inner,
          .demo-grid,
          .pricing-section,
          .growth-section,
          .proof-section {
            grid-template-columns: 1fr;
          }

          .ops-visual {
            max-width: 560px;
          }

          .workflow,
          .module-grid,
          .problem-grid,
          .integration-grid,
          .onboarding-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }

          .trade-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
          }
        }

        @media (max-width: 680px) {
          .hero {
            padding: 42px 14px 28px;
          }

          h1 {
            font-size: 2.65rem;
          }

          .hero-lede {
            font-size: 1rem;
          }

          .demo-section,
          .workflow-section,
          .problem-section,
          .positioning-section,
          .trade-section,
          .modules-section,
          .integrations-section,
          .pricing-section,
          .growth-section,
          .onboarding-section,
          .proof-section,
          .faq-section,
          .final-cta {
            padding: 42px 14px;
          }

          .section-heading h2,
          .pricing-copy h2,
          .growth-copy h2,
          .final-cta h2 {
            font-size: 1.9rem;
          }

          .hero-actions,
          .trust-row {
            flex-direction: column;
          }

          .primary-action,
          .secondary-action {
            width: 100%;
          }

          .workflow,
          .module-grid,
          .pricing-grid,
          .trade-grid,
          .outcome-strip,
          .problem-grid,
          .comparison-grid,
          .integration-grid,
          .growth-list,
          .onboarding-grid,
          .faq-grid {
            grid-template-columns: 1fr;
          }

          .outcome-strip {
            margin-top: 0;
            padding: 14px;
          }

          .summary-preview dl {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </>
  );
}
