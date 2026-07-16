"""Gage linearity study.

Sources and tolerances: ``references/linearity.yaml``.

Linearity is a t-test on the slope of bias-vs-reference. It is pinned to scipy's
``linregress`` (an independent regression) and to the AIAG worked example, whose
slope and intercept are fixed by the published per-part biases.
"""

from __future__ import annotations

import numpy as np
import pytest
import yaml
from capstat_core import LinearityReport, linearity
from conftest import REFERENCES
from scipy import stats

DOCUMENT = yaml.safe_load((REFERENCES / "linearity.yaml").read_text())
CASES = {case["id"]: case for case in DOCUMENT["cases"]}

# A fixed zero-mean scatter, so each part's mean bias is exactly its target.
_SCATTER = np.array([-0.2, -0.1, -0.05, 0.05, 0.0, 0.0, -0.05, 0.05, 0.1, 0.2])


def _reconstruct(references: list[float], part_biases: list[float]) -> list[np.ndarray]:
    scatter = _SCATTER - _SCATTER.mean()
    return [
        ref + bias + scatter for ref, bias in zip(references, part_biases, strict=True)
    ]


# ---------------------------------------------------------------------------
# AIAG worked example, and scipy
# ---------------------------------------------------------------------------


def test_aiag_slope_intercept_and_percent_linearity() -> None:
    case = CASES["linearity-aiag"]
    inp, exp, tol = case["input"], case["expected"], case["tolerance"]["abs"]
    report = linearity(
        inp["references"],
        _reconstruct(inp["references"], inp["part_biases"]),
        process_variation=inp["process_variation"],
    )
    assert report.slope == pytest.approx(exp["slope"], abs=tol)
    assert report.intercept == pytest.approx(exp["intercept"], abs=tol)
    assert report.percent_linearity == pytest.approx(exp["percent_linearity"], abs=tol)
    assert report.linearity == pytest.approx(exp["linearity"], abs=tol)
    assert report.part_mean_biases == pytest.approx(exp["part_mean_biases"], abs=tol)
    assert report.linearity_significant is exp["linearity_significant"]
    assert report.n == 50
    assert report.n_parts == 5


def test_regression_matches_scipy_linregress() -> None:
    rng = np.random.default_rng(11)
    references = [2.0, 4.0, 6.0, 8.0]
    measurements = [rng.normal(r * 1.02, 0.3, 8) for r in references]
    report = linearity(references, measurements)

    x = np.repeat(references, 8)
    y = np.concatenate([m - r for r, m in zip(references, measurements, strict=True)])
    lr = stats.linregress(x, y)
    assert report.slope == pytest.approx(lr.slope, rel=1e-12)
    assert report.intercept == pytest.approx(lr.intercept, rel=1e-12)
    assert report.r_squared == pytest.approx(lr.rvalue**2, rel=1e-12)
    assert report.slope_std_error == pytest.approx(lr.stderr, rel=1e-9)
    assert report.slope_p_value == pytest.approx(lr.pvalue, rel=1e-9)


def test_percent_linearity_is_abs_slope_times_100() -> None:
    report = linearity([1.0, 2.0, 3.0], _reconstruct([1.0, 2.0, 3.0], [0.0, 0.1, 0.2]))
    assert report.percent_linearity == pytest.approx(abs(report.slope) * 100.0)


# ---------------------------------------------------------------------------
# Flat bias, degenerate fit, absolute linearity
# ---------------------------------------------------------------------------


def test_constant_bias_is_linear() -> None:
    # The same offset at every reference -> a flat line -> no linearity problem.
    refs = [2.0, 4.0, 6.0, 8.0]
    report = linearity(refs, _reconstruct(refs, [0.5, 0.5, 0.5, 0.5])[: len(refs)])
    assert abs(report.slope) < 1e-9
    assert report.linearity_significant is False


def test_absolute_linearity_requires_process_variation() -> None:
    report = linearity([1.0, 2.0, 3.0], _reconstruct([1.0, 2.0, 3.0], [0.0, 0.1, 0.2]))
    assert report.linearity is None
    assert report.percent_linearity is not None  # the percentage never needs it


def test_perfect_line_is_a_degenerate_slope_test() -> None:
    # Bias exactly equals the reference (readings 0, 2, 4 at references 0, 1, 2):
    # the points lie exactly on a line, so the residuals are exactly zero and the
    # slope test degenerates, but the slope itself is reported.
    report = linearity([0.0, 1.0, 2.0], [[0.0], [2.0], [4.0]])
    assert report.slope == pytest.approx(1.0, abs=1e-12)
    assert report.slope_std_error == 0.0
    assert any("no residual scatter" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_perfectly_on_target_leaves_r_squared_undefined() -> None:
    # Every reading equals its reference -> no bias anywhere -> the bias never
    # varies, so r^2 (variation explained) is undefined and the slope is zero.
    report = linearity([0.0, 1.0, 2.0], [[0.0], [1.0], [2.0]])
    assert report.slope == pytest.approx(0.0, abs=1e-12)
    assert np.isnan(report.r_squared)
    assert report.linearity_significant is False


def test_one_part_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 2 reference parts"):
        linearity([5.0], [[5.0, 5.1]])


def test_length_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="same length"):
        linearity([1.0, 2.0], [[1.0, 1.1]])


def test_all_equal_references_are_rejected() -> None:
    with pytest.raises(ValueError, match="all equal"):
        linearity([5.0, 5.0], [[5.0, 5.1], [5.2, 4.9]])


def test_too_few_total_readings_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 3 readings"):
        linearity([1.0, 2.0], [[1.0], [2.0]])


def test_non_finite_measurement_is_rejected() -> None:
    with pytest.raises(ValueError, match="NaN or infinite"):
        linearity([1.0, 2.0], [[1.0, 1.1], [2.0, float("inf")]])


def test_non_finite_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="references contain NaN"):
        linearity([1.0, float("nan")], [[1.0, 1.1], [2.0, 2.1]])


def test_bad_alpha_is_rejected() -> None:
    with pytest.raises(ValueError, match="alpha must be in"):
        linearity([1.0, 2.0], [[1.0, 1.1], [2.0, 2.1]], alpha=0.0)


def test_report_is_immutable() -> None:
    report = linearity([1.0, 2.0, 3.0], _reconstruct([1.0, 2.0, 3.0], [0.0, 0.1, 0.2]))
    with pytest.raises(AttributeError):
        report.slope = 0.0  # type: ignore[misc]
    assert isinstance(report, LinearityReport)
