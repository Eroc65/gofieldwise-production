import Head from "next/head";
import { useEffect, useRef, useState } from "react";

import { getDemoTranscriptStreamUrl, startDemoCall } from "../lib/api";

function normalizeLines(transcript) {
  if (!Array.isArray(transcript)) return [];
  return transcript
    .map((line) => ({
      role: line.role || line.speaker || "agent",
      content: line.content || line.text || "",
    }))
    .filter((line) => line.content);
}

function errorMessage(err) {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;
  try {
    return JSON.stringify(err);
  } catch {
    return "Something went wrong starting the demo call.";
  }
}

export default function DemoPage() {
  const [form, setForm] = useState({ name: "", email: "", phone: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [callId, setCallId] = useState("");
  const [transcript, setTranscript] = useState([]);
  const [summary, setSummary] = useState(null);
  const streamRef = useRef(null);

  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.close();
    };
  }, []);

  function updateField(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function openTranscriptStream(nextCallId) {
    if (streamRef.current) streamRef.current.close();
    const source = new EventSource(getDemoTranscriptStreamUrl(nextCallId));
    streamRef.current = source;

    source.addEventListener("transcript", (event) => {
      const payload = JSON.parse(event.data);
      setTranscript(normalizeLines(payload.transcript));
    });

    source.addEventListener("call_ended", (event) => {
      const payload = JSON.parse(event.data);
      setSummary(payload.extraction || {});
      setNotice("Call complete. Your summary text is being sent.");
      source.close();
    });

    source.onerror = () => {
      setNotice("Call started. Waiting for Adrian's transcript...");
    };
  }

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    setSummary(null);
    setTranscript([]);

    try {
      const result = await startDemoCall(form);
      if (!result.call_started) {
        throw new Error(result.call_error || result.message || "Demo call could not be started.");
      }
      setCallId(result.call_sid);
      setNotice("Adrian is calling now. Keep this page open to watch the transcript.");
      openTranscriptStream(result.call_sid);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Head>
        <title>GoFieldwise Demo - Live Adrian Call</title>
        <meta
          name="description"
          content="Try a live GoFieldwise demo call with Adrian and watch the transcript appear in real time."
        />
      </Head>

      <main className="demo-page">
        <section className="hero">
          <a className="brand" href="/">GoFieldwise</a>
          <div className="hero-copy">
            <p className="eyebrow">Live Demo</p>
            <h1>Talk to Adrian and watch the call notes appear.</h1>
            <p>
              Enter your details and Adrian will call you from (602) 932-0967. The transcript appears here during the
              call, then you receive a summary text after the call ends.
            </p>
          </div>
        </section>

        <section className="demo-grid">
          <form className="demo-card" onSubmit={onSubmit}>
            <label>
              Your Name
              <input
                value={form.name}
                onChange={(event) => updateField("name", event.target.value)}
                placeholder="John Smith"
                autoComplete="name"
                required
              />
            </label>
            <label>
              Email Address
              <input
                type="email"
                value={form.email}
                onChange={(event) => updateField("email", event.target.value)}
                placeholder="john@example.com"
                autoComplete="email"
                required
              />
            </label>
            <label>
              Your Phone Number
              <input
                value={form.phone}
                onChange={(event) => updateField("phone", event.target.value)}
                placeholder="4055551234"
                autoComplete="tel"
                inputMode="tel"
                required
              />
            </label>

            <button type="submit" disabled={busy}>
              {busy ? "Starting Call..." : "Try Demo"}
            </button>
            <a className="secondary" href="tel:+16029320967">Call Instead: (602) 932-0967</a>
            {notice ? <p className="notice">{notice}</p> : null}
            {error ? <p className="error">{error}</p> : null}
            {callId ? <p className="call-id">Call ID: {callId}</p> : null}
          </form>

          <section className="demo-card transcript-card">
            <h2>Chat Display</h2>
            {transcript.length > 0 ? (
              <ul className="transcript">
                {transcript.map((line, index) => (
                  <li key={`${line.role}-${index}`} className={line.role === "user" ? "customer" : "adrian"}>
                    <strong>{line.role === "user" ? "Customer" : "Adrian"}:</strong> {line.content}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty">Transcript will appear here during the demo call.</p>
            )}

            {summary ? (
              <div className="summary">
                <h3>Summary Text Sent</h3>
                <dl>
                  <dt>Service</dt>
                  <dd>{summary.service_type || "Not captured"}</dd>
                  <dt>Address</dt>
                  <dd>{summary.address || "Not captured"}</dd>
                  <dt>Urgency</dt>
                  <dd>{summary.urgency || "Not captured"}</dd>
                  <dt>Preferred Time</dt>
                  <dd>{summary.preferred_time || "Not captured"}</dd>
                  <dt>Notes</dt>
                  <dd>{summary.notes || "No extra notes"}</dd>
                </dl>
              </div>
            ) : null}
          </section>
        </section>
      </main>

      <style jsx>{`
        .demo-page {
          min-height: 100vh;
          background: #f7f3ea;
          color: #101828;
          font-family: Arial, sans-serif;
        }
        .hero {
          background: #111827;
          color: white;
          padding: 28px max(24px, calc((100vw - 1100px) / 2));
        }
        .brand {
          color: #facc15;
          font-weight: 800;
          text-decoration: none;
        }
        .hero-copy {
          max-width: 760px;
          padding: 44px 0 28px;
        }
        .eyebrow {
          color: #facc15;
          font-weight: 800;
          margin: 0 0 10px;
        }
        h1 {
          font-size: 46px;
          line-height: 1.05;
          margin: 0 0 18px;
        }
        .hero p {
          font-size: 18px;
          line-height: 1.6;
        }
        .demo-grid {
          display: grid;
          grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
          gap: 24px;
          max-width: 1100px;
          margin: -18px auto 0;
          padding: 0 24px 64px;
        }
        .demo-card {
          background: white;
          border: 1px solid #d7dce8;
          border-radius: 8px;
          padding: 24px;
          box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
        }
        label {
          display: block;
          font-weight: 800;
          margin-bottom: 18px;
        }
        input {
          display: block;
          width: 100%;
          min-height: 48px;
          margin-top: 8px;
          border: 1px solid #cbd5e1;
          border-radius: 8px;
          padding: 0 14px;
          font-size: 16px;
        }
        button,
        .secondary {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-height: 44px;
          border-radius: 8px;
          padding: 0 18px;
          font-weight: 800;
          text-decoration: none;
          margin-right: 10px;
        }
        button {
          border: 0;
          background: #facc15;
          color: #111827;
          cursor: pointer;
        }
        button:disabled {
          opacity: 0.7;
          cursor: wait;
        }
        .secondary {
          border: 1px solid #d4a72c;
          color: #111827;
          background: #fff8d2;
        }
        .notice {
          color: #047857;
          font-weight: 700;
        }
        .error {
          color: #b42318;
          font-weight: 700;
        }
        .call-id,
        .empty {
          color: #64748b;
        }
        .transcript {
          list-style: none;
          padding: 0;
          margin: 0;
          display: grid;
          gap: 10px;
        }
        .transcript li {
          border-radius: 8px;
          padding: 12px;
          line-height: 1.5;
        }
        .adrian {
          background: #eef6ff;
        }
        .customer {
          background: #fff7dc;
        }
        .summary {
          border-top: 1px solid #e2e8f0;
          margin-top: 22px;
          padding-top: 18px;
        }
        dl {
          display: grid;
          grid-template-columns: 130px 1fr;
          gap: 8px 14px;
        }
        dt {
          font-weight: 800;
        }
        dd {
          margin: 0;
        }
        @media (max-width: 820px) {
          h1 {
            font-size: 34px;
          }
          .demo-grid {
            grid-template-columns: 1fr;
          }
          button,
          .secondary {
            width: 100%;
            margin: 0 0 10px;
          }
        }
      `}</style>
    </>
  );
}
