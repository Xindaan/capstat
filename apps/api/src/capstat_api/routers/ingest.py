"""File ingestion: CSV / XLSX -> numeric columns as JSON arrays.

Stateless and parse-only. The service extracts the numeric columns a client can
feed back into the compute endpoints; it does not compute anything here. This
is the one place pandas/openpyxl are allowed -- the core never sees them.

What the caller is told, not just given:
* non-numeric columns are ignored and named (so a mistyped column is visible);
* missing cells are dropped per column and counted (JSON cannot carry ``NaN``,
  and a silent drop would misstate the sample size).
"""

from __future__ import annotations

import io

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


def _read_frame(filename: str, raw: bytes) -> pd.DataFrame:
    name = filename.lower()
    buffer = io.BytesIO(raw)
    if name.endswith(".csv"):
        return pd.read_csv(buffer)
    if name.endswith((".xlsx", ".xlsm")):
        return pd.read_excel(buffer, engine="openpyxl")
    raise HTTPException(
        status_code=HTTP_415,
        detail=f"Unsupported file type: {filename!r}. Use .csv or .xlsx.",
    )


def _to_response(frame: pd.DataFrame) -> IngestResponse:
    columns: list[IngestColumn] = []
    ignored: list[str] = []
    warnings: list[str] = []

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
        frame = _read_frame(filename, raw)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=HTTP_422,
            detail=f"Could not parse {filename!r}: {exc}",
        ) from exc
    return _to_response(frame)
