from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_runtime.tool_policies import get_tool_policy


@dataclass
class ToolResult:
    ok: bool
    tool_name: str
    result: dict[str, Any]


class ToolExecutionError(RuntimeError):
    pass


class ToolExecutor:
    """
    Safe repo-scoped tool executor.

    Default tools:
    - read_file
    - write_file
    - append_file
    - list_dir
    - search_text
    - run_command

    Safety:
    - all file operations are restricted to repo root
    - command execution is restricted by an allowlist of command prefixes
    - shell=False always
    """

    def __init__(self, repo_root: str | Path = ".", mode: str | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        if not self.repo_root.exists():
            raise ToolExecutionError(f"Repo root does not exist: {self.repo_root}")

        resolved_mode = (mode or os.getenv("AGENT_TOOL_MODE", "dev")).strip()
        self.policy = get_tool_policy(resolved_mode)
        self.allowed_prefixes = list(self.policy.allowed_command_prefixes)

    def _ensure_allowed(self, flag: bool, action: str) -> None:
        if not flag:
            raise ToolExecutionError(f"Tool action not allowed in mode={self.policy.mode}: {action}")

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        tool_name = request.get("tool_name")
        args = request.get("args") or {}

        if tool_name == "read_file":
            return self.read_file(**args)
        if tool_name == "write_file":
            return self.write_file(**args)
        if tool_name == "append_file":
            return self.append_file(**args)
        if tool_name == "list_dir":
            return self.list_dir(**args)
        if tool_name == "search_text":
            return self.search_text(**args)
        if tool_name == "run_command":
            return self.run_command(**args)

        raise ToolExecutionError(f"Unknown tool: {tool_name}")

    def _resolve_repo_path(self, relative_path: str) -> Path:
        candidate = (self.repo_root / relative_path).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError as exc:
            raise ToolExecutionError(f"Path escapes repo root: {relative_path}") from exc
        return candidate

    def _read_text_safe(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8", errors="replace")

    def read_file(self, path: str, max_chars: int = 20000) -> dict[str, Any]:
        self._ensure_allowed(self.policy.allow_read_file, "read_file")
        file_path = self._resolve_repo_path(path)
        if not file_path.exists():
            raise ToolExecutionError(f"File does not exist: {path}")
        if not file_path.is_file():
            raise ToolExecutionError(f"Path is not a file: {path}")

        text = self._read_text_safe(file_path)
        truncated = len(text) > max_chars
        return {
            "tool_name": "read_file",
            "ok": True,
            "path": path,
            "truncated": truncated,
            "content": text[:max_chars],
            "size_chars": len(text),
        }

    def write_file(self, path: str, content: str, create_dirs: bool = True) -> dict[str, Any]:
        self._ensure_allowed(self.policy.allow_write_file, "write_file")
        file_path = self._resolve_repo_path(path)
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return {
            "tool_name": "write_file",
            "ok": True,
            "path": path,
            "bytes_written": len(content.encode("utf-8")),
        }

    def append_file(self, path: str, content: str, create_dirs: bool = True) -> dict[str, Any]:
        self._ensure_allowed(self.policy.allow_append_file, "append_file")
        file_path = self._resolve_repo_path(path)
        if create_dirs:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("a", encoding="utf-8") as fh:
            fh.write(content)
        return {
            "tool_name": "append_file",
            "ok": True,
            "path": path,
            "bytes_appended": len(content.encode("utf-8")),
        }

    def list_dir(self, path: str = ".", recursive: bool = False, max_entries: int = 200) -> dict[str, Any]:
        self._ensure_allowed(self.policy.allow_list_dir, "list_dir")
        dir_path = self._resolve_repo_path(path)
        if not dir_path.exists():
            raise ToolExecutionError(f"Directory does not exist: {path}")
        if not dir_path.is_dir():
            raise ToolExecutionError(f"Path is not a directory: {path}")

        entries: list[str] = []
        if recursive:
            for p in dir_path.rglob("*"):
                rel = p.relative_to(self.repo_root).as_posix()
                entries.append(rel + ("/" if p.is_dir() else ""))
                if len(entries) >= max_entries:
                    break
        else:
            for p in dir_path.iterdir():
                rel = p.relative_to(self.repo_root).as_posix()
                entries.append(rel + ("/" if p.is_dir() else ""))
                if len(entries) >= max_entries:
                    break

        return {
            "tool_name": "list_dir",
            "ok": True,
            "path": path,
            "recursive": recursive,
            "entries": sorted(entries),
        }

    def search_text(
        self,
        pattern: str,
        path: str = ".",
        file_extensions: list[str] | None = None,
        max_hits: int = 100,
        max_line_length: int = 300,
    ) -> dict[str, Any]:
        self._ensure_allowed(self.policy.allow_search_text, "search_text")
        root = self._resolve_repo_path(path)
        if not root.exists():
            raise ToolExecutionError(f"Search root does not exist: {path}")

        exts = set(file_extensions or [])
        hits: list[dict[str, Any]] = []

        files = root.rglob("*") if root.is_dir() else [root]
        for p in files:
            if not p.is_file():
                continue
            if exts and p.suffix not in exts:
                continue

            try:
                text = self._read_text_safe(p)
            except Exception:
                continue

            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    hits.append(
                        {
                            "path": p.relative_to(self.repo_root).as_posix(),
                            "line_number": lineno,
                            "line": line[:max_line_length],
                        }
                    )
                    if len(hits) >= max_hits:
                        return {
                            "tool_name": "search_text",
                            "ok": True,
                            "pattern": pattern,
                            "hits": hits,
                            "truncated": True,
                        }

        return {
            "tool_name": "search_text",
            "ok": True,
            "pattern": pattern,
            "hits": hits,
            "truncated": False,
        }

    def run_command(
        self,
        command: str,
        timeout_seconds: int = 120,
        cwd: str = ".",
        env_overrides: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self._ensure_allowed(self.policy.allow_run_command, "run_command")
        normalized = command.strip()
        if not self._command_allowed(normalized):
            raise ToolExecutionError(f"Command not allowed by policy: {command}")

        cwd_path = self._resolve_repo_path(cwd)
        if not cwd_path.exists():
            raise ToolExecutionError(f"cwd does not exist: {cwd}")
        if not cwd_path.is_dir():
            raise ToolExecutionError(f"cwd is not a directory: {cwd}")

        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)

        args = shlex.split(normalized, posix=os.name != "nt")
        completed = subprocess.run(
            args,
            cwd=str(cwd_path),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
            shell=False,
        )

        return {
            "tool_name": "run_command",
            "ok": completed.returncode == 0,
            "command": command,
            "cwd": cwd,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-20000:],
            "stderr": completed.stderr[-20000:],
        }

    def _command_allowed(self, command: str) -> bool:
        dangerous_prefixes = [
            "rm ",
            "sudo ",
            "shutdown",
            "reboot",
            "mkfs",
            "dd ",
            "chmod 777",
            "chown ",
            "kill -9",
            "docker system prune",
        ]
        lowered = command.lower()
        if any(lowered.startswith(x) for x in dangerous_prefixes):
            return False

        allowed = [x.lower() for x in self.allowed_prefixes]
        return any(lowered.startswith(prefix) for prefix in allowed)