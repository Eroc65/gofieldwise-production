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

**Get current org:**
GET `/api/auth/org` (Bearer token)

**Protected test route:**
GET `/api/protected` (Bearer token)

**Lead booking workflow:**
POST `/api/leads/{lead_id}/book` (Bearer token) with `{ scheduled_time, technician_id }`

## Setup
1. Install Python 3.11+
2. `pip install -r requirements.txt`
3. `uvicorn app.main:app --reload --port 8001`
	- API docs: http://localhost:8001/docs

## Validation
- `pytest -q`
- `python scripts/smoke_auth.py`

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
- Example (bash):
	- `export AGENT_MODEL_BASE_URL="http://localhost:1234/v1"`
	- `export AGENT_MODEL_API_KEY="lm-studio"`
	- `export AGENT_MODEL_NAME="gpt-4.1-mini"`
	- `export AGENT_MODEL_TIMEOUT_SECONDS="120"`
	- `export AGENT_MODEL_TEMPERATURE="0.1"`
	- `export AGENT_MODEL_MAX_TOKENS="4000"`
	- `python -m agent_runtime.run_once`
- Example (PowerShell):
	- `$env:AGENT_MODEL_BASE_URL="http://localhost:1234/v1"`
	- `$env:AGENT_MODEL_API_KEY="lm-studio"`
	- `$env:AGENT_MODEL_NAME="gpt-4.1-mini"`
	- `$env:AGENT_MODEL_TIMEOUT_SECONDS="120"`
	- `$env:AGENT_MODEL_TEMPERATURE="0.1"`
	- `$env:AGENT_MODEL_MAX_TOKENS="4000"`
	- `python -m agent_runtime.run_once`

## VS Code Tasks
- `backend: test (backend dir)`
- `backend: run`
- `backend: smoke auth`
- `backend: stop`