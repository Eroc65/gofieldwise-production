-- GoFieldwise Supabase Foundation (Phase A)
-- Safe to run multiple times (uses IF NOT EXISTS where possible)
-- Creates:
--   organizations
--   subscriptions
--   connector_configs
--   handoff_logs

-- Required for gen_random_uuid()
create extension if not exists pgcrypto;

-- ===== organizations =====
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text unique,
  owner_email text,
  billing_email text,
  stripe_customer_id text unique,
  stripe_subscription_id text unique,
  subscription_status text not null default 'inactive',
  plan_code text default 'gofieldwise_pro_200',
  is_active boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_organizations_subscription_status
  on public.organizations (subscription_status);

-- ===== subscriptions =====
create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  provider text not null default 'stripe',
  provider_subscription_id text not null,
  provider_customer_id text,
  status text not null default 'inactive',
  price_id text,
  current_period_start timestamptz,
  current_period_end timestamptz,
  cancel_at timestamptz,
  canceled_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (provider, provider_subscription_id)
);

create index if not exists idx_subscriptions_org
  on public.subscriptions (organization_id);

create index if not exists idx_subscriptions_status
  on public.subscriptions (status);

-- ===== connector_configs =====
create table if not exists public.connector_configs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  provider text not null,
  status text not null default 'disconnected',
  auth_type text,
  -- Store encrypted token blobs/secret refs only, never plaintext credentials.
  secrets_encrypted jsonb not null default '{}'::jsonb,
  settings jsonb not null default '{}'::jsonb,
  scope text,
  last_synced_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, provider)
);

create index if not exists idx_connector_configs_org
  on public.connector_configs (organization_id);

create index if not exists idx_connector_configs_provider
  on public.connector_configs (provider);

create index if not exists idx_connector_configs_status
  on public.connector_configs (status);

-- ===== handoff_logs =====
create table if not exists public.handoff_logs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  connector_config_id uuid references public.connector_configs(id) on delete set null,
  provider text not null,
  direction text not null default 'outbound', -- outbound | inbound
  event_type text not null default 'lead_handoff',
  status text not null default 'queued', -- queued | success | failed | skipped
  idempotency_key text,
  request_payload jsonb not null default '{}'::jsonb,
  response_payload jsonb not null default '{}'::jsonb,
  error_message text,
  requested_at timestamptz not null default now(),
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_handoff_logs_org
  on public.handoff_logs (organization_id);

create index if not exists idx_handoff_logs_status
  on public.handoff_logs (status);

create index if not exists idx_handoff_logs_requested_at
  on public.handoff_logs (requested_at desc);

create unique index if not exists uq_handoff_logs_provider_idempotency
  on public.handoff_logs (organization_id, provider, idempotency_key)
  where idempotency_key is not null;

-- ===== subscription_events (webhook diagnostics) =====
create table if not exists public.subscription_events (
  id uuid primary key default gen_random_uuid(),
  stripe_event_id text,
  event_type text,
  org_id uuid references public.organizations(id) on delete set null,
  payload jsonb not null default '{}'::jsonb,
  error text,
  created_at timestamptz not null default now()
);

create index if not exists idx_subscription_events_created_at
  on public.subscription_events (created_at desc);

create unique index if not exists uq_subscription_events_stripe_event_id
  on public.subscription_events (stripe_event_id)
  where stripe_event_id is not null;
