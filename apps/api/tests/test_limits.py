"""The compute body ceiling (T-0063).

`/ingest` has capped uploads since T-0056; `/compute/*` had no limit at all.
The guard is transport-level, so these tests work in bytes rather than in
schema fields -- and they check the two things a size guard is usually got
wrong on: that it does not trust Content-Length, and that a refusal is still
readable by the browser that provoked it.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator, MutableMapping
from typing import Any

import pytest
from capstat_api.limits import DEFAULT_MAX_COMPUTE_BYTES, ComputeBodyLimit
from capstat_api.main import _max_compute_bytes, create_app
from fastapi.testclient import TestClient


def _series_body(points: int) -> bytes:
    return json.dumps(
        {
            "data": [10.0 + (i % 97) * 0.01 for i in range(points)],
            "lsl": 9.0,
            "usl": 12.0,
        }
    ).encode()


def test_a_realistic_series_is_unaffected(client: TestClient) -> None:
    # 100 000 points is 0.66 MB -- three orders of magnitude beyond a real
    # capability study, and still well inside the limit.
    body = _series_body(100_000)
    assert len(body) < DEFAULT_MAX_COMPUTE_BYTES
    resp = client.post(
        "/compute/capability",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 200


def test_an_oversized_body_is_refused_with_the_limit_stated(client: TestClient) -> None:
    body = b'{"data": [' + b"1.0," * 3_000_000 + b'1.0], "lsl": 0, "usl": 2}'
    assert len(body) > DEFAULT_MAX_COMPUTE_BYTES
    resp = client.post(
        "/compute/capability",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 413
    detail = resp.json()["detail"]
    assert "10 MB" in detail
    # It says what to do, not just that something was wrong.
    assert "fewer points" in detail


def test_the_guard_does_not_trust_content_length(client: TestClient) -> None:
    """A chunked body sends no Content-Length, and a lying one is the case
    worth defending against. The bytes are counted as they arrive."""

    def chunks() -> Iterator[bytes]:
        yield b'{"data": ['
        for _ in range(3_000):
            yield b"1.0," * 1_000
        yield b'1.0], "lsl": 0, "usl": 2}'

    resp = client.post(
        "/compute/capability",
        content=chunks(),
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 413


def test_a_refusal_still_carries_the_cors_headers(client: TestClient) -> None:
    """Ordering check: the limit sits inside CORS, not outside it.

    Reversed, a browser would see an opaque CORS failure instead of the
    sentence naming the limit -- the error would be unreadable exactly where it
    is most needed.
    """
    body = b'{"data": [' + b"1.0," * 3_000_000 + b'1.0], "lsl": 0, "usl": 2}'
    resp = client.post(
        "/compute/capability",
        content=body,
        headers={"content-type": "application/json", "origin": "http://localhost:3000"},
    )
    assert resp.status_code == 413
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_ingest_keeps_its_own_guard(client: TestClient) -> None:
    """`/ingest` is deliberately outside this middleware.

    It counts its own chunks, and wrapping it here would hold a streamed
    upload in memory twice. Its 413 is still its own.
    """
    oversized = b"diameter\n" + b"1.0\n" * 6_000_000
    resp = client.post("/ingest", files={"file": ("big.csv", oversized, "text/csv")})
    assert resp.status_code == 413
    assert "MB limit" in resp.json()["detail"]


def test_other_routes_are_not_wrapped(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    assert client.get("/rules/catalogue").status_code == 200


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, DEFAULT_MAX_COMPUTE_BYTES),
        ("2048", 2048),
        ("not-a-number", DEFAULT_MAX_COMPUTE_BYTES),
        ("0", DEFAULT_MAX_COMPUTE_BYTES),
        ("-1", DEFAULT_MAX_COMPUTE_BYTES),
    ],
)
def test_the_ceiling_is_configurable_but_cannot_be_typoed_away(
    monkeypatch: pytest.MonkeyPatch, raw: str | None, expected: int
) -> None:
    if raw is None:
        monkeypatch.delenv("CAPSTAT_MAX_COMPUTE_BYTES", raising=False)
    else:
        monkeypatch.setenv("CAPSTAT_MAX_COMPUTE_BYTES", raw)
    assert _max_compute_bytes() == expected


def test_a_configured_ceiling_actually_applies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAPSTAT_MAX_COMPUTE_BYTES", "512")
    configured = TestClient(create_app())
    resp = configured.post("/compute/descriptive", json={"data": [1.0] * 500})
    assert resp.status_code == 413


# --- The ASGI paths a TestClient request never takes -------------------------
# Driven directly, because they are about what happens when the *transport*
# misbehaves: a client that hangs up mid-body, and an app that reads the body
# twice. Both are reachable in production and neither is reachable through a
# well-behaved HTTP client. Run with asyncio.run rather than an async test
# plugin -- two coroutines do not justify a new dev dependency.

Message = MutableMapping[str, Any]


def _drive(app: ComputeBodyLimit, messages: list[Message]) -> list[Message]:
    """Feed `messages` to `app` and return what the inner app received."""
    received: list[Message] = []
    stream = iter(messages)

    async def receive() -> Message:
        return next(stream)

    async def send(message: Message) -> None:
        return None

    async def inner(scope: Message, rcv: object, snd: object) -> None:
        received.append(await rcv())  # type: ignore[operator]
        # A second read must report the end of the stream, not repeat the body.
        received.append(await rcv())  # type: ignore[operator]

    app.app = inner
    scope: Message = {"type": "http", "path": "/compute/descriptive", "headers": []}
    asyncio.run(app(scope, receive, send))
    return received


def test_a_client_hanging_up_mid_body_is_passed_on() -> None:
    """A disconnect is the server's business, not a size verdict."""
    limit = ComputeBodyLimit(lambda *_: None, max_bytes=1024)  # type: ignore[arg-type]
    received = _drive(limit, [{"type": "http.disconnect"}])
    assert received[0] == {"type": "http.disconnect"}


def test_a_body_arriving_in_several_chunks_is_reassembled() -> None:
    """The under-limit multi-chunk path: counted, buffered, handed on whole."""
    limit = ComputeBodyLimit(lambda *_: None, max_bytes=1024)  # type: ignore[arg-type]
    received = _drive(
        limit,
        [
            {"type": "http.request", "body": b'{"a":', "more_body": True},
            {"type": "http.request", "body": b" 1}", "more_body": False},
        ],
    )
    assert received[0] == {
        "type": "http.request",
        "body": b'{"a": 1}',
        "more_body": False,
    }
    assert received[1] == {"type": "http.disconnect"}
