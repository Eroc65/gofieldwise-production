from typing import Iterable

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
]


def has_stall_language(text: str) -> bool:
    lowered = (text or "").lower()
    return any(pattern in lowered for pattern in STALL_PATTERNS)


def choose_next_slice(options: list[str]) -> str:
    priority_order = [
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
    ]

    lowered_options = [o.lower() for o in options]
    for priority in priority_order:
        for i, option in enumerate(lowered_options):
            if priority in option:
                return options[i]

    return options[0]


def extract_hard_blockers(blockers: Iterable[str]) -> list[str]:
    out: list[str] = []
    for blocker in blockers:
        if blocker in HARD_BLOCKERS:
            out.append(blocker)
    return out
