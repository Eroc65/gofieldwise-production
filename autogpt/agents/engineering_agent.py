"""Engineering Agent — builds and deploys web applications.

Responsibilities
----------------
* Create GitHub repositories and scaffold starter code.
* Set up a managed PostgreSQL database on Render.
* Deploy the application to Render and return the public URL.
* Expose a simple ``run(task)`` interface that accepts a plain-English
  task description and uses the OpenAI API to plan + execute the steps.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import openai

from autogpt.config import Config
from autogpt.tools.github_tools import GitHubTools
from autogpt.tools.render_tools import RenderTools
from autogpt.tools.database_tools import DatabaseTools
from autogpt.utils.logger import get_logger

_SYSTEM_PROMPT = """\
You are an expert full-stack engineering agent.
When given a task description you respond with a JSON object containing:
{
  "repo_name": "<slug for the new GitHub repo>",
  "description": "<one-sentence project description>",
  "files": {
    "<relative/path/to/file>": "<raw file content as a string>"
  },
  "build_command": "<shell command to install dependencies>",
  "start_command": "<shell command to start the app>",
  "env_vars": {"<KEY>": "<value or placeholder>"}
}
Only output the JSON object — no prose, no markdown fences.
"""


class EngineeringAgent:
    """Builds and deploys a web application end-to-end.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        self._github = GitHubTools(config.github_token, config.github_org, config.verbose)
        self._render = RenderTools(config.render_api_key, config.render_owner_id, config.verbose)
        self._db = DatabaseTools(config.database_url, config.verbose)
        openai.api_key = config.openai_api_key

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

    def run(self, task: str) -> dict[str, Any]:
        """Execute a build-and-deploy task described in plain English.

        Args:
            task: Natural-language description, e.g.
                  ``"Build a Flask todo-list API with a Postgres backend."``.

        Returns:
            A dict with keys ``repo_url``, ``deploy_url``, ``db_info``,
            and ``status``.
        """
        self._log.info("EngineeringAgent received task: %s", task)

        plan = self._plan(task)
        self._log.info("Plan produced. Repo name: %s", plan.get("repo_name"))

        repo_meta = self._scaffold_repo(plan)
        db_meta = self._provision_database(plan.get("repo_name", "app"))
        service_meta = self._deploy(plan, repo_meta, db_meta)

        return {
            "repo_url": repo_meta.get("html_url", ""),
            "deploy_url": service_meta.get("serviceDetails", {}).get("url", ""),
            "db_info": {
                "id": db_meta.get("id", ""),
                "name": db_meta.get("name", ""),
            },
            "status": "deployed",
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _plan(self, task: str) -> dict[str, Any]:
        """Ask GPT to produce a structured deployment plan."""
        import json

        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": task},
            ],
            temperature=0.2,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            self._log.warning("Could not parse GPT plan as JSON; using empty plan.")
            return {}

    def _scaffold_repo(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Create the GitHub repo and push all scaffolded files."""
        name = plan.get("repo_name", "autogpt-app")
        description = plan.get("description", "")
        owner = self._cfg.github_org or self._get_authenticated_user()

        repo_meta = self._github.create_repo(name, description)
        owner = repo_meta.get("owner", {}).get("login", owner)

        for path, content in plan.get("files", {}).items():
            encoded = base64.b64encode(content.encode()).decode()
            self._github.create_file(
                owner,
                name,
                path,
                encoded,
                f"chore: scaffold {path}",
            )

        self._log.info("Repository scaffolded at %s", repo_meta.get("html_url"))
        return repo_meta

    def _provision_database(self, app_name: str) -> dict[str, Any]:
        """Create a Render-managed Postgres database."""
        db_name = f"{app_name}-db"
        return self._render.create_postgres(db_name)

    def _deploy(
        self,
        plan: dict[str, Any],
        repo_meta: dict[str, Any],
        db_meta: dict[str, Any],
    ) -> dict[str, Any]:
        """Create and deploy a Render web service."""
        env_vars: dict[str, str] = plan.get("env_vars", {})
        db_url = db_meta.get("databaseUrl", "")
        if db_url:
            env_vars["DATABASE_URL"] = db_url

        service = self._render.create_web_service(
            name=plan.get("repo_name", "autogpt-app"),
            repo_url=repo_meta.get("clone_url", repo_meta.get("html_url", "")),
            build_command=plan.get("build_command", "pip install -r requirements.txt"),
            start_command=plan.get("start_command", "python main.py"),
            env_vars=env_vars,
        )
        self._log.info("Deployment initiated for service id=%s", service.get("id"))
        return service

    def _get_authenticated_user(self) -> str:
        """Return the GitHub username for the current token."""
        import requests

        resp = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {self._cfg.github_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=15,
        )
        if resp.ok:
            return resp.json().get("login", "")
        return ""
