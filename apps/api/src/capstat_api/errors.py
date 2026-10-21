"""Turn capstat-core input errors into HTTP responses.

The core raises ``ValueError`` for domain-invalid input (too few points, a
degenerate subgroup, a spec that makes an index undefined). That is a client
error, not a server fault, so it maps to HTTP 422 with the core's own message
preserved -- the message is part of what makes the library trustworthy and
should reach the caller verbatim.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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


def _json_safe(value: Any) -> Any:
    """``value`` with every non-finite float replaced by its JSON-ish name.

    JSON has no NaN or Infinity, and the response encoder refuses them.
    """
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "NaN"
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    return value


async def request_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI's own 422 for an invalid request, safe for NaN and Infinity.

    The default handler echoes each offending ``input`` back. When that input
    is NaN or Infinity -- an out-of-range ``aql``, a NaN where an int belongs,
    or any float now that requests refuse non-finite numbers -- encoding the
    422 raised, and the caller got a plain-text 500 from outside the CORS
    middleware instead of the error naming the field (T-0105, API-3). Same
    status, same ``{"detail": [...]}`` shape; only the unencodable numbers
    become strings.
    """
    assert isinstance(exc, RequestValidationError)  # registered for that type
    return JSONResponse(
        status_code=HTTP_422,
        content={"detail": jsonable_encoder(_json_safe(exc.errors()))},
    )
