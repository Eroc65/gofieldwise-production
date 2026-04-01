"""FastAPI + WebSocket chat backend.

Exposes two endpoints:

* ``GET /``          — serves the single-page chat UI (``static/index.html``)
* ``GET /health``    — JSON liveness probe
* ``POST /chat``     — REST JSON endpoint (session_id + message → reply)
* ``WS  /ws/{session_id}`` — WebSocket endpoint (text frames in, text frames out)

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

    def _get_orchestrator(session_id: str) -> Orchestrator:
        if session_id not in _sessions:
            _sessions[session_id] = Orchestrator(config, session_id=session_id)
        return _sessions[session_id]

    app = FastAPI(
        title="Auto-GPT Startup Operations Platform",
        description="AI-powered cofounder chat interface.",
        version="0.1.0",
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
