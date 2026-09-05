"""FastAPI application: the single source of truth for the OpenAPI schema.

The app is built by :func:`create_app` so tests and the schema exporter share
exactly the construction the server uses -- there is no second code path that
could drift from the running service.
"""

from __future__ import annotations

import os

from capstat_core import NELSON_RULES, WESTERN_ELECTRIC_RULES
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from capstat_api import __version__
from capstat_api.limits import DEFAULT_MAX_COMPUTE_BYTES, ComputeBodyLimit
from capstat_api.routers import compute, ingest

DESCRIPTION = (
    "Stateless HTTP surface over capstat-core: reference-validated SPC, "
    "process-capability and run-rule statistics, plus CSV/XLSX ingestion. "
    "Every response mirrors a core dataclass faithfully, warnings included."
)

# The Next.js dev server runs on :3000; the browser makes a cross-origin call to
# this API, which the same-origin policy blocks without an explicit allow-list.
# Both hostnames are permitted because either can reach a local dev server.
# Override with a comma-separated CAPSTAT_CORS_ORIGINS for other deployments.
_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def _cors_origins() -> list[str]:
    raw = os.environ.get("CAPSTAT_CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _max_compute_bytes() -> int:
    """The compute body ceiling, overridable for an unusual deployment.

    Invalid or non-positive settings fall back to the default rather than
    disabling the guard: a typo in an environment variable must not be the way
    the limit gets turned off.
    """
    raw = os.environ.get("CAPSTAT_MAX_COMPUTE_BYTES")
    if raw is None:
        return DEFAULT_MAX_COMPUTE_BYTES
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_COMPUTE_BYTES
    return value if value > 0 else DEFAULT_MAX_COMPUTE_BYTES


def create_app() -> FastAPI:
    app = FastAPI(
        title="capstat API",
        version=__version__,
        description=DESCRIPTION,
    )
    # Only the browser needs CORS; it is not part of the HTTP contract, so the
    # OpenAPI schema (and its drift check) is unaffected. GET/POST suffice for
    # the compute and ingest surface; no credentials are ever sent.
    # Transport-level, so the OpenAPI contract is unchanged (T-0063). Added
    # *before* CORS on purpose: add_middleware puts the last one added on the
    # outside, so this ordering leaves CORS outermost and its headers therefore
    # reach the 413. Reversed, a browser could not read the refusal -- it would
    # see an opaque CORS failure instead of the message saying what the limit is.
    app.add_middleware(ComputeBodyLimit, max_bytes=_max_compute_bytes())
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(compute.router)
    app.include_router(ingest.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/rules/catalogue", tags=["meta"])
    def rules_catalogue() -> dict[str, dict[int, str]]:
        """The human-readable rule descriptions, keyed by rule number."""
        return {
            "nelson": dict(NELSON_RULES),
            "western_electric": dict(WESTERN_ELECTRIC_RULES),
        }

    return app


app = create_app()
