"""Bias study.

Sources and tolerances: ``references/bias.yaml``.

The bias test is a one-sample t-test against a reference. It is pinned to
scipy's own ``ttest_1samp`` (an independent implementation) and to the two AIAG
worked examples -- one biased, one not.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest
import yaml
from capstat_core import BiasReport, bias
from conftest import REFERENCES
from scipy import stats

DOCUMENT = yaml.safe_load((REFERENCES / "bias.yaml").read_text())
CASES = {case["id"]: case for case in DOCUMENT["cases"]}


def _sample_with(mean: float, sd: float, n: int) -> npt.NDArray[np.float64]:
    """A sample of size n with exactly the given mean and sample sd (ddof=1)."""
    base = np.arange(n, dtype=np.float64)
    z = (base - base.mean()) / base.std(ddof=1)
    # asarray with an explicit dtype: numpy's stubs infer the arithmetic as Any
    # on some versions, which mypy strict rejects as a bare return.
    return np.asarray(mean + sd * z, dtype=np.float64)


# ---------------------------------------------------------------------------
# Against scipy, and an exact hand case
# ---------------------------------------------------------------------------


def test_t_and_p_match_scipy_ttest() -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(10.2, 0.5, 20)
    report = bias(data, 10.0)
    scipy_result = stats.ttest_1samp(data, 10.0)
    assert report.t_statistic == pytest.approx(scipy_result.statistic, rel=1e-12)
    assert report.p_value == pytest.approx(scipy_result.pvalue, rel=1e-12)


def test_bias_is_mean_minus_reference() -> None:
    report = bias([5.0, 7.0], 5.0)
    assert report.mean == 6.0
    assert report.bias == 1.0
    assert report.repeatability == pytest.approx(np.std([5.0, 7.0], ddof=1))


# ---------------------------------------------------------------------------
# AIAG worked examples (reconstructed from the published summary statistics)
# ---------------------------------------------------------------------------


def test_aiag_hardness_shows_no_significant_bias() -> None:
    case = CASES["bias-aiag-hardness"]
    inp, exp, tol = case["input"], case["expected"], case["tolerance"]["abs"]
    report = bias(
        _sample_with(inp["target_mean"], inp["target_sd"], inp["n"]),
        inp["reference"],
        alpha=inp["alpha"],
    )
    assert report.mean == pytest.approx(exp["mean"], abs=tol)
    assert report.bias == pytest.approx(exp["bias"], abs=tol)
    assert report.repeatability == pytest.approx(exp["repeatability"], abs=tol)
    # CI for the bias, shifted by the reference, is the CI for the average.
    assert report.ci_lower + inp["reference"] == pytest.approx(
        exp["ci_avg_lower"], abs=tol
    )
    assert report.ci_upper + inp["reference"] == pytest.approx(
        exp["ci_avg_upper"], abs=tol
    )
    assert report.bias_significant is exp["bias_significant"]
    assert report.warnings == ()


def test_aiag_colorimeter_shows_significant_bias() -> None:
    case = CASES["bias-aiag-colorimeter"]
    inp, exp, tol = case["input"], case["expected"], case["tolerance"]["abs"]
    report = bias(
        _sample_with(inp["target_mean"], inp["target_sd"], inp["n"]),
        inp["reference"],
        alpha=inp["alpha"],
    )
    assert report.bias == pytest.approx(exp["bias"], abs=tol)
    assert report.ci_upper + inp["reference"] == pytest.approx(
        exp["ci_avg_upper"], abs=tol
    )
    assert report.bias_significant is True
    assert any("biased" in w and "reads low" in w for w in report.warnings)


def test_ci_verdict_agrees_with_the_p_value() -> None:
    # The CI-based and p-based verdicts are two views of the same test.
    rng = np.random.default_rng(7)
    for shift in (0.0, 0.3, 1.0):
        data = rng.normal(10.0 + shift, 0.4, 15)
        report = bias(data, 10.0, alpha=0.05)
        assert report.bias_significant == (report.p_value < 0.05)


# ---------------------------------------------------------------------------
# Degenerate and validation
# ---------------------------------------------------------------------------


def test_zero_repeatability_with_offset_is_biased() -> None:
    report = bias([7.0, 7.0, 7.0], 5.0)
    assert report.repeatability == 0.0
    assert report.bias_significant is True
    assert any("zero repeatability" in w for w in report.warnings)


def test_zero_repeatability_on_target_is_not_biased() -> None:
    report = bias([5.0, 5.0, 5.0], 5.0)
    assert report.bias == 0.0
    assert report.bias_significant is False


def test_single_measurement_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        bias([5.0], 5.0)


def test_non_finite_is_rejected() -> None:
    with pytest.raises(ValueError, match="NaN or infinite"):
        bias([5.0, float("nan")], 5.0)


def test_bad_alpha_is_rejected() -> None:
    with pytest.raises(ValueError, match="alpha must be in"):
        bias([5.0, 6.0], 5.0, alpha=1.5)


def test_report_is_immutable() -> None:
    report = bias([5.0, 7.0], 5.0)
    with pytest.raises(AttributeError):
        report.bias = 0.0  # type: ignore[misc]
    assert isinstance(report, BiasReport)
