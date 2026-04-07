import IndustryPage from "../components/industry-page";

export default function LandscapingPage() {
  return (
    <IndustryPage
      industryLabel="Landscaping Companies"
      slug="landscaping"
      heroTagline="AI Field Service Management for Landscaping Teams"
      description="GoFieldwise helps landscaping businesses keep routes organized, improve customer communication, and collect payments without admin chaos."
      ctaLabel="Try Landscaping Demo"
      bullets={[
        { title: "Route-Friendly Scheduling", text: "Group jobs by area to reduce windshield time and fuel cost." },
        { title: "Recurring Workflows", text: "Automate repeat service reminders for mowing and maintenance." },
        { title: "Same-Day Billing", text: "Send invoices and payment links as soon as jobs are done." },
      ]}
    />
  );
}
