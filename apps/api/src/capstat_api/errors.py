"""Turn capstat-core input errors into HTTP responses.

The core raises ``ValueError`` for domain-invalid input (too few points, a
degenerate subgroup, a spec that makes an index undefined). That is a client
error, not a server fault, so it maps to HTTP 422 with the core's own message
preserved -- the message is part of what makes the library trustworthy and
should reach the caller verbatim.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException

# 422 Unprocessable Content. Used as an int literal rather than the Starlette
# constant, whose name churned (ENTITY -> CONTENT) and emits a deprecation
# warning; the code itself is stable.
HTTP_422 = 422


@contextmanager
def core_errors() -> Iterator[None]:
    try:
        yield
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_422, detail=str(exc)) from exc
