-- 001_init.sql: Initial schema for AI Ops Hub

-- Users
CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text UNIQUE NOT NULL,
    name text,
    created_at timestamptz DEFAULT now()
);

-- Credentials
CREATE TABLE credentials (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL,
    label text,
    secret_ref text NOT NULL,
    scopes text[],
    last_validated_at timestamptz,
    created_at timestamptz DEFAULT now()
);

-- Agents
CREATE TABLE agents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    type text NOT NULL,
    status text,
    created_at timestamptz DEFAULT now()
);

-- Tasks
CREATE TABLE tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by uuid REFERENCES users(id),
    type text NOT NULL,
    status text NOT NULL,
    priority int DEFAULT 0,
    requested_action text,
    assigned_agent uuid REFERENCES agents(id),
    risk_level text,
    requires_approval boolean DEFAULT false,
    due_at timestamptz,
    created_at timestamptz DEFAULT now()
);

-- Task Steps
CREATE TABLE task_steps (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid REFERENCES tasks(id),
    step_order int,
    description text,
    status text,
    started_at timestamptz,
    ended_at timestamptz
);

-- Runs
CREATE TABLE runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid REFERENCES tasks(id),
    started_at timestamptz,
    ended_at timestamptz,
    result_status text,
    summary text,
    error_message text
);

-- Approvals
CREATE TABLE approvals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid REFERENCES tasks(id),
    action_type text,
    approval_status text,
    approved_by uuid REFERENCES users(id),
    approved_at timestamptz
);

-- Artifacts
CREATE TABLE artifacts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid REFERENCES tasks(id),
    type text,
    url text,
    created_at timestamptz DEFAULT now()
);

-- Audit Logs
CREATE TABLE audit_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id),
    action text,
    target_type text,
    target_id uuid,
    details jsonb,
    created_at timestamptz DEFAULT now()
);

-- Scheduled Jobs
CREATE TABLE scheduled_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid REFERENCES tasks(id),
    run_at timestamptz,
    status text,
    created_at timestamptz DEFAULT now()
);
