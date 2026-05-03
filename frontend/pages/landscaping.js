import IndustryPage from "../components/industry-page";

export default function LandscapingPage() {
  return (
    <IndustryPage
      industryLabel="Landscaping Companies"
      slug="landscaping"
      heroTagline="AI Field Service Management for Landscaping Teams"
      description="GoFieldwise helps landscaping businesses keep routes organized, improve customer communication, and collect payments without admin chaos."
      ctaLabel="Try Landscaping Demo"
      operatorPromise="Landscaping is route density, recurring work, weather delays, estimates, and customer expectations about what the crew did today."
      scenario={{
        title: "New weekly maintenance lead",
        body: "Adrian captures property size, gate access, service frequency, current pain points, and preferred day so the estimate is route-aware.",
        urgency: "Route-density scheduling",
        outcome: "The lead is ready for a quote, route grouping, and recurring service follow-up.",
      }}
      intakeFields={[
        { name: "Property type", example: "Residential corner lot with backyard gate" },
        { name: "Service", example: "Weekly mowing, edging, shrub trim monthly" },
        { name: "Access", example: "Gate code needed, dog inside after 3 PM" },
        { name: "Route note", example: "Near Edmond Tuesday route" },
      ]}
      differentiators={[
        {
          label: "Routes",
          title: "Profit depends on grouping work",
          text: "Adrian captures location and service frequency so scheduling can protect route density.",
        },
        {
          label: "Recurring",
          title: "The money is in repeat service",
          text: "Maintenance, seasonal cleanups, fertilization, and reactivation need steady follow-up.",
        },
        {
          label: "Weather",
          title: "Customer updates reduce complaints",
          text: "Weather delays and completion notices keep clients informed without office back-and-forth.",
        },
      ]}
      workflow={{
        title: "From new yard inquiry to recurring route revenue.",
        steps: [
          { title: "Qualify", text: "Adrian captures property, service type, frequency, and access notes." },
          { title: "Route", text: "Jobs are grouped by area, frequency, and crew capacity." },
          { title: "Update", text: "Weather delay, on-the-way, and completion messages reduce customer calls." },
          { title: "Renew", text: "Seasonal cleanups and repeat service reminders keep revenue predictable." },
        ],
      }}
      proof={{
        quote: "For landscaping, the front office is really a route-profit engine.",
        metric: "Margin lever",
        value: "Routes",
        text: "Better intake and follow-up help crews spend less time driving and more time billing.",
      }}
      bullets={[
        { title: "Route-Friendly Scheduling", text: "Group work by area, frequency, crew capacity, and access requirements." },
        { title: "Recurring Workflows", text: "Automate mowing, maintenance, seasonal cleanup, and reactivation reminders." },
        { title: "Same-Day Billing", text: "Send completion texts, invoices, and payment links as soon as jobs are done." },
      ]}
    />
  );
}
