import IndustryPage from "../components/industry-page";

export default function CleaningServicesPage() {
  return (
    <IndustryPage
      industryLabel="Cleaning Services"
      slug="cleaning-services"
      heroTagline="AI Field Service Management for Cleaning Businesses"
      description="GoFieldwise helps cleaning teams answer inquiries, coordinate schedules, and handle invoicing with a simple workflow built for small service crews."
      ctaLabel="Try Cleaning Demo"
      bullets={[
        { title: "Lead to Booking", text: "Convert inquiry calls and web leads into scheduled jobs fast." },
        { title: "Team Visibility", text: "Keep staff schedules and customer expectations in sync." },
        { title: "Automated Follow-Up", text: "Trigger review requests and repeat service reminders automatically." },
      ]}
    />
  );
}
