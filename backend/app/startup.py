from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy import inspect

from .core.db import Base, engine


def _assert_schema_compatibility() -> None:
    required_technician_columns = {
        "availability_start_hour_utc",
        "availability_end_hour_utc",
        "availability_weekdays",
    }

    with engine.connect() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
        if "technicians" not in table_names:
            return

        existing_columns = {column["name"] for column in inspector.get_columns("technicians")}
        missing = sorted(required_technician_columns - existing_columns)
        if missing:
            missing_text = ", ".join(missing)
            raise RuntimeError(
                "Database schema mismatch for technicians table. "
                f"Missing columns: {missing_text}. "
                "Run `alembic upgrade head` (or reset local sqlite test.db) before starting the API."
            )


async def startup_services(app: FastAPI) -> None:
    """
    Move startup side effects here so importing app.main stays side-effect free.
    """
    Base.metadata.create_all(bind=engine)
    _assert_schema_compatibility()


async def shutdown_services(app: FastAPI) -> None:
    """
    Stop anything started in startup_services().
    """
    return None
