"""Ingestion: parse CSV/XLSX to numeric columns, and say what was dropped."""

from __future__ import annotations

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

CSV = b"width,height,label\n1.0,2.0,a\n3.0,4.0,b\n5.0,6.0,c\n"


def _xlsx(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def test_csv_extracts_numeric_columns(client: TestClient) -> None:
    resp = client.post("/ingest", files={"file": ("data.csv", CSV, "text/csv")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_rows"] == 3
    names = {c["name"] for c in body["columns"]}
    assert names == {"width", "height"}
    width = next(c for c in body["columns"] if c["name"] == "width")
    assert width["values"] == [1.0, 3.0, 5.0]
    # The text column is named as ignored, not silently gone.
    assert body["ignored_columns"] == ["label"]
    assert any("label" in w for w in body["warnings"])


def test_csv_counts_dropped_missing(client: TestClient) -> None:
    # A blank cell *within* a row: pandas skips wholly blank lines, so the gap
    # must sit beside a populated column to survive as a missing value.
    csv = b"x,y\n1.0,2.0\n,4.0\n5.0,6.0\n"
    body = client.post("/ingest", files={"file": ("g.csv", csv, "text/csv")}).json()
    x = next(c for c in body["columns"] if c["name"] == "x")
    assert x["values"] == [1.0, 5.0]
    assert x["dropped_missing"] == 1
    assert any("dropped" in w for w in body["warnings"])


def test_xlsx_round_trip(client: TestClient) -> None:
    frame = pd.DataFrame({"m": [0.1, 0.2, 0.3], "note": ["p", "q", "r"]})
    body = client.post(
        "/ingest",
        files={"file": ("d.xlsx", _xlsx(frame), "application/vnd.ms-excel")},
    ).json()
    assert [c["name"] for c in body["columns"]] == ["m"]
    assert body["columns"][0]["values"] == [0.1, 0.2, 0.3]
    assert body["ignored_columns"] == ["note"]


def test_unsupported_type_is_415(client: TestClient) -> None:
    resp = client.post("/ingest", files={"file": ("d.txt", b"1 2 3", "text/plain")})
    assert resp.status_code == 415


def test_unparseable_csv_is_422(client: TestClient) -> None:
    resp = client.post("/ingest", files={"file": ("empty.csv", b"", "text/csv")})
    assert resp.status_code == 422


def test_all_text_yields_no_columns_warning(client: TestClient) -> None:
    body = client.post(
        "/ingest", files={"file": ("t.csv", b"a,b\nx,y\n", "text/csv")}
    ).json()
    assert body["columns"] == []
    assert any("No numeric columns" in w for w in body["warnings"])


def test_oversized_file_is_413(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("capstat_api.routers.ingest.MAX_BYTES", 4)
    resp = client.post("/ingest", files={"file": ("big.csv", CSV, "text/csv")})
    assert resp.status_code == 413
