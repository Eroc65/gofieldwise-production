from __future__ import annotations

import importlib
import importlib.util
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .settings import load_settings
from .startup import shutdown_services, startup_services


def register_routers(app: FastAPI) -> None:
    """
    Keep router imports here, not in app.main.
    """
    spec = importlib.util.find_spec("app.api")
    if spec is None:
        return

    api_module = importlib.import_module("app.api")
    router = getattr(api_module, "router", None)
    if router is not None:
            app.include_router(router)


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "https://gofieldwise.com",
        "https://www.gofieldwise.com",
        "http://localhost:3000",
        "http://localhost:3100",
        "http://localhost:3105",
        "http://127.0.0.1:3105",
    ]


def create_app(*, testing: bool = False) -> FastAPI:
    settings = load_settings(testing=testing)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.enable_startup_side_effects:
            await startup_services(app)
        try:
            yield
        finally:
            if settings.enable_startup_side_effects:
                await shutdown_services(app)

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Billing-Sync-Secret"],
    )
    register_routers(app)

    @app.get("/")
    def read_root():
        return {"message": "FrontDesk Pro API is running"}

    return app

