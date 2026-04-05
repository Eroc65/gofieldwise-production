from __future__ import annotations

from backend.agent_runtime.policy import (  # re-export runtime policy as single source of truth
    AGENT_DESCRIPTION,
    AgentRole,
    AutonomyPolicy,
    HOW_DO_YOU_FIX_PROBLEMS,
    SYSTEM_PROMPT,
)

CAPABILITY_STATEMENT = " ".join(AGENT_DESCRIPTION.strip().split())
HOW_FIX_PROBLEMS_STATEMENT = " ".join(HOW_DO_YOU_FIX_PROBLEMS.strip().split())


if __name__ == "__main__":
    print(CAPABILITY_STATEMENT)
    print()
    print(HOW_FIX_PROBLEMS_STATEMENT)
