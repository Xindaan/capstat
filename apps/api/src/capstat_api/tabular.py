"""Turning an uploaded table into numeric columns.

Extracted from the ingest router (T-0077) so that the CLI can parse a file the
same way the HTTP endpoint does. There is one implementation of "what does this
file contain", and two callers -- which is the only arrangement in which a
`capstat capability data.csv` and a POST to `/ingest` cannot disagree about a
decimal comma.

Nothing here imports FastAPI. What the HTTP layer adds is the upload, the size
guard and the response model; what the CLI adds is a terminal.
"""

from __future__ import annotations

import csv
import io
import re

import pandas as pd
from capstat_core import Caveat


class UnsupportedFile(ValueError):
    """The extension is not one capstat parses.

    A subclass of ValueError so a caller that does not care about the
    distinction -- the CLI's catch-all, say -- still handles it as bad input.
    """


_CANDIDATE_DELIMITERS = ",;\t|"
_DELIMITER_NAMES = {",": "a comma", ";": "a semicolon", "\t": "a tab", "|": "a pipe"}

# 9,71 and 1.234,56 -- a decimal comma, with optional thousands dots. Anchored,
# so "a,b" and "1,2,3" do not match and are left as the text they are.
_DECIMAL_COMMA = re.compile(r"^-?\d+(?:\.\d{3})*,\d+$")

# utf-8-sig first: Excel writes a byte-order mark, and reading it as plain
# utf-8 leaves it glued to the first column name. cp1252 is the Western-European
# fallback the same Excel produces when it does not write UTF-8 at all.
_ENCODINGS = ("utf-8-sig", "cp1252")


def decode(raw: bytes) -> tuple[str, str]:
    """The upload's text, and the name of the encoding that read it."""
    for encoding in _ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not read the file as text (tried utf-8 and cp1252).")


def detect_delimiter(text: str) -> str:
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


def repair_decimal_commas(frame: pd.DataFrame) -> list[str]:
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


def read_frame(filename: str, raw: bytes) -> tuple[pd.DataFrame, list[Caveat]]:
    """The parsed table, plus what had to be detected to parse it."""
    name = filename.lower()
    notes: list[Caveat] = []

    if name.endswith(".csv"):
        text, encoding = decode(raw)
        if encoding != _ENCODINGS[0]:
            notes.append(
                Caveat(
                    "ingest.encoding-detected",
                    f"Read as {encoding}; the file is not valid UTF-8.",
                )
            )
        delimiter = detect_delimiter(text)
        if delimiter != ",":
            notes.append(
                Caveat(
                    "ingest.separator-detected",
                    f"Detected {_DELIMITER_NAMES[delimiter]} as the column separator.",
                )
            )
        frame = pd.read_csv(io.StringIO(text), sep=delimiter)
        repaired = repair_decimal_commas(frame)
        if repaired:
            notes.append(
                Caveat(
                    "ingest.decimal-comma-detected",
                    "Read a decimal comma as the decimal mark in column(s): "
                    f"{', '.join(repaired)}.",
                )
            )
        return frame, notes

    if name.endswith((".xlsx", ".xlsm")):
        book = pd.ExcelFile(io.BytesIO(raw), engine="openpyxl")
        sheets = [str(sheet) for sheet in book.sheet_names]
        if len(sheets) > 1:
            notes.append(
                Caveat(
                    "ingest.sheet-selected",
                    f"The workbook holds {len(sheets)} sheets; only the first "
                    f"({sheets[0]!r}) was read.",
                )
            )
        return book.parse(sheets[0]), notes

    raise UnsupportedFile(f"Unsupported file type: {filename!r}. Use .csv or .xlsx.")
