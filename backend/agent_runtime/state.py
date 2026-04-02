from dataclasses import dataclass, field
from typing import Any


StepStatus = str  # success | failed | blocked


@dataclass
class StepResult:
    role: str
    objective: str
    status: StepStatus
    summary: str
    artifacts: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    next_recommended_role: str | None = None
    next_objective: str | None = None
    done: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionState:
    user_goal: str
    repo_context: dict[str, Any] = field(default_factory=dict)
    completed_steps: list[StepResult] = field(default_factory=list)
    pending_objectives: list[dict[str, str]] = field(default_factory=list)
    active_objective: dict[str, str] | None = None
    blockers: list[str] = field(default_factory=list)
    done: bool = False
    loop_count: int = 0
    max_loops: int = 20

    def add_pending(self, role: str, objective: str) -> None:
        self.pending_objectives.append({"role": role, "objective": objective})

    def prepend_pending(self, role: str, objective: str) -> None:
        self.pending_objectives.insert(0, {"role": role, "objective": objective})

    def add_step(self, result: StepResult) -> None:
        self.completed_steps.append(result)
        if result.status == "blocked":
            self.blockers.extend(result.blockers)

    @property
    def latest_step(self) -> StepResult | None:
        return self.completed_steps[-1] if self.completed_steps else None
