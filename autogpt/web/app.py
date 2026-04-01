"""FastAPI + WebSocket chat backend.

Exposes the following endpoints:

* ``GET /``                        — serves the single-page chat UI
* ``GET /health``                  — JSON liveness probe
* ``POST /chat``                   — REST chat (session_id + message → reply)
* ``WS  /ws/{session_id}``         — WebSocket chat
* ``GET /sessions``                — list active in-memory sessions
* ``GET /history/{session_id}``    — return conversation history for a session
* ``DELETE /sessions/{session_id}``— clear (reset) a session's history
* ``POST /jobs``                   — schedule a recurring task
* ``GET /jobs``                    — list all scheduled jobs
* ``DELETE /jobs/{job_id}``        — remove a scheduled job

Usage (programmatic)::

    from autogpt.config import Config
    from autogpt.web.app import create_app
    import uvicorn

    app = create_app(Config())
    uvicorn.run(app, host="0.0.0.0", port=8000)

Usage (CLI via ``autogpt --web``)::

    python -m autogpt.main --web
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from autogpt.config import Config
from autogpt.orchestrator import Orchestrator
from autogpt.utils.logger import get_logger

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel

    _FASTAPI_AVAILABLE = True

    class ChatRequest(BaseModel):
        session_id: str
        message: str

    class ChatResponse(BaseModel):
        session_id: str
        reply: str

    class JobRequest(BaseModel):
        task: str
        trigger_type: str
        trigger_params: dict[str, Any] = {}
        job_id: str | None = None

    class JobResponse(BaseModel):
        job_id: str

except ImportError:  # pragma: no cover
    _FASTAPI_AVAILABLE = False

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(config: Config) -> Any:
    """Build and return the FastAPI application.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.

    Returns:
        A :class:`fastapi.FastAPI` instance ready to be served by uvicorn.

    Raises:
        RuntimeError: When FastAPI or its dependencies are not installed.
    """
    if not _FASTAPI_AVAILABLE:
        raise RuntimeError(
            "FastAPI is not installed. "
            "Run `pip install fastapi uvicorn[standard]` to enable the web UI."
        )

    log: logging.Logger = get_logger("autogpt.web", config.verbose)

    # One Orchestrator per session, keyed by session_id.
    _sessions: dict[str, Orchestrator] = {}

    # Scheduler instance (started in lifespan when enabled).
    _scheduler: Any = None

    def _get_orchestrator(session_id: str) -> Orchestrator:
        if session_id not in _sessions:
            _sessions[session_id] = Orchestrator(config, session_id=session_id)
        return _sessions[session_id]

    # ------------------------------------------------------------------ #
    # Lifespan — start/stop the background scheduler
    # ------------------------------------------------------------------ #

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[type-arg]
        nonlocal _scheduler
        if config.scheduler_enabled:
            try:
                from autogpt.scheduler import TaskScheduler
                _scheduler = TaskScheduler(config)
                _scheduler.start()
                log.info("Background task scheduler started.")
            except Exception as exc:
                log.warning("Could not start scheduler: %s", exc)
        yield
        if _scheduler is not None:
            try:
                _scheduler.shutdown(wait=False)
                log.info("Background task scheduler stopped.")
            except Exception:
                pass

    app = FastAPI(
        title="Auto-GPT Startup Operations Platform",
        description="AI-powered cofounder chat interface.",
        version="0.2.0",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------ #
    # Static files (index.html lives in autogpt/web/static/)
    # ------------------------------------------------------------------ #
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # ------------------------------------------------------------------ #
    # HTTP endpoints
    # ------------------------------------------------------------------ #

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def index() -> HTMLResponse:
        """Serve the chat UI."""
        html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(content=html)

    @app.get("/health")
    async def health() -> JSONResponse:
        """Liveness probe."""
        return JSONResponse({"status": "ok"})

    @app.post("/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest) -> ChatResponse:
        """Send a message and receive a reply (REST / polling fallback)."""
        log.info("REST /chat  session=%s  msg=%s", req.session_id, req.message[:60])
        orc = _get_orchestrator(req.session_id)
        reply = orc.chat(req.message)
        return ChatResponse(session_id=req.session_id, reply=reply)

    # ------------------------------------------------------------------ #
    # Session management endpoints
    # ------------------------------------------------------------------ #

    @app.get("/sessions")
    async def list_sessions() -> JSONResponse:
        """List all active in-memory sessions."""
        return JSONResponse(
            {
                "sessions": [
                    {"session_id": sid, "history_length": len(orc._history)}
                    for sid, orc in _sessions.items()
                ]
            }
        )

    @app.get("/history/{session_id}")
    async def get_history(session_id: str) -> JSONResponse:
        """Return the conversation history for a session.

        Creates a new (empty) session if the ID is not yet known.
        """
        orc = _get_orchestrator(session_id)
        # Exclude the system prompt from the public response.
        messages = [m for m in orc._history if m.get("role") != "system"]
        return JSONResponse({"session_id": session_id, "messages": messages})

    @app.delete("/sessions/{session_id}")
    async def reset_session(session_id: str) -> JSONResponse:
        """Clear the conversation history for a session (keeps the system prompt)."""
        orc = _get_orchestrator(session_id)
        orc.reset()
        log.info("Session %s reset via DELETE /sessions.", session_id)
        return JSONResponse({"session_id": session_id, "status": "reset"})

    # ------------------------------------------------------------------ #
    # Scheduler endpoints
    # ------------------------------------------------------------------ #

    @app.post("/jobs", response_model=JobResponse)
    async def create_job(req: JobRequest) -> JobResponse:
        """Schedule a new recurring task.

        Example body::

            {
              "task": "Post a morning motivation tweet",
              "trigger_type": "cron",
              "trigger_params": {"hour": 9, "minute": 0}
            }
        """
        if _scheduler is None:
            return JSONResponse(  # type: ignore[return-value]
                status_code=503,
                content={"detail": "Scheduler is not running."},
            )
        job_id = _scheduler.add_job(
            task=req.task,
            trigger_type=req.trigger_type,
            trigger_params=req.trigger_params,
            job_id=req.job_id,
        )
        return JobResponse(job_id=job_id)

    @app.get("/jobs")
    async def list_jobs() -> JSONResponse:
        """Return all scheduled jobs."""
        if _scheduler is None:
            return JSONResponse({"jobs": []})
        return JSONResponse({"jobs": _scheduler.list_jobs()})

    @app.delete("/jobs/{job_id}")
    async def delete_job(job_id: str) -> JSONResponse:
        """Remove a scheduled job."""
        if _scheduler is None:
            return JSONResponse(  # type: ignore[return-value]
                status_code=503,
                content={"detail": "Scheduler is not running."},
            )
        _scheduler.remove_job(job_id)
        return JSONResponse({"job_id": job_id, "status": "removed"})

    # ------------------------------------------------------------------ #
    # WebSocket endpoint
    # ------------------------------------------------------------------ #

    @app.websocket("/ws/{session_id}")
    async def websocket_chat(websocket: WebSocket, session_id: str) -> None:
        """Stream chat messages over a WebSocket connection.

        The client sends plain text messages; the server replies with plain
        text.  This keeps the protocol dead-simple and compatible with the
        built-in browser ``WebSocket`` API.
        """
        await websocket.accept()
        log.info("WebSocket connected  session=%s", session_id)
        orc = _get_orchestrator(session_id)

        try:
            while True:
                message = await websocket.receive_text()
                if not message.strip():
                    continue
                log.info("WS  session=%s  msg=%s", session_id, message[:60])
                reply = orc.chat(message)
                await websocket.send_text(reply)
        except WebSocketDisconnect:
            log.info("WebSocket disconnected  session=%s", session_id)

    return app

