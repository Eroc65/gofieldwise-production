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

## VS Code Tasks
- `backend: test (backend dir)`
- `backend: run`
- `backend: smoke auth`
- `backend: stop`