import { useMemo, useState } from "react";

import DispatchAssistant from "../components/DispatchAssistant";
import { submitPublicLeadIntake } from "../lib/api";

const PHONE_NUMBER = process.env.NEXT_PUBLIC_SALES_PHONE || "+1 (555) 010-2024";
const BOOKING_URL = process.env.NEXT_PUBLIC_BOOKING_URL || "https://cal.com/gofieldwise/demo";
const INTAKE_KEY = process.env.NEXT_PUBLIC_INTAKE_KEY || "";
const LEGACY_INTAKE_ORG_ID = process.env.NEXT_PUBLIC_INTAKE_ORG_ID || "";

const offerings = [
  {
    title: "AI Voice Agents",
    subtitle: "Answer every call. Never miss a lead.",
    description:
      "Human-like AI phone agents that answer calls, respond to questions, capture lead details, qualify prospects, and book appointments 24/7.",
    includes: [
      "Answers calls 24/7, including after hours and weekends",
      "Speaks naturally and handles complex conversations",
      "Captures caller name, number, and reason for calling",
      "Qualifies prospects based on your criteria",
      "Books, reschedules, or cancels appointments",
      "Missed call text-back flows to recover lost leads",
      "Transfers to a human when needed",
      "Works on your existing business phone number",
    ],
    idealFor: "HVAC, Plumbing, Dental, Med Spa, Pest Control, Auto Services, Contractors",
  },
  {
    title: "AI Chatbots",
    subtitle: "Engage every visitor. Convert more leads.",
    description:
      "Intelligent website chatbots that engage visitors instantly, answer common questions, collect lead information, qualify prospects, and guide users toward booking.",
    includes: [
      "Responds to visitors instantly with zero wait time",
      "Trained on your specific services and FAQs",
      "Collects name, phone, email, and inquiry details",
      "Qualifies visitors before they reach you",
      "Books appointments or triggers quote requests",
      "Runs around the clock on your website",
      "Sends real-time lead notifications",
      "Fully branded to match your business",
    ],
    idealFor: "Restaurants, Salons, Dentists, Service Businesses, Agencies, Consultants",
  },
  {
    title: "AI-Integrated Websites",
    subtitle: "A site that works as hard as you do.",
    description:
      "Modern, high-converting websites built to explain your offer clearly, build trust fast, capture leads, and connect directly with chatbot and booking systems.",
    includes: [
      "Modern, mobile-responsive premium design",
      "AI chatbot or voice widget built directly in",
      "Clear, conversion-focused copywriting",
      "Lead capture forms that convert",
      "Direct booking system integration",
      "SEO-optimized structure for local search",
      "Fast load speeds and clean layout",
      "Live in 4 to 5 business days",
    ],
    idealFor: "Any local or service business ready to grow online",
  },
  {
    title: "Lead Capture And Booking Automation",
    subtitle: "Turn every touchpoint into a booked appointment.",
    description:
      "Connect website, chatbot, forms, and AI systems so leads are captured instantly, organized automatically, and pushed toward booking calls, demos, estimates, or appointments.",
    includes: [
      "Multi-channel lead capture across website, chatbot, and forms",
      "Instant lead notifications to phone or email",
      "Automatic lead organization and routing",
      "Online booking available 24/7",
      "Calendar sync with existing tools",
      "Automatic confirmation and reminder messages",
      "Rescheduling and no-show reduction flows",
      "Full lead reporting and visibility",
    ],
    idealFor: "High-volume businesses, Real Estate, Insurance, Service Companies",
  },
  {
    title: "Custom Business Automation",
    subtitle: "Built around how your business actually works.",
    description:
      "Custom workflows for follow-up, notifications, CRM syncing, intake forms, appointment flows, and other automations that reduce manual work.",
    includes: [
      "Multi-step follow-up text and email sequences",
      "CRM syncing and contact management",
      "Custom intake and onboarding forms",
      "Internal team notifications and routing",
      "Review request automation",
      "Re-engagement campaigns for cold leads",
      "Custom appointment workflows",
      "Built around your existing tools and processes",
    ],
    idealFor: "Any business with repetitive manual tasks or broken follow-up",
  },
];

export default function HomePage() {
  const [selectedService, setSelectedService] = useState(offerings[0].title);
  const [lead, setLead] = useState({
    name: "",
    phone: "",
    email: "",
    company: "",
    details: "",
  });
  const [submitMessage, setSubmitMessage] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const offeringAnchors = useMemo(
    () => offerings.map((offering) => ({ ...offering, id: offering.title.toLowerCase().replace(/[^a-z0-9]+/g, "-") })),
    [],
  );

  function handleGetStarted(serviceName) {
    setSelectedService(serviceName);
    setSubmitMessage("");
    setSubmitError("");
    const el = document.getElementById("get-started");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function onLeadFieldChange(field, value) {
    setLead((prev) => ({ ...prev, [field]: value }));
  }

  async function onSubmitLead(event) {
    event.preventDefault();
    setSubmitMessage("");
    setSubmitError("");
    setIsSubmitting(true);
    try {
      if (!INTAKE_KEY && !LEGACY_INTAKE_ORG_ID) {
        throw new Error("Lead intake is not configured. Set NEXT_PUBLIC_INTAKE_KEY.");
      }
      await submitPublicLeadIntake({
        intakeKey: INTAKE_KEY,
        orgId: LEGACY_INTAKE_ORG_ID,
        name: lead.name,
        phone: lead.phone,
        email: lead.email,
        service: selectedService,
        company: lead.company,
        details: lead.details,
      });
      setSubmitMessage("Intake received. Our team will contact you shortly to map your setup plan.");
      setLead({
        name: "",
        phone: "",
        email: "",
        company: "",
        details: "",
      });
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Unable to submit intake right now.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">GoFieldWise</p>
        <h1>AI Voice Agents And Automation For Service Businesses</h1>
        <p>
          AI-forward systems that answer every call, capture and qualify leads, and book work 24/7.
          Never miss a lead because the phone rang at the wrong time.
        </p>
        <div className="hero-actions">
          <button type="button" onClick={() => handleGetStarted("AI Voice Agents")}>Start With AI Voice</button>
          <a className="ghost-link" href={BOOKING_URL} target="_blank" rel="noreferrer">
            Book A Demo Call
          </a>
          <a className="ghost-link" href="/leads">
            Open Lead Inbox
          </a>
          <a className="ghost-link" href="/metrics">
            View Metrics
          </a>
          <a className="ghost-link" href="/growth">
            Growth Infrastructure
          </a>
          <a className="ghost-link" href="/platform">
            Platform Console
          </a>
          <a className="ghost-link" href="/status">
            Status
          </a>
        </div>
      </section>

      <section className="service-jump" aria-label="Service shortcuts">
        {offeringAnchors.map((offering) => (
          <a key={offering.id} href={`#${offering.id}`}>
            {offering.title}
          </a>
        ))}
      </section>

      <section className="offerings" aria-label="GoFieldWise offerings">
        {offeringAnchors.map((offering) => (
          <article className="offering-card" key={offering.title} id={offering.id}>
            <header>
              <h2>{offering.title}</h2>
              <p className="offering-subtitle">{offering.subtitle}</p>
            </header>
            <p className="offering-description">{offering.description}</p>

            <h3>What&apos;s Included</h3>
            <ul>
              {offering.includes.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>

            <p className="ideal-for">
              <strong>Ideal For:</strong> {offering.idealFor}
            </p>
            <button type="button" onClick={() => handleGetStarted(offering.title)}>Get Started</button>
          </article>
        ))}
      </section>

      <section className="lead-capture" id="get-started" aria-label="Get started">
        <article className="lead-intro">
          <p className="eyebrow">Get Started</p>
          <h2>Tell us your business and we will map the automation stack</h2>
          <p>
            Picked service: <strong>{selectedService}</strong>
          </p>
          <div className="contact-quick-actions">
            <a href={`tel:${PHONE_NUMBER.replace(/[^\d+]/g, "")}`}>Call {PHONE_NUMBER}</a>
            <a href={BOOKING_URL} target="_blank" rel="noreferrer">Schedule Demo</a>
          </div>
        </article>

        <form className="lead-form" onSubmit={onSubmitLead}>
          <label>
            Service Needed
            <select value={selectedService} onChange={(e) => setSelectedService(e.target.value)}>
              {offerings.map((offering) => (
                <option key={offering.title} value={offering.title}>{offering.title}</option>
              ))}
            </select>
          </label>

          <label>
            Name
            <input value={lead.name} onChange={(e) => onLeadFieldChange("name", e.target.value)} required />
          </label>

          <label>
            Phone
            <input value={lead.phone} onChange={(e) => onLeadFieldChange("phone", e.target.value)} required />
          </label>

          <label>
            Email
            <input type="email" value={lead.email} onChange={(e) => onLeadFieldChange("email", e.target.value)} required />
          </label>

          <label>
            Business Name
            <input value={lead.company} onChange={(e) => onLeadFieldChange("company", e.target.value)} />
          </label>

          <label>
            What should we automate first?
            <textarea value={lead.details} onChange={(e) => onLeadFieldChange("details", e.target.value)} rows={4} />
          </label>

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Submitting..." : "Send Intake And Get Setup Plan"}
          </button>
          {submitMessage ? <p className="submit-note">{submitMessage}</p> : null}
          {submitError ? <p className="submit-error">{submitError}</p> : null}
        </form>
      </section>

      <DispatchAssistant />
    </main>
  );
}
