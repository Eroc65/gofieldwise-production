import { useEffect, useState } from "react";
import { getCurrentUser, getPublicStatus } from "../lib/api";

const TOKEN_KEYS = ["fdp.dispatch.token", "access_token", "token"];

function readToken() {
  if (typeof window === "undefined") return "";
  for (const key of TOKEN_KEYS) {
    const value = window.localStorage.getItem(key);
    if (value) return value;
  }
  return "";
}

export default function ConnectCenterPage() {
  const [token, setToken] = useState("");
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState("Checking your operator session...");
  const [error, setError] = useState("");

  useEffect(() => {
    const storedToken = readToken();
    setToken(storedToken);

    if (!storedToken) {
      setMessage("No operator session found. Complete operator setup first.");
      return;
    }

    (async () => {
      try {
        const [me, publicStatus] = await Promise.all([
          getCurrentUser({ token: storedToken }),
          getPublicStatus().catch(() => null),
        ]);
        setUser(me);
        setStatus(publicStatus);
        setMessage("Operator session active.");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load operator session.");
        setMessage("Operator session could not be verified.");
      }
    })();
  }, []);

  function signOut() {
    TOKEN_KEYS.forEach((key) => window.localStorage.removeItem(key));
    window.localStorage.removeItem("gofieldwise_user");
    window.localStorage.removeItem("gofieldwise_org");
    window.location.href = "/operator/setup";
  }

  return (
    <main className="connectShell">
      <section className="hero">
        <p className="eyebrow">GoFieldWise Connect Center</p>
        <h1>Operator dashboard ready.</h1>
        <p className="intro">
          This is the authenticated landing page for new GoFieldWise operators after setup.
        </p>
      </section>

      <section className="panel">
        <div className="panelHeader">
          <div>
            <h2>Session</h2>
            <p>{message}</p>
          </div>
          {token ? <span className="badge success">JWT detected</span> : <span className="badge danger">No token</span>}
        </div>

        {error ? <p className="error">{error}</p> : null}

        {user ? (
          <div className="grid">
            <article>
              <span>Email</span>
              <strong>{user.email}</strong>
            </article>
            <article>
              <span>Role</span>
              <strong>{user.role}</strong>
            </article>
            <article>
              <span>Organization</span>
              <strong>#{user.organization_id}</strong>
            </article>
            <article>
              <span>API</span>
              <strong>{status?.ok === false ? "Needs attention" : "Reachable"}</strong>
            </article>
          </div>
        ) : (
          <div className="empty">
            <p>Complete operator setup with your one-time key to access Connect Center.</p>
            <a href="/operator/setup">Go to operator setup</a>
          </div>
        )}

        {user ? (
          <div className="actions">
            <a href="/platform">Platform settings</a>
            <a href="/leads">Lead center</a>
            <a href="/metrics">Metrics</a>
            <button type="button" onClick={signOut}>Sign out</button>
          </div>
        ) : null}
      </section>

      <style jsx>{`
        .connectShell {
          min-height: 100vh;
          background: #f5f1e8;
          color: #13231f;
          padding: 44px 20px;
        }
        .hero,
        .panel {
          width: min(980px, 100%);
          margin: 0 auto;
        }
        .hero {
          margin-bottom: 24px;
        }
        .eyebrow {
          color: #a66f00;
          font-size: 12px;
          font-weight: 900;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          margin: 0 0 10px;
        }
        h1 {
          color: #10231e;
          font-size: clamp(38px, 7vw, 72px);
          line-height: 0.95;
          margin: 0 0 12px;
        }
        .intro,
        .panel p,
        .empty p {
          color: #4f625c;
          line-height: 1.6;
        }
        .panel {
          background: #fff;
          border: 1px solid rgba(20, 35, 31, 0.12);
          border-radius: 18px;
          padding: clamp(20px, 4vw, 34px);
          box-shadow: 0 24px 70px rgba(24, 38, 35, 0.14);
        }
        .panelHeader {
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: flex-start;
          margin-bottom: 18px;
        }
        h2 {
          margin: 0 0 4px;
          color: #10231e;
        }
        .badge {
          border-radius: 999px;
          padding: 7px 11px;
          font-size: 12px;
          font-weight: 900;
          white-space: nowrap;
        }
        .success {
          background: #eef9f1;
          color: #135c2d;
        }
        .danger {
          background: #fff1ee;
          color: #9d2f19;
        }
        .error {
          background: #fff1ee;
          border: 1px solid rgba(157, 47, 25, 0.2);
          border-radius: 12px;
          color: #9d2f19;
          font-weight: 800;
          padding: 12px 14px;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 12px;
          margin: 20px 0;
        }
        article {
          background: #fffdf8;
          border: 1px solid rgba(19, 35, 31, 0.14);
          border-radius: 12px;
          padding: 14px;
          min-width: 0;
        }
        article span {
          display: block;
          color: #667a73;
          font-size: 12px;
          font-weight: 800;
          margin-bottom: 5px;
        }
        article strong {
          color: #10231e;
          overflow-wrap: anywhere;
        }
        .actions {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          margin-top: 20px;
        }
        a,
        button {
          border: 0;
          border-radius: 10px;
          background: #13231f;
          color: #fff;
          cursor: pointer;
          display: inline-flex;
          font: inherit;
          font-weight: 900;
          padding: 11px 14px;
          text-decoration: none;
        }
        button {
          background: #fff4de;
          color: #13231f;
        }
        .empty {
          background: #fffdf8;
          border: 1px dashed rgba(19, 35, 31, 0.22);
          border-radius: 14px;
          padding: 18px;
        }
        @media (max-width: 760px) {
          .grid {
            grid-template-columns: 1fr;
          }
          .panelHeader {
            display: grid;
          }
        }
      `}</style>
    </main>
  );
}
