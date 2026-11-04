"""The local CLI (T-0077).

The statistics are the core's and are tested there; what is tested here is the
part the CLI owns -- reading a file, choosing a column, exit codes, and whether
the numbers it prints are the ones the rest of capstat produces for the same
input. The last of those is the point: a second surface onto the same library
is only worth having if it cannot disagree with the first.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from capstat_api.cli import EXIT_BAD_INPUT, EXIT_OK, EXIT_SIGNAL, main

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO = REPO_ROOT / "examples" / "shaft-diameter.csv"


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_columns_lists_what_is_numeric(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "columns", str(DEMO))
    assert code == EXIT_OK
    assert "diameter_mm: 60 values" in out
    # The text column is not a numeric column -- but it is named as ignored,
    # exactly as /ingest names it, so a mistyped column is visible (API-9).
    assert "operator:" not in out
    assert "[ingest.non-numeric-columns-ignored]" in out
    assert "operator" in out


def test_capability_reproduces_the_documented_demo_figures(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI must agree with the README, the web app and the library.

    These are the numbers the README quotes for this file and the screenshots
    show: the percentile path, Pp 1.379, Ppk 0.942, and *no* Cp or Cpk, because
    that path has no within/between split. A second surface onto one library is
    only worth having if it cannot disagree with the first.
    """
    code, out, _ = run(
        capsys,
        "capability",
        str(DEMO),
        "--column",
        "diameter_mm",
        "--lsl",
        "9.7",
        "--usl",
        "10.3",
        "--json",
    )
    assert code == EXIT_OK
    report = json.loads(out)
    assert report["path"] == "percentile"
    assert report["pp"] == pytest.approx(1.3792, abs=5e-5)
    assert report["ppk"] == pytest.approx(0.9418, abs=5e-5)
    assert report["cp"] is None and report["cpk"] is None


def test_warnings_are_printed_with_their_codes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A report that dropped them would be the thing capstat exists to replace."""
    _, out, _ = run(
        capsys, "capability", str(DEMO), "--column", "diameter_mm", "--usl", "10.3"
    )
    assert "[nonnormal.percentile-no-cpk]" in out


def test_subgroups_change_the_report_and_name_the_leftovers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # 60 measurements in subgroups of 7: eight complete, four left over. Those
    # four take no part, and saying so is the difference between this study and
    # a different one presented as this one.
    code, out, _ = run(
        capsys,
        "capability",
        str(DEMO),
        "--column",
        "diameter_mm",
        "--lsl",
        "9.7",
        "--usl",
        "10.3",
        "--subgroup-size",
        "7",
    )
    assert code == EXIT_OK
    assert "subgroups of 7" in out
    assert "4 value(s) at the end form no complete subgroup" in out


def test_the_chart_reports_its_phase_and_a_baseline_holds_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, out, _ = run(capsys, "chart", str(DEMO), "--column", "diameter_mm", "--json")
    assert json.loads(out)["phase"] == "I"

    _, out, _ = run(
        capsys,
        "chart",
        str(DEMO),
        "--column",
        "diameter_mm",
        "--center",
        "10.0",
        "--sigma",
        "0.05",
        "--json",
    )
    assert json.loads(out)["phase"] == "II"


def test_a_signal_is_a_report_by_default_and_a_gate_only_when_asked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Turning "out of control" into a non-zero exit unasked would make every
    scripted run a pass/fail test, which is not what a control chart is for."""
    code, out, _ = run(capsys, "chart", str(DEMO), "--column", "diameter_mm")
    assert code == EXIT_OK
    assert "OUT OF CONTROL" in out

    code, _, _ = run(
        capsys, "chart", str(DEMO), "--column", "diameter_mm", "--fail-on-signal"
    )
    assert code == EXIT_SIGNAL


def test_an_ambiguous_column_is_refused_rather_than_guessed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, _, err = run(capsys, "capability", str(DEMO), "--lsl", "9.7", "--usl", "10.3")
    assert code == EXIT_BAD_INPUT
    assert "several numeric columns" in err
    # It names them, so the next command can be written without opening the file.
    assert "diameter_mm" in err


def test_a_named_column_that_is_not_there_says_what_is(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, _, err = run(capsys, "columns", str(DEMO))
    assert code == EXIT_OK
    code, _, err = run(
        capsys, "capability", str(DEMO), "--column", "nope", "--usl", "1"
    )
    assert code == EXIT_BAD_INPUT
    assert "no numeric column named 'nope'" in err
    assert "diameter_mm" in err


def test_the_core_s_own_message_reaches_the_terminal(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Domain errors are passed through verbatim, as the HTTP layer does.

    The messages are part of what makes the library trustworthy; rewording them
    here would be a second voice for the same fault.
    """
    code, _, err = run(
        capsys, "chart", str(DEMO), "--column", "diameter_mm", "--center", "10.0"
    )
    assert code == EXIT_BAD_INPUT
    assert "both center and sigma" in err

    code, _, err = run(capsys, "capability", str(DEMO), "--column", "diameter_mm")
    assert code == EXIT_BAD_INPUT
    assert "at least one specification limit" in err


def test_a_missing_or_unreadable_file_is_bad_input_not_a_crash(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    code, _, err = run(capsys, "columns", str(tmp_path / "absent.csv"))
    assert code == EXIT_BAD_INPUT
    assert "no such file" in err

    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("nothing tabular here")
    code, _, err = run(capsys, "columns", str(unsupported))
    assert code == EXIT_BAD_INPUT
    assert "Unsupported file type" in err


def test_a_file_with_no_numeric_columns_says_so(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    text_only = tmp_path / "labels.csv"
    text_only.write_text("operator\nalice\nbob\n")
    code, out, _ = run(capsys, "columns", str(text_only))
    assert code == EXIT_OK
    assert "No numeric columns found." in out

    code, _, err = run(capsys, "capability", str(text_only), "--usl", "1")
    assert code == EXIT_BAD_INPUT
    assert "no numeric columns" in err


def test_the_cli_reads_a_german_csv_the_same_way_the_endpoint_does(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """One implementation of "what does this file contain", two callers.

    A CLI with its own CSV reader would disagree with `/ingest` about a decimal
    comma sooner or later; sharing `tabular` is what stops it (T-0077).
    """
    german = tmp_path / "messung.csv"
    german.write_bytes("durchmesser;charge\n9,71;1\n9,80;2\n9,75;3\n".encode("cp1252"))
    code, out, _ = run(capsys, "columns", str(german))
    assert code == EXIT_OK
    assert "durchmesser: 3 values" in out
    assert "[ingest.separator-detected]" in out
    assert "[ingest.decimal-comma-detected]" in out


def test_the_json_output_carries_the_codes_too(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, out, _ = run(capsys, "chart", str(DEMO), "--column", "diameter_mm", "--json")
    payload = json.loads(out)
    assert payload["in_control"] is False
    assert payload["location"]["name"] == "individuals"
    assert any(w["code"].startswith("control-chart.") for w in payload["warnings"])


def test_columns_json_lists_counts(capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = run(capsys, "columns", str(DEMO), "--json")
    payload = json.loads(out)
    assert payload["columns"]["diameter_mm"] == 60


def test_a_single_numeric_column_needs_no_column_flag(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    one = tmp_path / "one.csv"
    one.write_text("m\n" + "\n".join(str(10 + i % 3) for i in range(30)) + "\n")
    code, out, _ = run(capsys, "capability", str(one), "--lsl", "8", "--usl", "13")
    assert code == EXIT_OK
    assert "Column 'm'" in out


def test_the_version_flag_reports_the_package_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from capstat_api import __version__

    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_the_chart_command_follows_the_subgroup_size_to_the_right_pair(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Which pair suits the data is a consequence of the size, not a flag.

    The range reads only the largest and smallest value of a subgroup, so above
    ten the s chart is the better estimator -- and the CLI picks rather than
    making the caller know, then names what it picked.
    """
    _, out, _ = run(
        capsys,
        "chart",
        str(DEMO),
        "--column",
        "diameter_mm",
        "--subgroup-size",
        "5",
        "--json",
    )
    ranged = json.loads(out)
    assert ranged["location"]["name"] == "X-bar"
    assert ranged["dispersion"]["name"] == "R"

    _, out, _ = run(
        capsys,
        "chart",
        str(DEMO),
        "--column",
        "diameter_mm",
        "--subgroup-size",
        "12",
        "--json",
    )
    deviation = json.loads(out)
    assert deviation["location"]["name"] == "X-bar"
    assert deviation["dispersion"]["name"] == "s"


def test_a_one_column_german_csv_gives_the_same_indices_as_its_dot_twin(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The report that started T-0095: Cp 1.97 became 0.0197 and Cpk -8.61.

    A file `Wert / 9,79 / ...` has no separator, so the comma was taken for one
    and the integer part became the row index. The same readings with a decimal
    point are the reference; the German file must reproduce them exactly.
    """
    rows = [line.split(",")[2] for line in DEMO.read_text().splitlines()[1:]]
    dot = tmp_path / "dot.csv"
    dot.write_text("Wert\n" + "\n".join(rows) + "\n")
    german = tmp_path / "de.csv"
    german.write_text("Wert\n" + "\n".join(r.replace(".", ",") for r in rows) + "\n")
    args = ("--lsl", "9.7", "--usl", "10.3")

    code_dot, out_dot, _ = run(capsys, "capability", str(dot), *args)
    code_de, out_de, _ = run(capsys, "capability", str(german), *args)

    assert code_dot == code_de == EXIT_OK

    def indices(out: str) -> list[str]:
        return [line for line in out.splitlines() if line.startswith("  C")]

    assert indices(out_de) == indices(out_dot)
    assert len(indices(out_de)) == 2
    assert "[ingest.single-column-detected]" in out_de


# --- T-0102: a dropped cell must not shift later subgroups --------------------


def _hourly_csv(
    tmp_path: Path, *, blank_row: int | None, skip_hour: int | None
) -> Path:
    """Six hours of five readings, each hour at its own level, one blank cell.

    Deterministic, with a level that differs per hour and a spread that differs
    per position, so a subgroup cut at the wrong boundary changes every index.
    """
    spread = [-0.04, 0.01, 0.05, -0.02, 0.03]
    level = [10.00, 10.02, 9.99, 10.03, 10.01, 9.98]
    cells: list[str] = []
    for hour in range(6):
        if hour == skip_hour:
            continue
        for k in range(5):
            row = hour * 5 + k
            cells.append("" if row == blank_row else f"{level[hour] + spread[k]:.3f}")
    path = tmp_path / f"hourly-{blank_row}-{skip_hour}.csv"
    # A blank *line* would be skipped by the reader; a second column keeps the
    # row alive, which is how a real gap looks in a two-column export.
    path.write_text("x,y\n" + "".join(f"{v},1\n" for v in cells))
    return path


def _indices(capsys: pytest.CaptureFixture[str], path: Path) -> dict[str, float]:
    code, out, _ = run(
        capsys,
        "capability",
        str(path),
        "--column",
        "x",
        "--lsl",
        "9.8",
        "--usl",
        "10.2",
        "--subgroup-size",
        "5",
        "--json",
    )
    assert code == EXIT_OK
    report = json.loads(out)
    return {k: report[k] for k in ("cp", "cpk", "pp", "ppk")}


def test_a_blank_cell_costs_its_own_subgroup_and_moves_no_other(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The subgroups are cut by ROW (CHART-2).

    Cutting the compacted list moved every boundary after the gap by one, so the
    gap's subgroup was mixed into its neighbours. Reading the file with hour 2's
    cell blank must give exactly what reading it with hour 2 removed gives.
    """
    gap = _hourly_csv(tmp_path, blank_row=7, skip_hour=None)
    removed = _hourly_csv(tmp_path, blank_row=None, skip_hour=1)
    assert _indices(capsys, gap) == _indices(capsys, removed)


def test_the_cli_names_the_subgroup_a_gap_cost_and_the_dropped_cell(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    gap = _hourly_csv(tmp_path, blank_row=7, skip_hour=None)
    _, out, _ = run(
        capsys,
        "chart",
        str(gap),
        "--column",
        "x",
        "--subgroup-size",
        "5",
        "--json",
    )
    warnings = {w["code"]: w["message"] for w in json.loads(out)["warnings"]}
    assert "data row(s) 8" in warnings["ingest.cells-dropped"]
    assert warnings["subgroups.incomplete"].startswith(
        "Subgroup(s) 2 hold fewer than 5"
    )
    assert "subgroups.leftover" not in warnings


@pytest.mark.parametrize(
    ("size", "rows", "left"),
    [(5, 12, 2), (11, 25, 3)],
    ids=["x-bar-r", "x-bar-s"],
)
def test_chart_reports_leftover_values_instead_of_dropping_them(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    size: int,
    rows: int,
    left: int,
) -> None:
    """`capability` named the leftovers; `chart` threw them away in silence (API-9).

    Both chart pairs: the range pair (size <= 10) and the s pair (size > 10) are
    separate return paths.
    """
    path = tmp_path / "leftover.csv"
    path.write_text(
        "x\n" + "\n".join(f"{10 + (i % 4) * 0.01:.2f}" for i in range(rows))
    )
    for args in (("chart",), ("capability", "--lsl", "9.5", "--usl", "10.5")):
        _, out, _ = run(
            capsys, *args, str(path), "--subgroup-size", str(size), "--json"
        )
        warnings = {w["code"]: w["message"] for w in json.loads(out)["warnings"]}
        assert (
            f"{left} value(s) at the end form no complete subgroup"
            in warnings["subgroups.leftover"]
        ), args
        assert "subgroups.incomplete" not in warnings


def test_columns_reports_what_was_dropped_the_way_ingest_does(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    path = tmp_path / "naish.csv"
    path.write_text("d,note\n9.71,a\nn.a.,b\n9.70,c\n")
    code, out, _ = run(capsys, "columns", str(path))
    assert code == EXIT_OK
    assert "d: 2 values" in out
    assert "[ingest.cells-dropped]" in out
    assert "data row(s) 2" in out
    assert "[ingest.non-numeric-columns-ignored]" in out


def test_a_clean_file_prints_no_warnings_block(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Nothing dropped, nothing detected, nothing ignored: nothing to say."""
    path = tmp_path / "clean.csv"
    path.write_text("x\n1.0\n2.0\n")
    code, out, _ = run(capsys, "columns", str(path))
    assert code == EXIT_OK
    assert out == "x: 2 values\n"
