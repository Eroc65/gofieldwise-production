"""PostgreSQL helpers used by the engineering agent."""

from __future__ import annotations

import logging
from typing import Any

from autogpt.utils.logger import get_logger

try:
    import psycopg2
    import psycopg2.extras

    _PSYCOPG2_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PSYCOPG2_AVAILABLE = False


class DatabaseTools:
    """Utilities for provisioning and managing a Postgres database."""

    def __init__(self, database_url: str, verbose: bool = False) -> None:
        self._url = database_url
        self._log: logging.Logger = get_logger(__name__, verbose)

    # ------------------------------------------------------------------ #
    # Connection
    # ------------------------------------------------------------------ #

    def _connect(self) -> Any:
        if not _PSYCOPG2_AVAILABLE:
            raise RuntimeError(
                "psycopg2 is not installed. "
                "Run `pip install psycopg2-binary` to enable database features."
            )
        return psycopg2.connect(self._url)

    # ------------------------------------------------------------------ #
    # Schema helpers
    # ------------------------------------------------------------------ #

    def execute_sql(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        """Execute a single DDL or DML statement."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
        self._log.debug("Executed SQL: %s", sql[:80])

    def execute_many(self, sql: str, rows: list[tuple[Any, ...]]) -> None:
        """Execute *sql* for each row in *rows* using a fast batch insert."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                psycopg2.extras.execute_batch(cur, sql, rows)
            conn.commit()
        self._log.debug("Batch executed %d rows: %s", len(rows), sql[:60])

    def query(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        """Run a SELECT and return rows as a list of dicts."""
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]

    def create_table(self, ddl: str) -> None:
        """Execute a ``CREATE TABLE`` statement."""
        self.execute_sql(ddl)
        self._log.info("Table created/verified.")

    def table_exists(self, table_name: str, schema: str = "public") -> bool:
        """Return *True* if the named table exists in *schema*."""
        rows = self.query(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",
            (schema, table_name),
        )
        return bool(rows)
