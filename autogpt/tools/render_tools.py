"""Render.com API helpers used by the engineering agent."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from autogpt.utils.logger import get_logger


class RenderTools:
    """Thin wrapper around the Render REST API v1."""

    _BASE = "https://api.render.com/v1"

    def __init__(self, api_key: str, owner_id: str, verbose: bool = False) -> None:
        self._key = api_key
        self._owner_id = owner_id
        self._log: logging.Logger = get_logger(__name__, verbose)
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ #
    # Services (web apps)
    # ------------------------------------------------------------------ #

    def create_web_service(
        self,
        name: str,
        repo_url: str,
        branch: str = "main",
        build_command: str = "pip install -r requirements.txt",
        start_command: str = "python main.py",
        plan: str = "free",
        env_vars: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a new Render web service linked to a GitHub repository."""
        payload: dict[str, Any] = {
            "type": "web_service",
            "name": name,
            "ownerId": self._owner_id,
            "repo": repo_url,
            "branch": branch,
            "buildCommand": build_command,
            "startCommand": start_command,
            "plan": plan,
            "envVars": [
                {"key": k, "value": v} for k, v in (env_vars or {}).items()
            ],
        }
        resp = requests.post(
            f"{self._BASE}/services",
            json=payload,
            headers=self._headers,
            timeout=30,
        )
        resp.raise_for_status()
        service = resp.json().get("service", resp.json())
        self._log.info("Created Render web service: %s (id=%s)", name, service.get("id"))
        return service

    def create_postgres(
        self,
        name: str,
        plan: str = "free",
        region: str = "oregon",
    ) -> dict[str, Any]:
        """Create a managed Postgres database on Render."""
        payload = {
            "name": name,
            "ownerId": self._owner_id,
            "plan": plan,
            "region": region,
        }
        resp = requests.post(
            f"{self._BASE}/postgres",
            json=payload,
            headers=self._headers,
            timeout=30,
        )
        resp.raise_for_status()
        db = resp.json().get("postgres", resp.json())
        self._log.info("Created Postgres DB: %s (id=%s)", name, db.get("id"))
        return db

    def get_service(self, service_id: str) -> dict[str, Any]:
        """Fetch the current status of a Render service."""
        resp = requests.get(
            f"{self._BASE}/services/{service_id}",
            headers=self._headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def trigger_deploy(self, service_id: str) -> dict[str, Any]:
        """Trigger a new deployment for an existing Render service."""
        resp = requests.post(
            f"{self._BASE}/services/{service_id}/deploys",
            json={"clearCache": "do_not_clear"},
            headers=self._headers,
            timeout=30,
        )
        resp.raise_for_status()
        deploy = resp.json()
        self._log.info("Triggered deploy for service %s", service_id)
        return deploy

    def wait_for_deploy(
        self,
        service_id: str,
        timeout_seconds: int = 300,
        poll_interval: int = 10,
    ) -> str:
        """Poll until the latest deploy reaches a terminal state.

        Returns the final status string (``"live"``, ``"failed"``, etc.).
        """
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            svc = self.get_service(service_id)
            status = svc.get("serviceDetails", {}).get("url", "")
            deploy_status = svc.get("suspended", "not_suspended")
            # Check deploys endpoint for real status
            deploys_resp = requests.get(
                f"{self._BASE}/services/{service_id}/deploys",
                headers=self._headers,
                params={"limit": 1},
                timeout=30,
            )
            if deploys_resp.ok:
                deploys = deploys_resp.json()
                if deploys:
                    latest = deploys[0].get("deploy", deploys[0])
                    state = latest.get("status", "")
                    self._log.debug("Deploy status for %s: %s", service_id, state)
                    if state in {"live", "failed", "canceled"}:
                        return state
            time.sleep(poll_interval)
        return "timeout"
