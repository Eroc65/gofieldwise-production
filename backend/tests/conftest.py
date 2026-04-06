from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["APP_TESTING"] = "1"

# Ensure tests can import `app` even if pytest is invoked from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app  # noqa: E402


@pytest.fixture()
def app():
    return create_app(testing=True)


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client
