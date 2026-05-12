import { useEffect, useState } from "react";
import Head from "next/head";

const PLAN = {
  name: "GoFieldwise Pro",
  price: 200,
  interval: "month",
  features: [
    "Adrian AI answering calls 24/7",
    "Unlimited call capture",
    "Google Calendar integration",
    "Zapier / webhook dispatch",
    "Dispatch SMS summaries",
    "Follow-up task creation",
    "Priority support",
  ],
  trial: "14-day free trial included",
};

export default function BillingPage({ initialStatus = "inactive" }) {
  const [status, setStatus] = useState(initialStatus || "inactive");
  const [customerId, setCustomerId] = useState(null);
  const [nextBillingDate, setNextBillingDate] = useState(null);
  const [nextAmount, setNextAmount] = useState(null);
  const [currency, setCurrency] = useState(null);
  const [token, setToken] = useState("");
  const [statusLoading, setStatusLoading] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("fdp.dispatch.token") || "";
    setToken(savedToken);
    if (!savedToken) {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    async function loadStatus() {
      if (!token) return;

      setStatusLoading(true);
      setError(null);

      try {
        const res = await fetch("/api/stripe/status", {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        const data = await res.json();

        if (!active) return;

        if (!res.ok || !data?.ok) {
          setStatus("inactive");
          setCustomerId(null);
          setNextBillingDate(null);
          setNextAmount(null);
          setCurrency(null);
          return;
        }

        setStatus(data.status || "inactive");
        setCustomerId(data.customerId || null);
        setNextBillingDate(data.nextBillingDate || null);
        setNextAmount(typeof data.nextAmount === "number" ? data.nextAmount : null);
        setCurrency(data.currency || null);
      } catch {
        if (!active) return;
        setError("Could not load live billing status. Please refresh.");
      } finally {
        if (active) setStatusLoading(false);
      }
    }

    loadStatus();

    return () => {
      active = false;
    };
  }, [token]);

  async function startCheckout() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/stripe/checkout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ action: "checkout" }),
      });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        setError(data.error || "Failed to start checkout");
      }
    } catch (err) {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function openPortal() {
    setLoading(true);
    setError(null);
    if (!token && !customerId) {
      setError("Login first to open the billing portal for your account.");
      setLoading(false);
      return;
    }
    try {
      const res = await fetch("/api/stripe/checkout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ action: "portal", customerId: customerId || undefined }),
      });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        setError(data.error || "Failed to open billing portal");
      }
    } catch (err) {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const statusConfig = {
    active: {
      label: "Active",
      color: "#1d9e75",
      bg: "rgba(16,110,86,0.08)",
      dot: "#1d9e75",
      message: "Your subscription is active. Adrian is answering calls.",
    },
    trialing: {
      label: "Free Trial",
      color: "#ef9f27",
      bg: "rgba(239,159,39,0.1)",
      dot: "#ef9f27",
      message: "You're on your 14-day free trial. No charge until the trial ends.",
    },
    past_due: {
      label: "Payment Due",
      color: "#e24b4a",
      bg: "rgba(226,75,74,0.08)",
      dot: "#e24b4a",
      message: "Your last payment failed. Update your payment method to keep Adrian running.",
    },
    inactive: {
      label: "No Subscription",
      color: "#888",
      bg: "#f7f6f3",
      dot: "#aaa",
      message: "Start your subscription to activate Adrian and the connector hub.",
    },
  };

  const s = statusConfig[status] || statusConfig.inactive;
  const isActive = status === "active" || status === "trialing";

  return (
    <>
      <Head>
        <title>Billing — GoFieldwise</title>
      </Head>

      <div
        style={{
          minHeight: "100vh",
          background: "#f7f6f3",
          fontFamily: "'Inter', system-ui, sans-serif",
          padding: "48px 24px",
        }}
      >
        <div style={{ maxWidth: 680, margin: "0 auto" }}>
          <div style={{ marginBottom: 40 }}>
            <h1
              style={{
                fontSize: 28,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                margin: "0 0 8px",
                color: "#1a1a1a",
              }}
            >
              Billing
            </h1>
            <p style={{ fontSize: 15, color: "#666", margin: 0 }}>
              Manage your GoFieldwise subscription and payment method.
            </p>
          </div>

          <div
            style={{
              background: "#fff",
              border: "1px solid #e5e3dc",
              borderRadius: 16,
              padding: "28px 32px",
              marginBottom: 24,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                flexWrap: "wrap",
                gap: 16,
                marginBottom: 24,
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: "#aaa",
                    marginBottom: 6,
                  }}
                >
                  Current plan
                </div>
                <div style={{ fontSize: 22, fontWeight: 700, color: "#1a1a1a" }}>{PLAN.name}</div>
                <div style={{ fontSize: 15, color: "#888", marginTop: 4 }}>
                  ${PLAN.price}/{PLAN.interval}
                </div>
              </div>

              <span
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  background: s.bg,
                  color: s.color,
                  fontSize: 13,
                  fontWeight: 600,
                  padding: "6px 14px",
                  borderRadius: 100,
                }}
              >
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    background: s.dot,
                    display: "inline-block",
                  }}
                />
                {s.label}
              </span>
            </div>

            <div
              style={{
                background: s.bg,
                borderRadius: 10,
                padding: "12px 16px",
                fontSize: 14,
                color: s.color,
                marginBottom: 24,
              }}
            >
              {statusLoading ? "Loading live billing status..." : s.message}
            </div>

            {nextBillingDate && nextAmount !== null && (
              <div
                style={{
                  background: "#f7f6f3",
                  border: "1px solid #e5e3dc",
                  borderRadius: 10,
                  padding: "12px 16px",
                  fontSize: 14,
                  color: "#444",
                  marginBottom: 16,
                }}
              >
                Next billing: {formatMoney(nextAmount, currency)} on {formatDate(nextBillingDate)}
              </div>
            )}

            {error && (
              <div
                style={{
                  background: "rgba(226,75,74,0.08)",
                  border: "1px solid rgba(226,75,74,0.2)",
                  borderRadius: 8,
                  padding: "10px 14px",
                  fontSize: 13,
                  color: "#e24b4a",
                  marginBottom: 16,
                }}
              >
                {error}
              </div>
            )}

            {isActive ? (
              <button onClick={openPortal} disabled={loading} style={buttonStyle("outline", loading)}>
                {loading ? "Opening portal…" : "Manage subscription"}
              </button>
            ) : (
              <button onClick={startCheckout} disabled={loading} style={buttonStyle("primary", loading)}>
                {loading ? "Loading…" : `Start free trial — $${PLAN.price}/mo after 14 days`}
              </button>
            )}
          </div>

          <div
            style={{
              background: "#fff",
              border: "1px solid #e5e3dc",
              borderRadius: 16,
              padding: "28px 32px",
            }}
          >
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: "#aaa",
                marginBottom: 20,
              }}
            >
              What's included
            </div>
            <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
              {PLAN.features.map((f, i) => (
                <li
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "10px 0",
                    borderBottom: i < PLAN.features.length - 1 ? "1px solid #f0ede6" : "none",
                    fontSize: 15,
                    color: "#444",
                  }}
                >
                  <span style={{ color: "#1d9e75", fontWeight: 700, flexShrink: 0 }}>✓</span>
                  {f}
                </li>
              ))}
            </ul>
            <div
              style={{
                marginTop: 20,
                fontSize: 13,
                color: "#888",
                fontStyle: "italic",
              }}
            >
              {PLAN.trial}
            </div>
          </div>

          <div style={{ textAlign: "center", marginTop: 32, fontSize: 14, color: "#888" }}>
            Questions about billing?{" "}
            <a href="mailto:hello@gofieldwise.com" style={{ color: "#1a1a1a", fontWeight: 500 }}>
              hello@gofieldwise.com
            </a>
          </div>
        </div>
      </div>
    </>
  );
}

function formatDate(isoString) {
  const dt = new Date(isoString);
  if (Number.isNaN(dt.getTime())) return "-";
  return dt.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatMoney(amountInCents, currency = "usd") {
  const normalizedCurrency = String(currency || "usd").toUpperCase();
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: normalizedCurrency,
  }).format((amountInCents || 0) / 100);
}

function buttonStyle(variant, disabled) {
  const base = {
    padding: "13px 24px",
    borderRadius: 10,
    fontSize: 15,
    fontWeight: 600,
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.6 : 1,
    border: "none",
    transition: "opacity 0.15s",
    width: "100%",
  };
  if (variant === "primary") {
    return { ...base, background: "#0d0d0d", color: "#fff" };
  }
  return {
    ...base,
    background: "transparent",
    color: "#1a1a1a",
    border: "1.5px solid #d4d2ca",
  };
}
