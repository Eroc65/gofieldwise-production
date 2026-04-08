# FrontDesk Pro

AI-first front desk software for small trades businesses.

## Repo Structure
- `frontend/` — Next.js (React, JavaScript) app
- `backend/` — FastAPI backend (Python)
- `.github/` — CI/CD, templates, project management
- `infra/` — Deployment, environment config
- `render.yaml` — Render.com deployment config

## Official GoFieldwise Stack

### Frontend
- Next.js (pages router) with React
- JavaScript and CSS (global styles + component-level styles)

### Backend
- FastAPI (Python)
- Organization-scoped API and auth flows

### Infrastructure
- Render for web service hosting, deploy pipelines, SSL, and runtime configuration
- Neon Postgres for persistent application data (users, organizations, jobs, customers, reminders)

### Runtime Request Flow
1. Browser sends request to the app hosted on Render.
2. Backend service validates auth/business logic and queries Neon.
3. Neon returns data to backend.
4. Backend returns API response/UI data to browser.

### Branding Standard
- Use `GoFieldwise` consistently in docs, UI, and campaigns.

## Local Development

### Backend (FastAPI)
1. Install Python 3.11+
2. `pip install -r backend/requirements.txt`
3. `uvicorn backend.app.main:app --reload --port 8001`
	- API docs: http://localhost:8001/docs

### Frontend (Next.js)
**BLOCKED:** Node.js/npm are missing in this environment. You must install Node.js (https://nodejs.org/) to run or validate the frontend.
1. Install Node.js (if not blocked)
2. `cd frontend && npm install`
3. `npm run dev`
	- App: http://localhost:3000

### Environment Variables
- Copy `.env.example` to `.env` and fill in values as needed.
- See `.env.example` for backend/DB/secret config and frontend API URL.

### Render Deployment
- See `render.yaml` for Render.com service definitions (frontend/backend, build/start commands, env vars).

## CI/CD
- GitHub Actions: `.github/workflows/ci.yml` runs backend tests from `backend/` on pushes and pull requests to `main`.
- `.github/workflows/deploy-staging.yml` triggers staging deploy hooks from the release-hardening branch.
- `.github/workflows/deploy-production.yml` triggers production deploy hooks from `main`.
- `.github/workflows/post-deploy-smoke.yml` runs live post-deploy API smoke checks.
- `.github/workflows/deploy-guardrails.yml` opens incident issues on deploy workflow failures.
- Required secrets are listed in `.github/SECRETS_SETUP.md`.

## VS Code Tasks
- `backend: test (backend dir)` runs the backend pytest suite from the correct working directory.
- `backend: run` starts the FastAPI API on `http://127.0.0.1:8001`.
- `backend: smoke auth` runs the live auth smoke script against the running backend.
- `backend: stop` stops the local API process listening on port `8001`.

## Blockers
- **Frontend setup/validation is currently blocked due to missing Node.js/npm.**
  All backend/devops work is unblocked and complete.

## Entry Points
- Backend: `backend/app/main.py` (FastAPI app)
- Frontend: `frontend/` (Next.js app)
