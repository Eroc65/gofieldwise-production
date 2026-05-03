import IndustryPage from "../components/industry-page";

export default function ElectricalPage() {
  return (
    <IndustryPage
      industryLabel="Electrical Contractors"
      slug="electrical"
      heroTagline="AI Field Service Management for Electrical Businesses"
      description="GoFieldwise gives electrical shops a practical front desk system: instant call response, organized dispatch, and clean invoicing in one flow."
      ctaLabel="Try Electrical Demo"
      operatorPromise="Electrical calls depend on risk: outage, burning smell, breaker trips, panel work, remodel scope, permits, and whether power is partially or fully down."
      scenario={{
        title: "Breaker keeps tripping",
        body: "Adrian asks what circuit is affected, whether there is burning smell or heat, what changed recently, and whether the home has partial power.",
        urgency: "Safety-aware triage",
        outcome: "The dispatch note separates emergency hazard from scheduled troubleshooting.",
      }}
      intakeFields={[
        { name: "Symptom", example: "Breaker trips when microwave and lights run" },
        { name: "Safety flag", example: "No smoke, no burning smell, panel not hot" },
        { name: "Scope", example: "Troubleshooting plus possible dedicated circuit" },
        { name: "Access", example: "Panel in garage, customer home after 2 PM" },
      ]}
      differentiators={[
        {
          label: "Safety",
          title: "Hazards need different routing",
          text: "Adrian flags smoke, burning smells, hot panels, outages, and unsafe DIY work before dispatch.",
        },
        {
          label: "Scope",
          title: "Small calls and project leads are not the same",
          text: "Panel upgrades, EV chargers, remodel wiring, and troubleshooting calls get captured with different context.",
        },
        {
          label: "Compliance",
          title: "Permits and access notes matter",
          text: "Electrical work often needs site details, panel access, photos, and follow-up notes before the tech arrives.",
        },
      ]}
      workflow={{
        title: "From safety concern to clean electrical work order.",
        steps: [
          { title: "Answer", text: "Adrian handles the call without sending customers to voicemail." },
          { title: "Screen risk", text: "Outage, smoke, heat, tripping breaker, or planned install gets triaged." },
          { title: "Scope", text: "Panel, fixture, EV charger, remodel, or troubleshooting details are organized." },
          { title: "Close loop", text: "Customer updates, invoice, and review request go out after completion." },
        ],
      }}
      proof={{
        quote: "For electrical shops, a better intake call means safer dispatch and fewer vague work orders.",
        metric: "Intake focus",
        value: "Safety",
        text: "Adrian captures hazard signals and scope before the technician walks in.",
      }}
      bullets={[
        { title: "Safety-Aware Intake", text: "Capture outages, breaker issues, hot panels, burning smells, and urgent hazards." },
        { title: "Project Coordination", text: "Organize panel upgrades, EV chargers, fixtures, remodel wiring, and access notes." },
        { title: "Post-Job Review Boost", text: "Send structured follow-ups after clean, professional electrical service." },
      ]}
    />
  );
}
