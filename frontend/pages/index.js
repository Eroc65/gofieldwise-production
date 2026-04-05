import DispatchAssistant from "../components/DispatchAssistant";

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
  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">GoFieldWise</p>
        <h1>AI Voice Agents And Automation For Service Businesses</h1>
        <p>
          AI-forward systems that answer every call, capture and qualify leads, and book work 24/7.
          Never miss a lead because the phone rang at the wrong time.
        </p>
      </section>

      <section className="offerings" aria-label="GoFieldWise offerings">
        {offerings.map((offering) => (
          <article className="offering-card" key={offering.title}>
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
            <button type="button">Get Started</button>
          </article>
        ))}
      </section>

      <DispatchAssistant />
    </main>
  );
}
