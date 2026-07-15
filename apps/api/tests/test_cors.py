"""CORS: the browser's cross-origin call from the Next.js dev server must pass.

The compute/ingest surface is called from a page served on :3000; without an
explicit allow-list the browser blocks the response. These tests pin the
allowed origin, the rejection of an unknown one, and the env override -- the
one behaviour the OpenAPI contract cannot express.
"""

from __future__ import annotations

import pytest
from capstat_api.main import create_app
from fastapi.testclient import TestClient

ALLOWED = "http://localhost:3000"
FOREIGN = "https://evil.example"


def test_preflight_allows_dev_origin() -> None:
    client = TestClient(create_app())
    resp = client.options(
        "/ingest",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == ALLOWED


def test_actual_request_echoes_allowed_origin() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/compute/descriptive",
        json={"data": [1.0, 2.0, 3.0]},
        headers={"Origin": ALLOWED},
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == ALLOWED


def test_unknown_origin_is_not_allowed() -> None:
    client = TestClient(create_app())
    resp = client.post(
        "/compute/descriptive",
        json={"data": [1.0, 2.0, 3.0]},
        headers={"Origin": FOREIGN},
    )
    # The request still succeeds server-side; the browser is what blocks it,
    # because no allow-origin header names the foreign origin.
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") != FOREIGN


def test_env_override_replaces_default_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom = "https://capstat.example"
    monkeypatch.setenv("CAPSTAT_CORS_ORIGINS", custom)
    client = TestClient(create_app())
    resp = client.post(
        "/compute/descriptive",
        json={"data": [1.0, 2.0, 3.0]},
        headers={"Origin": custom},
    )
    assert resp.headers["access-control-allow-origin"] == custom
    # The built-in default no longer applies once overridden.
    resp_default = client.post(
        "/compute/descriptive",
        json={"data": [1.0, 2.0, 3.0]},
        headers={"Origin": ALLOWED},
    )
    assert resp_default.headers.get("access-control-allow-origin") != ALLOWED
