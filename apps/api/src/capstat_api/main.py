"""FastAPI application: the single source of truth for the OpenAPI schema.

The app is built by :func:`create_app` so tests and the schema exporter share
exactly the construction the server uses -- there is no second code path that
could drift from the running service.
"""

from __future__ import annotations

from capstat_core import NELSON_RULES, WESTERN_ELECTRIC_RULES
from fastapi import FastAPI

from capstat_api import __version__
from capstat_api.routers import compute, ingest

DESCRIPTION = (
    "Stateless HTTP surface over capstat-core: reference-validated SPC, "
    "process-capability and run-rule statistics, plus CSV/XLSX ingestion. "
    "Every response mirrors a core dataclass faithfully, warnings included."
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="capstat API",
        version=__version__,
        description=DESCRIPTION,
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
