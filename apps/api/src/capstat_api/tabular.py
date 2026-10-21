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
from dataclasses import dataclass

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


@dataclass(frozen=True)
class CsvLayout:
    """How the lines of a CSV split into fields (T-0095).

    ``fields`` is the number of logical columns. ``trailing`` means every data
    row carries one extra, empty field -- a delimiter at the end of the line
    that the header does not have, which the exporters of instruments and ERP
    systems write. ``single_column`` means the header names one column while the
    data rows hold commas: a one-column file from a German Excel, where no
    separator exists and every comma is a decimal mark.
    """

    delimiter: str
    fields: int
    trailing: bool = False
    single_column: bool = False


def _profile(lines: list[str], candidate: str) -> tuple[int, bool] | None:
    """(logical field count, trailing delimiter?) if ``candidate`` fits, else None."""
    rows = list(csv.reader(lines, delimiter=candidate))
    header = len(rows[0])
    widths = {len(row) for row in rows}
    if len(widths) == 1:
        return header, False
    # One field more than the header is a trailing delimiter -- or a stray extra
    # field, which `_check_rows` refuses by line once the layout is chosen. Any
    # other width is a ragged file. Rows with and without it may be mixed.
    if widths <= {header, header + 1}:
        return header, True
    return None


def detect_layout(text: str) -> CsvLayout:
    """The separator that splits these lines consistently into several fields.

    Deliberately not ``csv.Sniffer``: it guesses from character frequency and is
    unreliable on exactly the short, sparse files an SPC study produces. This
    asks the only question that matters -- does every line split into the same
    number of fields, and is that number more than one -- and answers it with
    the csv module's own quote-aware reader, so a quoted "9,71" does not read as
    two fields. Ties keep the comma, which is what pandas would have used.

    Two shapes are consistent in a looser sense and are recognised on purpose
    rather than left to pandas, which reads both *silently wrong*: data rows
    that all end in a delimiter the header lacks (pandas promotes the first
    field to the row index and shifts every label one column left), and a
    one-column file whose rows are German decimals (the comma is taken as the
    separator and the integer part becomes the index: "9,79" reads as 79).
    """
    lines = [line for line in text.splitlines()[:20] if line.strip()]
    if not lines:
        return CsvLayout(",", 1)
    best = CsvLayout(",", 1)
    for candidate in _CANDIDATE_DELIMITERS:
        profile = _profile(lines, candidate)
        if profile is None:
            continue  # ragged under this separator, so it is not the separator
        fields, trailing = profile
        # A tie keeps the comma -- except when a decimal comma is what makes the
        # comma fit: "9,71;1" splits into two fields on either character.
        decimal_tie = (
            fields == best.fields
            and best.delimiter == ","
            and fields > 1
            and all(re.search(r"\d,\d", line) for line in lines)
        )
        if fields > best.fields or decimal_tie:
            best = CsvLayout(candidate, fields, trailing)
    header, body = lines[0], lines[1:]
    if not any(candidate in header for candidate in _CANDIDATE_DELIMITERS) and any(
        "," in line for line in body
    ):
        if _NO_SEPARATOR in text:
            raise ValueError("Could not read the file: it contains control characters.")
        return CsvLayout(_NO_SEPARATOR, 1, single_column=True)
    return best


_NO_SEPARATOR = "\x1f"  # the ASCII unit separator: in no text file anyone exports


_NUMBER = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")


def _is_number(field: str) -> bool:
    field = field.strip()
    return _NUMBER.match(field) is not None or _DECIMAL_COMMA.match(field) is not None


def _check_rows(text: str, layout: CsvLayout) -> list[str]:
    """The header fields; refuses a data row wider than the header.

    pandas shifts every label when the *first* data row is wider than the header
    and loses data when a later one is, so a wider row is not parsed but named.
    The one allowed excess is the empty field of a trailing delimiter.
    """
    reader = csv.reader(io.StringIO(text), delimiter=layout.delimiter)
    header: list[str] | None = None
    for row in reader:
        if not row:
            continue
        if header is None:
            header = row
            continue
        extra = len(row) - len(header)
        if extra > 0 and not (layout.trailing and extra == 1 and row[-1].strip() == ""):
            raise ValueError(
                f"Line {reader.line_num} has {len(row)} fields but the header has "
                f"{len(header)}. capstat will not guess which column the extra "
                "field belongs to; fix the row or add the missing column name."
            )
    return header or []


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


def _name_by_position(frame: pd.DataFrame) -> None:
    frame.columns = pd.Index([f"column {i + 1}" for i in range(frame.shape[1])])


def _headerless_note() -> Caveat:
    return Caveat(
        "ingest.header-missing",
        "The first row holds only numbers, so it was read as data, not as column "
        "names; the columns are called 'column 1', 'column 2', ... If that row "
        "was a header, give the columns text names.",
    )


def _read_csv(raw: bytes) -> tuple[pd.DataFrame, list[Caveat]]:
    notes: list[Caveat] = []
    text, encoding = decode(raw)
    if encoding != _ENCODINGS[0]:
        notes.append(
            Caveat(
                "ingest.encoding-detected",
                f"Read as {encoding}; the file is not valid UTF-8.",
            )
        )
    layout = detect_layout(text)
    header = _check_rows(text, layout)
    if layout.single_column:
        notes.append(
            Caveat(
                "ingest.single-column-detected",
                "The file has one column, so commas were read as decimal marks, "
                "not as column separators.",
            )
        )
    elif layout.delimiter != ",":
        name = _DELIMITER_NAMES[layout.delimiter]
        notes.append(
            Caveat(
                "ingest.separator-detected",
                f"Detected {name} as the column separator.",
            )
        )

    headerless = bool(header) and all(
        _is_number(field) for field in header if field.strip()
    )
    if headerless:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if layout.delimiter == "," and all(
            _DECIMAL_COMMA.match(line) for line in lines
        ):
            raise ValueError(
                "The first row holds only numbers and every row has the form "
                "'9,71': that is either one column of decimals written with a "
                "comma or two columns of integers, and capstat cannot tell "
                "which. Add a header row (for example 'value') and upload again."
            )
        notes.append(_headerless_note())

    frame = pd.read_csv(
        io.StringIO(text),
        sep=layout.delimiter,
        header=None if headerless else "infer",
        index_col=False if layout.trailing else None,
    )
    if headerless:
        _name_by_position(frame)
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


def read_frame(filename: str, raw: bytes) -> tuple[pd.DataFrame, list[Caveat]]:
    """The parsed table, plus what had to be detected to parse it."""
    name = filename.lower()

    if name.endswith(".csv"):
        return _read_csv(raw)

    if name.endswith((".xlsx", ".xlsm")):
        notes: list[Caveat] = []
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
        frame = book.parse(sheets[0])
        # A number where a column name belongs means the sheet has no header row
        # and pandas has just spent its first measurement on the labels.
        if len(frame.columns) and all(
            isinstance(label, (int, float)) and not isinstance(label, bool)
            for label in frame.columns
        ):
            frame = book.parse(sheets[0], header=None)
            _name_by_position(frame)
            notes.append(_headerless_note())
        return frame, notes

    raise UnsupportedFile(f"Unsupported file type: {filename!r}. Use .csv or .xlsx.")
