"""File ingestion: CSV / XLSX -> numeric columns as JSON arrays.

Stateless and parse-only. The service extracts the numeric columns a client can
feed back into the compute endpoints; it does not compute anything here. This
is the one place pandas/openpyxl are allowed -- the core never sees them.

What the caller is told, not just given:
* non-numeric columns are ignored and named (so a mistyped column is visible);
* missing cells are dropped per column and counted (JSON cannot carry ``NaN``,
  and a silent drop would misstate the sample size);
* the separator, encoding and decimal mark that were *detected* are reported,
  because guessing them silently is how a measurement column turns into text.
"""

from __future__ import annotations

import csv
import io
import re

import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter(prefix="/ingest", tags=["ingest"])

# Generous for a stateless SPC upload; guards against a memory-exhaustion body.
MAX_BYTES = 10 * 1024 * 1024

# The body is read a chunk at a time so an oversized upload is refused *before*
# it is resident, not after. Reading it whole and then measuring produced the
# right status code and none of the protection the limit exists for: a 2 GB
# body cost 2 GB, per concurrent request. One chunk is the most that can be
# read past the limit.
CHUNK_BYTES = 1024 * 1024

# Int literals rather than Starlette status constants, whose names churn and
# emit deprecation warnings; the codes are stable.
HTTP_413 = 413  # Content Too Large
HTTP_415 = 415  # Unsupported Media Type
HTTP_422 = 422  # Unprocessable Content


class IngestColumn(BaseModel):
    name: str
    values: list[float]
    dropped_missing: int


class IngestResponse(BaseModel):
    n_rows: int
    columns: list[IngestColumn]
    ignored_columns: list[str]
    warnings: list[str]


# Excel writes CSV in the operator's locale. A German Excel writes
# "durchmesser;9,71" where pandas expects "durchmesser,9.71", and both halves of
# that mismatch fail *silently*: the semicolon file parses as a single text
# column, and a decimal comma turns a perfectly good measurement column into
# text, which is then reported as "ignored non-numeric" (T-0067). Detecting them
# is straightforward; the part that matters is saying which was detected.
_CANDIDATE_DELIMITERS = ",;\t|"
_DELIMITER_NAMES = {",": "a comma", ";": "a semicolon", "\t": "a tab", "|": "a pipe"}

# 9,71 and 1.234,56 -- a decimal comma, with optional thousands dots. Anchored,
# so "a,b" and "1,2,3" do not match and are left as the text they are.
_DECIMAL_COMMA = re.compile(r"^-?\d+(?:\.\d{3})*,\d+$")

# utf-8-sig first: Excel writes a byte-order mark, and reading it as plain
# utf-8 leaves it glued to the first column name. cp1252 is the Western-European
# fallback the same Excel produces when it does not write UTF-8 at all.
_ENCODINGS = ("utf-8-sig", "cp1252")


def _decode(raw: bytes) -> tuple[str, str]:
    """The upload's text, and the name of the encoding that read it."""
    for encoding in _ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise HTTPException(
        status_code=HTTP_422,
        detail="Could not read the file as text (tried utf-8 and cp1252).",
    )


def _detect_delimiter(text: str) -> str:
    """The separator that splits these lines consistently into several fields.

    Deliberately not ``csv.Sniffer``: it guesses from character frequency and is
    unreliable on exactly the short, sparse files an SPC study produces. This
    asks the only question that matters -- does every line split into the same
    number of fields, and is that number more than one -- and answers it with
    the csv module's own quote-aware reader, so a quoted "9,71" does not read as
    two fields. Ties keep the comma, which is what pandas would have used.
    """
    lines = [line for line in text.splitlines()[:20] if line.strip()]
    if not lines:
        return ","
    best, best_fields = ",", 1
    for candidate in _CANDIDATE_DELIMITERS:
        widths = {len(row) for row in csv.reader(lines, delimiter=candidate)}
        if len(widths) != 1:
            continue  # ragged under this separator, so it is not the separator
        fields = widths.pop()
        if fields > best_fields:
            best, best_fields = candidate, fields
    return best


def _repair_decimal_commas(frame: pd.DataFrame) -> list[str]:
    """Re-read, in place, any column whose values are all European decimals.

    Only a column that is *entirely* decimal commas is touched. A column holding
    "1,2" alongside "abc" is genuinely text and is left alone -- repairing a
    column that merely looks numeric is how a label becomes a measurement.
    """
    repaired: list[str] = []
    for name in frame.columns:
        series = frame[name]
        if pd.api.types.is_numeric_dtype(series):
            continue
        text = series.dropna().astype(str).str.strip()
        if text.empty:
            continue
        looks_european = text.map(lambda v: _DECIMAL_COMMA.match(str(v)) is not None)
        if not bool(looks_european.all()):
            continue
        frame[name] = pd.to_numeric(
            series.astype(str)
            .str.strip()
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False),
            errors="coerce",
        )
        repaired.append(str(name))
    return repaired


def _read_frame(filename: str, raw: bytes) -> tuple[pd.DataFrame, list[str]]:
    """The parsed table, plus what had to be detected to parse it."""
    name = filename.lower()
    notes: list[str] = []

    if name.endswith(".csv"):
        text, encoding = _decode(raw)
        if encoding != _ENCODINGS[0]:
            notes.append(f"Read as {encoding}; the file is not valid UTF-8.")
        delimiter = _detect_delimiter(text)
        if delimiter != ",":
            notes.append(
                f"Detected {_DELIMITER_NAMES[delimiter]} as the column separator."
            )
        frame = pd.read_csv(io.StringIO(text), sep=delimiter)
        repaired = _repair_decimal_commas(frame)
        if repaired:
            notes.append(
                "Read a decimal comma as the decimal mark in column(s): "
                f"{', '.join(repaired)}."
            )
        return frame, notes

    if name.endswith((".xlsx", ".xlsm")):
        book = pd.ExcelFile(io.BytesIO(raw), engine="openpyxl")
        sheets = [str(sheet) for sheet in book.sheet_names]
        if len(sheets) > 1:
            notes.append(
                f"The workbook holds {len(sheets)} sheets; only the first "
                f"({sheets[0]!r}) was read."
            )
        return book.parse(sheets[0]), notes

    raise HTTPException(
        status_code=HTTP_415,
        detail=f"Unsupported file type: {filename!r}. Use .csv or .xlsx.",
    )


def _to_response(frame: pd.DataFrame, notes: list[str]) -> IngestResponse:
    columns: list[IngestColumn] = []
    ignored: list[str] = []
    # What was detected comes first: it explains the column list below it.
    warnings: list[str] = list(notes)

    for name in frame.columns:
        series = frame[name]
        numeric = pd.to_numeric(series, errors="coerce")
        # A genuinely non-numeric column coerces entirely to NaN; ignore it.
        if numeric.notna().sum() == 0:
            ignored.append(str(name))
            continue
        dropped = int(series.notna().sum() - numeric.notna().sum())
        clean = numeric.dropna()
        columns.append(
            IngestColumn(
                name=str(name),
                values=[float(v) for v in clean],
                dropped_missing=int(series.isna().sum()) + dropped,
            )
        )

    if ignored:
        warnings.append(f"Ignored non-numeric column(s): {', '.join(ignored)}.")
    for col in columns:
        if col.dropped_missing:
            warnings.append(
                f"Column {col.name!r}: dropped {col.dropped_missing} "
                "missing/non-numeric cell(s)."
            )
    if not columns:
        warnings.append("No numeric columns found.")

    return IngestResponse(
        n_rows=len(frame),
        columns=columns,
        ignored_columns=ignored,
        warnings=warnings,
    )


async def _read_within_limit(file: UploadFile) -> bytes:
    """The upload's bytes, or a 413 raised before they are all in memory.

    Reads in chunks and stops at the first one that crosses ``MAX_BYTES``, so
    at most one chunk more than the limit is ever held. The alternative --
    trusting ``Content-Length`` -- does not work on its own: a chunked upload
    does not send one, and a lying one is exactly the case worth defending
    against. Chunking is the measure that holds; a header check would only be
    an early exit on top of it.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_BYTES)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > MAX_BYTES:
            raise HTTPException(
                status_code=HTTP_413,
                detail=f"File exceeds {MAX_BYTES // (1024 * 1024)} MB limit.",
            )
        chunks.append(chunk)


@router.post("", response_model=IngestResponse)
async def ingest_file(file: UploadFile) -> IngestResponse:
    raw = await _read_within_limit(file)
    filename = file.filename or ""
    try:
        frame, notes = _read_frame(filename, raw)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=HTTP_422,
            detail=f"Could not parse {filename!r}: {exc}",
        ) from exc
    return _to_response(frame, notes)
