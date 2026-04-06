from __future__ import annotations

from .factory import create_app

__all__ = ["create_app"]

# Backward compatibility for existing tests that still import `app` directly.
app = create_app()
