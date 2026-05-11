import Link from "next/link";

export default function SiteNav() {
  return (
    <header className="site-nav">
      <div className="site-nav-inner">
        <Link href="/" className="brand">GoFieldwise</Link>
        <nav className="links" aria-label="Primary">
          <details className="trade-menu">
            <summary>By Trade</summary>
            <div>
              <Link href="/plumbing">Plumbing</Link>
              <Link href="/hvac">HVAC</Link>
              <Link href="/electrical">Electrical</Link>
              <Link href="/landscaping">Landscaping</Link>
              <Link href="/cleaning-services">Cleaning</Link>
            </div>
          </details>
          <Link href="/marketing-ai">Marketing AI</Link>
          <Link href="/platform">Platform</Link>
        </nav>
      </div>
      <style jsx>{`
        .site-nav {
          position: sticky;
          top: 0;
          z-index: 50;
          background: rgba(15, 23, 42, 0.92);
          backdrop-filter: blur(8px);
          border-bottom: 1px solid rgba(148, 163, 184, 0.2);
        }
        .site-nav-inner {
          max-width: 1120px;
          margin: 0 auto;
          padding: 0.75rem 1rem;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
        }
        .brand {
          color: #ffffff;
          font-weight: 800;
          letter-spacing: 0.02em;
          text-decoration: none;
          white-space: nowrap;
        }
        .site-nav-inner :global(a.brand) {
          color: #ffffff;
          text-decoration: none;
        }
        .site-nav-inner :global(a.brand:hover) {
          color: #ffd9ae;
        }
        .links {
          display: flex;
          align-items: center;
          gap: 0.9rem;
          flex-wrap: wrap;
          justify-content: flex-end;
        }
        .links :global(a) {
          color: #cbd5e1;
          text-decoration: none;
          font-size: 0.92rem;
          font-weight: 600;
        }
        .links :global(a:hover) {
          color: #ffd9ae;
        }
        .trade-menu {
          position: relative;
          color: #cbd5e1;
          font-size: 0.92rem;
          font-weight: 700;
        }
        .trade-menu summary {
          cursor: pointer;
          list-style: none;
        }
        .trade-menu summary::-webkit-details-marker {
          display: none;
        }
        .trade-menu summary::after {
          content: "▾";
          margin-left: 0.35rem;
          font-size: 0.75rem;
        }
        .trade-menu[open] summary {
          color: #ffd9ae;
        }
        .trade-menu div {
          position: absolute;
          top: calc(100% + 12px);
          right: 0;
          min-width: 190px;
          display: grid;
          gap: 0.35rem;
          padding: 0.7rem;
          border: 1px solid rgba(148, 163, 184, 0.24);
          border-radius: 8px;
          background: #111827;
          box-shadow: 0 18px 38px rgba(0, 0, 0, 0.25);
        }
        .trade-menu div :global(a) {
          display: block;
          padding: 0.45rem 0.55rem;
          border-radius: 6px;
        }
        .trade-menu div :global(a:hover) {
          background: rgba(255, 217, 174, 0.1);
        }
        @media (max-width: 840px) {
          .site-nav-inner {
            flex-direction: column;
            align-items: flex-start;
          }
          .links {
            width: 100%;
            justify-content: flex-start;
          }
          .trade-menu div {
            left: 0;
            right: auto;
          }
        }
      `}</style>
    </header>
  );
}
