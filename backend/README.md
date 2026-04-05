# FrontDesk Pro Backend

This is the FastAPI backend for FrontDesk Pro.

- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic (migrations)
- PostgreSQL


## Structure
- `app/` — Main application code
- `alembic/` — DB migrations
- `tests/` — Backend tests
- `agent_runtime/` — Autonomous orchestration loop primitives (state, policies, dispatch contract, orchestrator)

## Auth & Organization Vertical Slice

- **User model/schema:** `app/schemas/user.py`, `app/models/user.py`
- **Organization model/schema:** `app/schemas/organization.py`, `app/models/organization.py`
- **Membership:** `organization_id` field on user
- **Storage:** signup, login, and current-organization resolution are DB-backed through SQLAlchemy
- **Signup/Login endpoints:** `/api/auth/signup`, `/api/auth/login`
- **Protected route pattern:** `/api/protected` (requires Bearer token)
- **Current-organization context:** `/api/auth/org` (returns org for current user)
- **Authenticated test endpoint:** `/api/protected`

### Example Usage

**Signup:**
POST `/api/auth/signup` { email, password, organization_name }

**Login:**
POST `/api/auth/login` (OAuth2 form: username=email, password)

**Get current user:**
GET `/api/auth/me` (Bearer token)
- includes `role` (`owner`, `admin`, `dispatcher`, `technician`)

**Organization users (role admins only):**
- GET `/api/auth/users` (Bearer token; owner/admin only)
- PATCH `/api/auth/users/{user_id}/role` with `{ role }` (owner/admin only)

**Get current org:**
GET `/api/auth/org` (Bearer token)

**Protected test route:**
GET `/api/protected` (Bearer token)

**Lead booking workflow:**
POST `/api/leads/{lead_id}/book` (Bearer token) with `{ scheduled_time, technician_id }`
- role-gated to `owner`, `admin`, `dispatcher`

**Lead qualification workflow:**
POST `/api/leads/{lead_id}/qualify` (Bearer token)
- role-gated to `owner`, `admin`, `dispatcher`

**Lead activity audit trail:**
- GET `/api/leads/{lead_id}/activity` (Bearer token)
	- optional query filters: `action`, `since_hours` (1-720)

**Public intake routing options:**
- POST `/api/leads/intake/{org_id}`
- POST `/api/leads/intake/by-key/{intake_key}`
- POST `/api/leads/intake/missed-call/{org_id}`
- POST `/api/leads/intake/missed-call/by-key/{intake_key}`
- GET `/api/auth/org` returns `intake_key` for authenticated org admins

**Operator metrics reporting:**
- GET `/api/reports/lead-conversion?days=7` (auth required, days 1-30)
	- includes `recommended_next_action` for operator prioritization

**Schedule readiness workflow:**
- GET `/api/jobs/scheduling/conflict` with query: `technician_id`, `scheduled_time`, optional `exclude_job_id`, `buffer_minutes`
- GET `/api/jobs/scheduling/next-slot` with query: `technician_id`, `requested_time`, optional `search_hours`, `step_minutes`, `exclude_job_id`, `buffer_minutes`
- PATCH `/api/jobs/{job_id}/dispatch` with `{ technician_id, scheduled_time }` and optional query `buffer_minutes`
- technician availability defaults: 8:00 AM to 7:00 PM Central, Monday to Friday

**Job lifecycle quick-actions (Sprint A):**
- PATCH `/api/jobs/{job_id}/on-my-way`
- PATCH `/api/jobs/{job_id}/start`
- PATCH `/api/jobs/{job_id}/complete` with optional `{ completion_notes }`
- GET `/api/jobs/{job_id}/timeline`

## Setup
1. Install Python 3.11+
2. `pip install -r requirements.txt`
3. `uvicorn app.main:app --reload --port 8001`
	- API docs: http://localhost:8001/docs

## Validation
- `pytest -q`
- `pytest -q tests/test_dispatch_flow_integration.py tests/test_dispatch.py -k "lifecycle_quick_actions_require_valid_order or conflict_next_slot_then_dispatch"`
- `python scripts/smoke_auth.py`
- `python scripts/smoke_schedule_readiness.py`
- `python scripts/smoke_collections_readiness.py`

## Agent Runtime Invocation
- Runtime entrypoints:
	- `python -m agent_runtime`
	- `python -m agent_runtime.run_once`
- Model backend is OpenAI-compatible chat completions and uses these env vars:
	- `AGENT_MODEL_BASE_URL` (example: `http://localhost:1234/v1` or `https://api.openai.com/v1`)
	- `AGENT_MODEL_API_KEY`
	- `AGENT_MODEL_NAME` (example: `gpt-4.1-mini`)
	- `AGENT_MODEL_TIMEOUT_SECONDS` (optional, default `120`)
	- `AGENT_MODEL_TEMPERATURE` (optional, default `0.1`)
	- `AGENT_MODEL_MAX_TOKENS` (optional, default `4000`)
	- `AGENT_MODEL_AUTORECOVER` (optional, default `1`)
	- `AGENT_MODEL_HEALTH_PATH` (optional, default `/models`)
	- `AGENT_MODEL_PRECHECK_TIMEOUT_SECONDS` (optional, default `4`)
	- `AGENT_MODEL_RECOVERY_SCRIPT_TIMEOUT_SECONDS` (optional, default `60`)
	- `AGENT_MODEL_START_CMD` (optional bootstrap command for backend start)
- Tool executor policy env var:
	- `AGENT_TOOL_MODE` (default `dev`): `readonly`, `test`, `dev`, `deploy`, `production_safe`
	- `AGENT_ALLOWED_COMMAND_PREFIXES` (comma-separated command prefixes)
	- default allowlist includes: `python`, `pytest`, `alembic`, `git status`, `git rev-parse`, `git branch`, `rg`, `grep`, `cat`, `head`, `tail`, `sed`, `make`, and test/run commands for npm/pnpm/yarn.
	- mode behavior:
		- `readonly`: inspect/list/search only
		- `test`: read/list/search + test commands
		- `dev`: read/write/append + safe dev commands
		- `deploy`: dev capabilities plus deployment-related command prefixes (`docker compose`, `render`)
		- `production_safe`: read/list/search + non-destructive validate/check commands
- Automatic mode resolver picks mode per step based on role and objective:
	- `planner`, `architect`, `reviewer` -> `readonly`
	- `backend_engineer`, `frontend_engineer`, `docs_engineer` -> `dev`
	- `qa_engineer` -> `test` for validation objectives
	- deploy/release objectives -> `deploy`
	- live/prod/health/metrics/reconcile objectives -> `production_safe`
- Example (bash):
	- `export AGENT_MODEL_BASE_URL="http://localhost:1234/v1"`
	- `export AGENT_MODEL_API_KEY="lm-studio"`
	- `export AGENT_MODEL_NAME="gpt-4.1-mini"`
	- `export AGENT_MODEL_TIMEOUT_SECONDS="120"`
	- `export AGENT_MODEL_TEMPERATURE="0.1"`
	- `export AGENT_MODEL_MAX_TOKENS="4000"`
	- `export AGENT_MODEL_AUTORECOVER="1"`
	- `export AGENT_MODEL_HEALTH_PATH="/models"`
	- `export AGENT_MODEL_PRECHECK_TIMEOUT_SECONDS="4"`
	- `export AGENT_MODEL_RECOVERY_SCRIPT_TIMEOUT_SECONDS="60"`
	- `export AGENT_TOOL_MODE="dev"`
	- `export AGENT_ALLOWED_COMMAND_PREFIXES="python,pytest,alembic,git status,git rev-parse,git branch,ls,pwd,rg,grep,cat,head,tail,sed,make,npm test,npm run,pnpm test,pnpm run,yarn test,yarn run"`
	- `python -m agent_runtime.run_once`
- Example (PowerShell):
	- `$env:AGENT_MODEL_BASE_URL="http://localhost:1234/v1"`
	- `$env:AGENT_MODEL_API_KEY="lm-studio"`
	- `$env:AGENT_MODEL_NAME="gpt-4.1-mini"`
	- `$env:AGENT_MODEL_TIMEOUT_SECONDS="120"`
	- `$env:AGENT_MODEL_TEMPERATURE="0.1"`
	- `$env:AGENT_MODEL_MAX_TOKENS="4000"`
	- `$env:AGENT_MODEL_AUTORECOVER="1"`
	- `$env:AGENT_MODEL_HEALTH_PATH="/models"`
	- `$env:AGENT_MODEL_PRECHECK_TIMEOUT_SECONDS="4"`
	- `$env:AGENT_MODEL_RECOVERY_SCRIPT_TIMEOUT_SECONDS="60"`
	- `$env:AGENT_TOOL_MODE="dev"`
	- `$env:AGENT_ALLOWED_COMMAND_PREFIXES="python,pytest,alembic,git status,git rev-parse,git branch,ls,pwd,rg,grep,cat,head,tail,sed,make,npm test,npm run,pnpm test,pnpm run,yarn test,yarn run"`
	- `python -m agent_runtime.run_once`

- Runtime preflight behavior:
	- Probes `AGENT_MODEL_BASE_URL + AGENT_MODEL_HEALTH_PATH` before each model request.
	- If unavailable and autorecover is enabled, executes `scripts/ensure_model_backend.ps1`.
	- Retries connection failures once after recovery.

## VS Code Tasks
- `backend: test (backend dir)`
- `backend: run`
- `backend: smoke auth`
- `backend: stop`