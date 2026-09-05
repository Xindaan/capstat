"""A size limit on compute request bodies.

``/ingest`` has capped uploads at 10 MB since T-0056. The ``/compute/*``
endpoints had no limit at all: they take ``list[float]`` with no maximum, and
the only middleware was CORS. Measured on this code, a body of 2,000,000 floats
is 13.15 MB on the wire and costs about 214 MB of resident memory once parsed --
roughly a 16x amplification, per concurrent request. It is not a CPU problem;
the same request computes in 0.43 s. The failure mode is an out-of-memory kill,
which nobody reads (T-0063).

Why a byte limit in middleware, rather than ``max_length`` on each field:
the resource at risk is memory, memory is bytes, and an element count is only a
proxy for it. A transport-level guard also leaves the published OpenAPI schema
untouched, so the contract and its generated client do not change. The price is
stated plainly in the docs: the limit is *not* visible in the schema, so a
client learns it by receiving a 413.

Why buffering here is the protection rather than a cost: the body is read in
chunks and abandoned at the first chunk that crosses the limit, so at most one
chunk beyond it is ever held -- the same shape as the ingest guard, and for the
same reason. Trusting ``Content-Length`` alone would not do: a chunked request
does not send one, and a lying one is exactly the case worth defending against.

``/ingest`` is deliberately *not* covered. It already counts its own chunks, and
wrapping it here would force a streamed upload to be held in memory twice.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

#: Default ceiling for a single compute request body. Matches ``/ingest``'s
#: upload cap on purpose: a 10 MB CSV with one numeric column yields a compute
#: body of roughly 7 MB, so a smaller ceiling here would accept a file and then
#: refuse to compute it -- an asymmetry with no defensible explanation. At this
#: size a request carries about 1.5 million points, three orders of magnitude
#: beyond any capability study.
DEFAULT_MAX_COMPUTE_BYTES = 10 * 1024 * 1024

HTTP_413 = 413  # Content Too Large


class ComputeBodyLimit:
    """ASGI middleware refusing an oversized body on the compute endpoints.

    Written as raw ASGI rather than a ``BaseHTTPMiddleware`` subclass because
    the decision has to be made *while* the body arrives. Starlette's HTTP
    middleware hands over a request whose body is already assembled, which is
    the moment the memory has been spent.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int = DEFAULT_MAX_COMPUTE_BYTES,
        path_prefix: str = "/compute",
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.path_prefix = path_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or not path.startswith(self.path_prefix):
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                # A disconnect before the body finished. Hand it on and let the
                # server deal with it; there is nothing to judge.
                await self.app(scope, _replay(message), send)
                return
            total += len(message.get("body", b""))
            if total > self.max_bytes:
                await self._refuse(send)
                return
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break

        await self.app(scope, _replay_body(b"".join(chunks)), send)

    async def _refuse(self, send: Send) -> None:
        megabytes = self.max_bytes // (1024 * 1024)
        detail = (
            f"Request body exceeds the {megabytes} MB limit for compute "
            f"endpoints. Send fewer points per request: a capability study "
            f"needs tens of measurements, not millions."
        )
        body = json.dumps({"detail": detail}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": HTTP_413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def _replay_body(body: bytes) -> Receive:
    """Hand the buffered body to the app once, then report a disconnect."""
    delivered = False

    async def receive() -> Message:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _replay(message: Message) -> Receive:
    """Hand one already-read message back to the app."""

    async def receive() -> Message:
        return message

    return receive
