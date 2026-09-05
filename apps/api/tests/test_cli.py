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
    # The text column is not numeric and is simply absent.
    assert "operator" not in out


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
