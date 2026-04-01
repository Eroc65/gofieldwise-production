"""GitHub API helpers used by the engineering agent."""

from __future__ import annotations

import logging
from typing import Any

import requests

from autogpt.utils.logger import get_logger


class GitHubTools:
    """Thin wrapper around the GitHub REST API v3."""

    _BASE = "https://api.github.com"

    def __init__(self, token: str, org: str = "", verbose: bool = False) -> None:
        self._token = token
        self._org = org
        self._log: logging.Logger = get_logger(__name__, verbose)
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # ------------------------------------------------------------------ #
    # Repositories
    # ------------------------------------------------------------------ #

    def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = True,
        auto_init: bool = True,
    ) -> dict[str, Any]:
        """Create a new repository and return its metadata."""
        endpoint = (
            f"{self._BASE}/orgs/{self._org}/repos"
            if self._org
            else f"{self._BASE}/user/repos"
        )
        payload = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }
        resp = requests.post(endpoint, json=payload, headers=self._headers, timeout=30)
        resp.raise_for_status()
        self._log.info("Created GitHub repo: %s", name)
        return resp.json()

    def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch metadata for an existing repository."""
        resp = requests.get(
            f"{self._BASE}/repos/{owner}/{repo}",
            headers=self._headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def create_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content_b64: str,
        message: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Create or update a file in a repository."""
        url = f"{self._BASE}/repos/{owner}/{repo}/contents/{path}"
        # Check if file already exists to get its sha for updates
        sha: str | None = None
        check = requests.get(url, headers=self._headers, timeout=30)
        if check.status_code == 200:
            sha = check.json().get("sha")

        payload: dict[str, Any] = {
            "message": message,
            "content": content_b64,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha

        resp = requests.put(url, json=payload, headers=self._headers, timeout=30)
        resp.raise_for_status()
        self._log.info("Pushed file '%s' to %s/%s", path, owner, repo)
        return resp.json()

    def list_repos(self, owner: str) -> list[dict[str, Any]]:
        """Return all repositories for *owner* (handles pagination)."""
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            resp = requests.get(
                f"{self._BASE}/users/{owner}/repos",
                headers=self._headers,
                params={"per_page": 100, "page": page},
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            results.extend(batch)
            page += 1
        return results
