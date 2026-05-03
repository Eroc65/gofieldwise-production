import IndustryPage from "../components/industry-page";

export default function PlumbingPage() {
  return (
    <IndustryPage
      industryLabel="Plumbers"
      slug="plumbing"
      heroTagline="AI Field Service Management Built for Plumbing Businesses"
      description="Stop missing plumbing calls. GoFieldwise answers 24/7, books jobs, dispatches technicians, and sends invoices automatically for plumbing teams."
      ctaLabel="Try Plumbing Demo"
      operatorPromise="Plumbing is urgency-heavy: leaks, shutoffs, drains, water heaters, and customers who need an answer before damage spreads."
      scenario={{
        title: "Active leak in the garage",
        body: "Adrian identifies whether water is still running, asks about shutoff access, captures the address, and marks the job same-day.",
        urgency: "Emergency routing",
        outcome: "Leak status, shutoff note, address, and preferred arrival window are ready for dispatch.",
      }}
      intakeFields={[
        { name: "Problem type", example: "Water heater leaking in garage" },
        { name: "Active damage", example: "Water still running, customer needs shutoff help" },
        { name: "Access notes", example: "Side gate open, unit is next to laundry room" },
        { name: "Dispatch priority", example: "Same-day emergency" },
      ]}
      differentiators={[
        {
          label: "Urgency",
          title: "Leaking now matters more than 'available next week'",
          text: "Adrian separates emergencies from routine installs so your best tech is not buried in low-priority calls.",
        },
        {
          label: "Parts",
          title: "Better notes reduce second trips",
          text: "Drain, fixture, water heater, shutoff, and access details help the tech roll with the right expectation.",
        },
        {
          label: "Trust",
          title: "Customers want calm immediately",
          text: "A fast answer with clear next steps keeps the customer from calling the next plumber on Google.",
        },
      ]}
      workflow={{
        title: "From emergency call to paid plumbing job.",
        steps: [
          { title: "Answer", text: "Adrian answers after-hours and captures the issue without voicemail." },
          { title: "Triage", text: "Active leak, no water, clogged drain, or routine fixture work gets categorized." },
          { title: "Dispatch", text: "Job notes include urgency, address, access, and customer contact." },
          { title: "Follow up", text: "Invoice, payment link, and review request go out after completion." },
        ],
      }}
      proof={{
        quote: "For plumbing, speed is trust. The first calm, useful answer often wins the job.",
        metric: "Target response",
        value: "60 sec",
        text: "Adrian keeps new plumbing calls moving before the customer starts dialing competitors.",
      }}
      bullets={[
        { title: "Emergency Intake", text: "Capture active leaks, no-water calls, clogs, fixture failures, and water heater issues." },
        { title: "Smart Dispatch", text: "Send the right tech with urgency, access notes, and job context already summarized." },
        { title: "Fast Invoicing", text: "Send invoices and payment links immediately when the work is complete." },
      ]}
    />
  );
}
