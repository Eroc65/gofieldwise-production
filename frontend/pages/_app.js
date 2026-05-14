import Head from "next/head";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";

import SiteNav from "../components/SiteNav";
import { submitPublicLeadIntake } from "../lib/api";
import "../styles/globals.css";

const EXIT_AUDIT_SESSION_KEY = "gf_exit_audit_session_seen";

function ExitAuditModal() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let armed = false;
    const seenInSession = window.sessionStorage.getItem(EXIT_AUDIT_SESSION_KEY);
    if (seenInSession) {
      return undefined;
    }

    const armTimer = window.setTimeout(() => {
      armed = true;
    }, 1500);

    const onExitIntent = (event) => {
      if (!armed) {
        return;
      }
      if (window.sessionStorage.getItem(EXIT_AUDIT_SESSION_KEY)) {
        return;
      }
      const leavingWindow = !event.relatedTarget && !event.toElement;
      const nearTopEdge = event.clientY <= 0;
      if (leavingWindow && nearTopEdge) {
        window.sessionStorage.setItem(EXIT_AUDIT_SESSION_KEY, "1");
        setOpen(true);
      }
    };

    document.addEventListener("mouseout", onExitIntent);

    return () => {
      window.clearTimeout(armTimer);
      document.removeEventListener("mouseout", onExitIntent);
    };
  }, []);

  const closeModal = () => {
    window.sessionStorage.setItem(EXIT_AUDIT_SESSION_KEY, "1");
    setOpen(false);
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    const trimmedName = name.trim();
    const trimmedEmail = email.trim();
    if (!trimmedName || !trimmedEmail) {
      return;
    }

    setError("");
    try {
      const intakeKey = process.env.NEXT_PUBLIC_INTAKE_KEY || "";
      const orgId = process.env.NEXT_PUBLIC_INTAKE_ORG_ID || "";
      if (intakeKey || orgId) {
        await submitPublicLeadIntake({
          intakeKey,
          orgId,
          name: trimmedName,
          email: trimmedEmail,
          service: "5-minute operations audit",
          details: "Exit intent audit lead",
        });
      }
      window.sessionStorage.setItem(EXIT_AUDIT_SESSION_KEY, "1");
      setSubmitted(true);
    } catch (submitError) {
      setError("We could not submit right now. Please try again.");
    }
  };

  if (!open) {
    return null;
  }

  return (
    <div role="dialog" aria-modal="true" className="overlay">
      <div className="modal">
        <button onClick={closeModal} aria-label="Close" className="close">
          x
        </button>
        <p className="wait">WAIT</p>
        <h3>Don&apos;t leave your leads on the table.</h3>
        <p>
          Get our 5-Minute Operations Audit - a quick checklist that shows exactly where your business is
          leaking revenue.
        </p>
        <ul>
          <li>Where missed calls are costing you</li>
          <li>Scheduling gaps stealing your time</li>
          <li>Follow-up failures losing repeat business</li>
        </ul>

        {submitted ? (
          <p className="ok">Audit request received. Check your email shortly.</p>
        ) : (
          <form onSubmit={onSubmit}>
            <label htmlFor="audit-name">Your name</label>
            <input
              id="audit-name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="John Smith"
              required
            />

            <label htmlFor="audit-email">Enter your email to get it free</label>
            <input
              id="audit-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
              required
            />

            <button type="submit">Send My Audit</button>
            {error ? <p className="error">{error}</p> : null}
          </form>
        )}
      </div>

      <style jsx>{`
        .overlay {
          position: fixed;
          inset: 0;
          display: grid;
          place-items: center;
          background: #0b0f1a9e;
          padding: 16px;
          z-index: 200;
        }

        .modal {
          position: relative;
          width: min(560px, 100%);
          background: #fff;
          border: 1px solid #d5dbea;
          border-radius: 12px;
          padding: 18px;
        }

        .close {
          position: absolute;
          top: 8px;
          right: 8px;
          border: 0;
          background: transparent;
          cursor: pointer;
          font-size: 16px;
          font-weight: 700;
          line-height: 1;
        }

        .wait {
          margin: 0;
          color: #b45309;
          font-weight: 800;
        }

        h3 {
          margin: 4px 0 8px;
          color: #121826;
        }

        p {
          margin: 0 0 8px;
          color: #394256;
        }

        ul {
          margin: 0 0 10px;
          padding-left: 18px;
          display: grid;
          gap: 4px;
        }

        form {
          display: grid;
          gap: 8px;
        }

        label {
          font-size: 0.95rem;
          font-weight: 700;
          color: #111827;
        }

        input {
          border: 1px solid #d5dbea;
          border-radius: 10px;
          padding: 10px 12px;
          font-size: 1rem;
        }

        button[type="submit"] {
          border: 0;
          border-radius: 10px;
          padding: 10px 12px;
          font-weight: 800;
          background: #f5c542;
          color: #0b0f1a;
          cursor: pointer;
        }

        .ok {
          color: #166534;
          font-weight: 700;
        }

        .error {
          margin: 0;
          color: #b91c1c;
          font-weight: 700;
        }
      `}</style>
    </div>
  );
}

export default function App({ Component, pageProps }) {
  const router = useRouter();

  useEffect(() => {
    const removeBuildFooterLine = () => {
      const footer = document.querySelector("footer, [role='contentinfo']");
      if (!footer) {
        return;
      }

      footer.querySelectorAll("p, div, span").forEach((node) => {
        const text = (node.textContent || "").trim();
        if (text.startsWith("Build:")) {
          node.remove();
        }
      });
    };

    removeBuildFooterLine();
    router.events.on("routeChangeComplete", removeBuildFooterLine);

    const observer = new MutationObserver(removeBuildFooterLine);
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      router.events.off("routeChangeComplete", removeBuildFooterLine);
      observer.disconnect();
    };
  }, [router.events]);

  const baseUrl = "https://gofieldwise.com";
  const path = (router.asPath || "/").split("?")[0].split("#")[0];
  const currentUrl = `${baseUrl}${path}`;

  const defaultMeta = {
    title: "GoFieldwise - AI Field Service Management for Home Service Businesses",
    description:
      "Never miss a customer. Automate every job-from first call to paid invoice. AI-powered scheduling, dispatch, and invoicing for contractors.",
    image: `${baseUrl}/og-image.png`,
  };

  const meta = {
    title: pageProps?.meta?.title || defaultMeta.title,
    description: pageProps?.meta?.description || defaultMeta.description,
    image: pageProps?.meta?.image || defaultMeta.image,
  };

  const softwareSchema = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "GoFieldwise",
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    description: "AI-powered field service management software for home service businesses",
    url: baseUrl,
    publisher: {
      "@type": "Organization",
      name: "GoFieldwise",
      url: baseUrl,
    },
    offers: {
      "@type": "Offer",
      price: "200",
      priceCurrency: "USD",
      priceSpecification: {
        "@type": "PriceSpecification",
        price: "200",
        priceCurrency: "USD",
        billingIncrement: "1",
        unitText: "MONTH",
      },
    },
    aggregateRating: {
      "@type": "AggregateRating",
      ratingValue: "4.9",
      ratingCount: "87",
      bestRating: "5",
      worstRating: "1",
    },
  };

  return (
    <>
      <Head>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="robots" content="index, follow" />
        <meta name="language" content="English" />

        <title>{meta.title}</title>
        <meta name="description" content={meta.description} />

        <meta property="og:type" content="website" />
        <meta property="og:url" content={currentUrl} />
        <meta property="og:title" content={meta.title} />
        <meta property="og:description" content={meta.description} />
        <meta property="og:image" content={meta.image} />
        <meta property="og:site_name" content="GoFieldwise" />

        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={meta.title} />
        <meta name="twitter:description" content={meta.description} />
        <meta name="twitter:image" content={meta.image} />

        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareSchema) }}
        />

        <link rel="icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="canonical" href={currentUrl} />
      </Head>

      <SiteNav />
      <Component {...pageProps} />
      <ExitAuditModal />
    </>
  );
}
