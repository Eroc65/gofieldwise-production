# FrontDesk Pro Infra

Infrastructure, Docker, and deployment configuration for FrontDesk Pro.

- `docker-compose.yml` — Multi-service orchestration
- `.env.example` — Environment variable template

## Setup
1. Copy `.env.example` to `.env` and fill in values as needed.
2. For Render.com deployment, see `render.yaml` in the repo root.
3. Backend: `pip install -r backend/requirements.txt` then `uvicorn backend.app.main:app --reload --port 8001`
4. Frontend: **BLOCKED** (Node.js/npm missing in this environment)