import IndustryPage from "../components/industry-page";

export default function PlumbingPage() {
  return (
    <IndustryPage
      industryLabel="Plumbers"
      slug="plumbing"
      heroTagline="AI Field Service Management Built for Plumbing Businesses"
      description="Stop missing plumbing calls. GoFieldwise answers 24/7, books jobs, dispatches technicians, and sends invoices automatically for plumbing teams."
      ctaLabel="Try Plumbing Demo"
      bullets={[
        { title: "24/7 Call Intake", text: "Capture emergency and routine plumbing calls even after hours." },
        { title: "Smart Dispatch", text: "Send the right tech with the right parts to reduce callbacks." },
        { title: "Fast Invoicing", text: "Generate and send invoices immediately when work is complete." },
      ]}
    />
  );
}
