from __future__ import annotations

import importlib
import importlib.util
from contextlib import asynccontextmanager

from fastapi import FastAPI

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
    register_routers(app)

    @app.get("/")
    def read_root():
        return {"message": "FrontDesk Pro API is running"}

    return app
