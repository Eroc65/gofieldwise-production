# AI Ops Hub Architecture

## Overview
- Control agent receives user requests, plans tasks, and routes to specialist workers.
- Workers execute domain-specific tasks (web, research, browser, Meta, X).
- Supabase provides managed Postgres, Auth, Storage, and Edge Functions.
- All risky actions require approval and are logged/audited.

## Key Flows
1. User request → Control agent → Task plan → Worker execution → Approval (if needed) → Artifacts/logs
2. Operator console provides task inbox, approvals, run log, and chat interface.

## Directory Structure
- apps/console: Operator dashboard (Next.js)
- apps/api: Webhook/API service (FastAPI or Supabase Edge Functions)
- workers/: Specialized agents
- packages/: Shared types, db, LLM, integrations
- supabase/: DB schema, migrations, functions
- docs/: Documentation

## Security
- Credentials and secrets are server-side only
- All agent actions are logged and auditable
- Approval required for risky actions
