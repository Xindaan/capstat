"""capstat on the command line.

T-0026 decided that capstat runs on your own machine and your measurements
never leave it. The web app honours that but still wants two processes and a
browser; this is the same analysis with neither::

    capstat columns shaft.csv
    capstat capability shaft.csv --column diameter --lsl 9.7 --usl 10.3
    capstat chart shaft.csv --column diameter --subgroup-size 5

It lives in ``capstat-api`` rather than a package of its own because it needs
exactly what that package already owns: the tabular parsing, in one
implementation shared with ``/ingest`` (see :mod:`capstat_api.tabular`). A CLI
with its own CSV reader would be a second answer to "what does this file
contain", and the two would disagree about a decimal comma sooner or later.

The statistics are the core's, untouched -- this module reads a file, calls the
same functions the HTTP layer calls, and prints. Warnings are printed with their
codes, because a report that dropped them would be the thing capstat exists to
replace.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from capstat_core import Caveat, analyze_capability, capability
from capstat_core.control_charts import (
    ChartPair,
    i_mr_chart,
    xbar_r_chart,
    xbar_s_chart,
)

from capstat_api import __version__
from capstat_api.tabular import (
    Column,
    UnsupportedFile,
    extract_columns,
    read_frame,
)

#: Exit codes. ``2`` is "your input was refused", which is a different thing
#: from a crash and scripts should be able to tell them apart.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_BAD_INPUT = 2
#: Only with --fail-on-signal: the analysis ran and the process signalled.
EXIT_SIGNAL = 3

#: Above this, the range is a poor scale estimator and the s chart is used.
RANGE_CHART_MAX_SIZE = 10


def _numeric_columns(path: Path) -> tuple[dict[str, Column], list[Caveat]]:
    """The file's numeric columns, and what was detected or left out reading it.

    The same extraction as ``/ingest``, so a dropped cell, an ignored column or a
    detected separator is reported here exactly as it is there (API-9).
    """
    frame, notes = read_frame(path.name, path.read_bytes())
    found = extract_columns(frame, notes)
    return {c.name: c for c in found.columns}, found.warnings


def _pick(columns: dict[str, Column], wanted: str | None) -> Column:
    if not columns:
        raise ValueError("no numeric columns in this file")
    if wanted is None:
        if len(columns) > 1:
            names = ", ".join(columns)
            raise ValueError(
                f"this file has several numeric columns ({names}); name one "
                f"with --column"
            )
        return next(iter(columns.values()))
    if wanted not in columns:
        names = ", ".join(columns) or "none"
        raise ValueError(f"no numeric column named {wanted!r}; found: {names}")
    return columns[wanted]


def _subgroup(column: Column, size: int) -> tuple[list[list[float]], list[Caveat]]:
    """Subgroups of ``size`` consecutive *rows*, and what did not make one.

    Cut by row, not by position among the values that survived: with a blank
    cell in row 8, the compacted list shifts every later boundary by one and
    mixes neighbouring subgroups (T-0102). A block of rows that lost a cell is
    left out and named; rows after the last full block are reported as leftover.
    """
    blocks = (column.rows[-1] + 1) // size
    held: list[list[float]] = [[] for _ in range(blocks)]
    leftover = 0
    for row, value in zip(column.rows, column.values, strict=True):
        if row // size < blocks:
            held[row // size].append(value)
        else:
            leftover += 1
    groups = [g for g in held if len(g) == size]
    caveats: list[Caveat] = []
    short = [str(k + 1) for k, g in enumerate(held) if len(g) != size]
    if short:
        caveats.append(
            Caveat(
                "subgroups.incomplete",
                f"Subgroup(s) {', '.join(short)} hold fewer than {size} values "
                "because a cell in their rows is missing; they were left out "
                "rather than re-cut from the values after them.",
            )
        )
    if leftover:
        caveats.append(
            Caveat(
                "subgroups.leftover",
                f"{leftover} value(s) at the end form no complete subgroup and "
                "took no part in this analysis.",
            )
        )
    return groups, caveats


def _print_caveats(caveats: Sequence[Caveat], stream: Any) -> None:
    if not caveats:
        return
    print("\nWarnings:", file=stream)
    for caveat in caveats:
        print(f"  [{caveat.code}] {caveat.message}", file=stream)


def _fmt(value: float | None, digits: int = 4) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _cmd_columns(args: argparse.Namespace, out: Any) -> int:
    columns, notes = _numeric_columns(args.file)
    if args.json:
        print(
            json.dumps(
                {
                    "columns": {k: len(v.values) for k, v in columns.items()},
                    "warnings": [{"code": c.code, "message": c.message} for c in notes],
                },
                indent=2,
            ),
            file=out,
        )
        return EXIT_OK
    for name, column in columns.items():
        print(f"{name}: {len(column.values)} values", file=out)
    _print_caveats(notes, out)
    return EXIT_OK


def _cmd_capability(args: argparse.Namespace, out: Any) -> int:
    columns, notes = _numeric_columns(args.file)
    picked = _pick(columns, args.column)
    name, values = picked.name, picked.values

    if args.subgroup_size > 1:
        groups, cut = _subgroup(picked, args.subgroup_size)
        notes = notes + cut
        report = capability(groups, lsl=args.lsl, usl=args.usl, target=args.target)
        indices = {
            "cp": report.cp,
            "cpk": report.cpk,
            "pp": report.pp,
            "ppk": report.ppk,
        }
        caveats = list(report.warnings)
        path = f"subgroups of {args.subgroup_size}"
    else:
        analysis = analyze_capability(
            values, lsl=args.lsl, usl=args.usl, target=args.target
        )
        within = (
            analysis.normal
            if analysis.path == "normal"
            else analysis.box_cox.capability
            if analysis.box_cox
            else None
        )
        indices = {
            "cp": within.cp if within else None,
            "cpk": within.cpk if within else None,
            "pp": analysis.pp,
            "ppk": analysis.ppk,
        }
        caveats = list(analysis.warnings)
        path = analysis.path

    if args.json:
        print(
            json.dumps(
                {
                    "column": name,
                    "n": len(values),
                    "path": path,
                    **indices,
                    "warnings": [
                        {"code": c.code, "message": c.message} for c in notes + caveats
                    ],
                },
                indent=2,
            ),
            file=out,
        )
        return EXIT_OK

    print(f"Column {name!r}, {len(values)} measurements — {path}", file=out)
    print(f"  Cp  {_fmt(indices['cp'])}    Pp  {_fmt(indices['pp'])}", file=out)
    print(f"  Cpk {_fmt(indices['cpk'])}    Ppk {_fmt(indices['ppk'])}", file=out)
    _print_caveats(notes + caveats, out)
    return EXIT_OK


def _chart_for(
    column: Column, args: argparse.Namespace
) -> tuple[ChartPair, list[Caveat]]:
    baseline: dict[str, float] = {}
    if args.center is not None or args.sigma is not None:
        # Passed straight through so the core's own message explains a half
        # baseline, rather than this layer inventing a second wording for it.
        baseline = {"center": args.center, "sigma": args.sigma}
    if args.subgroup_size <= 1:
        return i_mr_chart(column.values, **baseline), []
    groups, cut = _subgroup(column, args.subgroup_size)
    if args.subgroup_size <= RANGE_CHART_MAX_SIZE:
        return xbar_r_chart(groups, **baseline), cut
    return xbar_s_chart(groups, **baseline), cut


def _cmd_chart(args: argparse.Namespace, out: Any) -> int:
    columns, notes = _numeric_columns(args.file)
    picked = _pick(columns, args.column)
    name = picked.name
    pair, cut = _chart_for(picked, args)
    notes = notes + cut

    if args.json:
        print(
            json.dumps(
                {
                    "column": name,
                    "phase": pair.phase,
                    "in_control": pair.in_control,
                    "location": {
                        "name": pair.location.name,
                        "violations": list(pair.location.violations),
                    },
                    "dispersion": {
                        "name": pair.dispersion.name,
                        "violations": list(pair.dispersion.violations),
                    },
                    "warnings": [
                        {"code": c.code, "message": c.message}
                        for c in notes + list(pair.warnings)
                    ],
                },
                indent=2,
            ),
            file=out,
        )
    else:
        state = "in control" if pair.in_control else "OUT OF CONTROL"
        print(
            f"Column {name!r} — {pair.location.name} / {pair.dispersion.name}, "
            f"Phase {pair.phase}: {state}",
            file=out,
        )
        for chart in (pair.location, pair.dispersion):
            # Counted from 1, the way a person reads a chart and the way the
            # web app labels its points. Note that the core's own warnings
            # below quote the raw 0-based indices, so the same excursion can
            # appear under two numbers in one report -- see TASK.md T-0078.
            points = ", ".join(str(i + 1) for i in chart.violations) or "none"
            print(f"  {chart.name}, out of control at point(s): {points}", file=out)
        _print_caveats(notes + list(pair.warnings), out)

    # A report by default; a gate only when asked. Turning "out of control" into
    # a non-zero exit unasked would make every scripted run of this command a
    # pass/fail test, which is not what a control chart is for.
    if args.fail_on_signal and not pair.in_control:
        return EXIT_SIGNAL
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capstat",
        description=(
            "Reference-validated SPC, capability and MSA statistics, on a file "
            "you already have. Nothing is uploaded and nothing is stored."
        ),
    )
    parser.add_argument("--version", action="version", version=f"capstat {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    def with_file(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
        sub.add_argument("file", type=Path, help="a .csv, .xlsx or .xlsm file")
        sub.add_argument("--json", action="store_true", help="machine-readable output")
        return sub

    listing = with_file(
        subcommands.add_parser("columns", help="list the numeric columns in a file")
    )
    listing.set_defaults(run=_cmd_columns)

    cap = with_file(
        subcommands.add_parser("capability", help="capability indices for one column")
    )
    cap.add_argument("--column", help="which column (required if there are several)")
    cap.add_argument("--lsl", type=float, help="lower specification limit")
    cap.add_argument("--usl", type=float, help="upper specification limit")
    cap.add_argument("--target", type=float, help="target, for Cpm")
    cap.add_argument(
        "--subgroup-size",
        type=int,
        default=1,
        help="group consecutive rows; 1 (default) treats them as individuals",
    )
    cap.set_defaults(run=_cmd_capability)

    chart = with_file(
        subcommands.add_parser("chart", help="a control chart pair for one column")
    )
    chart.add_argument("--column", help="which column (required if there are several)")
    chart.add_argument("--subgroup-size", type=int, default=1)
    chart.add_argument("--center", type=float, help="known centre (Phase II)")
    chart.add_argument("--sigma", type=float, help="known within sigma (Phase II)")
    chart.add_argument(
        "--fail-on-signal",
        action="store_true",
        help=f"exit {EXIT_SIGNAL} when the process is out of control",
    )
    chart.set_defaults(run=_cmd_chart)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.run(args, sys.stdout))
    except (UnsupportedFile, ValueError) as exc:
        # The core raises ValueError for domain-invalid input, and its messages
        # are part of what makes it trustworthy -- so they reach the terminal
        # verbatim, exactly as the HTTP layer passes them through as a 422.
        print(f"capstat: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT
    except FileNotFoundError:
        print(f"capstat: no such file: {args.file}", file=sys.stderr)
        return EXIT_BAD_INPUT


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
