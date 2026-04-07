import Head from "next/head";
import Link from "next/link";

export default function IndustryPage({
  industryLabel,
  slug,
  description,
  heroTagline,
  bullets,
  ctaLabel,
}) {
  const pageTitle = `AI Field Service Management for ${industryLabel} | GoFieldwise`;
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

      <main className="page-shell">
        <section className="hero">
          <div className="container">
            <p className="eyebrow">GoFieldwise for {industryLabel}</p>
            <h1>{heroTagline}</h1>
            <p>{description}</p>
            <div className="hero-cta">
              <Link href={`/demo?industry=${slug}`} className="btn btn-primary">
                {ctaLabel}
              </Link>
              <Link href="/" className="btn btn-secondary">
                Back to Home
              </Link>
            </div>
          </div>
        </section>

        <section className="benefits">
          <div className="container">
            <h2>What GoFieldwise Automates for {industryLabel}</h2>
            <div className="grid">
              {bullets.map((item) => (
                <article key={item.title} className="card">
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      </main>

      <style jsx>{`
        .page-shell {
          min-height: 100vh;
          background: #f8fafc;
          color: #0f172a;
        }
        .container {
          max-width: 1120px;
          margin: 0 auto;
          padding: 0 1rem;
        }
        .hero {
          padding: 4.5rem 1rem;
          background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
          color: #fff;
          text-align: center;
        }
        .eyebrow {
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-weight: 700;
          color: #93c5fd;
          margin-bottom: 0.75rem;
          font-size: 0.8rem;
        }
        h1 {
          font-size: clamp(2rem, 4vw, 3rem);
          margin: 0 0 1rem;
        }
        .hero p {
          max-width: 760px;
          margin: 0 auto 2rem;
          font-size: 1.1rem;
          color: #cbd5e1;
        }
        .hero-cta {
          display: flex;
          justify-content: center;
          gap: 0.8rem;
          flex-wrap: wrap;
        }
        .btn {
          border-radius: 10px;
          padding: 0.85rem 1.35rem;
          text-decoration: none;
          font-weight: 700;
        }
        .btn-primary {
          color: #fff;
          background: #2563eb;
        }
        .btn-secondary {
          color: #e2e8f0;
          border: 1px solid #475569;
        }
        .benefits {
          padding: 4rem 1rem;
        }
        h2 {
          text-align: center;
          font-size: clamp(1.5rem, 3vw, 2rem);
          margin: 0 0 2rem;
        }
        .grid {
          display: grid;
          gap: 1rem;
          grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
        }
        .card {
          background: #fff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 1.25rem;
        }
        .card h3 {
          margin: 0 0 0.5rem;
          font-size: 1.05rem;
        }
        .card p {
          margin: 0;
          color: #475569;
          line-height: 1.45;
        }
      `}</style>
    </>
  );
}
