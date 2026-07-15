"""Shared fixtures for the API tests."""

from __future__ import annotations

import pytest
from capstat_api.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())
