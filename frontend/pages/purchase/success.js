import Head from "next/head";
import Link from "next/link";

export default function PurchaseSuccessPage() {
  return (
    <>
      <Head>
        <title>Purchase Complete | GoFieldWise</title>
        <meta
          name="description"
          content="Your GoFieldWise Connect account is being prepared."
        />
      </Head>

      <main className="success-page">
        <section className="success-shell">
          <div className="status-panel">
            <span className="status-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" role="img">
                <path d="M9.2 16.6 4.9 12.3l1.4-1.4 2.9 2.9 8.5-8.5 1.4 1.4-9.9 9.9Z" />
              </svg>
            </span>
            <p className="eyebrow">Purchase Complete</p>
            <h1>Your GoFieldWise Connect account is being prepared.</h1>
            <p className="lead">
              Check your email for your Operator Setup link. The setup link expires in
              72 hours.
            </p>

            <div className="actions">
              <Link className="primary" href="/operator/setup">
                Go to Operator Setup
              </Link>
              <a className="secondary" href="mailto:support@gofieldwise.com">
                Contact Support
              </a>
            </div>
          </div>

          <aside className="next-panel" aria-label="What happens next">
            <h2>What happens next</h2>
            <div className="step">
              <span>1</span>
              <div>
                <strong>Open your setup email</strong>
                <p>Use the secure operator link sent after checkout.</p>
              </div>
            </div>
            <div className="step">
              <span>2</span>
              <div>
                <strong>Create your login</strong>
                <p>Set the dashboard email and password for your business.</p>
              </div>
            </div>
            <div className="step">
              <span>3</span>
              <div>
                <strong>Start Connect Center</strong>
                <p>Finish call handling, lead capture, and automation setup.</p>
              </div>
            </div>
            <p className="support">
              Need help? Email{" "}
              <a href="mailto:support@gofieldwise.com">support@gofieldwise.com</a>.
            </p>
          </aside>
        </section>
      </main>

      <style jsx>{`
        .success-page {
          min-height: 100vh;
          background:
            linear-gradient(180deg, rgba(255, 248, 235, 0.92), rgba(246, 250, 249, 0.96)),
            #f8f6ef;
          color: #14242c;
          padding: 64px 20px;
          display: flex;
          align-items: center;
        }

        .success-shell {
          width: 100%;
          max-width: 1080px;
          margin: 0 auto;
          display: grid;
          grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
          gap: 22px;
          align-items: stretch;
        }

        .status-panel,
        .next-panel {
          border: 1px solid #d8e3e1;
          background: rgba(255, 255, 255, 0.86);
          box-shadow: 0 20px 60px rgba(23, 48, 56, 0.12);
          border-radius: 10px;
        }

        .status-panel {
          padding: clamp(28px, 5vw, 54px);
        }

        .status-icon {
          width: 48px;
          height: 48px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 999px;
          background: #e4f5ec;
          color: #17643a;
          margin-bottom: 22px;
        }

        .status-icon svg {
          width: 26px;
          height: 26px;
          fill: currentColor;
        }

        .eyebrow {
          margin: 0 0 10px;
          color: #b66d13;
          font-size: 0.78rem;
          font-weight: 900;
          letter-spacing: 0.12em;
          text-transform: uppercase;
        }

        h1 {
          margin: 0;
          color: #0b2633;
          font-size: clamp(2.4rem, 6vw, 4.8rem);
          line-height: 0.98;
          max-width: 760px;
        }

        .lead {
          margin: 22px 0 0;
          max-width: 650px;
          color: #4e6872;
          font-size: 1.08rem;
          line-height: 1.65;
        }

        .actions {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin-top: 28px;
        }

        .actions a {
          min-height: 46px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 8px;
          padding: 0 18px;
          font-weight: 900;
          text-decoration: none;
        }

        .primary {
          background: #0b2633;
          color: #fffdf8;
        }

        .secondary {
          border: 1px solid #d7a14b;
          background: #fff6e7;
          color: #0b2633;
        }

        .next-panel {
          padding: 24px;
        }

        .next-panel h2 {
          margin: 0 0 18px;
          color: #0b2633;
          font-size: 1.18rem;
        }

        .step {
          display: grid;
          grid-template-columns: 38px 1fr;
          gap: 12px;
          padding: 16px 0;
          border-top: 1px solid #e5eeec;
        }

        .step span {
          width: 32px;
          height: 32px;
          border-radius: 999px;
          background: #0b2633;
          color: #fffdf8;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          font-weight: 900;
        }

        .step strong {
          color: #0b2633;
        }

        .step p {
          margin: 4px 0 0;
          color: #5a737b;
          line-height: 1.5;
        }

        .support {
          margin: 18px 0 0;
          padding-top: 16px;
          border-top: 1px solid #e5eeec;
          color: #5a737b;
          line-height: 1.55;
        }

        .support a {
          color: #0b2633;
          font-weight: 900;
        }

        @media (max-width: 860px) {
          .success-page {
            align-items: flex-start;
            padding-top: 36px;
          }

          .success-shell {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </>
  );
}
