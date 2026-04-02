from datetime import datetime
from typing import Any, Iterable

HARD_BLOCKERS = {
    "MISSING_CREDENTIAL",
    "DESTRUCTIVE_ACTION_REQUIRES_APPROVAL",
    "EXTERNAL_SYSTEM_ACCESS_DENIED",
    "PRODUCT_DIRECTION_AMBIGUITY",
    "COMPLIANCE_OR_SAFETY_REVIEW_REQUIRED",
}

STALL_PATTERNS = [
    "which would you like",
    "should i proceed",
    "let me know if you want",
    "i can do x or y",
    "do you want me to continue",
    "which should i do first",
]


ROADMAP_PRIORITY = [
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
    "ui shell",
    "dashboard",
]


def is_hard_blocker(code: str) -> bool:
    return code in HARD_BLOCKERS


def looks_like_stall(text: str) -> bool:
    lowered = (text or "").lower()
    return any(pattern in lowered for pattern in STALL_PATTERNS)


def has_stall_language(text: str) -> bool:
    # Backward-compatible alias used by existing tests/callers.
    return looks_like_stall(text)


def choose_next_slice(options: list[str]) -> str:
    lowered_options = [(opt, opt.lower()) for opt in options]
    for priority in ROADMAP_PRIORITY:
        for original, lowered in lowered_options:
            if priority in lowered:
                return original

    return options[0]


def build_noncompliance_fix_objective() -> str:
    return (
        "Do not ask the user to choose between valid next steps. "
        "Choose the highest-leverage option from the roadmap and continue implementation."
    )


def utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def summarize_state_counts(summary: dict[str, Any]) -> str:
    return (
        f"critical_passed={summary.get('critical_passed', 0)} "
        f"critical_failed={summary.get('critical_failed', 0)} "
        f"noncritical_passed={summary.get('noncritical_passed', 0)} "
        f"noncritical_failed={summary.get('noncritical_failed', 0)}"
    )


def extract_hard_blockers(blockers: Iterable[str]) -> list[str]:
    out: list[str] = []
    for blocker in blockers:
        if is_hard_blocker(blocker):
            out.append(blocker)
    return out
