import Head from "next/head";
import Link from "next/link";
import { useState } from "react";

export default function Home() {
  const [demoActive, setDemoActive] = useState(false);

  return (
    <>
      <Head>
        <title>GoFieldwise - AI Field Service Management for Home Service Businesses</title>
        <meta
          name="description"
          content="Never miss a customer. Automate every job-from first call to paid invoice. AI-powered scheduling, dispatch & invoicing for contractors. $200/mo flat rate. Try live demo."
        />
        <meta
          name="keywords"
          content="AI field service management, contractor software, plumbing scheduling, HVAC dispatch, electrician invoicing, automated job booking, AI receptionist"
        />
        <meta property="og:title" content="GoFieldwise - AI Field Service Management" />
        <meta
          property="og:description"
          content="Stop missing calls & jobs. GoFieldwise answers, books, dispatches, and invoices automatically-even while you sleep."
        />
        <meta property="og:image" content="https://gofieldwise.com/og-image.png" />
        <meta property="og:url" content="https://gofieldwise.com" />
        <meta name="twitter:card" content="summary_large_image" />
        <link rel="canonical" href="https://gofieldwise.com" />
      </Head>

      <section className="hero">
        <div className="container">
          <h1 className="hero-title">
            Never Miss a Customer.
            <br />
            <span className="highlight">Automate Every Job</span>-From First Call to Paid Invoice.
          </h1>
          <p className="hero-subtitle">
            GoFieldwise is AI-powered field service management built for home service businesses-no surprise pricing, no
            setup headaches, just more jobs booked and more time for real work.
          </p>
          <div className="hero-cta">
            <Link href="/demo" className="btn btn-primary btn-large">
              See GoFieldwise in Action-No Signup Needed
            </Link>
            <button className="btn btn-secondary btn-large" onClick={() => setDemoActive(true)}>
              Call Our AI Receptionist: (602) 932-0967
            </button>
            <Link href="/marketing-ai" className="btn btn-secondary btn-large">
              Generate AI Marketing Images
            </Link>
          </div>
          <div className="hero-stats">
            <div className="stat">
              <span className="stat-number">24/7</span>
              <span className="stat-label">Instant Lead Capture</span>
            </div>
            <div className="stat">
              <span className="stat-number">$200/mo</span>
              <span className="stat-label">Flat Rate, No Hidden Fees</span>
            </div>
            <div className="stat">
              <span className="stat-number">60 min</span>
              <span className="stat-label">Live in Under an Hour</span>
            </div>
          </div>
        </div>
      </section>

      <section className="social-proof">
        <div className="container">
          <div className="testimonial-card">
            <div className="stars">★★★★★</div>
            <p className="testimonial-text">
              "GoFieldwise replaced my $3,500/mo office manager. We miss zero calls and book jobs even when nobody&apos;s
              at the office."
            </p>
            <div className="testimonial-author">
              <strong>Dave K.</strong> - Plumber, Phoenix, AZ
            </div>
          </div>
          <div className="metrics">
            <div className="metric">
              <div className="metric-value">87</div>
              <div className="metric-label">Google reviews in 90 days</div>
            </div>
            <div className="metric">
              <div className="metric-value">60s</div>
              <div className="metric-label">Avg. time from call to job booked</div>
            </div>
            <div className="metric">
              <div className="metric-value">0</div>
              <div className="metric-label">Missed calls since switching</div>
            </div>
          </div>
        </div>
      </section>

      <section className="value-prop">
        <div className="container">
          <h2>Why Choose GoFieldwise Over "AI Agencies"?</h2>
          <div className="comparison-grid">
            <div className="comparison-card">
              <h3>Most AI Agencies</h3>
              <ul>
                <li>Just answer calls & capture leads</li>
                <li>Custom quotes & hidden pricing</li>
                <li>No scheduling, dispatch, or invoicing</li>
                <li>Slow setup (4-5 days)</li>
                <li>Limited to front-end automation</li>
              </ul>
            </div>
            <div className="comparison-card highlight">
              <h3>GoFieldwise</h3>
              <ul>
                <li>
                  <strong>Full workflow automation</strong>-calls, booking, dispatch, invoicing, reviews
                </li>
                <li>
                  <strong>$200/mo flat rate</strong>-no surprises, no demo required
                </li>
                <li>
                  <strong>Live in under 60 minutes</strong>-self-serve, no technical knowledge needed
                </li>
                <li>
                  <strong>Built for home service businesses</strong> (1-20 techs)
                </li>
                <li>
                  <strong>End-to-end operations</strong>-not just lead capture
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="how-it-works">
        <div className="container">
          <h2>From First Ring to Five-Star Review-Every Step Automated</h2>
          <div className="steps">
            {[
              { number: "01", title: "Customer Calls", desc: "AI answers 24/7, captures job details" },
              { number: "02", title: "Job Booked", desc: "Auto-scheduled to best available slot" },
              { number: "03", title: "Tech Dispatched", desc: "Right person gets all details on their phone" },
              { number: "04", title: "Invoice Sent", desc: "Auto-generated & sent the moment work is done" },
              { number: "05", title: "Payment Collected", desc: "Text payment link, paid before tech leaves" },
              { number: "06", title: "Review Requested", desc: "Auto-follow-up for Google reviews" },
            ].map((step) => (
              <div className="step" key={step.number}>
                <div className="step-number">{step.number}</div>
                <h3>{step.title}</h3>
                <p>{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="industry-links">
        <div className="container">
          <h2>Built for Your Trade</h2>
          <p>Explore tailored pages for your business type.</p>
          <div className="industry-grid">
            <Link href="/plumbing" className="industry-card">Plumbing</Link>
            <Link href="/hvac" className="industry-card">HVAC</Link>
            <Link href="/electrical" className="industry-card">Electrical</Link>
            <Link href="/landscaping" className="industry-card">Landscaping</Link>
            <Link href="/cleaning-services" className="industry-card">Cleaning Services</Link>
          </div>
        </div>
      </section>

      <section className="cta-final">
        <div className="container">
          <h2>Ready to Stop Missing Calls & Start Growing?</h2>
          <p>
            Join hundreds of contractors who trust GoFieldwise to handle their front desk-so they can focus on the work
            that pays.
          </p>
          <div className="cta-buttons">
            <Link href="/demo" className="btn btn-primary btn-xlarge">
              Try the Live Demo Now
            </Link>
            <Link href="/pricing" className="btn btn-outline btn-xlarge">
              See Transparent Pricing
            </Link>
          </div>
          <p className="cta-note">
            <small>No credit card required. Cancel anytime.</small>
          </p>
        </div>
      </section>

      {demoActive && (
        <div className="demo-modal">
          <div className="modal-content">
            <h3>Call Our AI Receptionist Now</h3>
            <p>
              Dial <strong>(602) 932-0967</strong> to experience how GoFieldwise answers, qualifies, and books jobs-24/7.
            </p>
            <button className="btn btn-secondary" onClick={() => setDemoActive(false)}>
              Close
            </button>
          </div>
        </div>
      )}

      <style jsx>{`
        .hero {
          padding: 5rem 1rem;
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          color: white;
          text-align: center;
        }
        .container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 1rem;
        }
        .hero-title {
          font-size: 3.5rem;
          line-height: 1.1;
          margin-bottom: 1.5rem;
        }
        .highlight {
          color: #3b82f6;
        }
        .hero-subtitle {
          font-size: 1.25rem;
          max-width: 800px;
          margin: 0 auto 2.5rem;
          opacity: 0.9;
        }
        .hero-cta {
          display: flex;
          gap: 1rem;
          justify-content: center;
          flex-wrap: wrap;
          margin-bottom: 3rem;
        }
        .btn {
          padding: 1rem 2rem;
          border-radius: 8px;
          font-weight: 600;
          text-decoration: none;
          display: inline-block;
          cursor: pointer;
          border: none;
          transition: all 0.2s;
        }
        .btn-primary {
          background: #3b82f6;
          color: white;
        }
        .btn-primary:hover {
          background: #2563eb;
        }
        .btn-secondary {
          background: transparent;
          color: white;
          border: 2px solid #64748b;
        }
        .btn-secondary:hover {
          border-color: #3b82f6;
          color: #3b82f6;
        }
        .btn-large {
          font-size: 1.125rem;
          padding: 1.25rem 2.5rem;
        }
        .btn-xlarge {
          font-size: 1.25rem;
          padding: 1.5rem 3rem;
        }
        .btn-outline {
          background: transparent;
          border: 2px solid white;
          color: white;
        }
        .hero-stats {
          display: flex;
          justify-content: center;
          gap: 3rem;
          margin-top: 3rem;
        }
        .stat {
          text-align: center;
        }
        .stat-number {
          display: block;
          font-size: 2.5rem;
          font-weight: 700;
          color: #3b82f6;
        }
        .stat-label {
          font-size: 0.95rem;
          opacity: 0.8;
        }
        .social-proof {
          padding: 4rem 1rem;
          background: #f8fafc;
        }
        .testimonial-card {
          max-width: 700px;
          margin: 0 auto 3rem;
          padding: 2rem;
          background: white;
          border-radius: 12px;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
          text-align: center;
        }
        .stars {
          font-size: 1.5rem;
          color: #fbbf24;
          margin-bottom: 1rem;
        }
        .testimonial-text {
          font-size: 1.25rem;
          font-style: italic;
          margin-bottom: 1rem;
        }
        .metrics {
          display: flex;
          justify-content: center;
          gap: 4rem;
          flex-wrap: wrap;
        }
        .metric-value {
          font-size: 2.5rem;
          font-weight: 700;
          color: #0f172a;
        }
        .metric-label {
          font-size: 0.95rem;
          color: #64748b;
        }
        .value-prop {
          padding: 5rem 1rem;
        }
        .value-prop h2 {
          text-align: center;
          font-size: 2.5rem;
          margin-bottom: 3rem;
        }
        .comparison-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 2rem;
          max-width: 1000px;
          margin: 0 auto;
        }
        .comparison-card {
          padding: 2rem;
          border-radius: 12px;
          border: 2px solid #e2e8f0;
        }
        .comparison-card.highlight {
          border-color: #3b82f6;
          background: #eff6ff;
        }
        .comparison-card h3 {
          margin-top: 0;
          margin-bottom: 1.5rem;
        }
        .comparison-card ul {
          padding-left: 1.5rem;
          margin: 0;
        }
        .comparison-card li {
          margin-bottom: 0.75rem;
        }
        .how-it-works {
          padding: 5rem 1rem;
          background: #f8fafc;
        }
        .industry-links {
          padding: 5rem 1rem;
          background: white;
          text-align: center;
        }
        .industry-links p {
          margin: 0 auto 2rem;
          color: #64748b;
        }
        .industry-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 1rem;
          max-width: 900px;
          margin: 0 auto;
        }
        .industry-card {
          display: inline-block;
          border: 1px solid #cbd5e1;
          border-radius: 12px;
          padding: 1rem;
          text-decoration: none;
          color: #0f172a;
          font-weight: 600;
          transition: all 0.2s;
          background: #f8fafc;
        }
        .industry-card:hover {
          border-color: #3b82f6;
          background: #eff6ff;
          color: #1d4ed8;
        }
        .how-it-works h2 {
          text-align: center;
          font-size: 2.5rem;
          margin-bottom: 3rem;
        }
        .steps {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 2rem;
          max-width: 1200px;
          margin: 0 auto;
        }
        .step {
          text-align: center;
          padding: 2rem;
          background: white;
          border-radius: 12px;
          box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
        }
        .step-number {
          font-size: 2rem;
          font-weight: 700;
          color: #3b82f6;
          margin-bottom: 1rem;
        }
        .cta-final {
          padding: 5rem 1rem;
          background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
          color: white;
          text-align: center;
        }
        .cta-final h2 {
          font-size: 2.5rem;
          margin-bottom: 1.5rem;
        }
        .cta-final p {
          font-size: 1.25rem;
          max-width: 700px;
          margin: 0 auto 3rem;
          opacity: 0.9;
        }
        .cta-buttons {
          display: flex;
          gap: 1.5rem;
          justify-content: center;
          flex-wrap: wrap;
          margin-bottom: 1.5rem;
        }
        .demo-modal {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        .modal-content {
          background: white;
          padding: 3rem;
          border-radius: 12px;
          max-width: 500px;
          text-align: center;
        }
        @media (max-width: 768px) {
          .hero-title {
            font-size: 2.5rem;
          }
          .hero-cta {
            flex-direction: column;
            align-items: center;
          }
          .hero-stats,
          .metrics {
            flex-direction: column;
            gap: 2rem;
          }
          .comparison-grid {
            grid-template-columns: 1fr;
          }
          .cta-buttons {
            flex-direction: column;
            align-items: center;
          }
        }
      `}</style>
    </>
  );
}
