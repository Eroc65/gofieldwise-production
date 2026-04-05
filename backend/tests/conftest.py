from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ["APP_TESTING"] = "1"

from app.main import create_app  # noqa: E402


@pytest.fixture()
def app():
    return create_app(testing=True)


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client
