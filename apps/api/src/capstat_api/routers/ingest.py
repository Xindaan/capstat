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

import pandas as pd
from capstat_core import Caveat
from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from capstat_api.schemas import CaveatOut
from capstat_api.tabular import UnsupportedFile, extract_columns, read_frame

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
    # Where each value sat among the file's data rows (0-based), so a consumer
    # that cuts subgroups can cut by row. `values` is compacted -- the missing
    # cells are gone -- and cutting the compacted list moves every boundary
    # after a gap (T-0102).
    rows: list[int]
    dropped_missing: int


class IngestResponse(BaseModel):
    n_rows: int
    columns: list[IngestColumn]
    ignored_columns: list[str]
    warnings: list[CaveatOut]


# Excel writes CSV in the operator's locale. A German Excel writes
# "durchmesser;9,71" where pandas expects "durchmesser,9.71", and both halves of
# that mismatch fail *silently*: the semicolon file parses as a single text
# column, and a decimal comma turns a perfectly good measurement column into
# text, which is then reported as "ignored non-numeric" (T-0067). Detecting them
# is straightforward; the part that matters is saying which was detected.
def _to_response(frame: pd.DataFrame, notes: list[Caveat]) -> IngestResponse:
    found = extract_columns(frame, notes)
    return IngestResponse(
        n_rows=found.n_rows,
        columns=[
            IngestColumn(
                name=c.name,
                values=c.values,
                rows=c.rows,
                dropped_missing=c.dropped_missing,
            )
            for c in found.columns
        ],
        ignored_columns=found.ignored,
        # Split here rather than leaning on the schema's validator: the
        # declared type and the value passed should agree at the call site.
        warnings=[CaveatOut(code=w.code, message=str(w)) for w in found.warnings],
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
        frame, notes = read_frame(filename, raw)
    except UnsupportedFile as exc:
        # A wrong extension is not a parse failure; it is a media type this
        # service does not accept, and 415 says so.
        raise HTTPException(status_code=HTTP_415, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=HTTP_422,
            detail=f"Could not parse {filename!r}: {exc}",
        ) from exc
    return _to_response(frame, notes)
