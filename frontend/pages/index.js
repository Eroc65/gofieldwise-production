import Head from "next/head";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { getDemoTranscriptStreamUrl, startDemoCall } from "../lib/api";

const stats = [
  { value: "$$$", label: "Missed calls quietly cost contractors thousands in lost revenue." },
  { value: "$200", label: "Per month. Not a $2,000 enterprise platform." },
  { value: "<60 sec", label: "Designed to respond to inbound calls and lead requests before the customer moves on." },
  { value: "24/7", label: "Never calls in sick. Never quits on a busy Monday." },
];

const dashboardJobs = [
  { customer: "Hernandez", job: "Water heater replacement", status: "En route", tone: "live" },
  { customer: "Thompson", job: "HVAC tune-up at 10 AM", status: "Scheduled", tone: "scheduled" },
  { customer: "Park", job: "Drain unclog, invoice sent", status: "Paid", tone: "paid" },
  { customer: "Martinez", job: "2 PM leak captured by Adrian", status: "New", tone: "new" },
];

const storySteps = [
  {
    time: "7:02 AM",
    title: "Customer calls",
    body: "A pipe burst overnight. Adrian answers instantly, gets the address, confirms urgency, and captures the details while the owner is still asleep.",
  },
  {
    time: "7:03 AM",
    title: "Job booked",
    body: "The job lands on the board. The closest available tech gets the dispatch note, customer context, and arrival window.",
  },
  {
    time: "9:45 AM",
    title: "Job complete",
    body: "The tech marks it done. The invoice goes out while the truck is still in the driveway. No paperwork waiting for tonight.",
  },
  {
    time: "10:15 AM",
    title: "Review request sent",
    body: "Once the job is wrapped, GoFieldwise sends the review request and keeps the customer relationship warm.",
  },
];

const testimonials = [
  {
    quote: "Approved customer quote goes here after the beta customer signs off on name, company, city, and wording.",
    name: "Verified quote",
    role: "Customer permission required before publishing",
    metric: "Social proof slot",
  },
  {
    quote: "Show a real before-and-after result here, such as calls captured, jobs booked, or follow-ups sent.",
    name: "Result snapshot",
    role: "Use measured data from the first approved client",
    metric: "Outcome proof",
  },
  {
    quote: "Add an approved screenshot or short demo clip showing the transcript, dispatch summary, and follow-up flow.",
    name: "Product proof",
    role: "Use only approved or first-party demo assets",
    metric: "Visual evidence",
  },
];

const automationSteps = [
  ["01", "Intake", "Adrian answers and captures service type, location, urgency, and notes."],
  ["02", "Book", "The job gets a clear next step instead of sitting in voicemail."],
  ["03", "Dispatch", "The owner or team sees the details needed to route the work."],
  ["04", "Invoice", "Billing can happen when the job closes, not days later."],
  ["05", "Follow-up", "Review requests and rebook nudges keep the relationship warm."],
];

const stages = [
  {
    title: "One van",
    body: "You need every call answered, every lead captured, and every invoice sent without hiring office staff too early.",
  },
  {
    title: "Small crew",
    body: "You need dispatch visibility, cleaner schedules, customer updates, and fewer jobs living in your head.",
  },
  {
    title: "Growing team",
    body: "You need repeatable operations, owner reporting, permissions, and automation that does not break when call volume rises.",
  },
];

const platformCards = [
  {
    title: "AI Dispatcher",
    body: "Adrian answers inbound calls, qualifies the request, captures context, and starts the booking flow.",
  },
  {
    title: "Lean Operations",
    body: "Track jobs, tech availability, customer updates, invoices, follow-ups, and owner visibility in one workflow.",
  },
  {
    title: "Scale Without Overhead",
    body: "Add more work and more techs without turning the owner into a full-time admin department.",
  },
];

const painPoints = [
  ["Missed calls become lost jobs", "When you are under a sink or on a roof, Adrian can still answer and qualify the lead."],
  ["Scheduling turns into guesswork", "Jobs need urgency, location, skills, and time windows, not sticky notes and memory."],
  ["Follow-up never happens", "Invoices, payment links, review asks, and rebook reminders should not depend on Friday-night admin."],
  ["An office manager is expensive", "At the early stage, full-time admin payroll is hard to justify. GoFieldwise fills the gap."],
];

const productFeatures = [
  {
    title: "Job Management",
    body: "New jobs land on the board, move through status changes, and keep notes, photos, customers, techs, invoices, and reminders connected.",
    tag: "Full visibility",
  },
  {
    title: "Automated Customer Updates",
    body: "Appointment confirmations, on-the-way alerts, completion texts, invoice links, and review requests go out without manual sending.",
    tag: "Zero manual follow-up",
  },
  {
    title: "Instant Invoicing",
    body: "Professional invoices can go out the moment work is complete, so customers can pay while the job is still fresh.",
    tag: "Paid faster",
  },
  {
    title: "AI Customer Intake",
    body: "Adrian captures calls, web inquiries, after-hours issues, urgency, service type, address, and notes before dispatch.",
    tag: "Runs automatically",
  },
  {
    title: "Smart Scheduling",
    body: "Assign work based on who is available, who is nearby, and what the job requires. Fewer bad routes, fewer missed windows.",
    tag: "AI-assisted",
  },
  {
    title: "Real-Time Dashboard",
    body: "See jobs, techs, statuses, revenue signals, warm leads, and follow-up risk from the office or the road.",
    tag: "Owner view",
  },
];

const comparisonRows = [
  ["Customer intake", "Answered only when someone is free", "Forms and workflows still need an operator", "Adrian captures it automatically"],
  ["Job dispatch", "Owner or dispatcher coordinates manually", "Drag-and-drop, you decide", "AI-assisted assignment and routing"],
  ["Customer follow-up", "Depends on staff memory", "Templates someone has to send", "Sent automatically at the right moment"],
  ["Invoicing", "Handled after the job or after hours", "Requires manual action", "Triggered when the job closes"],
  ["Admin overhead", "Payroll, training, and coverage gaps", "Still needs someone to run it", "Built to operate the front office"],
  ["Pricing", "Often $3,000+ per month for full-time help", "$500 to $2,000+ per month", "$200/month core plan"],
  ["Team growth", "More calls usually means more staff", "Per-user or per-tech fees are common", "No per-tech pricing in the core offer"],
];

const pricingBullets = [
  "AI customer intake and job capture",
  "Scheduling and dispatch workflow",
  "Automatic follow-ups and reminders",
  "Invoicing and billing automation",
  "Real-time job board and owner dashboard",
  "Unlimited technicians in the core plan",
  "Unlimited jobs in the core plan",
];

const pricingMath = [
  ["Average missed job", "$400"],
  ["One recovered job", "Can cover 2 months"],
  ["Core plan", "$200/month"],
];

const integrations = [
  ["Housecall Pro handoff", "Adrian captures structured intake notes that can be routed into your workflow after setup."],
  ["ServiceTitan handoff", "Sync depth is scoped before launch. No native two-way sync is promised without review."],
  ["Jobber handoff", "Lead details can be prepared for manual entry, Zapier, or approved workflow automation."],
  ["Google Calendar", "Scheduling handoff can be configured for simple calendar-based operations."],
  ["Google Business Profile", "AI can draft posts and review responses, but publishing stays human-approved."],
  ["Zapier/webhooks", "Best first path for alerts, CRM handoffs, and lightweight automations."],
];

const tradePages = [
  ["Plumbers", "/plumbing", "Emergency calls, leaks, water heaters, and after-hours intake."],
  ["HVAC", "/hvac", "Tune-ups, no-cool calls, replacements, and seasonal scheduling."],
  ["Electricians", "/electrical", "Panel issues, safety requests, estimates, and dispatch notes."],
  ["Landscapers", "/landscaping", "Recurring maintenance, quotes, follow-ups, and route-ready work."],
];

const faqItems = [
  [
    "What is the live demo?",
    "Adrian calls your phone, handles a sample service call, shows the transcript on this page, and creates dispatch notes so you can hear the experience before signing up.",
  ],
  [
    "How does the AI sound on calls?",
    "Adrian is designed to sound like a calm front-office assistant: clear, practical, and focused on capturing the job details a dispatcher needs.",
  ],
  [
    "Do customers know it is AI?",
    "You decide how transparent the greeting should be. The important part is that customers get answered quickly and their service details are captured accurately.",
  ],
  [
    "What happens during setup?",
    "We collect your services, service area, business hours, preferred booking rules, phone workflow, and follow-up preferences, then test the intake flow before it goes live.",
  ],
  [
    "Does this replace Housecall Pro, Jobber, or ServiceTitan?",
    "Not always. GoFieldwise can support the front-office layer and connect with your existing tools where possible instead of forcing a full system replacement.",
  ],
];

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
  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqItems.map(([question, answer]) => ({
      "@type": "Question",
      name: question,
      acceptedAnswer: {
        "@type": "Answer",
        text: answer,
      },
    })),
  };

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
        <title>GoFieldwise - AI That Runs the Front Office for Home Service Businesses</title>
        <meta
          name="description"
          content="GoFieldwise answers calls, books jobs, dispatches techs, sends invoices, and follows up for plumbing, HVAC, electrical, roofing, landscaping, and cleaning businesses."
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
        />
      </Head>

      <main className="business-page">
        <section className="hero">
          <div className="hero-inner">
            <div className="hero-copy">
              <p className="eyebrow">Solo operator to crew of 20</p>
              <h1>Built for the first van. Ready for the full crew.</h1>
              <p>Adrian answers the call. You do the job.</p>
              <div className="actions">
                <a className="primary-action" href="#live-demo">Hear Adrian answer a real call</a>
                <a className="secondary-action" href="#sandbox">Explore the product</a>
              </div>
              <small>Live demo = Adrian calls your phone, answers like a service dispatcher, and shows the transcript.</small>
            </div>

            <aside className="hero-card" aria-label="GoFieldwise dashboard preview">
              <div className="card-top">
                <span>gofieldwise / Dashboard</span>
                <b>Live</b>
              </div>
              <div className="mini-stats">
                <div><strong>7</strong><span>Jobs Today</span></div>
                <div><strong>3</strong><span>Techs Out</span></div>
                <div><strong>$4.2k</strong><span>Invoiced</span></div>
              </div>
              <div className="job-list">
                {dashboardJobs.map((job) => (
                  <div className={`job-row ${job.tone}`} key={`${job.customer}-${job.status}`}>
                    <span>{job.customer} - {job.job}</span>
                    <b>{job.status}</b>
                  </div>
                ))}
              </div>
              <div className="call-preview">
                <span>AI call preview</span>
                <p><b>Adrian:</b> "What service do you need, what address, and how urgent is it?"</p>
                <p><b>Owner alert:</b> New leak call captured with address, urgency, and preferred arrival window.</p>
              </div>
              <p>This is the product shape: calls become jobs, jobs become dispatch, dispatch becomes invoices.</p>
            </aside>
          </div>
        </section>

        <section className="stat-strip">
          {stats.map((stat) => (
            <article key={stat.value}>
              <strong>{stat.value}</strong>
              <span>{stat.label}</span>
            </article>
          ))}
        </section>

        <section id="sandbox" className="product-demo">
          <div className="section-heading">
            <p className="eyebrow">Try it right now</p>
            <h2>See how the product handles a real service call.</h2>
            <p>
              Walk through a real Monday morning: Adrian answers the call, books the job, dispatches the tech, and
              sends the invoice. This is what day one should feel like.
            </p>
          </div>
          <div className="sandbox-board">
            <div className="board-column">
              <span>Call captured</span>
              <h3>Martinez leak</h3>
              <p>Address, urgency, shutoff status, preferred arrival window, and notes captured by Adrian.</p>
            </div>
            <div className="board-column">
              <span>Dispatch ready</span>
              <h3>Mike assigned</h3>
              <p>Closest available tech gets the work order and customer context before rolling.</p>
            </div>
            <div className="board-column">
              <span>Cash collected</span>
              <h3>Invoice sent</h3>
              <p>Customer receives the invoice link and review request without the owner chasing it down.</p>
            </div>
          </div>
        </section>

        <section id="live-demo" className="live-demo">
          <div className="section-heading">
            <p className="eyebrow">Live demo flow</p>
            <h2>Experience what your customers will experience.</h2>
            <p>
              Enter your details, Adrian calls your phone, the transcript appears live, and a dispatch summary text
              follows after the call.
            </p>
          </div>
          <div className="demo-grid">
            <form className="demo-form" onSubmit={onSubmit}>
              <label>
                Your name
                <span>Example: John Smith</span>
                <input value={form.name} onChange={(event) => updateField("name", event.target.value)} required />
              </label>
              <label>
                Email address
                <span>Used only for demo context.</span>
                <input type="email" value={form.email} onChange={(event) => updateField("email", event.target.value)} required />
              </label>
              <label>
                Phone number
                <span>Adrian calls this number from (602) 932-0967.</span>
                <input value={form.phone} onChange={(event) => updateField("phone", event.target.value)} inputMode="tel" required />
              </label>
              <button type="submit" disabled={busy}>{busy ? "Starting call..." : "Hear the live AI call"}</button>
              <a className="call-link" href="tel:+16029320967">Call instead: (602) 932-0967</a>
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
                    <div className="empty-state">The live transcript and extracted dispatch notes appear here during the demo call.</div>
                  </>
                )}
              </div>
              <div className="summary-preview">
                <h3>Dispatch summary SMS</h3>
                {summary ? (
                  <dl>
                    <dt>Service</dt><dd>{summary.service_type || "Not captured"}</dd>
                    <dt>Address</dt><dd>{summary.address || "Not captured"}</dd>
                    <dt>Urgency</dt><dd>{summary.urgency || "Not captured"}</dd>
                    <dt>Preferred time</dt><dd>{summary.preferred_time || "Not captured"}</dd>
                  </dl>
                ) : (
                  <p>Adrian captures service type, address, urgency, preferred time, and notes for dispatch.</p>
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="story-section">
          <div className="section-heading">
            <p className="eyebrow">How it works in real life</p>
            <h2>A Monday morning with GoFieldwise.</h2>
            <p>
              Sarah runs a 3-person plumbing crew. Here is what changes when the owner stops doing every office task
              personally.
            </p>
          </div>
          <div className="story-grid">
            <div className="story-card">
              <span>Sarah's story / Plumbing</span>
              <h3>Before GoFieldwise, Monday started with missed calls and handwritten notes.</h3>
              <p>Now the system answers, books, routes, bills, and follows up before Sarah opens the laptop.</p>
            </div>
            <div className="timeline">
              {storySteps.map((step) => (
                <article key={step.time}>
                  <span>{step.time}</span>
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="testimonials">
          {testimonials.map((item) => (
            <article key={item.name}>
              <strong>{item.metric}</strong>
              <p>"{item.quote}"</p>
              <span>{item.name}</span>
              <small>{item.role}</small>
            </article>
          ))}
        </section>

        <section className="integrations-section">
          <div className="section-heading center">
            <p className="eyebrow">Integration-ready workflows</p>
            <h2>Keep the tools you already use.</h2>
            <p>
              Adrian captures the call, structures the job details, and prepares the handoff. Native sync, Zapier, or
              manual handoff is scoped during setup so GoFieldwise never overpromises a connection you do not have.
            </p>
          </div>
          <div className="integration-grid">
            {integrations.map(([name, detail]) => (
              <article key={name}>
                <strong>{name}</strong>
                <span>{detail}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="automation-section">
          <div className="section-heading center">
            <p className="eyebrow">How it works</p>
            <h2>From first call to follow-up.</h2>
            <p>Five steps. Minimal manual work. GoFieldwise keeps the front office moving while the crew works.</p>
          </div>
          <div className="automation-grid">
            {automationSteps.map(([number, title, body]) => (
              <article key={number}>
                <span>{number}</span>
                <h3>{title}</h3>
                <p>{body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="stages-section">
          <div className="section-heading center">
            <p className="eyebrow">Who it is for</p>
            <h2>Built for every stage of your growth.</h2>
            <p>
              Too big for sticky notes, too early for an office army. That gap is exactly where GoFieldwise lives.
            </p>
          </div>
          <div className="three-grid">
            {stages.map((stage) => (
              <article key={stage.title}>
                <h3>{stage.title}</h3>
                <p>{stage.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="platform-section">
          <div className="section-heading">
            <p className="eyebrow">The digital office</p>
            <h2>One platform. Three things that change the business.</h2>
          </div>
          <div className="three-grid">
            {platformCards.map((card) => (
              <article key={card.title}>
                <h3>{card.title}</h3>
                <p>{card.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="pain-section">
          <div className="section-heading">
            <p className="eyebrow">Sound familiar?</p>
            <h2>You are still answering phones from the crawlspace.</h2>
            <p>
              You got into the trade to do the work, not to chase invoices at midnight. GoFieldwise removes the admin
              drag that keeps small shops stuck.
            </p>
          </div>
          <div className="pain-list">
            {painPoints.map(([title, body], index) => (
              <article key={title}>
                <span>{index + 1}</span>
                <div>
                  <h3>{title}</h3>
                  <p>{body}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="features-section">
          <div className="section-heading center">
            <p className="eyebrow">What you get</p>
            <h2>Everything an office manager does. None of the overhead.</h2>
            <p>GoFieldwise does the actual work, not just organizes it.</p>
          </div>
          <div className="feature-grid">
            {productFeatures.map((feature) => (
              <article key={feature.title}>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
                <span>{feature.tag}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="comparison-section">
          <div className="section-heading">
            <p className="eyebrow">Why GoFieldwise</p>
            <h2>Most software organizes your work. GoFieldwise does it.</h2>
            <p>
              Traditional field service tools still need a human operator. GoFieldwise is built to run the front office
              from first call to final payment.
            </p>
          </div>
          <div className="comparison-table">
            <div className="table-head">
              <span>Capability</span>
              <span>Hiring office help</span>
              <span>Traditional tools</span>
              <span>GoFieldwise</span>
            </div>
            {comparisonRows.map(([capability, staff, traditional, fieldwise]) => (
              <div className="table-row" key={capability}>
                <b>{capability}</b>
                <span>{staff}</span>
                <span>{traditional}</span>
                <strong>{fieldwise}</strong>
              </div>
            ))}
          </div>
          <p className="pricing-note">No per-technician pricing. No surprise add-on fees. $200/month for the core operating system.</p>
        </section>

        <section className="pricing-section">
          <div className="section-heading center">
            <p className="eyebrow">Simple pricing</p>
            <h2>One core price. Everything included.</h2>
            <p>No per-user fees. No module add-ons. No "contact sales" maze.</p>
          </div>
          <div className="price-card">
            <span>Core Operations</span>
            <strong>$200 <small>/month</small></strong>
            <p>Less than a week of office-manager payroll.</p>
            <div className="pricing-math">
              {pricingMath.map(([label, value]) => (
                <article key={label}>
                  <b>{value}</b>
                  <span>{label}</span>
                </article>
              ))}
            </div>
            <p className="roi-note">If one missed job is worth about $400, the core plan can pay for itself fast when it helps recover even one call.</p>
            <ul>
              {pricingBullets.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <div className="actions">
              <a className="primary-action" href="#live-demo">Try the live demo</a>
              <Link className="secondary-action light" href="/platform">See the platform</Link>
            </div>
          </div>
        </section>

        <section className="trade-pages-section">
          <div className="section-heading">
            <p className="eyebrow">Built by trade</p>
            <h2>Industry-specific pages for better fit.</h2>
            <p>
              Home service buyers respond faster when the page speaks their trade. Start with the closest fit and see
              how GoFieldwise handles calls, intake, and follow-up in that workflow.
            </p>
          </div>
          <div className="trade-grid">
            {tradePages.map(([name, href, body]) => (
              <Link href={href} key={name}>
                <strong>{name}</strong>
                <span>{body}</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="faq-section">
          <div className="section-heading center">
            <p className="eyebrow">Questions owners ask first</p>
            <h2>Know what happens before you try it.</h2>
          </div>
          <div className="faq-list">
            {faqItems.map(([question, answer]) => (
              <article key={question}>
                <h3>{question}</h3>
                <p>{answer}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="final-cta">
          <h2>Stop wearing six hats. Let Adrian handle the office.</h2>
          <p>
            You started this business to do the work you are good at, not to return missed calls, chase invoices, and
            play dispatcher from the truck.
          </p>
          <div className="actions">
            <a className="primary-action" href="#live-demo">Hear Adrian answer a real call</a>
            <a className="secondary-action light" href="mailto:support@gofieldwise.com">Contact support@gofieldwise.com</a>
          </div>
        </section>

        <section className="origin-section">
          <p className="eyebrow">Nationwide</p>
          <h2>Built for tradespeople who are drowning in admin.</h2>
          <p>
            GoFieldwise is built for plumbers, HVAC techs, electricians, roofers, landscapers, cleaners, and the small
            crews who run on hustle and word of mouth. The software that existed was often too expensive, too
            complicated, or just a prettier spreadsheet. So GoFieldwise focuses on the missing piece: a front office
            that actually runs itself.
          </p>
          <footer>
            <span>support@gofieldwise.com</span>
            <nav>
              <Link href="/privacy">Privacy Policy</Link>
              <Link href="/terms">Terms of Service</Link>
              <a href="mailto:support@gofieldwise.com">Contact Us</a>
            </nav>
          </footer>
        </section>

        <div className="mobile-sticky-cta">
          <a href="#live-demo">Try live AI call</a>
          <a href="tel:+16029320967">Call demo number</a>
        </div>
      </main>

      <style jsx>{`
        .business-page {
          background: var(--paper);
          color: var(--ink);
          overflow-x: hidden;
        }

        .hero {
          padding: 70px 20px 42px;
          color: #fffdf8;
          background: linear-gradient(120deg, var(--navy), var(--navy-light));
        }

        .hero-inner,
        .stat-strip,
        .product-demo,
        .live-demo,
        .story-section,
        .testimonials,
        .integrations-section,
        .automation-section,
        .stages-section,
        .platform-section,
        .pain-section,
        .features-section,
        .comparison-section,
        .pricing-section,
        .trade-pages-section,
        .faq-section,
        .final-cta,
        .origin-section {
          width: 100%;
          max-width: 1120px;
          margin: 0 auto;
        }

        .hero-inner {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 430px;
          gap: 36px;
          align-items: center;
        }

        .eyebrow {
          margin: 0 0 10px;
          color: #ffd9ae;
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
          max-width: 760px;
          font-size: clamp(3rem, 6vw, 5.5rem);
          line-height: 0.95;
        }

        .hero-copy p:not(.eyebrow),
        .section-heading p,
        .final-cta p,
        .origin-section p {
          color: #35505b;
          line-height: 1.65;
          font-size: 1.05rem;
        }

        .hero-copy p:not(.eyebrow) {
          max-width: 690px;
          margin: 20px 0 0;
          color: #f7efe1;
          font-size: 1.18rem;
        }

        .actions {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-top: 26px;
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
          font-weight: 900;
          text-decoration: none;
        }

        .primary-action,
        .demo-form button {
          border: 1px solid rgba(242, 181, 68, 0.42);
          background: linear-gradient(120deg, var(--navy-deep), var(--navy-light));
          color: #fffdf8;
          cursor: pointer;
        }

        .primary-action:hover,
        .demo-form button:hover {
          background: var(--accent);
          color: var(--navy-deep);
        }

        .secondary-action,
        .call-link {
          border: 1px solid rgba(255, 217, 174, 0.72);
          color: #fffdf8;
          background: rgba(255, 255, 255, 0.08);
        }

        .secondary-action.light,
        .call-link {
          color: var(--navy);
          background: #fff4de;
          border-color: #edc17c;
        }

        .hero-copy small {
          display: block;
          margin-top: 12px;
          color: #f7efe1;
          font-weight: 800;
        }

        .hero-card,
        .sandbox-board,
        .demo-form,
        .transcript-console,
        .story-card,
        .testimonials article,
        .three-grid article,
        .pain-list article,
        .feature-grid article,
        .price-card {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          box-shadow: var(--shadow);
        }

        .hero-card {
          padding: 18px;
          color: var(--ink);
        }

        .card-top,
        .console-header {
          display: flex;
          justify-content: space-between;
          gap: 14px;
          align-items: center;
        }

        .card-top span,
        .console-header span {
          color: #4e6a74;
          font-size: 0.78rem;
          font-weight: 900;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .card-top b,
        .console-header b {
          border-radius: 999px;
          padding: 6px 10px;
          background: #e8f5ed;
          color: #17643a;
          font-size: 0.78rem;
        }

        .mini-stats {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
          margin: 16px 0;
        }

        .mini-stats div,
        .job-row,
        .sandbox-board .board-column {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fffcf7;
          padding: 12px;
        }

        .mini-stats strong {
          display: block;
          color: var(--navy);
          font-size: 1.6rem;
        }

        .mini-stats span,
        .hero-card p,
        .job-row span {
          color: #4e6a74;
          line-height: 1.45;
        }

        .job-list {
          display: grid;
          gap: 8px;
        }

        .call-preview {
          display: grid;
          gap: 8px;
          margin-top: 12px;
          border: 1px solid #edc17c;
          border-radius: 8px;
          background: #fff4de;
          padding: 12px;
        }

        .call-preview span {
          color: var(--accent-dark);
          font-size: 0.78rem;
          font-weight: 900;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .call-preview p {
          margin: 0;
          color: var(--navy);
          line-height: 1.45;
        }

        .job-row {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          border-left: 5px solid var(--accent);
        }

        .job-row.paid {
          border-left-color: #247a4d;
        }

        .job-row.live {
          border-left-color: #0e6a7a;
        }

        .job-row b {
          color: var(--navy);
          white-space: nowrap;
        }

        .stat-strip {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 12px;
          padding: 20px;
          margin-top: -26px;
          position: relative;
        }

        .stat-strip article {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          box-shadow: var(--shadow);
          padding: 18px;
        }

        .stat-strip strong {
          display: block;
          color: var(--navy);
          font-size: 2rem;
        }

        .stat-strip span {
          color: #4e6a74;
          line-height: 1.4;
          font-weight: 750;
        }

        .product-demo,
        .live-demo,
        .story-section,
        .integrations-section,
        .automation-section,
        .stages-section,
        .platform-section,
        .pain-section,
        .features-section,
        .comparison-section,
        .pricing-section,
        .trade-pages-section,
        .faq-section,
        .final-cta,
        .origin-section {
          padding: 64px 20px;
        }

        .section-heading {
          max-width: 760px;
          margin-bottom: 26px;
        }

        .section-heading.center,
        .final-cta,
        .pricing-section .section-heading {
          text-align: center;
          margin-left: auto;
          margin-right: auto;
        }

        .section-heading h2,
        .final-cta h2,
        .origin-section h2 {
          margin: 0;
          color: var(--navy);
          font-size: clamp(2.2rem, 4.5vw, 3.4rem);
          line-height: 1.04;
        }

        .sandbox-board {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
          padding: 16px;
        }

        .board-column span,
        .feature-grid article span,
        .price-card > span {
          color: #4e6a74;
          font-size: 0.78rem;
          font-weight: 900;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }

        .board-column h3,
        .three-grid h3,
        .feature-grid h3,
        .pain-list h3 {
          margin: 10px 0 8px;
          color: var(--navy);
        }

        .board-column p,
        .three-grid p,
        .feature-grid p,
        .pain-list p,
        .testimonials p,
        .story-card p,
        .timeline p {
          margin: 0;
          color: #35505b;
          line-height: 1.58;
        }

        .demo-grid {
          display: grid;
          grid-template-columns: 410px minmax(0, 1fr);
          gap: 18px;
        }

        .demo-form {
          padding: 20px;
          display: grid;
          gap: 14px;
        }

        .demo-form label {
          display: grid;
          gap: 6px;
          color: var(--navy);
          font-weight: 850;
        }

        .demo-form label span {
          color: #607a84;
          font-size: 0.9rem;
        }

        .demo-form input {
          min-height: 48px;
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 0 12px;
          font-size: 1rem;
        }

        .demo-form button {
          width: 100%;
        }

        .notice,
        .form-error,
        .call-id {
          margin: 0;
          font-weight: 850;
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
          background: var(--navy);
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
          min-height: 280px;
          padding: 18px;
          display: grid;
          align-content: start;
          gap: 12px;
        }

        .bubble {
          max-width: 86%;
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.1);
          padding: 12px;
        }

        .bubble.customer {
          margin-left: auto;
          background: #fff4de;
          color: var(--navy);
        }

        .bubble span {
          display: block;
          margin-bottom: 4px;
          color: #ffd9ae;
          font-weight: 900;
          font-size: 0.82rem;
        }

        .bubble.customer span {
          color: var(--accent-dark);
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
          color: var(--navy);
        }

        .summary-preview dl {
          display: grid;
          grid-template-columns: 120px minmax(0, 1fr);
          gap: 8px 12px;
          margin: 0;
        }

        .summary-preview dt {
          color: #607a84;
          font-weight: 850;
        }

        .summary-preview dd {
          margin: 0;
        }

        .story-grid {
          display: grid;
          grid-template-columns: 360px minmax(0, 1fr);
          gap: 18px;
          align-items: start;
        }

        .story-card {
          padding: 22px;
          background: #fff8ee;
        }

        .story-card span {
          color: var(--accent-dark);
          font-weight: 900;
        }

        .story-card h3 {
          margin: 12px 0;
          color: var(--navy);
          font-size: 1.45rem;
        }

        .timeline {
          display: grid;
          gap: 12px;
        }

        .timeline article {
          border-left: 5px solid var(--accent);
          border-radius: 8px;
          background: var(--panel);
          box-shadow: var(--shadow);
          padding: 16px;
        }

        .timeline span {
          color: var(--accent-dark);
          font-weight: 900;
        }

        .timeline h3 {
          margin: 8px 0;
          color: var(--navy);
        }

        .testimonials {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
          padding: 0 20px 64px;
        }

        .testimonials article {
          padding: 20px;
        }

        .testimonials strong {
          color: var(--accent-dark);
        }

        .testimonials span {
          display: block;
          margin-top: 14px;
          color: var(--navy);
          font-weight: 900;
        }

        .testimonials small {
          color: #607a84;
        }

        .integration-grid {
          display: grid;
          grid-template-columns: repeat(6, minmax(0, 1fr));
          gap: 10px;
        }

        .integration-grid article {
          min-height: 70px;
          display: grid;
          align-content: start;
          gap: 6px;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          box-shadow: var(--shadow);
          color: var(--navy);
          font-weight: 900;
          text-align: center;
          padding: 12px;
        }

        .integration-grid strong {
          color: var(--navy);
        }

        .integration-grid span {
          color: #4e6a74;
          font-size: 0.86rem;
          line-height: 1.35;
          font-weight: 750;
        }

        .automation-section,
        .features-section,
        .pricing-section {
          background: #fff8ee;
          max-width: none;
        }

        .automation-section .section-heading,
        .features-section .section-heading,
        .pricing-section .section-heading,
        .automation-grid,
        .feature-grid,
        .price-card {
          max-width: 1120px;
          margin-left: auto;
          margin-right: auto;
        }

        .automation-grid {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 8px;
        }

        .automation-grid article {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          padding: 12px;
        }

        .automation-grid span {
          color: var(--accent-dark);
          font-weight: 900;
        }

        .automation-grid h3 {
          margin: 8px 0 6px;
          color: var(--navy);
          font-size: 0.98rem;
        }

        .automation-grid p {
          margin: 0;
          color: #4e6a74;
          font-size: 0.9rem;
          line-height: 1.4;
        }

        .three-grid,
        .feature-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
        }

        .three-grid article,
        .feature-grid article {
          padding: 20px;
        }

        .pain-section {
          display: grid;
          grid-template-columns: 0.85fr 1.15fr;
          gap: 24px;
          align-items: start;
        }

        .pain-list {
          display: grid;
          gap: 12px;
        }

        .pain-list article {
          display: grid;
          grid-template-columns: 42px minmax(0, 1fr);
          gap: 12px;
          padding: 18px;
        }

        .pain-list span {
          width: 34px;
          height: 34px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 999px;
          background: var(--accent);
          color: var(--navy-deep);
          font-weight: 900;
        }

        .feature-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .comparison-table {
          border: 1px solid var(--line);
          border-radius: 8px;
          overflow: hidden;
          background: var(--panel);
          box-shadow: var(--shadow);
        }

        .table-head,
        .table-row {
          display: grid;
          grid-template-columns: 0.78fr 1fr 1fr 1fr;
          gap: 0;
        }

        .table-head {
          background: var(--navy);
          color: #fffdf8;
          font-weight: 900;
        }

        .table-head span,
        .table-row b,
        .table-row span,
        .table-row strong {
          padding: 14px;
          border-bottom: 1px solid var(--line);
        }

        .table-row strong {
          color: var(--navy);
          background: #fff8ee;
        }

        .pricing-note {
          color: var(--navy);
          font-weight: 900;
          font-size: 1.1rem;
        }

        .price-card {
          padding: 26px;
          text-align: center;
        }

        .price-card strong {
          display: block;
          margin: 12px 0;
          color: var(--navy);
          font-size: 3.5rem;
          line-height: 1;
        }

        .price-card small {
          font-size: 1rem;
        }

        .pricing-math {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 10px;
          max-width: 680px;
          margin: 18px auto 0;
        }

        .pricing-math article {
          border: 1px solid #edc17c;
          border-radius: 8px;
          background: #fff4de;
          padding: 14px;
        }

        .pricing-math b {
          display: block;
          color: var(--navy);
          font-size: 1.35rem;
        }

        .pricing-math span,
        .roi-note {
          color: #4e6a74;
          font-weight: 800;
        }

        .roi-note {
          max-width: 640px;
          margin: 14px auto 0;
          line-height: 1.5;
        }

        .price-card ul {
          max-width: 560px;
          margin: 22px auto 0;
          padding: 0;
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
          list-style: none;
          text-align: left;
        }

        .price-card li {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #fffdf8;
          padding: 12px;
          color: var(--navy);
          font-weight: 800;
        }

        .price-card .actions,
        .final-cta .actions {
          justify-content: center;
        }

        .trade-grid,
        .faq-list {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 12px;
        }

        .trade-grid a,
        .faq-list article {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          box-shadow: var(--shadow);
          padding: 18px;
          text-decoration: none;
        }

        .trade-grid strong,
        .faq-list h3 {
          display: block;
          margin: 0 0 8px;
          color: var(--navy);
          font-size: 1.08rem;
        }

        .trade-grid span,
        .faq-list p {
          margin: 0;
          color: #35505b;
          line-height: 1.55;
        }

        .faq-list {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .mobile-sticky-cta {
          display: none;
        }

        .final-cta h2 {
          max-width: 800px;
          margin-left: auto;
          margin-right: auto;
        }

        .final-cta p {
          max-width: 780px;
          margin-left: auto;
          margin-right: auto;
        }

        .origin-section {
          border-top: 1px solid var(--line);
        }

        .origin-section p {
          max-width: 860px;
        }

        .origin-section footer {
          display: flex;
          flex-wrap: wrap;
          justify-content: space-between;
          gap: 16px;
          margin-top: 26px;
          color: var(--navy);
          font-weight: 800;
        }

        .origin-section nav {
          display: flex;
          flex-wrap: wrap;
          gap: 14px;
        }

        .origin-section a {
          color: var(--navy);
        }

        @media (max-width: 980px) {
          .hero-inner,
          .demo-grid,
          .story-grid,
          .pain-section {
            grid-template-columns: 1fr;
          }

          .hero-card,
          .story-card {
            max-width: 560px;
          }

          .automation-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
          }

          .three-grid,
          .testimonials,
          .sandbox-board,
          .integration-grid,
          .trade-grid,
          .faq-list {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 640px) {
          .hero {
            padding: 46px 14px 32px;
          }

          .product-demo,
          .live-demo,
          .story-section,
          .integrations-section,
          .automation-section,
          .stages-section,
          .platform-section,
          .pain-section,
          .features-section,
          .comparison-section,
          .pricing-section,
          .trade-pages-section,
          .faq-section,
          .final-cta,
          .origin-section {
            padding: 44px 14px;
          }

          .stat-strip {
            grid-template-columns: 1fr;
            margin-top: 0;
            padding: 14px;
          }

          .actions {
            flex-direction: column;
          }

          .primary-action,
          .secondary-action,
          .call-link {
            width: 100%;
          }

          .mini-stats,
          .automation-grid,
          .feature-grid,
          .price-card ul,
          .pricing-math {
            grid-template-columns: 1fr;
          }

          .job-row {
            display: grid;
          }

          .table-head {
            display: none;
          }

          .table-row {
            grid-template-columns: 1fr;
            border-bottom: 1px solid var(--line);
          }

          .summary-preview dl {
            grid-template-columns: 1fr;
          }

          .business-page {
            padding-bottom: 76px;
          }

          .mobile-sticky-cta {
            position: fixed;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 50;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            padding: 10px;
            background: rgba(255, 253, 248, 0.96);
            border-top: 1px solid var(--line);
            box-shadow: 0 -14px 30px rgba(7, 31, 42, 0.14);
          }

          .mobile-sticky-cta a {
            min-height: 48px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            background: var(--navy);
            color: #fffdf8;
            text-decoration: none;
            font-weight: 900;
            text-align: center;
            padding: 0 10px;
          }

          .mobile-sticky-cta a + a {
            background: #fff4de;
            color: var(--navy);
            border: 1px solid #edc17c;
          }
        }
      `}</style>
    </>
  );
}
