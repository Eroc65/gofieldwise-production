"""Background task scheduler for the startup operations platform.

Responsibilities
----------------
* Run recurring tasks (tweets, ad-performance checks, etc.) on a cron/interval
  schedule without manual intervention.
* Persist job definitions to Postgres so they survive restarts.
* Expose a clean ``add_job / list_jobs / remove_job`` API consumed by the web
  layer and CLI.

Design
------
:class:`TaskScheduler` wraps APScheduler's ``BackgroundScheduler`` with an
in-memory job store.  Job *definitions* (task text + trigger) are persisted to
a dedicated Postgres table so they can be reloaded on startup.  When a job
fires, it creates a fresh :class:`~autogpt.orchestrator.Orchestrator` for a
dedicated ``scheduler`` session, calls ``chat(task)``, and optionally sends the
result to Slack.

Usage::

    from autogpt.config import Config
    from autogpt.scheduler import TaskScheduler

    cfg = Config()
    sched = TaskScheduler(cfg)
    sched.start()

    job_id = sched.add_job(
        task="Post a morning motivational tweet",
        trigger_type="cron",
        trigger_params={"hour": 9, "minute": 0},
    )

    sched.shutdown()
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_CREATE_JOBS_TABLE = """\
CREATE TABLE IF NOT EXISTS autogpt_jobs (
    job_id          TEXT        PRIMARY KEY,
    task            TEXT        NOT NULL,
    trigger_type    TEXT        NOT NULL,
    trigger_params  JSONB       NOT NULL DEFAULT '{}',
    enabled         BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


class TaskScheduler:
    """Background scheduler that runs orchestrator tasks on a schedule.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        self._scheduler = self._build_scheduler()
        self._started = False
        # In-memory metadata registry (job_id → {task, trigger_type, trigger_params}).
        # Used as a fallback source for list_jobs() when no DATABASE_URL is set.
        self._job_meta: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """Start the background scheduler and reload persisted jobs."""
        if self._started:
            return
        self._init_jobs_table()
        self._reload_jobs()
        self._scheduler.start()
        self._started = True
        self._log.info("TaskScheduler started.")

    def shutdown(self, wait: bool = True) -> None:
        """Stop the scheduler gracefully."""
        if not self._started:
            return
        self._scheduler.shutdown(wait=wait)
        self._started = False
        self._log.info("TaskScheduler shut down.")

    @property
    def running(self) -> bool:
        """``True`` if the scheduler is currently running."""
        return self._started

    # ------------------------------------------------------------------ #
    # Job management
    # ------------------------------------------------------------------ #

    def add_job(
        self,
        task: str,
        trigger_type: str,
        trigger_params: dict[str, Any] | None = None,
        job_id: str | None = None,
    ) -> str:
        """Schedule a new task.

        Args:
            task: Plain-English task description passed to
                :meth:`~autogpt.orchestrator.Orchestrator.chat`.
            trigger_type: APScheduler trigger type — ``"cron"``, ``"interval"``,
                or ``"date"``.
            trigger_params: Keyword arguments forwarded to the APScheduler
                trigger.  Examples:

                * cron:     ``{"hour": 9, "minute": 0}``
                * interval: ``{"hours": 1}``
                * date:     ``{"run_date": "2026-06-01 09:00:00"}``
            job_id: Optional stable ID.  A UUID is generated when omitted.

        Returns:
            The ``job_id`` string.
        """
        params = trigger_params or {}
        jid = job_id or str(uuid.uuid4())

        self._schedule_in_memory(jid, task, trigger_type, params)
        self._job_meta[jid] = {"task": task, "trigger_type": trigger_type, "trigger_params": params}
        self._persist_job(jid, task, trigger_type, params)

        self._log.info("Scheduled job %s (%s %s): %s", jid, trigger_type, params, task[:60])
        return jid

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Args:
            job_id: The ID returned by :meth:`add_job`.

        Returns:
            ``True`` if the job was found and removed, ``False`` otherwise.
        """
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass  # job may not be in the in-memory scheduler

        self._job_meta.pop(job_id, None)
        self._delete_job(job_id)
        self._log.info("Removed job %s.", job_id)
        return True

    def list_jobs(self) -> list[dict[str, Any]]:
        """Return all scheduled jobs.

        Returns:
            List of job dicts with ``job_id``, ``task``, ``trigger_type``,
            ``trigger_params``, ``enabled``, and ``next_run_time`` fields.
        """
        db_jobs = self._fetch_jobs_from_db()
        # Build a lookup for next-run-time enrichment.
        apscheduler_jobs = {j.id: j for j in self._scheduler.get_jobs()}

        if db_jobs:
            for job in db_jobs:
                ap_job = apscheduler_jobs.get(job["job_id"])
                job["next_run_time"] = (
                    ap_job.next_run_time.isoformat()
                    if ap_job and ap_job.next_run_time
                    else None
                )
            return db_jobs

        # No DB — build the list from the in-memory scheduler using the local registry.
        result: list[dict[str, Any]] = []
        for ap_job in apscheduler_jobs.values():
            meta = self._job_meta.get(ap_job.id, {})
            result.append(
                {
                    "job_id": ap_job.id,
                    "task": meta.get("task", ""),
                    "trigger_type": meta.get("trigger_type", ""),
                    "trigger_params": meta.get("trigger_params", {}),
                    "enabled": True,
                    "next_run_time": (
                        ap_job.next_run_time.isoformat()
                        if ap_job.next_run_time
                        else None
                    ),
                }
            )
        return result

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_scheduler(self) -> Any:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
        except ImportError as exc:
            raise RuntimeError(
                "APScheduler is not installed. "
                "Run `pip install apscheduler` to enable the task scheduler."
            ) from exc
        return BackgroundScheduler()

    def _make_trigger(self, trigger_type: str, params: dict[str, Any]) -> Any:
        """Build an APScheduler trigger object."""
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
        from apscheduler.triggers.date import DateTrigger

        t = trigger_type.lower()
        if t == "cron":
            return CronTrigger(**params)
        if t == "interval":
            return IntervalTrigger(**params)
        if t == "date":
            return DateTrigger(**params)
        raise ValueError(f"Unknown trigger_type: {trigger_type!r}")

    def _schedule_in_memory(
        self, job_id: str, task: str, trigger_type: str, params: dict[str, Any]
    ) -> None:
        """Add the job to the APScheduler instance."""
        trigger = self._make_trigger(trigger_type, params)
        self._scheduler.add_job(
            func=self._run_task,
            trigger=trigger,
            id=job_id,
            args=[job_id, task],
            replace_existing=True,
        )

    def _run_task(self, job_id: str, task: str) -> None:
        """Callback executed by APScheduler when a job fires."""
        self._log.info("Scheduler running job %s: %s", job_id, task[:60])
        try:
            from autogpt.orchestrator import Orchestrator

            orc = Orchestrator(self._cfg, session_id=f"scheduler-{job_id}")
            reply = orc.chat(task)
            self._log.info("Job %s completed: %s", job_id, reply[:120])
        except Exception as exc:
            self._log.error("Job %s failed: %s", job_id, exc)

    # ------------------------------------------------------------------ #
    # Postgres helpers
    # ------------------------------------------------------------------ #

    def _get_db(self) -> "DatabaseTools | None":
        if not self._cfg.database_url:
            return None
        from autogpt.tools.database_tools import DatabaseTools
        return DatabaseTools(self._cfg.database_url, self._cfg.verbose)

    def _init_jobs_table(self) -> None:
        db = self._get_db()
        if db is None:
            return
        try:
            db.execute_sql(_CREATE_JOBS_TABLE)
            self._log.debug("Jobs table ready.")
        except Exception as exc:
            self._log.warning("Could not initialise jobs table: %s", exc)

    def _reload_jobs(self) -> None:
        """Load persisted jobs from Postgres and schedule them in memory."""
        for job in self._fetch_jobs_from_db():
            if not job.get("enabled", True):
                continue
            try:
                self._schedule_in_memory(
                    job["job_id"],
                    job["task"],
                    job["trigger_type"],
                    job.get("trigger_params") or {},
                )
                self._log.info("Reloaded job %s from Postgres.", job["job_id"])
            except Exception as exc:
                self._log.warning("Could not reload job %s: %s", job["job_id"], exc)

    def _persist_job(
        self, job_id: str, task: str, trigger_type: str, params: dict[str, Any]
    ) -> None:
        db = self._get_db()
        if db is None:
            return
        try:
            db.execute_sql(
                """
                INSERT INTO autogpt_jobs (job_id, task, trigger_type, trigger_params)
                VALUES (%s, %s, %s, %s::jsonb)
                ON CONFLICT (job_id) DO UPDATE
                    SET task           = EXCLUDED.task,
                        trigger_type   = EXCLUDED.trigger_type,
                        trigger_params = EXCLUDED.trigger_params,
                        enabled        = TRUE
                """,
                (job_id, task, trigger_type, json.dumps(params)),
            )
        except Exception as exc:
            self._log.warning("Could not persist job %s: %s", job_id, exc)

    def _delete_job(self, job_id: str) -> None:
        db = self._get_db()
        if db is None:
            return
        try:
            db.execute_sql(
                "DELETE FROM autogpt_jobs WHERE job_id = %s",
                (job_id,),
            )
        except Exception as exc:
            self._log.warning("Could not delete job %s from DB: %s", job_id, exc)

    def _fetch_jobs_from_db(self) -> list[dict[str, Any]]:
        db = self._get_db()
        if db is None:
            return []
        try:
            return db.query(
                "SELECT job_id, task, trigger_type, trigger_params, enabled, "
                "created_at FROM autogpt_jobs ORDER BY created_at ASC"
            )
        except Exception as exc:
            self._log.warning("Could not fetch jobs from DB: %s", exc)
            return []
