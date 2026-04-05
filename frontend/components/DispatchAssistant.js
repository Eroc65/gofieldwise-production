import { useEffect, useMemo, useState } from "react";

import {
  checkSchedulingConflict,
  dispatchJob,
  getApiBase,
  getNextSlot,
  listJobs,
  listTechnicians,
  login,
  signup,
} from "../lib/api";

function toLocalInputValue(date) {
  const d = date instanceof Date ? date : new Date(date);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function prettyDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function DispatchAssistant() {
  const [token, setToken] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [jobId, setJobId] = useState("");
  const [technicianId, setTechnicianId] = useState("");
  const [jobs, setJobs] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [excludeJobId, setExcludeJobId] = useState("");
  const [scheduledTime, setScheduledTime] = useState(toLocalInputValue(new Date(Date.now() + 2 * 60 * 60 * 1000)));
  const [searchHours, setSearchHours] = useState(24);
  const [stepMinutes, setStepMinutes] = useState(30);
  const [bufferMinutes, setBufferMinutes] = useState(0);
  const [conflictResult, setConflictResult] = useState(null);
  const [slotResult, setSlotResult] = useState(null);
  const [dispatchResult, setDispatchResult] = useState(null);
  const [error, setError] = useState("");
  const [busyAction, setBusyAction] = useState("");

  const selectedIso = useMemo(() => new Date(scheduledTime).toISOString(), [scheduledTime]);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("fdp.dispatch.token") || "";
    const savedEmail = window.localStorage.getItem("fdp.dispatch.email") || "";
    if (savedToken) {
      setToken(savedToken);
    }
    if (savedEmail) {
      setAuthEmail(savedEmail);
    }
  }, []);

  useEffect(() => {
    if (token) {
      window.localStorage.setItem("fdp.dispatch.token", token);
    }
  }, [token]);

  useEffect(() => {
    if (authEmail) {
      window.localStorage.setItem("fdp.dispatch.email", authEmail);
    }
  }, [authEmail]);

  useEffect(() => {
    if (!token) {
      setJobs([]);
      setTechnicians([]);
      return;
    }
    void refreshLookups();
  }, [token]);

  async function withAction(name, fn) {
    setError("");
    setBusyAction(name);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyAction("");
    }
  }

  async function onCheckConflict() {
    await withAction("conflict", async () => {
      const result = await checkSchedulingConflict({
        token,
        technicianId: Number(technicianId),
        scheduledTime: selectedIso,
        excludeJobId,
        bufferMinutes,
      });
      setConflictResult(result);
    });
  }

  async function refreshLookups() {
    await withAction("lookup", async () => {
      const [jobList, techList] = await Promise.all([
        listJobs({ token }),
        listTechnicians({ token }),
      ]);
      setJobs(Array.isArray(jobList) ? jobList : []);
      setTechnicians(Array.isArray(techList) ? techList : []);
    });
  }

  async function onLogin() {
    await withAction("auth", async () => {
      if (!authEmail || !authPassword) {
        throw new Error("Email and password are required for login.");
      }
      const result = await login({
        email: authEmail,
        password: authPassword,
      });
      if (!result.access_token) {
        throw new Error("Login succeeded but no access token was returned.");
      }
      setToken(result.access_token);
    });
  }

  async function onSignupAndLogin() {
    await withAction("auth", async () => {
      if (!authEmail || !authPassword || !organizationName) {
        throw new Error("Email, password, and organization are required for signup.");
      }
      await signup({
        email: authEmail,
        password: authPassword,
        organizationName,
      });
      const result = await login({
        email: authEmail,
        password: authPassword,
      });
      if (!result.access_token) {
        throw new Error("Signup/login succeeded but no access token was returned.");
      }
      setToken(result.access_token);
    });
  }

  async function onSuggestSlot() {
    await withAction("slot", async () => {
      const result = await getNextSlot({
        token,
        technicianId: Number(technicianId),
        requestedTime: selectedIso,
        searchHours,
        stepMinutes,
        excludeJobId,
        bufferMinutes,
      });
      setSlotResult(result);
      if (result.next_available_time) {
        setScheduledTime(toLocalInputValue(result.next_available_time));
      }
    });
  }

  async function onDispatch(useSuggested) {
    await withAction("dispatch", async () => {
      if (!jobId) {
        throw new Error("Job ID is required for dispatch.");
      }
      const chosenTime = useSuggested && slotResult && slotResult.next_available_time
        ? slotResult.next_available_time
        : selectedIso;

      const result = await dispatchJob({
        token,
        jobId: Number(jobId),
        technicianId: Number(technicianId),
        scheduledTime: chosenTime,
      });
      setDispatchResult(result);
    });
  }

  return (
    <section className="dispatch-card">
      <header className="dispatch-head">
        <h2>Dispatch Assistant</h2>
        <p>Business window defaults: 8:00 AM to 7:00 PM Central, Monday to Friday.</p>
      </header>

      <div className="form-grid">
        <label>
          API Base
          <input value={getApiBase()} readOnly />
        </label>

        <label>
          Auth Email
          <input
            value={authEmail}
            onChange={(e) => setAuthEmail(e.target.value)}
            placeholder="owner@shop.com"
          />
        </label>

        <label>
          Auth Password
          <input
            type="password"
            value={authPassword}
            onChange={(e) => setAuthPassword(e.target.value)}
            placeholder="password"
          />
        </label>

        <label>
          Organization (for signup)
          <input
            value={organizationName}
            onChange={(e) => setOrganizationName(e.target.value)}
            placeholder="Acme HVAC"
          />
        </label>

        <label className="span-2">
          Bearer Token
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste JWT access token"
          />
        </label>

        <label>
          Job ID
          <input value={jobId} onChange={(e) => setJobId(e.target.value)} placeholder="42" />
        </label>

        <label>
          Pick Job
          <select value={jobId} onChange={(e) => setJobId(e.target.value)}>
            <option value="">Select a job</option>
            {jobs.map((job) => (
              <option key={job.id} value={String(job.id)}>
                #{job.id} {job.title} ({job.status})
              </option>
            ))}
          </select>
        </label>

        <label>
          Technician ID
          <input value={technicianId} onChange={(e) => setTechnicianId(e.target.value)} placeholder="7" />
        </label>

        <label>
          Pick Technician
          <select value={technicianId} onChange={(e) => setTechnicianId(e.target.value)}>
            <option value="">Select a technician</option>
            {technicians.map((tech) => (
              <option key={tech.id} value={String(tech.id)}>
                #{tech.id} {tech.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Exclude Job ID
          <input value={excludeJobId} onChange={(e) => setExcludeJobId(e.target.value)} placeholder="optional" />
        </label>

        <label>
          Requested Time
          <input
            type="datetime-local"
            value={scheduledTime}
            onChange={(e) => setScheduledTime(e.target.value)}
          />
        </label>

        <label>
          Search Hours
          <input
            type="number"
            min={1}
            max={168}
            value={searchHours}
            onChange={(e) => setSearchHours(Number(e.target.value))}
          />
        </label>

        <label>
          Step Minutes
          <input
            type="number"
            min={5}
            max={240}
            value={stepMinutes}
            onChange={(e) => setStepMinutes(Number(e.target.value))}
          />
        </label>

        <label>
          Buffer Minutes
          <input
            type="number"
            min={0}
            max={480}
            value={bufferMinutes}
            onChange={(e) => setBufferMinutes(Number(e.target.value))}
          />
        </label>
      </div>

      <div className="actions">
        <button type="button" onClick={onLogin} disabled={busyAction !== "" || !authEmail || !authPassword}>
          {busyAction === "auth" ? "Authorizing..." : "Login And Set Token"}
        </button>
        <button
          type="button"
          onClick={onSignupAndLogin}
          disabled={busyAction !== "" || !authEmail || !authPassword || !organizationName}
        >
          {busyAction === "auth" ? "Authorizing..." : "Signup + Login"}
        </button>
        <button
          type="button"
          onClick={refreshLookups}
          disabled={busyAction !== "" || !token}
        >
          {busyAction === "lookup" ? "Refreshing..." : "Refresh Jobs + Techs"}
        </button>
        <button type="button" onClick={onCheckConflict} disabled={busyAction !== "" || !token || !technicianId}>
          {busyAction === "conflict" ? "Checking..." : "Check Conflict"}
        </button>
        <button type="button" onClick={onSuggestSlot} disabled={busyAction !== "" || !token || !technicianId}>
          {busyAction === "slot" ? "Searching..." : "Suggest Next Slot"}
        </button>
        <button
          type="button"
          onClick={() => onDispatch(false)}
          disabled={busyAction !== "" || !token || !technicianId || !jobId}
        >
          {busyAction === "dispatch" ? "Dispatching..." : "Dispatch At Selected Time"}
        </button>
        <button
          type="button"
          onClick={() => onDispatch(true)}
          disabled={busyAction !== "" || !token || !technicianId || !jobId || !slotResult?.next_available_time}
        >
          {busyAction === "dispatch" ? "Dispatching..." : "Dispatch At Suggested Time"}
        </button>
      </div>

      {error ? <div className="panel error">{error}</div> : null}

      <div className="results-grid">
        <article className="panel">
          <h3>Conflict Check</h3>
          {conflictResult ? (
            <ul>
              <li>Conflict: {String(conflictResult.conflict)}</li>
              <li>Conflicting Job ID: {conflictResult.conflicting_job_id ?? "-"}</li>
              <li>Message: {conflictResult.message}</li>
            </ul>
          ) : (
            <p>No result yet.</p>
          )}
        </article>

        <article className="panel">
          <h3>Next Slot</h3>
          {slotResult ? (
            <ul>
              <li>Requested: {prettyDate(slotResult.requested_time)}</li>
              <li>Suggested: {prettyDate(slotResult.next_available_time)}</li>
              <li>Conflicts seen: {(slotResult.conflicting_job_ids || []).join(", ") || "none"}</li>
            </ul>
          ) : (
            <p>No result yet.</p>
          )}
        </article>

        <article className="panel">
          <h3>Dispatch Result</h3>
          {dispatchResult ? (
            <ul>
              <li>Job ID: {dispatchResult.id}</li>
              <li>Status: {dispatchResult.status}</li>
              <li>Technician: {dispatchResult.technician_id ?? "-"}</li>
              <li>Scheduled: {prettyDate(dispatchResult.scheduled_time)}</li>
            </ul>
          ) : (
            <p>No dispatch yet.</p>
          )}
        </article>
      </div>
    </section>
  );
}
