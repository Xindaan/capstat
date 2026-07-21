"""Write (or verify) the committed OpenAPI schema.

The schema is the contract the TypeScript client is generated from, so it is a
tracked artefact, not a build output. CI runs ``--check``: it regenerates the
schema from the live app and fails if the committed file describes a different
API, catching the case where an endpoint changed but the contract was not
refreshed.

The comparison is *semantic*, not byte-for-byte, because the committed file is
not only written by us: release-please rewrites it to stamp ``info.version``,
and its JavaScript JSON writer cannot tell ``5.0`` from ``5``. A byte-for-byte
check failed the release commit over three whitespace-equivalent numbers -- a
red build on an artefact nobody had touched. What this check must guarantee is
that the contract matches the code, so it compares the parsed documents.

Usage::

    python -m capstat_api.export_openapi          # write openapi.json
    python -m capstat_api.export_openapi --check   # fail on drift
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from capstat_api.main import create_app

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "openapi.json"


def render() -> str:
    """Deterministic JSON so the diff is stable across runs and platforms."""
    schema = create_app().openapi()
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    rendered = render()

    if "--check" in args:
        if not SCHEMA_PATH.exists():
            print(f"error: {SCHEMA_PATH} is missing; run the exporter.")
            return 1
        current = SCHEMA_PATH.read_text(encoding="utf-8")
        try:
            committed = json.loads(current)
        except json.JSONDecodeError as exc:
            print(f"error: openapi.json is not valid JSON ({exc}).")
            return 1
        if committed != json.loads(rendered):
            print(
                "error: openapi.json is out of date.\n"
                "Regenerate with: uv run python -m capstat_api.export_openapi"
            )
            return 1
        if current != rendered:
            # Same API, different bytes -- a foreign writer reformatted the file.
            # Not a failure: the contract is intact, and forcing byte equality
            # here is what broke the release commit.
            print("openapi.json is up to date (formatting differs from ours).")
            return 0
        print("openapi.json is up to date.")
        return 0

    SCHEMA_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {SCHEMA_PATH}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
