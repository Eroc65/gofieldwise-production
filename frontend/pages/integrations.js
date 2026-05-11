import Head from "next/head";
import Link from "next/link";
import { useMemo, useState } from "react";

const providers = [
  {
    id: "zapier",
    name: "Zapier / Webhooks",
    status: "live",
    statusLabel: "Live now",
    method: "Webhook / Zapier",
    auth: "Webhook URL",
    description:
      "The fastest path to connecting GoFieldwise to almost anything. When Adrian captures a call, GoFieldwise can send a structured payload to Zapier or a webhook endpoint.",
    capabilities: [
      "New job captured -> trigger a Zap",
      "Dispatch summary -> Slack, email, SMS, or CRM alert",
      "Invoice closed -> update spreadsheet or CRM",
      "Follow-up scheduled -> notify the team",
    ],
    requirements: ["Webhook URL from Zapier or your destination app", "Optional Zapier Pro for multi-step flows"],
    syncDepth: "One-way push from GoFieldwise outbound",
    cta: "Connect Zapier",
    href: "/#live-demo",
  },
  {
    id: "gcal",
    name: "Google Calendar",
    status: "live",
    statusLabel: "Live now",
    method: "OAuth 2.0",
    auth: "Google OAuth calendar access",
    description:
      "Adrian can prepare clean booking details for a calendar workflow: customer, address, service type, urgency, preferred time, and dispatch notes.",
    capabilities: [
      "New booking -> create calendar event",
      "Reschedule -> update event after approval",
      "Cancellation -> remove or mark event",
      "Tech assignment -> include team context",
    ],
    requirements: ["Google account with Calendar access", "OAuth authorization during setup", "Test booking before launch"],
    syncDepth: "Calendar workflow support; final sync behavior is confirmed during setup",
    cta: "Connect Google Calendar",
    href: "/#live-demo",
  },
  {
    id: "gbp",
    name: "Google Business Profile",
    status: "beta",
    statusLabel: "Beta",
    method: "OAuth 2.0 / GBP API",
    auth: "Google OAuth manage access",
    description:
      "GoFieldwise can support local visibility workflows by drafting posts, review responses, and customer follow-up prompts. Publishing stays human-approved.",
    capabilities: [
      "Closed job -> draft review request",
      "Completed service -> draft GBP post",
      "New review -> draft response",
      "Monthly report -> summarize reputation work",
    ],
    requirements: ["Verified Google Business Profile", "Google/API access review", "Human approval before publishing"],
    syncDepth: "Draft and workflow support; Google controls API permissions and post behavior",
    cta: "Request Beta Access",
    href: "mailto:support@gofieldwise.com?subject=Google%20Business%20Profile%20beta%20access",
  },
  {
    id: "jobber",
    name: "Jobber",
    status: "planned",
    statusLabel: "Roadmap",
    method: "OAuth 2.0 + GraphQL",
    auth: "Jobber OAuth",
    description:
      "The planned connector maps Adrian's structured intake output to Jobber client, request, and job workflows after field mapping is approved.",
    capabilities: [
      "New intake -> prepare Jobber client and request",
      "Booked job -> map service details",
      "Invoice trigger -> prepare billing handoff",
      "Completed job -> update workflow status",
    ],
    requirements: ["Jobber account", "OAuth authorization", "Field mapping review before launch"],
    syncDepth: "Two-way planned; scope confirmed during onboarding",
    cta: "Join Waitlist",
    href: "mailto:support@gofieldwise.com?subject=Jobber%20integration%20waitlist",
  },
  {
    id: "housecall",
    name: "Housecall Pro",
    status: "planned",
    statusLabel: "Roadmap",
    method: "API key",
    auth: "Housecall Pro API access",
    description:
      "Housecall Pro API access is account-dependent. GoFieldwise will scope the connector before promising job, customer, or status sync behavior.",
    capabilities: [
      "New intake -> prepare customer and job payload",
      "Dispatch note -> attach service context",
      "Job status -> review sync options",
      "Invoice trigger -> prepare billing handoff",
    ],
    requirements: ["Housecall Pro plan with API access", "API key or approved access", "Setup review to confirm field mapping"],
    syncDepth: "One-way push first; two-way reviewed per account",
    cta: "Join Waitlist",
    href: "mailto:support@gofieldwise.com?subject=Housecall%20Pro%20integration%20waitlist",
  },
  {
    id: "servicetitan",
    name: "ServiceTitan",
    status: "planned",
    statusLabel: "Roadmap",
    method: "OAuth 2.0 / Client credentials",
    auth: "App key, tenant ID, client ID, client secret",
    description:
      "ServiceTitan requires app registration and tenant credential provisioning. GoFieldwise scopes this manually before any launch promise.",
    capabilities: [
      "New intake -> prepare customer and job payload",
      "Dispatch payload -> attach job context",
      "Job type mapping -> service category",
      "Technician assignment -> dispatch workflow",
    ],
    requirements: ["ServiceTitan API access", "Registered app key", "Tenant ID and client credentials", "Manual onboarding review"],
    syncDepth: "Two-way planned; timeline confirmed after app registration",
    cta: "Join Waitlist",
    href: "mailto:support@gofieldwise.com?subject=ServiceTitan%20integration%20waitlist",
  },
];

const onboardingSteps = [
  ["01", "Select your CRM", "Choose the field service software, calendar, webhook, or manual handoff workflow you already use."],
  ["02", "Choose integration mode", "Use native API where available, Zapier/webhook as the universal fallback, or manual handoff until automation is approved."],
  ["03", "Authorize access", "OAuth tokens and API keys belong in secure backend storage. No client passwords are stored in Google Sheets."],
  ["04", "Run a test lead", "Adrian captures a test call and sends a structured payload so field mapping, urgency, and notes can be checked."],
  ["05", "Human approval", "Nothing goes live until the owner confirms the payload lands correctly in the destination workflow."],
];

const aiActions = [
  "Answers and captures the call",
  "Extracts name, phone, email, and address",
  "Flags urgency level and service type",
  "Captures preferred arrival window",
  "Writes structured dispatch notes",
  "Selects the right connector or handoff mode",
  "Builds the CRM-ready payload",
  "Flags missing required fields",
  "Logs the handoff with timestamp",
  "Creates owner summary and follow-up tasks",
];

const statusStyles = {
  live: "live",
  beta: "beta",
  planned: "planned",
};

export default function IntegrationsPage() {
  const [activeFilter, setActiveFilter] = useState("all");
  const filteredProviders = useMemo(
    () => (activeFilter === "all" ? providers : providers.filter((provider) => provider.status === activeFilter)),
    [activeFilter],
  );

  return (
    <>
      <Head>
        <title>Integrations - GoFieldwise</title>
        <meta
          name="description"
          content="Connect GoFieldwise to Google Calendar, Zapier, Jobber, Housecall Pro, ServiceTitan, and Google Business Profile workflows with honest integration status and onboarding requirements."
        />
      </Head>

      <main className="integrations-page">
        <section className="hero">
          <div className="hero-inner">
            <p className="eyebrow">Integration Hub</p>
            <h1>Connect GoFieldwise to your existing stack.</h1>
            <p>
              Zapier and calendar workflows are the fastest starting point. Jobber, Housecall Pro, ServiceTitan, and
              Google Business Profile are scoped honestly by status, auth requirements, and sync depth.
            </p>
            <div className="hero-counters" aria-label="Integration status counts">
              <article><strong>2</strong><span>Live workflows</span></article>
              <article><strong>1</strong><span>Beta workflow</span></article>
              <article><strong>3</strong><span>Roadmap connectors</span></article>
            </div>
          </div>
        </section>

        <section className="filters" aria-label="Filter integrations">
          {[
            ["all", "All"],
            ["live", "Live"],
            ["beta", "Beta"],
            ["planned", "Coming soon"],
          ].map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={activeFilter === key ? "active" : ""}
              onClick={() => setActiveFilter(key)}
            >
              {label}
            </button>
          ))}
        </section>

        <section className="provider-section">
          <div className="provider-grid">
            {filteredProviders.map((provider) => (
              <article className="provider-card" key={provider.id}>
                <div className="provider-top">
                  <div>
                    <h2>{provider.name}</h2>
                    <p>{provider.method}</p>
                  </div>
                  <span className={`status ${statusStyles[provider.status]}`}>{provider.statusLabel}</span>
                </div>
                <p className="provider-description">{provider.description}</p>
                <div className="meta-grid">
                  <div>
                    <strong>Auth</strong>
                    <span>{provider.auth}</span>
                  </div>
                  <div>
                    <strong>Sync depth</strong>
                    <span>{provider.syncDepth}</span>
                  </div>
                </div>
                <div className="detail-block">
                  <h3>What it does</h3>
                  <ul>
                    {provider.capabilities.map((capability) => (
                      <li key={capability}>{capability}</li>
                    ))}
                  </ul>
                </div>
                <div className="detail-block requirements">
                  <h3>Requirements</h3>
                  <ul>
                    {provider.requirements.map((requirement) => (
                      <li key={requirement}>{requirement}</li>
                    ))}
                  </ul>
                </div>
                {provider.href.startsWith("mailto:") ? (
                  <a className={provider.status === "live" ? "card-cta primary" : "card-cta"} href={provider.href}>
                    {provider.cta}
                  </a>
                ) : (
                  <Link className={provider.status === "live" ? "card-cta primary" : "card-cta"} href={provider.href}>
                    {provider.cta}
                  </Link>
                )}
              </article>
            ))}
          </div>
        </section>

        <section className="ai-section">
          <div className="section-heading">
            <p className="eyebrow">Before the handoff</p>
            <h2>What Adrian does before anything touches your CRM.</h2>
            <p>
              Every connector receives a clean structured payload. The goal is not to dump a raw transcript into your
              software. The goal is to make the next step obvious.
            </p>
          </div>
          <div className="ai-grid">
            {aiActions.map((action, index) => (
              <article key={action}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{action}</p>
              </article>
            ))}
          </div>
          <div className="payload-card">
            <p className="payload-label">Sample structured payload</p>
            <pre>{`{
  "caller_name": "Dave Martinez",
  "phone": "+1 (316) 555-0142",
  "email": null,
  "service_type": "pipe_burst",
  "urgency": "emergency",
  "address": "4821 W Douglas Ave, Wichita KS",
  "preferred_time": "asap",
  "notes": "Water shutoff already done. Crawlspace access needed.",
  "missing_fields": ["email"],
  "captured_at": "2026-05-11T07:02:14Z",
  "connector": "google_calendar",
  "handoff_status": "queued"
}`}</pre>
          </div>
        </section>

        <section className="onboarding-section">
          <div className="section-heading">
            <p className="eyebrow">Onboarding</p>
            <h2>How integration setup works.</h2>
            <p>Five steps. Nothing goes live until the owner verifies the test lead lands correctly.</p>
          </div>
          <div className="timeline">
            {onboardingSteps.map(([step, title, description]) => (
              <article key={step}>
                <span>{step}</span>
                <div>
                  <h3>{title}</h3>
                  <p>{description}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="cta-section">
          <h2>Not sure which integration fits?</h2>
          <p>
            Start with Zapier or a webhook. It is the fastest way to connect GoFieldwise to the tools you already use,
            then move to a native connector once the workflow is proven.
          </p>
          <div className="cta-actions">
            <Link href="/#live-demo">See the live demo</Link>
            <a href="mailto:support@gofieldwise.com">Talk to the team</a>
          </div>
        </section>
      </main>

      <style jsx>{`
        .integrations-page {
          background: #f7f6f3;
          color: #1a1a1a;
        }

        .hero {
          background: #0d0d0d;
          color: #fff;
          padding: 82px 20px 72px;
          text-align: center;
        }

        .hero-inner,
        .provider-section,
        .ai-section,
        .onboarding-section {
          width: 100%;
          max-width: 1120px;
          margin: 0 auto;
        }

        .hero-inner {
          max-width: 760px;
        }

        .eyebrow {
          margin: 0 0 12px;
          color: #ef9f27;
          font-size: 0.78rem;
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
          margin: 0;
          font-size: clamp(2.8rem, 6vw, 5rem);
          line-height: 0.98;
        }

        .hero p:not(.eyebrow) {
          margin: 20px auto 0;
          max-width: 700px;
          color: rgba(255, 255, 255, 0.68);
          font-size: 1.12rem;
          line-height: 1.7;
        }

        .hero-counters {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
          margin-top: 34px;
        }

        .hero-counters article {
          border: 1px solid rgba(255, 255, 255, 0.14);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.06);
          padding: 16px;
        }

        .hero-counters strong {
          display: block;
          color: #ef9f27;
          font-size: 2rem;
        }

        .hero-counters span {
          color: rgba(255, 255, 255, 0.72);
          font-weight: 800;
        }

        .filters {
          position: sticky;
          top: 53px;
          z-index: 10;
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          gap: 6px;
          border-bottom: 1px solid #e5e3dc;
          background: rgba(247, 246, 243, 0.94);
          padding: 12px 20px;
          backdrop-filter: blur(8px);
        }

        .filters button {
          border: 0;
          border-radius: 8px;
          background: transparent;
          color: #6b6b6b;
          cursor: pointer;
          font-weight: 800;
          padding: 10px 16px;
        }

        .filters button.active {
          background: #fff;
          color: #1a1a1a;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .provider-section,
        .ai-section,
        .onboarding-section {
          padding: 58px 20px;
        }

        .provider-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 18px;
        }

        .provider-card,
        .ai-grid article,
        .payload-card,
        .timeline article {
          border: 1px solid #e5e3dc;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 16px 34px rgba(18, 24, 36, 0.06);
        }

        .provider-card {
          display: grid;
          gap: 18px;
          padding: 24px;
        }

        .provider-top {
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: start;
        }

        .provider-top h2,
        .section-heading h2,
        .cta-section h2 {
          margin: 0;
          color: #111827;
          line-height: 1.08;
        }

        .provider-top p {
          margin: 4px 0 0;
          color: #777;
          font-weight: 800;
          font-size: 0.86rem;
        }

        .status {
          border-radius: 999px;
          padding: 7px 10px;
          font-size: 0.78rem;
          font-weight: 900;
          white-space: nowrap;
        }

        .status.live {
          background: rgba(16, 110, 86, 0.1);
          color: #0f6e56;
        }

        .status.beta {
          background: rgba(186, 117, 23, 0.12);
          color: #854f0b;
        }

        .status.planned {
          background: rgba(83, 74, 183, 0.1);
          color: #3c3489;
        }

        .provider-description,
        .section-heading p,
        .timeline p,
        .cta-section p {
          margin: 0;
          color: #555;
          line-height: 1.65;
        }

        .meta-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
        }

        .meta-grid div,
        .detail-block.requirements {
          border-radius: 8px;
          background: #f7f6f3;
          padding: 12px;
        }

        .meta-grid strong,
        .detail-block h3,
        .payload-label {
          display: block;
          margin: 0 0 8px;
          color: #9a8c74;
          font-size: 0.72rem;
          font-weight: 900;
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }

        .meta-grid span {
          color: #333;
          font-size: 0.9rem;
          line-height: 1.45;
        }

        .detail-block ul {
          display: grid;
          gap: 7px;
          margin: 0;
          padding: 0;
          list-style: none;
        }

        .detail-block li {
          color: #444;
          font-size: 0.92rem;
          line-height: 1.45;
        }

        .detail-block li::before {
          content: "->";
          margin-right: 8px;
          color: #ef9f27;
          font-weight: 900;
        }

        .card-cta,
        .cta-actions a {
          min-height: 48px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border: 1px solid #d4d2ca;
          border-radius: 8px;
          color: #111827;
          font-weight: 900;
          text-decoration: none;
          padding: 0 18px;
        }

        .card-cta.primary,
        .cta-actions a:first-child {
          border-color: #0d0d0d;
          background: #0d0d0d;
          color: #fff;
        }

        .section-heading {
          max-width: 700px;
          margin-bottom: 30px;
        }

        .section-heading h2 {
          font-size: clamp(2rem, 4vw, 3rem);
        }

        .ai-grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 12px;
        }

        .ai-grid article {
          padding: 16px;
        }

        .ai-grid span {
          color: #ef9f27;
          font-weight: 900;
        }

        .ai-grid p {
          margin: 8px 0 0;
          color: #333;
          line-height: 1.45;
          font-weight: 750;
        }

        .payload-card {
          margin-top: 34px;
          padding: 22px;
          background: #0d0d0d;
        }

        .payload-label {
          color: #ef9f27;
        }

        .payload-card pre {
          margin: 0;
          overflow-x: auto;
          color: #d8d8d8;
          font-size: 0.9rem;
          line-height: 1.65;
        }

        .onboarding-section {
          max-width: none;
          background: #fff;
        }

        .onboarding-section .section-heading,
        .timeline {
          max-width: 1120px;
          margin-left: auto;
          margin-right: auto;
        }

        .timeline {
          display: grid;
          gap: 12px;
        }

        .timeline article {
          display: grid;
          grid-template-columns: 56px minmax(0, 1fr);
          gap: 16px;
          padding: 18px;
        }

        .timeline article > span {
          width: 46px;
          height: 46px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 999px;
          background: #0d0d0d;
          color: #fff;
          font-weight: 900;
        }

        .timeline h3 {
          margin: 0 0 6px;
          color: #111827;
        }

        .cta-section {
          padding: 72px 20px;
          background: #0d0d0d;
          color: #fff;
          text-align: center;
        }

        .cta-section h2 {
          color: #fff;
          font-size: clamp(2rem, 4vw, 3rem);
        }

        .cta-section p {
          max-width: 680px;
          margin: 16px auto 0;
          color: rgba(255, 255, 255, 0.68);
        }

        .cta-actions {
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          gap: 12px;
          margin-top: 28px;
        }

        .cta-actions a:first-child {
          background: #ef9f27;
          border-color: #ef9f27;
          color: #0d0d0d;
        }

        .cta-actions a:last-child {
          color: #fff;
          border-color: rgba(255, 255, 255, 0.24);
        }

        @media (max-width: 900px) {
          .provider-grid,
          .ai-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 640px) {
          .hero {
            padding: 58px 14px 48px;
          }

          .hero-counters,
          .provider-grid,
          .meta-grid,
          .ai-grid {
            grid-template-columns: 1fr;
          }

          .provider-section,
          .ai-section,
          .onboarding-section,
          .cta-section {
            padding: 44px 14px;
          }

          .filters {
            position: static;
            justify-content: flex-start;
            overflow-x: auto;
          }

          .provider-top {
            display: grid;
          }

          .timeline article {
            grid-template-columns: 1fr;
          }

          .cta-actions {
            display: grid;
          }
        }
      `}</style>
    </>
  );
}
