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
from capstat_api.tabular import UnsupportedFile, read_frame

#: Exit codes. ``2`` is "your input was refused", which is a different thing
#: from a crash and scripts should be able to tell them apart.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_BAD_INPUT = 2
#: Only with --fail-on-signal: the analysis ran and the process signalled.
EXIT_SIGNAL = 3

#: Above this, the range is a poor scale estimator and the s chart is used.
RANGE_CHART_MAX_SIZE = 10


def _numeric_columns(path: Path) -> tuple[dict[str, list[float]], list[Caveat]]:
    """The file's numeric columns, and what had to be detected to read it."""
    frame, notes = read_frame(path.name, path.read_bytes())
    columns: dict[str, list[float]] = {}
    import pandas as pd  # local: keeps `--help` off the pandas import path

    for name in frame.columns:
        numeric = pd.to_numeric(frame[name], errors="coerce").dropna()
        if not numeric.empty:
            columns[str(name)] = [float(v) for v in numeric]
    return columns, list(notes)


def _pick(
    columns: dict[str, list[float]], wanted: str | None
) -> tuple[str, list[float]]:
    if not columns:
        raise ValueError("no numeric columns in this file")
    if wanted is None:
        if len(columns) > 1:
            names = ", ".join(columns)
            raise ValueError(
                f"this file has several numeric columns ({names}); name one "
                f"with --column"
            )
        return next(iter(columns.items()))
    if wanted not in columns:
        names = ", ".join(columns) or "none"
        raise ValueError(f"no numeric column named {wanted!r}; found: {names}")
    return wanted, columns[wanted]


def _subgroup(values: list[float], size: int) -> tuple[list[list[float]], int]:
    """Consecutive subgroups in file order, and how many values are left over."""
    complete = len(values) // size
    groups = [values[i * size : (i + 1) * size] for i in range(complete)]
    return groups, len(values) - complete * size


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
                    "columns": {k: len(v) for k, v in columns.items()},
                    "warnings": [{"code": c.code, "message": c.message} for c in notes],
                },
                indent=2,
            ),
            file=out,
        )
        return EXIT_OK
    if not columns:
        print("No numeric columns found.", file=out)
    for name, values in columns.items():
        print(f"{name}: {len(values)} values", file=out)
    _print_caveats(notes, out)
    return EXIT_OK


def _cmd_capability(args: argparse.Namespace, out: Any) -> int:
    columns, notes = _numeric_columns(args.file)
    name, values = _pick(columns, args.column)

    leftover = 0
    if args.subgroup_size > 1:
        groups, leftover = _subgroup(values, args.subgroup_size)
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
    if leftover:
        print(
            f"\n  {leftover} value(s) at the end form no complete subgroup and "
            f"took no part in this report.",
            file=out,
        )
    _print_caveats(notes + caveats, out)
    return EXIT_OK


def _chart_for(values: list[float], args: argparse.Namespace) -> ChartPair:
    baseline: dict[str, float] = {}
    if args.center is not None or args.sigma is not None:
        # Passed straight through so the core's own message explains a half
        # baseline, rather than this layer inventing a second wording for it.
        baseline = {"center": args.center, "sigma": args.sigma}
    if args.subgroup_size <= 1:
        return i_mr_chart(values, **baseline)
    groups, _ = _subgroup(values, args.subgroup_size)
    if args.subgroup_size <= RANGE_CHART_MAX_SIZE:
        return xbar_r_chart(groups, **baseline)
    return xbar_s_chart(groups, **baseline)


def _cmd_chart(args: argparse.Namespace, out: Any) -> int:
    columns, notes = _numeric_columns(args.file)
    name, values = _pick(columns, args.column)
    pair = _chart_for(values, args)

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
