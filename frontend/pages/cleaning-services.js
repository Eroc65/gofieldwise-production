import IndustryPage from "../components/industry-page";

export default function CleaningServicesPage() {
  return (
    <IndustryPage
      industryLabel="Cleaning Services"
      slug="cleaning-services"
      heroTagline="AI Field Service Management for Cleaning Businesses"
      description="GoFieldwise helps cleaning teams answer inquiries, coordinate schedules, and handle invoicing with a simple workflow built for small service crews."
      ctaLabel="Try Cleaning Demo"
      operatorPromise="Cleaning businesses live on quoting accuracy: property size, frequency, access, pets, supplies, move-out deadlines, and recurring cadence."
      scenario={{
        title: "Move-out cleaning request",
        body: "Adrian captures square footage, bedrooms, bathrooms, deadline, key access, add-ons, and whether the home is empty.",
        urgency: "Deadline-based scheduling",
        outcome: "The team gets a quote-ready job with scope, access, and timing clearly captured.",
      }}
      intakeFields={[
        { name: "Job type", example: "Move-out clean before Friday walkthrough" },
        { name: "Scope", example: "3 bed, 2 bath, fridge and oven included" },
        { name: "Access", example: "Lockbox code, no pets, home empty" },
        { name: "Cadence", example: "Wants recurring biweekly after move" },
      ]}
      differentiators={[
        {
          label: "Scope",
          title: "Bad intake creates bad quotes",
          text: "Adrian captures room count, add-ons, condition, and deadline before the team commits.",
        },
        {
          label: "Access",
          title: "Crews need entry details",
          text: "Gate codes, lockboxes, pets, supplies, parking, and alarm notes stay attached to the job.",
        },
        {
          label: "Recurring",
          title: "One-time jobs can become subscriptions",
          text: "Follow-up can convert move-out, deep clean, and first-time customers into recurring service.",
        },
      ]}
      workflow={{
        title: "From cleaning inquiry to booked crew schedule.",
        steps: [
          { title: "Capture", text: "Adrian gathers property size, service type, add-ons, and access details." },
          { title: "Quote", text: "Scope is organized so pricing does not rely on a vague callback." },
          { title: "Schedule", text: "Deadline, team availability, and customer preference shape the booking." },
          { title: "Repeat", text: "Review requests and recurring cleaning offers go out after completion." },
        ],
      }}
      proof={{
        quote: "For cleaning teams, the difference between a profitable job and a messy one is scope clarity.",
        metric: "Best use",
        value: "Scope",
        text: "Adrian turns inquiries into quote-ready jobs with access and add-on details included.",
      }}
      bullets={[
        { title: "Lead to Booking", text: "Convert inquiries into scheduled jobs with scope, deadline, and access details." },
        { title: "Team Visibility", text: "Keep staff schedules, customer expectations, and property notes in sync." },
        { title: "Automated Follow-Up", text: "Trigger review requests, repeat service offers, and recurring cleaning reminders." },
      ]}
    />
  );
}
