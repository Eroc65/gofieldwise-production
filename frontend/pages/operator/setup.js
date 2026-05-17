import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/router";
import { redeemOperatorInvite, verifyOperatorInvite } from "../../lib/api";

const TOKEN_KEY = "fdp.dispatch.token";
const EMAIL_KEY = "fdp.dispatch.email";

const initialForm = {
  key: "",
  email: "",
  password: "",
  confirmPassword: "",
  ownerName: "",
  businessName: "",
  phone: "",
};

export default function OperatorSetupPage() {
  const router = useRouter();
  const [form, setForm] = useState(initialForm);
  const [invite, setInvite] = useState(null);
  const [status, setStatus] = useState("Enter your operator key to begin.");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const keyFromQuery = useMemo(() => {
    const raw = router.query?.key;
    return Array.isArray(raw) ? raw[0] : raw || "";
  }, [router.query]);

  useEffect(() => {
    if (!keyFromQuery) return;
    setForm((prev) => ({ ...prev, key: keyFromQuery }));
  }, [keyFromQuery]);

  useEffect(() => {
    if (!keyFromQuery) return;
    void onVerify(keyFromQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [keyFromQuery]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onVerify(keyOverride) {
    const key = (keyOverride || form.key).trim();
    if (!key) {
      setError("Enter your operator key first.");
      return;
    }

    setBusy(true);
    setError("");
    setStatus("Checking operator key...");
    try {
      const result = await verifyOperatorInvite({ operatorKey: key });
      setInvite(result);
      setForm((prev) => ({
        ...prev,
        key,
        email: prev.email || result.email || "",
        ownerName: prev.ownerName || result.owner_name || "",
        businessName: prev.businessName || result.organization_name || result.business_name || "",
        phone: prev.phone || result.phone || "",
      }));
      setStatus("Operator key verified. Create your owner login below.");
    } catch (err) {
      setInvite(null);
      setError(err instanceof Error ? err.message : "Could not verify operator key.");
      setStatus("Operator key could not be verified.");
    }
    setBusy(false);
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");

    if (!form.key.trim()) {
      setError("Operator key is required.");
      return;
    }
    if (!form.email.trim()) {
      setError("Email is required.");
      return;
    }
    if (!form.ownerName.trim()) {
      setError("Owner name is required.");
      return;
    }
    if (!form.businessName.trim()) {
      setError("Business name is required.");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setBusy(true);
    setStatus("Creating your GoFieldWise owner account...");
    try {
      const result = await redeemOperatorInvite({
        operatorKey: form.key.trim(),
        email: form.email.trim(),
        password: form.password,
        confirmPassword: form.confirmPassword,
        ownerName: form.ownerName.trim(),
        businessName: form.businessName.trim(),
        phone: form.phone.trim(),
      });

      if (!result.access_token) {
        throw new Error("Setup succeeded but no login token was returned.");
      }

      window.localStorage.setItem(TOKEN_KEY, result.access_token);
      window.localStorage.setItem(EMAIL_KEY, form.email.trim());
      window.localStorage.setItem("token", result.access_token);
      window.localStorage.setItem("access_token", result.access_token);
      window.localStorage.setItem("gofieldwise_user", JSON.stringify(result.user || {}));
      window.localStorage.setItem("gofieldwise_org", JSON.stringify(result.organization || {}));
      setStatus("Setup complete. Sending you to Connect Center...");
      router.push(result.redirect_to || "/connect-center");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not complete operator setup.");
      setStatus("Setup could not be completed.");
    }
    setBusy(false);
  }

  return (
    <main className="setupShell">
      <section className="setupCard">
        <div className="eyebrow">GoFieldWise Operator Setup</div>
        <h1>Create your owner login</h1>
        <p className="intro">
          Enter the one-time operator key from checkout, then create the FastAPI login that Connect Center uses.
        </p>

        <form onSubmit={onSubmit}>
          <label>
            Operator key
            <div className="keyRow">
              <input
                value={form.key}
                onChange={(event) => updateField("key", event.target.value)}
                placeholder="gfw_op_..."
                autoComplete="off"
              />
              <button type="button" onClick={() => onVerify()} disabled={busy || !form.key.trim()}>
                Verify
              </button>
            </div>
          </label>

          {invite ? (
            <div className="verified">
              <strong>Key verified</strong>
              <span>{invite.organization_name || invite.business_name || "Business details ready"} {invite.expires_at ? `- expires ${new Date(invite.expires_at).toLocaleDateString()}` : ""}</span>
            </div>
          ) : null}

          <div className="grid">
            <label>
              Owner name
              <input value={form.ownerName} onChange={(event) => updateField("ownerName", event.target.value)} autoComplete="name" />
            </label>
            <label>
              Business name
              <input value={form.businessName} onChange={(event) => updateField("businessName", event.target.value)} autoComplete="organization" />
            </label>
          </div>

          <div className="grid">
            <label>
              Email
              <input type="email" value={form.email} onChange={(event) => updateField("email", event.target.value)} autoComplete="email" />
            </label>
            <label>
              Phone
              <input value={form.phone} onChange={(event) => updateField("phone", event.target.value)} autoComplete="tel" />
            </label>
          </div>

          <div className="grid">
            <label>
              Password
              <input type="password" value={form.password} onChange={(event) => updateField("password", event.target.value)} autoComplete="new-password" />
            </label>
            <label>
              Confirm password
              <input type="password" value={form.confirmPassword} onChange={(event) => updateField("confirmPassword", event.target.value)} autoComplete="new-password" />
            </label>
          </div>

          {error ? <p className="error">{error}</p> : <p className="status">{status}</p>}

          <button className="submit" type="submit" disabled={busy}>
            {busy ? "Working..." : "Finish setup"}
          </button>
        </form>
      </section>

      <style jsx>{`
        .setupShell {
          min-height: 100vh;
          background: #f5f1e8;
          color: #13231f;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 32px 18px;
        }
        .setupCard {
          width: min(760px, 100%);
          background: #ffffff;
          border: 1px solid rgba(20, 35, 31, 0.12);
          border-radius: 18px;
          box-shadow: 0 24px 70px rgba(24, 38, 35, 0.14);
          padding: clamp(24px, 5vw, 42px);
        }
        .eyebrow {
          color: #a66f00;
          font-size: 12px;
          font-weight: 800;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          margin-bottom: 10px;
        }
        h1 {
          font-size: clamp(32px, 6vw, 52px);
          line-height: 1;
          margin: 0 0 12px;
          color: #10231e;
        }
        .intro {
          color: #4f625c;
          font-size: 16px;
          line-height: 1.6;
          margin: 0 0 26px;
        }
        form {
          display: grid;
          gap: 18px;
        }
        label {
          display: grid;
          gap: 7px;
          color: #243a34;
          font-size: 13px;
          font-weight: 800;
        }
        input {
          width: 100%;
          box-sizing: border-box;
          border: 1px solid rgba(19, 35, 31, 0.18);
          border-radius: 10px;
          padding: 12px 13px;
          font-size: 15px;
          color: #13231f;
          background: #fffdf8;
        }
        input:focus {
          outline: 2px solid rgba(204, 140, 18, 0.35);
          border-color: #b47a00;
        }
        .keyRow {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 10px;
        }
        .grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
        }
        button {
          border: 0;
          border-radius: 10px;
          background: #13231f;
          color: #fff;
          font-weight: 800;
          padding: 12px 16px;
          cursor: pointer;
        }
        button:disabled {
          cursor: not-allowed;
          opacity: 0.62;
        }
        .submit {
          background: #c88a10;
          color: #10231e;
          font-size: 16px;
          padding: 14px 18px;
        }
        .verified {
          display: grid;
          gap: 3px;
          border: 1px solid rgba(26, 126, 70, 0.22);
          background: #eef9f1;
          color: #135c2d;
          border-radius: 12px;
          padding: 12px 14px;
          font-size: 13px;
        }
        .verified span,
        .status {
          color: #4f625c;
          font-size: 13px;
          margin: 0;
        }
        .error {
          background: #fff1ee;
          color: #9d2f19;
          border: 1px solid rgba(157, 47, 25, 0.2);
          border-radius: 12px;
          padding: 11px 13px;
          margin: 0;
          font-size: 13px;
          font-weight: 700;
        }
        @media (max-width: 680px) {
          .grid,
          .keyRow {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </main>
  );
}
