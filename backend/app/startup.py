from __future__ import annotations

from fastapi import FastAPI

from .core.db import Base, engine


async def startup_services(app: FastAPI) -> None:
    """
    Move startup side effects here so importing app.main stays side-effect free.
    """
    Base.metadata.create_all(bind=engine)


async def shutdown_services(app: FastAPI) -> None:
    """
    Stop anything started in startup_services().
    """
    return None
