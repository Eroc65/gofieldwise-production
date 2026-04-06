const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";

export function getApiBase() {
  return API_BASE;
}

export async function signup({ email, password, organizationName }) {
  return apiFetch("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      organization_name: organizationName,
    }),
  });
}

export async function login({ email, password }) {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);

  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload && payload.detail ? payload.detail : `HTTP ${response.status}`;
    throw new Error(String(detail));
  }

  return payload;
}

export async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload && payload.detail ? payload.detail : `HTTP ${response.status}`;
    throw new Error(String(detail));
  }

  return payload;
}

export async function checkSchedulingConflict({ token, technicianId, scheduledTime, excludeJobId, bufferMinutes }) {
  const query = new URLSearchParams({
    technician_id: String(technicianId),
    scheduled_time: scheduledTime,
  });
  if (excludeJobId != null && excludeJobId !== "") {
    query.set("exclude_job_id", String(excludeJobId));
  }
  if (bufferMinutes != null && bufferMinutes !== "") {
    query.set("buffer_minutes", String(bufferMinutes));
  }

  return apiFetch(`/api/jobs/scheduling/conflict?${query.toString()}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNextSlot({
  token,
  technicianId,
  requestedTime,
  searchHours,
  stepMinutes,
  excludeJobId,
  bufferMinutes,
}) {
  const query = new URLSearchParams({
    technician_id: String(technicianId),
    requested_time: requestedTime,
    search_hours: String(searchHours),
    step_minutes: String(stepMinutes),
  });
  if (excludeJobId != null && excludeJobId !== "") {
    query.set("exclude_job_id", String(excludeJobId));
  }
  if (bufferMinutes != null && bufferMinutes !== "") {
    query.set("buffer_minutes", String(bufferMinutes));
  }

  return apiFetch(`/api/jobs/scheduling/next-slot?${query.toString()}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function dispatchJob({ token, jobId, technicianId, scheduledTime }) {
  return apiFetch(`/api/jobs/${jobId}/dispatch`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      technician_id: Number(technicianId),
      scheduled_time: scheduledTime,
    }),
  });
}

export async function markJobOnMyWay({ token, jobId }) {
  return apiFetch(`/api/jobs/${jobId}/on-my-way`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function markJobStarted({ token, jobId }) {
  return apiFetch(`/api/jobs/${jobId}/start`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function completeJob({ token, jobId, completionNotes }) {
  return apiFetch(`/api/jobs/${jobId}/complete`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ completion_notes: completionNotes || null }),
  });
}

export async function getJobTimeline({ token, jobId }) {
  return apiFetch(`/api/jobs/${jobId}/timeline`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function submitPublicLeadIntake({
  intakeKey,
  orgId,
  name,
  phone,
  email,
  service,
  company,
  details,
}) {
  const serviceLine = service ? `Service interest: ${service}` : "";
  const companyLine = company ? `Business: ${company}` : "";
  const detailBlock = details ? `Details: ${details}` : "";
  const rawMessage = [serviceLine, companyLine, detailBlock].filter(Boolean).join("\n");
  const route = intakeKey
    ? `/api/leads/intake/by-key/${encodeURIComponent(intakeKey)}`
    : `/api/leads/intake/${orgId}`;

  return apiFetch(route, {
    method: "POST",
    body: JSON.stringify({
      name: name || null,
      phone: phone || null,
      email: email || null,
      source: "web_form",
      raw_message: rawMessage || null,
    }),
  });
}

export async function listLeads({ token }) {
  return apiFetch("/api/leads", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getCurrentUser({ token }) {
  return apiFetch("/api/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateLeadStatus({ token, leadId, status }) {
  return apiFetch(`/api/leads/${leadId}/status`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ status }),
  });
}

export async function qualifyLead({
  token,
  leadId,
  emergency,
  budgetConfirmed,
  requestedWithin48h,
  serviceCategory,
}) {
  return apiFetch(`/api/leads/${leadId}/qualify`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      emergency: Boolean(emergency),
      budget_confirmed: Boolean(budgetConfirmed),
      requested_within_48h: Boolean(requestedWithin48h),
      service_category: serviceCategory || null,
    }),
  });
}

export async function bookLead({ token, leadId, technicianId, scheduledTime }) {
  return apiFetch(`/api/leads/${leadId}/book`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      technician_id: Number(technicianId),
      scheduled_time: scheduledTime,
    }),
  });
}

export async function getLeadConversionMetrics({ token, days = 7 }) {
  const query = new URLSearchParams({ days: String(days) });
  return apiFetch(`/api/reports/lead-conversion?${query.toString()}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getLeadActivity({ token, leadId, action, sinceHours }) {
  const query = new URLSearchParams();
  if (action) {
    query.set("action", action);
  }
  if (sinceHours != null && sinceHours !== "") {
    query.set("since_hours", String(sinceHours));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiFetch(`/api/leads/${leadId}/activity${suffix}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listOrganizationUsers({ token }) {
  return apiFetch("/api/auth/users", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateUserRole({ token, userId, role }) {
  return apiFetch(`/api/auth/users/${userId}/role`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ role }),
  });
}

export async function getRoleAuditLog({ token, limit = 100, actorUserId, targetUserId, days }) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (actorUserId != null && actorUserId !== "") {
    query.set("actor_user_id", String(actorUserId));
  }
  if (targetUserId != null && targetUserId !== "") {
    query.set("target_user_id", String(targetUserId));
  }
  if (days != null && days !== "") {
    query.set("days", String(days));
  }

  return apiFetch(`/api/auth/users/role-audit?${query.toString()}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export function getRoleAuditExportUrl({ limit = 500, actorUserId, targetUserId, days }) {
  const query = new URLSearchParams({ limit: String(limit) });
  if (actorUserId != null && actorUserId !== "") {
    query.set("actor_user_id", String(actorUserId));
  }
  if (targetUserId != null && targetUserId !== "") {
    query.set("target_user_id", String(targetUserId));
  }
  if (days != null && days !== "") {
    query.set("days", String(days));
  }
  return `${API_BASE}/api/auth/users/role-audit/export.csv?${query.toString()}`;
}

export async function listJobs({ token }) {
  return apiFetch("/api/jobs", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listTechnicians({ token }) {
  return apiFetch("/api/technicians", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
