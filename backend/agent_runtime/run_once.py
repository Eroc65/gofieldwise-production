from __future__ import annotations

import json
from pathlib import Path

from agent_runtime.orchestrator import format_final_output, run_orchestration


if __name__ == "__main__":
    repo_root = str(Path(__file__).resolve().parents[1])

    goal = "Build the next highest-leverage FrontDesk Pro vertical slice from the repo context."
    repo_context = {
        "repo_root": repo_root,
        "product": "FrontDesk Pro",
        "priority_order": [
            "inbound capture",
            "missed call recovery",
            "ai intake",
            "lead qualification",
            "follow-up automation",
            "booking",
            "scheduling",
            "dispatch",
            "billing",
            "reporting",
        ],
    }

    state = run_orchestration(goal, repo_context=repo_context, max_loops=12)
    print(json.dumps(format_final_output(state), indent=2))
