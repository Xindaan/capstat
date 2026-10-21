"""Ingestion: parse CSV/XLSX to numeric columns, and say what was dropped."""

from __future__ import annotations

import asyncio
import io
from typing import Any, cast

import pandas as pd
import pytest
from capstat_api.tabular import repair_decimal_commas
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

CSV = b"width,height,label\n1.0,2.0,a\n3.0,4.0,b\n5.0,6.0,c\n"


def _xlsx(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def _messages(body: dict[str, object]) -> list[str]:
    """The prose half of each warning (T-0074 made them {code, message})."""
    warnings = body["warnings"]
    assert isinstance(warnings, list)
    return [w["message"] for w in warnings]


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
    assert any("label" in w for w in _messages(body))


def test_csv_counts_dropped_missing(client: TestClient) -> None:
    # A blank cell *within* a row: pandas skips wholly blank lines, so the gap
    # must sit beside a populated column to survive as a missing value.
    csv = b"x,y\n1.0,2.0\n,4.0\n5.0,6.0\n"
    body = client.post("/ingest", files={"file": ("g.csv", csv, "text/csv")}).json()
    x = next(c for c in body["columns"] if c["name"] == "x")
    assert x["values"] == [1.0, 5.0]
    assert x["dropped_missing"] == 1
    assert any("dropped" in w for w in _messages(body))


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
    assert any("No numeric columns" in w for w in _messages(body))


def test_oversized_file_is_413(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("capstat_api.routers.ingest.MAX_BYTES", 4)
    resp = client.post("/ingest", files={"file": ("big.csv", CSV, "text/csv")})
    assert resp.status_code == 413


class _RecordingUpload:
    """Stands in for ``UploadFile`` and remembers how much it handed over.

    The point of the size guard is not the status code -- that was always right
    -- but that an oversized body is never fully resident. Only the amount
    actually read can show that, so this counts it (T-0056).
    """

    def __init__(self, payload: bytes, filename: str = "big.csv") -> None:
        self._buffer = io.BytesIO(payload)
        self.filename = filename
        self.handed_out = 0

    async def read(self, size: int = -1) -> bytes:
        chunk = self._buffer.read(None if size < 0 else size)
        self.handed_out += len(chunk)
        return chunk


def test_an_oversized_upload_is_never_fully_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 413 that costs the whole body in memory has not protected anything.

    The comment on MAX_BYTES promised a guard against memory exhaustion; the
    body was read in full and only then measured, so an oversized upload cost
    its own size in RAM per request before being refused.
    """
    from capstat_api.routers import ingest as module

    monkeypatch.setattr(module, "MAX_BYTES", 1024)
    monkeypatch.setattr(module, "CHUNK_BYTES", 256)
    payload = b"x" * (1024 * 1024)  # a thousand times the limit
    upload = _RecordingUpload(payload)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(module.ingest_file(cast(UploadFile, upload)))

    assert raised.value.status_code == 413
    # Bounded by the limit plus the chunk that crossed it, not by the body.
    assert upload.handed_out <= module.MAX_BYTES + module.CHUNK_BYTES
    assert upload.handed_out < len(payload)


def test_a_file_at_the_limit_is_still_read_whole(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The negative side: the guard must not truncate a legitimate upload.

    A body exactly at the limit is valid, and chunked reading is the kind of
    change that quietly eats a final partial chunk.
    """
    from capstat_api.routers import ingest as module

    monkeypatch.setattr(module, "CHUNK_BYTES", 7)  # deliberately not a divisor
    rows = b"width\n" + b"".join(b"%d.0\n" % i for i in range(200))
    upload = _RecordingUpload(rows, filename="data.csv")

    result = asyncio.run(module.ingest_file(cast(UploadFile, upload)))
    assert result.n_rows == 200
    assert upload.handed_out == len(rows)
    assert result.columns[0].values[-1] == 199.0


def test_a_german_excel_csv_is_read_rather_than_ignored(client: TestClient) -> None:
    """Semicolons and decimal commas are what Excel writes in a German locale.

    Both failed silently: the file parsed as a single text column, so the
    measurements came back as an "ignored non-numeric column" and the user was
    told, in effect, that their numbers were not numbers (T-0067).
    """
    csv = b"durchmesser;charge\n9,71;1\n9,80;2\n9,75;3\n"
    body = client.post("/ingest", files={"file": ("m.csv", csv, "text/csv")}).json()

    values = {c["name"]: c["values"] for c in body["columns"]}
    assert values["durchmesser"] == [9.71, 9.80, 9.75]
    assert values["charge"] == [1.0, 2.0, 3.0]
    assert body["ignored_columns"] == []
    # And it says what it detected rather than fixing things behind the back.
    assert any("semicolon" in w for w in _messages(body))
    assert any("decimal comma" in w and "durchmesser" in w for w in _messages(body))


def test_a_decimal_comma_survives_a_comma_separated_file(client: TestClient) -> None:
    """The ambiguous case: separator and decimal mark are both commas.

    Quoting is what tells them apart, which is why the detection uses a
    quote-aware split rather than counting characters.
    """
    csv = b'diameter,batch\n"9,71",1\n"9,80",2\n"9,75",3\n'
    body = client.post("/ingest", files={"file": ("q.csv", csv, "text/csv")}).json()

    values = {c["name"]: c["values"] for c in body["columns"]}
    assert values["diameter"] == [9.71, 9.80, 9.75]
    assert values["batch"] == [1.0, 2.0, 3.0]
    assert any("decimal comma" in w for w in _messages(body))


def test_a_cp1252_file_is_read_and_the_encoding_is_named(client: TestClient) -> None:
    """The same Excel that writes semicolons often does not write UTF-8."""
    csv = "größe;wert\n1,5;2\n2,5;3\n".encode("cp1252")
    body = client.post("/ingest", files={"file": ("e.csv", csv, "text/csv")}).json()

    assert [c["name"] for c in body["columns"]] == ["größe", "wert"]
    assert any("cp1252" in w for w in _messages(body))


def test_a_utf8_bom_does_not_stick_to_the_first_column_name(
    client: TestClient,
) -> None:
    """Excel's UTF-8 CSV carries a byte-order mark, and plain utf-8 keeps it."""
    body = client.post(
        "/ingest",
        files={
            "file": ("b.csv", "width,height\n1.0,2.0\n".encode("utf-8-sig"), "text/csv")
        },
    ).json()
    assert [c["name"] for c in body["columns"]] == ["width", "height"]


def test_a_multi_sheet_workbook_says_which_sheet_it_read(client: TestClient) -> None:
    """Only the first sheet is read, and that was nowhere on the response."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"m": [1.0, 2.0]}).to_excel(
            writer, sheet_name="measurements", index=False
        )
        pd.DataFrame({"other": [9.0]}).to_excel(writer, sheet_name="notes", index=False)

    body = client.post(
        "/ingest",
        files={"file": ("w.xlsx", buffer.getvalue(), "application/vnd.ms-excel")},
    ).json()
    assert [c["name"] for c in body["columns"]] == ["m"]
    assert any("2 sheets" in w and "measurements" in w for w in _messages(body))


def test_a_text_column_holding_commas_is_not_turned_into_numbers(
    client: TestClient,
) -> None:
    """The repair fires only on a column that is *entirely* decimal commas.

    A label column with one numeric-looking entry must stay a label. Inventing
    measurements out of text is worse than ignoring the column, which is the
    failure this whole file exists to avoid.
    """
    csv = b'label,value\n"a,b",1.0\n"9,71",2.0\n'
    body = client.post("/ingest", files={"file": ("t.csv", csv, "text/csv")}).json()

    assert body["ignored_columns"] == ["label"]
    assert [c["name"] for c in body["columns"]] == ["value"]
    assert not any("decimal comma" in w for w in _messages(body))


def test_a_file_that_is_text_in_no_encoding_capstat_reads_is_422(
    client: TestClient,
) -> None:
    """The fallback chain ends somewhere, and it ends with a stated reason."""
    # 0x81 and 0x8d are a stray continuation byte in UTF-8 and undefined in
    # cp1252, so neither decoder can claim this.
    resp = client.post(
        "/ingest", files={"file": ("bin.csv", b"\x81\x8d\x90", "text/csv")}
    )
    assert resp.status_code == 422
    assert "utf-8 and cp1252" in resp.json()["detail"]


def test_an_empty_column_is_not_reported_as_repaired() -> None:
    """A column with nothing in it has no decimal mark to have been read.

    `Series.all()` is vacuously true on an empty series, so without the guard an
    all-empty column would be listed among those whose decimal comma was
    converted -- a warning describing something that never happened.
    """

    frame = pd.DataFrame(
        {
            "blank": pd.Series([None, None], dtype=object),
            "real": pd.Series(["9,71", "9,80"], dtype=object),
        }
    )
    assert repair_decimal_commas(frame) == ["real"]
    assert frame["real"].tolist() == [9.71, 9.80]


# --- T-0095: files pandas read silently wrong ---------------------------------


def _ingest(client: TestClient, name: str, data: bytes) -> dict[str, Any]:
    resp = client.post("/ingest", files={"file": (name, data, "text/csv")})
    assert resp.status_code == 200, resp.text
    return cast(dict[str, Any], resp.json())


def _codes(body: dict[str, Any]) -> list[str]:
    return [w["code"] for w in body["warnings"]]


def _values(body: dict[str, Any]) -> dict[str, list[float]]:
    return {c["name"]: c["values"] for c in body["columns"]}


@pytest.mark.parametrize(
    "raw",
    [
        b"Wert\n9,79\n9,72\n9,70\n",
        b"Wert\r\n9,79\r\n9,72\r\n9,70\r\n",
        "﻿Wert\r\n9,79\r\n9,72\r\n9,70\r\n".encode(),
        b"Wert\n\n9,79\n9,72\n9,70\n",
    ],
    ids=["lf", "crlf", "bom-crlf", "blank-line"],
)
def test_a_one_column_german_csv_is_read_as_decimals_not_as_an_index(
    client: TestClient, raw: bytes
) -> None:
    """No separator exists in a one-column export, so every comma is a decimal mark.

    pandas took the comma as the separator and made the integer part the row
    index: 9,79 came back as 79 and a Cpk of 1.9 as -8.6, with no warning
    (API-1 / TQ-17).
    """
    body = _ingest(client, "m.csv", raw)
    assert _values(body) == {"Wert": [9.79, 9.72, 9.70]}
    assert body["ignored_columns"] == []
    # What was detected is named, not applied behind the user's back.
    assert "ingest.single-column-detected" in _codes(body)
    assert "ingest.decimal-comma-detected" in _codes(body)


def test_a_one_column_german_cp1252_file_keeps_its_umlaut_and_its_decimals(
    client: TestClient,
) -> None:
    raw = "Durchmesser \xd8\n9,71\n9,72\n10,05\n".encode("cp1252")
    body = _ingest(client, "m.csv", raw)
    assert _values(body) == {"Durchmesser \xd8": [9.71, 9.72, 10.05]}


def test_a_one_column_file_of_plain_decimals_gets_no_detection_note(
    client: TestClient,
) -> None:
    """The negative side: nothing was guessed, so nothing is announced."""
    body = _ingest(client, "m.csv", b"Wert\n9.79\n9.72\n")
    assert _values(body) == {"Wert": [9.79, 9.72]}
    assert _codes(body) == []


def test_a_one_column_text_file_with_commas_stays_text(client: TestClient) -> None:
    """Only a column that is entirely decimals is repaired; the rest is named."""
    body = _ingest(client, "t.csv", b"Kommentar\nok, aber Kratzer\nnicht ok, Riss\n")
    assert body["columns"] == []
    assert body["ignored_columns"] == ["Kommentar"]
    assert "ingest.decimal-comma-detected" not in _codes(body)


@pytest.mark.parametrize(
    ("raw", "codes"),
    [
        (b"a,b,c\n1,2,3,\n4,5,6,\n7,8,9,\n", []),
        (b"a;b;c\n1;2;3;\n4;5;6;\n7;8;9;\n", ["ingest.separator-detected"]),
        (b"a,b,c\n1,2,3,\n4,5,6\n7,8,9,\n", []),  # only some rows end in one
        (b"a,b,c\n1,2,3,\n", []),  # only the first row does
    ],
    ids=["comma", "semicolon", "mixed", "first-row-only"],
)
def test_a_trailing_delimiter_on_the_data_rows_does_not_shift_the_labels(
    client: TestClient, raw: bytes, codes: list[str]
) -> None:
    """Data rows ending in a delimiter the header lacks made pandas use the first
    field as the row index: column a held b's values and c vanished (API-1)."""
    body = _ingest(client, "t.csv", raw)
    values = _values(body)
    assert list(values) == ["a", "b", "c"]
    assert values["a"][0] == 1.0
    assert values["b"][0] == 2.0
    assert values["c"][0] == 3.0
    assert body["ignored_columns"] == []
    assert _codes(body) == codes


def test_a_data_row_wider_than_the_header_is_refused_with_its_line(
    client: TestClient,
) -> None:
    """capstat will not guess which column an extra field belongs to."""
    resp = client.post(
        "/ingest",
        files={"file": ("w.csv", b"a,b\n1,2\n3,4,5\n6,7\n", "text/csv")},
    )
    assert resp.status_code == 422
    assert "Line 3 has 3 fields but the header has 2" in resp.json()["detail"]


def test_a_wide_first_row_is_refused_not_shifted(client: TestClient) -> None:
    resp = client.post(
        "/ingest", files={"file": ("w.csv", b"x,y\n1,2,3\n4,5\n", "text/csv")}
    )
    assert resp.status_code == 422
    assert "Line 2 has 3 fields" in resp.json()["detail"]


def test_a_headerless_column_keeps_its_first_value(client: TestClient) -> None:
    """The first measurement was swallowed as the column's name (API-6)."""
    body = _ingest(client, "n.csv", b"9.71\n9.72\n9.70\n9.73\n")
    assert _values(body) == {"column 1": [9.71, 9.72, 9.70, 9.73]}
    assert body["n_rows"] == 4
    assert _codes(body) == ["ingest.header-missing"]


def test_a_headerless_table_is_named_by_position(client: TestClient) -> None:
    body = _ingest(client, "n.csv", b"1.5,2.5,3.5\n4.5,5.5,6.5\n")
    assert _values(body) == {
        "column 1": [1.5, 4.5],
        "column 2": [2.5, 5.5],
        "column 3": [3.5, 6.5],
    }
    assert body["n_rows"] == 2


def test_a_headerless_german_semicolon_file_is_read_as_such(
    client: TestClient,
) -> None:
    """9,71;1 splits into two fields on either character; the decimal comma is
    what makes the comma fit, so the semicolon is the separator."""
    body = _ingest(client, "n.csv", b"9,71;1\n9,72;2\n9,70;3\n")
    assert _values(body) == {
        "column 1": [9.71, 9.72, 9.70],
        "column 2": [1.0, 2.0, 3.0],
    }
    assert _codes(body) == [
        "ingest.separator-detected",
        "ingest.header-missing",
        "ingest.decimal-comma-detected",
    ]


def test_a_headerless_file_of_9_71_is_refused_as_ambiguous(
    client: TestClient,
) -> None:
    """One column of decimals or two of integers: the bytes do not say."""
    resp = client.post(
        "/ingest", files={"file": ("n.csv", b"9,71\n9,72\n9,70\n", "text/csv")}
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "cannot tell" in detail
    assert "header row" in detail


def test_a_header_with_one_number_among_names_is_still_a_header(
    client: TestClient,
) -> None:
    body = _ingest(client, "h.csv", b"2024,wert\n1,9.7\n2,9.8\n")
    assert _values(body) == {"2024": [1.0, 2.0], "wert": [9.7, 9.8]}
    assert _codes(body) == []


def test_a_headerless_workbook_keeps_its_first_value(client: TestClient) -> None:
    buffer = io.BytesIO()
    pd.DataFrame([[9.71], [9.72], [9.70]]).to_excel(
        buffer, index=False, header=False, engine="openpyxl"
    )
    body = client.post(
        "/ingest", files={"file": ("n.xlsx", buffer.getvalue(), "application/x")}
    ).json()
    assert _values(body) == {"column 1": [9.71, 9.72, 9.70]}
    assert [w["code"] for w in body["warnings"]] == ["ingest.header-missing"]


# --- TQ-14: the surviving tabular / ingest mutants ----------------------------


def test_negative_and_thousands_decimal_commas_are_repaired(
    client: TestClient,
) -> None:
    """A bias study is full of negatives; a thousands dot is routine in euros."""
    body = _ingest(
        client,
        "d.csv",
        b"abw;umsatz\n-0,5;1.234,56\n0,3;2.000,5\n-1,2;10,25\n",
    )
    assert _values(body) == {
        "abw": [-0.5, 0.3, -1.2],
        "umsatz": [1234.56, 2000.5, 10.25],
    }
    assert body["ignored_columns"] == []


def test_a_text_column_of_comma_separated_digits_is_not_repaired(
    client: TestClient,
) -> None:
    """'1,2,3' is a list, not a decimal: the anchors keep it text."""
    body = _ingest(client, "t.csv", b'code,x\n"1,2,3",1\n"4,5,6",2\n')
    assert body["ignored_columns"] == ["code"]
    assert "ingest.decimal-comma-detected" not in _codes(body)


def test_a_pipe_separated_file_is_split(client: TestClient) -> None:
    body = _ingest(client, "p.csv", b"a|b\n1|2\n3|4\n")
    assert _values(body) == {"a": [1.0, 3.0], "b": [2.0, 4.0]}
    assert _codes(body) == ["ingest.separator-detected"]


def test_a_tab_separated_file_is_split(client: TestClient) -> None:
    body = _ingest(client, "p.csv", b"a\tb\n1\t2\n3\t4\n")
    assert _values(body) == {"a": [1.0, 3.0], "b": [2.0, 4.0]}


@pytest.mark.parametrize("name", ["DATA.CSV", "Data.Csv"])
def test_the_extension_is_matched_without_regard_to_case(
    client: TestClient, name: str
) -> None:
    """Instrument exports are routinely upper-case."""
    assert _values(_ingest(client, name, b"a\n1\n2\n")) == {"a": [1.0, 2.0]}


def test_an_xlsm_workbook_is_accepted(client: TestClient) -> None:
    resp = client.post(
        "/ingest",
        files={"file": ("m.XLSM", _xlsx(pd.DataFrame({"m": [1.0, 2.0]})), "x/y")},
    )
    assert resp.status_code == 200
    assert resp.json()["columns"][0]["values"] == [1.0, 2.0]


def test_a_single_sheet_workbook_gets_no_sheet_note(client: TestClient) -> None:
    body = client.post(
        "/ingest",
        files={"file": ("s.xlsx", _xlsx(pd.DataFrame({"m": [1.0]})), "x/y")},
    ).json()
    assert body["warnings"] == []


def test_a_junk_cell_is_counted_and_warned_about_exactly_once(
    client: TestClient,
) -> None:
    """The count includes non-numeric cells, and only the dirty column warns.

    The old assertion was `any('dropped' in w ...)`, which an inverted condition
    (warn about every clean column, stay silent about the dirty one) also met.
    """
    body = _ingest(client, "d.csv", b"d,x\n1.0,1\nabc,2\n3.0,3\n")
    columns = {c["name"]: c for c in body["columns"]}
    assert columns["d"]["values"] == [1.0, 3.0]
    assert columns["d"]["dropped_missing"] == 1
    assert columns["x"]["dropped_missing"] == 0
    dropped = [w for w in body["warnings"] if w["code"] == "ingest.cells-dropped"]
    assert len(dropped) == 1
    assert "'d'" in dropped[0]["message"]
    assert "dropped 1 " in dropped[0]["message"]


def test_a_one_column_file_with_the_unit_separator_character_is_refused(
    client: TestClient,
) -> None:
    """The one-column reading splits on a character absent from the text."""
    resp = client.post(
        "/ingest",
        files={"file": ("c.csv", b"Wert\n9,7\x1f1\n9,72\n", "text/csv")},
    )
    assert resp.status_code == 422
    assert "control characters" in resp.json()["detail"]


def _refused(client: TestClient, raw: bytes) -> str:
    resp = client.post("/ingest", files={"file": ("w.csv", raw, "text/csv")})
    assert resp.status_code == 422, resp.text
    return str(resp.json()["detail"])


def test_a_row_with_a_real_extra_field_is_refused_even_in_a_trailing_file(
    client: TestClient,
) -> None:
    """The empty field of a trailing delimiter is the only excess allowed."""
    detail = _refused(client, b"a,b,c\n1,2,3,\n4,5,6,7\n")
    assert "Line 3 has 4 fields but the header has 3" in detail


def test_two_extra_fields_are_not_one_trailing_delimiter(client: TestClient) -> None:
    rows = b"".join(b"%d,%d,\n" % (i, i) for i in range(30))
    detail = _refused(client, b"a,b\n" + rows + b"31,31,,\n")
    assert "Line 32 has 4 fields but the header has 2" in detail


def test_a_stray_field_after_the_detection_window_is_still_refused_by_line(
    client: TestClient,
) -> None:
    """Layout is judged on the first lines; the whole file is still checked."""
    rows = b"".join(b"%d,%d\n" % (i, i) for i in range(30))
    detail = _refused(client, b"a,b\n" + rows + b"31,31,\n")
    assert "Line 32 has 3 fields but the header has 2" in detail


def test_a_leading_blank_line_does_not_make_the_next_line_the_header(
    client: TestClient,
) -> None:
    body = _ingest(client, "b.csv", b"\na,b\n1,2\n3,4\n")
    assert _values(body) == {"a": [1.0, 3.0], "b": [2.0, 4.0]}


def test_a_headerless_row_with_an_empty_cell_is_still_data(client: TestClient) -> None:
    """An empty cell is a missing value, not a reason to call the row a header."""
    body = _ingest(client, "n.csv", b"1.5,,3.5\n4.5,5.5,6.5\n")
    assert _values(body) == {
        "column 1": [1.5, 4.5],
        "column 2": [5.5],
        "column 3": [3.5, 6.5],
    }
    assert "ingest.header-missing" in _codes(body)


def test_the_ambiguity_refusal_needs_every_row_to_have_the_form_9_71(
    client: TestClient,
) -> None:
    """A lone '10' shows the file is not a column of decimals: read it as data."""
    body = _ingest(client, "n.csv", b"9,71\n9,72\n10\n")
    assert _values(body) == {"column 1": [9.0, 9.0, 10.0], "column 2": [71.0, 72.0]}
    assert "ingest.header-missing" in _codes(body)


def test_a_workbook_whose_header_cells_are_booleans_has_a_header(
    client: TestClient,
) -> None:
    """True/False labels are names, however Python spells them."""
    body = client.post(
        "/ingest",
        files={
            "file": (
                "b.xlsx",
                _xlsx(pd.DataFrame({True: [1.0, 2.0], False: [3.0, 4.0]})),
                "x/y",
            )
        },
    ).json()
    assert _values(body) == {"True": [1.0, 2.0], "False": [3.0, 4.0]}
    assert body["warnings"] == []
