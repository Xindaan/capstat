"""The API contract: schema stability, strict inputs, error mapping.

These guard the three ways the surface could quietly rot: the committed schema
drifting from the code, a mistyped field being ignored, and a core domain error
leaking as a 500 instead of a 422.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from capstat_api import export_openapi
from capstat_api.export_openapi import SCHEMA_PATH, main, render
from fastapi.testclient import TestClient


def test_committed_openapi_is_current() -> None:
    # The same check CI runs: the tracked schema must describe the same API as
    # a fresh render. Compared as parsed documents, not bytes -- see the module
    # docstring of export_openapi for why byte equality is the wrong assertion.
    committed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert committed == json.loads(render()), (
        "openapi.json is stale; run `uv run python -m capstat_api.export_openapi`."
    )


def test_warnings_are_in_the_schema() -> None:
    # The contract must carry the warnings field, not just the runtime response.
    schema = render()
    assert '"warnings"' in schema
    assert "CapabilityReportOut" in schema


def test_unknown_field_is_rejected(client: TestClient) -> None:
    resp = client.post(
        "/compute/descriptive",
        json={"data": [1.0, 2.0, 3.0], "smaple": True},
    )
    assert resp.status_code == 422


def test_core_domain_error_maps_to_422(client: TestClient) -> None:
    # capability with no spec limits is undefined; the core raises ValueError,
    # which must surface as 422 with the core's message, not a 500.
    resp = client.post("/compute/capability", json={"data": [1.0, 2.0, 3.0]})
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)


def test_empty_data_is_rejected_by_schema(client: TestClient) -> None:
    resp = client.post("/compute/descriptive", json={"data": []})
    assert resp.status_code == 422


def test_exporter_write_then_check_roundtrips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "openapi.json"
    monkeypatch.setattr(export_openapi, "SCHEMA_PATH", target)
    assert main([]) == 0  # writes
    assert target.exists()
    assert main(["--check"]) == 0  # fresh render matches what was written


def test_exporter_check_detects_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "openapi.json"
    target.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(export_openapi, "SCHEMA_PATH", target)
    assert main(["--check"]) == 1


def test_exporter_check_accepts_a_foreign_json_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # release-please stamps info.version and rewrites the file with JavaScript's
    # JSON writer, which renders 5.0 as 5. Same contract, different bytes -- and
    # a byte-for-byte check failed the 0.1.0 release commit over exactly this.
    target = tmp_path / "openapi.json"
    target.write_text(
        json.dumps(json.loads(render()), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    monkeypatch.setattr(export_openapi, "SCHEMA_PATH", target)
    assert "5.0" in render()  # the float this is about is really in the schema
    assert main(["--check"]) == 0


def test_exporter_check_still_catches_a_changed_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The looser comparison must not blunt the guard: a value that differs by
    # more than its formatting is still drift.
    schema = json.loads(render())
    schema["info"]["version"] = "9.9.9-not-the-code"
    target = tmp_path / "openapi.json"
    target.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    monkeypatch.setattr(export_openapi, "SCHEMA_PATH", target)
    assert main(["--check"]) == 1


def test_exporter_check_flags_unparseable_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "openapi.json"
    target.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(export_openapi, "SCHEMA_PATH", target)
    assert main(["--check"]) == 1


def test_exporter_check_flags_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(export_openapi, "SCHEMA_PATH", tmp_path / "absent.json")
    assert main(["--check"]) == 1


def test_an_already_split_caveat_passes_through(client: TestClient) -> None:
    """The wire form validates as itself, not only the core's str subclass.

    `_as_caveat` has to be idempotent: the API re-validates its own models in
    places (nested reports), and a dict arriving there must not be rewrapped.
    """
    from capstat_api.schemas import CaveatOut, _as_caveat

    already = {"code": "capability.no-target", "message": "no target was given"}
    assert _as_caveat(already) is already
    model = CaveatOut.model_validate(already)
    assert model.code == "capability.no-target"
