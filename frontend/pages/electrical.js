import IndustryPage from "../components/industry-page";

export default function ElectricalPage() {
  return (
    <IndustryPage
      industryLabel="Electrical Contractors"
      slug="electrical"
      heroTagline="AI Field Service Management for Electrical Businesses"
      description="GoFieldwise gives electrical shops a practical front desk system: instant call response, organized dispatch, and clean invoicing in one flow."
      ctaLabel="Try Electrical Demo"
      bullets={[
        { title: "Service Intake", text: "Capture panel, rewiring, and urgent outage jobs with full context." },
        { title: "Job Coordination", text: "Keep technicians, schedules, and customer updates aligned." },
        { title: "Post-Job Review Boost", text: "Send structured follow-ups to earn more five-star reviews." },
      ]}
    />
  );
}
