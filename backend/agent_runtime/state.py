from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    role: str
    objective: str
    status: str  # success | failed | blocked
    summary: str
    artifacts: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    next_recommended_role: str | None = None
    next_objective: str | None = None


@dataclass
class ExecutionState:
    user_goal: str
    repo_context: dict[str, Any] = field(default_factory=dict)
    completed_steps: list[StepResult] = field(default_factory=list)
    pending_objectives: list[dict[str, str]] = field(default_factory=list)
    active_objective: dict[str, str] | None = None
    blockers: list[str] = field(default_factory=list)
    done: bool = False
    max_loops: int = 20
    loop_count: int = 0
