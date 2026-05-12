# Supabase SQL Migrations

This folder contains SQL-first migrations for Supabase Postgres.

## Phase A

Run:

- `20260511_phase_a_foundation.sql`

Creates core tables for billing + integrations:

- `organizations`
- `subscriptions`
- `connector_configs`
- `handoff_logs`

## How to apply

1. Open Supabase Dashboard -> SQL Editor.
2. Paste the migration SQL.
3. Run it.
4. Verify tables exist in Table Editor.

## Notes

- Tokens/secrets should be encrypted before storing in `connector_configs.secrets_encrypted`.
- Do not store plaintext passwords or raw API keys.
- This migration is idempotent and safe to re-run.
