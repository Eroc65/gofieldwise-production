from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPolicy:
    mode: str
    allow_read_file: bool
    allow_write_file: bool
    allow_append_file: bool
    allow_list_dir: bool
    allow_search_text: bool
    allow_run_command: bool
    allowed_command_prefixes: list[str]


POLICIES: dict[str, ToolPolicy] = {
    "readonly": ToolPolicy(
        mode="readonly",
        allow_read_file=True,
        allow_write_file=False,
        allow_append_file=False,
        allow_list_dir=True,
        allow_search_text=True,
        allow_run_command=False,
        allowed_command_prefixes=[],
    ),
    "test": ToolPolicy(
        mode="test",
        allow_read_file=True,
        allow_write_file=False,
        allow_append_file=False,
        allow_list_dir=True,
        allow_search_text=True,
        allow_run_command=True,
        allowed_command_prefixes=[
            "python",
            "pytest",
            "ls",
            "pwd",
            "rg",
            "grep",
            "cat",
            "head",
            "tail",
            "sed",
        ],
    ),
    "dev": ToolPolicy(
        mode="dev",
        allow_read_file=True,
        allow_write_file=True,
        allow_append_file=True,
        allow_list_dir=True,
        allow_search_text=True,
        allow_run_command=True,
        allowed_command_prefixes=[
            "python",
            "pytest",
            "alembic",
            "git status",
            "git rev-parse",
            "git branch",
            "ls",
            "pwd",
            "rg",
            "grep",
            "cat",
            "head",
            "tail",
            "sed",
            "make",
            "npm test",
            "npm run",
            "pnpm test",
            "pnpm run",
            "yarn test",
            "yarn run",
        ],
    ),
    "deploy": ToolPolicy(
        mode="deploy",
        allow_read_file=True,
        allow_write_file=True,
        allow_append_file=True,
        allow_list_dir=True,
        allow_search_text=True,
        allow_run_command=True,
        allowed_command_prefixes=[
            "python",
            "pytest",
            "alembic",
            "git status",
            "git rev-parse",
            "git branch",
            "ls",
            "pwd",
            "rg",
            "grep",
            "cat",
            "head",
            "tail",
            "sed",
            "make",
            "npm test",
            "npm run",
            "pnpm test",
            "pnpm run",
            "yarn test",
            "yarn run",
            "docker compose",
            "render",
        ],
    ),
    "production_safe": ToolPolicy(
        mode="production_safe",
        allow_read_file=True,
        allow_write_file=False,
        allow_append_file=False,
        allow_list_dir=True,
        allow_search_text=True,
        allow_run_command=True,
        allowed_command_prefixes=[
            "python",
            "pytest",
            "git status",
            "git rev-parse",
            "ls",
            "pwd",
            "rg",
            "grep",
            "cat",
            "head",
            "tail",
            "sed",
            "curl",
        ],
    ),
}


def get_tool_policy(mode: str) -> ToolPolicy:
    if mode not in POLICIES:
        raise ValueError(f"Unknown AGENT_TOOL_MODE: {mode}")
    return POLICIES[mode]