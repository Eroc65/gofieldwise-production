import IndustryPage from "../components/industry-page";

export default function HvacPage() {
  return (
    <IndustryPage
      industryLabel="HVAC Teams"
      slug="hvac"
      heroTagline="AI Field Service Management for HVAC Shops"
      description="GoFieldwise helps HVAC businesses answer calls faster, schedule tune-ups efficiently, and keep every job moving from dispatch to payment."
      ctaLabel="Try HVAC Demo"
      bullets={[
        { title: "Seasonal Rush Ready", text: "Handle peak demand with automated scheduling and follow-up." },
        { title: "Tech Routing", text: "Dispatch based on availability, skill, and job urgency." },
        { title: "Maintenance Follow-Up", text: "Automatically trigger reminders for tune-ups and service plans." },
      ]}
    />
  );
}
