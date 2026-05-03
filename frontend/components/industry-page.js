import Head from "next/head";
import Link from "next/link";

export default function IndustryPage({
  industryLabel,
  slug,
  description,
  heroTagline,
  bullets,
  ctaLabel,
  operatorPromise,
  scenario,
  intakeFields,
  differentiators,
  workflow,
  proof,
}) {
  const pageTitle = `AI Operations Manager for ${industryLabel} | GoFieldwise`;
  const canonical = `https://gofieldwise.com/${slug}`;

  return (
    <>
      <Head>
        <title>{pageTitle}</title>
        <meta name="description" content={description} />
        <meta property="og:title" content={pageTitle} />
        <meta property="og:description" content={description} />
        <meta property="og:url" content={canonical} />
        <link rel="canonical" href={canonical} />
      </Head>

      <main className="industry-page">
        <section className="industry-hero">
          <div className="hero-inner">
            <div className="hero-copy">
              <p className="eyebrow">GoFieldwise for {industryLabel}</p>
              <h1>{heroTagline}</h1>
              <p>{description}</p>
              <div className="hero-cta">
                <Link href={`/demo?industry=${slug}`} className="btn btn-primary">
                  {ctaLabel}
                </Link>
                <Link href="/" className="btn btn-secondary">
                  Back home
                </Link>
              </div>
            </div>

            <aside className="scenario-card">
              <span>Adrian handles this</span>
              <h2>{scenario.title}</h2>
              <p>{scenario.body}</p>
              <div className="scenario-meta">
                <strong>{scenario.urgency}</strong>
                <small>{scenario.outcome}</small>
              </div>
            </aside>
          </div>
        </section>

        <section className="operator-promise">
          <p className="eyebrow">What makes this trade different</p>
          <h2>{operatorPromise}</h2>
          <div className="difference-grid">
            {differentiators.map((item) => (
              <article key={item.title} className="difference-card">
                <span>{item.label}</span>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="intake-section">
          <div className="section-copy">
            <p className="eyebrow">What Adrian captures</p>
            <h2>Trade-specific intake, not a generic voicemail transcript.</h2>
            <p>
              The demo call shows prospects how their own customers will be qualified, routed, and summarized before a
              human ever opens the schedule.
            </p>
          </div>
          <div className="intake-board">
            {intakeFields.map((field) => (
              <div className="intake-row" key={field.name}>
                <span>{field.name}</span>
                <strong>{field.example}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="benefits">
          <div className="section-copy">
            <p className="eyebrow">Automation that matters</p>
            <h2>What GoFieldwise automates for {industryLabel}</h2>
          </div>
          <div className="grid">
            {bullets.map((item) => (
              <article key={item.title} className="card">
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="workflow-section">
          <div className="section-copy">
            <p className="eyebrow">How the day runs</p>
            <h2>{workflow.title}</h2>
          </div>
          <div className="timeline">
            {workflow.steps.map((step, index) => (
              <article key={step.title}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="proof-section">
          <blockquote>{proof.quote}</blockquote>
          <div className="proof-card">
            <span>{proof.metric}</span>
            <strong>{proof.value}</strong>
            <p>{proof.text}</p>
          </div>
        </section>

        <section className="final-cta">
          <h2>Let Adrian answer the next {industryLabel.toLowerCase()} call.</h2>
          <p>Try the same AI receptionist, dispatch intake, and summary SMS your customers will experience.</p>
          <div className="hero-cta">
            <Link href={`/demo?industry=${slug}`} className="btn btn-primary">
              {ctaLabel}
            </Link>
            <Link href="/" className="btn btn-secondary light">
              Back home
            </Link>
          </div>
        </section>
      </main>

      <style jsx>{`
        .industry-page {
          min-height: 100vh;
          background: var(--paper);
          color: var(--ink);
          overflow-x: hidden;
        }

        .industry-hero {
          padding: 64px 20px 48px;
          background: linear-gradient(120deg, #19333c, #274f5d 62%, #2f6678);
          color: #fffdf8;
        }

        .hero-inner,
        .operator-promise,
        .intake-section,
        .benefits,
        .workflow-section,
        .proof-section,
        .final-cta {
          width: 100%;
          max-width: 1120px;
          margin: 0 auto;
        }

        .hero-inner {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 390px;
          gap: 34px;
          align-items: center;
          min-width: 0;
        }

        .eyebrow {
          margin: 0 0 10px;
          color: #ffd9ae;
          font-size: 0.78rem;
          font-weight: 900;
          text-transform: uppercase;
          letter-spacing: 0.12em;
        }

        h1,
        h2,
        h3,
        p {
          overflow-wrap: anywhere;
        }

        h1 {
          margin: 0;
          font-size: clamp(2.55rem, 5vw, 4rem);
          line-height: 1.02;
          max-width: 780px;
        }

        .hero-copy p:not(.eyebrow) {
          margin: 18px 0 0;
          color: #f7efe1;
          font-size: 1.12rem;
          line-height: 1.7;
          max-width: 700px;
        }

        .hero-copy,
        .section-copy,
        .scenario-card,
        .difference-card,
        .intake-board,
        .card,
        .timeline article,
        .proof-card {
          min-width: 0;
        }

        .hero-cta {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-top: 26px;
        }

        :global(a.btn) {
          min-height: 48px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 8px;
          padding: 0 18px;
          font-weight: 900;
          text-decoration: none;
        }

        :global(a.btn-primary) {
          color: #fffdf8;
          background: linear-gradient(120deg, var(--accent), #db6330);
          border: 1px solid rgba(255, 255, 255, 0.08);
        }

        :global(a.btn-primary:hover) {
          background: linear-gradient(120deg, var(--accent-dark), #c64f1f);
        }

        :global(a.btn-secondary) {
          color: #fffdf8;
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 217, 174, 0.72);
        }

        :global(a.btn-secondary:hover) {
          color: #19333c;
          background: #ffd9ae;
        }

        :global(a.btn-secondary.light) {
          color: #19333c;
          background: #fffdf8;
          border-color: var(--line);
        }

        .scenario-card,
        .difference-card,
        .intake-board,
        .card,
        .timeline article,
        .proof-card {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          box-shadow: var(--shadow);
        }

        .scenario-card {
          padding: 20px;
          color: var(--ink);
        }

        .scenario-card span,
        .difference-card span,
        .intake-row span,
        .proof-card span {
          color: #4e6a74;
          font-size: 0.78rem;
          font-weight: 900;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .scenario-card h2 {
          margin: 12px 0 10px;
          color: #19333c;
          font-size: 1.5rem;
          line-height: 1.12;
        }

        .scenario-card p,
        .scenario-meta small,
        .card p,
        .difference-card p,
        .timeline p,
        .section-copy p,
        .proof-card p,
        .final-cta p {
          color: #35505b;
          line-height: 1.6;
        }

        .scenario-meta {
          margin-top: 16px;
          padding: 14px;
          border-left: 5px solid var(--accent);
          border-radius: 8px;
          background: #fff4de;
          display: grid;
          gap: 4px;
        }

        .scenario-meta strong {
          color: var(--accent-dark);
        }

        .operator-promise,
        .intake-section,
        .benefits,
        .workflow-section,
        .proof-section,
        .final-cta {
          padding: 62px 20px;
        }

        .operator-promise h2,
        .section-copy h2,
        .final-cta h2 {
          margin: 0;
          color: #071d26;
          font-size: clamp(1.9rem, 3vw, 2.65rem);
          line-height: 1.08;
          max-width: 820px;
        }

        .difference-grid,
        .grid {
          display: grid;
          gap: 14px;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          margin-top: 26px;
        }

        .difference-card,
        .card,
        .timeline article {
          padding: 18px;
        }

        .difference-card h3,
        .card h3,
        .timeline h3 {
          margin: 10px 0 8px;
          font-size: 1.08rem;
        }

        .intake-section {
          display: grid;
          grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
          gap: 24px;
          align-items: center;
          border-top: 1px solid var(--line);
          border-bottom: 1px solid var(--line);
        }

        .section-copy p {
          margin: 12px 0 0;
          font-size: 1.04rem;
        }

        .intake-board {
          padding: 12px;
          display: grid;
          gap: 10px;
        }

        .intake-row {
          border: 1px solid #e6d7c4;
          border-radius: 8px;
          padding: 12px;
          background: #fffcf7;
          display: grid;
          gap: 5px;
        }

        .intake-row strong {
          color: #19333c;
        }

        .timeline {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 14px;
          margin-top: 26px;
        }

        .timeline article span {
          color: var(--accent);
          font-weight: 900;
        }

        .proof-section {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 340px;
          gap: 24px;
          align-items: center;
        }

        blockquote {
          margin: 0;
          color: #19333c;
          font-weight: 900;
          font-size: clamp(1.45rem, 3vw, 2.35rem);
          line-height: 1.2;
        }

        .proof-card {
          padding: 20px;
        }

        .proof-card strong {
          display: block;
          margin: 10px 0;
          color: var(--accent);
          font-size: 2.4rem;
          line-height: 1;
        }

        .final-cta {
          text-align: center;
        }

        .final-cta h2,
        .final-cta p {
          margin-left: auto;
          margin-right: auto;
        }

        .final-cta .hero-cta {
          justify-content: center;
        }

        @media (max-width: 900px) {
          .hero-inner,
          .intake-section,
          .proof-section {
            grid-template-columns: 1fr;
          }

          .scenario-card {
            max-width: 560px;
          }

          .difference-grid,
          .grid,
          .timeline {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 640px) {
          .industry-hero,
          .operator-promise,
          .intake-section,
          .benefits,
          .workflow-section,
          .proof-section,
          .final-cta {
            padding: 42px 14px;
          }

          .hero-inner,
          .operator-promise,
          .intake-section,
          .benefits,
          .workflow-section,
          .proof-section,
          .final-cta {
            max-width: calc(100vw - 28px);
          }

          .industry-hero .hero-inner {
            max-width: calc(100vw - 40px);
          }

          .hero-cta {
            flex-direction: column;
          }

          h1 {
            font-size: clamp(2.15rem, 11vw, 2.85rem);
          }

          h2 {
            font-size: clamp(2rem, 10vw, 2.6rem);
          }

          .scenario-card,
          .intake-board,
          .proof-card {
            max-width: 100%;
          }

          :global(a.btn) {
            width: 100%;
          }

          .difference-grid,
          .grid,
          .timeline {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </>
  );
}
