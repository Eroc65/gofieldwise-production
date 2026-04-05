from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    testing: bool
    enable_startup_side_effects: bool


def load_settings(*, testing: bool = False) -> Settings:
    env_testing = os.getenv("APP_TESTING", "").strip().lower() in {"1", "true", "yes", "on"}
    is_testing = testing or env_testing
    return Settings(
        testing=is_testing,
        enable_startup_side_effects=not is_testing,
    )
