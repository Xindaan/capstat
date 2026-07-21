"""Normality tests: reference validation and reporting contracts.

Sources and tolerances: ``references/normality.yaml``.

The Anderson-Darling p-value is the only part of this module capstat owns
outright (scipy supplies a statistic and critical values, but no p-value), so
it carries the heaviest validation: a round-trip against independently
published critical values, a branch-continuity check, and a cross-check of the
statistic itself against scipy on nine real datasets.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pytest
import yaml
from capstat_core import (
    anderson_darling,
    anderson_darling_pvalue,
    assess_normality,
    shapiro_wilk,
)
from capstat_core.normality import AD_MIN_SAMPLE_SIZE
from conftest import REFERENCES, load_strd_dataset
from scipy import stats

DOCUMENT = yaml.safe_load((REFERENCES / "normality.yaml").read_text())
CASES = {case["id"]: case for case in DOCUMENT["cases"]}

STRD_DATASETS = [
    "PiDigits",
    "Lottery",
    "Lew",
    "Mavro",
    "Michelso",
    "NumAcc2",
    "NumAcc3",
    "NumAcc4",
]


def _normal_sample(n: int = 200, seed: int = 20260714) -> np.ndarray:
    return np.random.default_rng(seed).normal(loc=100.0, scale=5.0, size=n)


# ---------------------------------------------------------------------------
# Shapiro-Wilk: published R shapiro.test() values
# ---------------------------------------------------------------------------


def test_shapiro_wilk_matches_published_r_value() -> None:
    case = CASES["shapiro-wilk-published-r-value"]
    tol = case["tolerance"]["abs"]

    result = shapiro_wilk(case["input"])

    assert result.statistic == pytest.approx(case["expected"]["statistic"], abs=tol)
    assert result.p_value == pytest.approx(case["expected"]["p_value"], abs=tol)
    assert result.normal is False, "the published example is clearly non-normal"
    assert result.test == "shapiro-wilk"
    assert result.n == 11


# ---------------------------------------------------------------------------
# Anderson-Darling p-value: validated against a source that did not produce it
# ---------------------------------------------------------------------------


def test_ad_pvalue_returns_nominal_alpha_at_published_critical_values() -> None:
    """The load-bearing test for the p-value approximation.

    Stephens' critical values for A*^2 and D'Agostino & Stephens' p-value
    approximation come from different publications. Feeding the former into the
    latter must return the nominal significance levels. If a coefficient were
    mis-transcribed, this round-trip would not close.
    """
    case = CASES["ad-pvalue-calibration"]
    rel = case["tolerance"]["rel"]

    critical_values = case["input"]["adjusted_statistic"]
    alphas = case["expected"]["alpha"]

    for critical, alpha in zip(critical_values, alphas, strict=True):
        assert anderson_darling_pvalue(critical) == pytest.approx(alpha, rel=rel)


def test_ad_critical_value_matches_the_nist_handbook() -> None:
    """The alpha = 0.05 critical value, against a source that is not scipy.

    Our table is Stephens (1974); the NIST/SEMATECH handbook states the same
    5 % value independently. This is deliberately a separate test from the
    scipy cross-check below, which scipy 1.19 will take away -- when it goes,
    this one still holds the table to an outside source.
    """
    published = CASES["ad-pvalue-calibration"]["input"]["adjusted_statistic"]
    alphas = CASES["ad-pvalue-calibration"]["expected"]["alpha"]

    # NIST/SEMATECH e-Handbook 1.3.5.14; see references/normality.yaml.
    assert published[alphas.index(0.05)] == 0.752


@pytest.mark.filterwarnings("ignore:As of SciPy 1.17:FutureWarning")
def test_ad_critical_values_agree_with_scipy() -> None:
    """Our critical-value source must be the same one scipy uses.

    scipy stores Stephens' table and divides it by the adjustment factor;
    capstat multiplies the statistic by that factor instead. The two are the
    same test, so scipy's tabulated values must be recoverable.

    scipy 1.17 deprecated the attributes this reads and 1.19 removes them.
    capstat's own code never touches them -- it implements the statistic
    itself -- so the right behaviour when they vanish is to stop performing a
    corroboration we can no longer perform, not to fail and not to quietly
    turn into a comparison of our table against itself. The handbook check
    above is what survives. Tracked as T-0021.
    """
    case = CASES["ad-pvalue-calibration"]
    published = case["input"]["adjusted_statistic"]

    n = 100
    scipy_result = stats.anderson(_normal_sample(n), dist="norm")
    if not hasattr(scipy_result, "critical_values"):  # pragma: no cover
        pytest.skip(
            "scipy no longer exposes anderson().critical_values (removed in "
            "1.19); the NIST handbook check still covers the table."
        )
    adjustment = 1.0 + 0.75 / n + 2.25 / n**2

    recovered = [c * adjustment for c in scipy_result.critical_values]
    # scipy rounds its table to 3 decimals, hence the 1e-3 tolerance.
    assert recovered == pytest.approx(published, abs=2e-3)
    assert list(scipy_result.significance_level) == [15.0, 10.0, 5.0, 2.5, 1.0]


@pytest.mark.parametrize("boundary", [0.2, 0.34, 0.6])
def test_ad_pvalue_branches_are_continuous(boundary: float) -> None:
    """A mistyped coefficient would tear a branch boundary open."""
    tol = CASES["ad-pvalue-branch-continuity"]["tolerance"]["abs"]
    below = anderson_darling_pvalue(boundary - 1e-12)
    at = anderson_darling_pvalue(boundary)
    assert below == pytest.approx(at, abs=tol)


def test_ad_pvalue_is_monotonically_decreasing() -> None:
    """More evidence against normality must never mean a larger p-value."""
    grid = np.linspace(0.01, 9.99, 2000)
    values = [anderson_darling_pvalue(float(a)) for a in grid]
    for previous, current in itertools.pairwise(values):
        assert current <= previous + 5e-3  # branch jumps, see the YAML


def test_ad_pvalue_is_bounded_to_the_unit_interval() -> None:
    for a in [1e-9, 0.05, 0.2, 0.34, 0.6, 1.0, 5.0, 9.99, 10.0, 1e6]:
        assert 0.0 <= anderson_darling_pvalue(a) <= 1.0


def test_ad_pvalue_uses_the_published_floor_beyond_ten() -> None:
    assert anderson_darling_pvalue(10.0) == 3.7e-24
    assert anderson_darling_pvalue(1e6) == 3.7e-24


# ---------------------------------------------------------------------------
# Anderson-Darling statistic: cross-check against scipy on real data
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", STRD_DATASETS)
def test_ad_statistic_matches_scipy(name: str) -> None:
    """Our A^2 must equal scipy's, an independent implementation, on real data.

    Tolerance 1e-10 rather than machine epsilon: Mavro's standard deviation is
    4.3e-04, so standardising by it amplifies rounding differences between the
    two implementations to ~2e-12 relative. That is agreement, not a defect.
    """
    data = load_strd_dataset(f"data/nist_strd/{name}.dat")
    ours = anderson_darling(data).statistic
    # method="interpolate": scipy 1.17 warns unless a method is chosen, and the
    # warning is raised by the *call*, not by reading a deprecated attribute.
    # This test only wants the statistic, which every method returns, so naming
    # one costs nothing and makes it scipy-1.19-proof.
    theirs = float(stats.anderson(data, dist="norm", method="interpolate").statistic)
    assert ours == pytest.approx(theirs, rel=1e-10)


def test_ad_statistic_survives_extreme_tails() -> None:
    """log-space cdf/sf, not log(cdf): the linear-space survival function
    underflows to zero far out in the tail, and log(0) would poison the sum."""
    data = np.concatenate([_normal_sample(50), np.array([1e3, -1e3])])
    result = anderson_darling(data)
    assert math.isfinite(result.statistic)
    assert result.statistic > 0.0
    assert 0.0 <= result.p_value <= 1.0


# ---------------------------------------------------------------------------
# Both tests: behaviour on data of known character
# ---------------------------------------------------------------------------


def test_both_tests_accept_normal_data() -> None:
    data = _normal_sample(300)
    assert anderson_darling(data).normal is True
    assert shapiro_wilk(data).normal is True


@pytest.mark.parametrize("name", ["Lottery", "Michelso"])
def test_both_tests_agree_on_real_datasets(name: str) -> None:
    """Sanity: the two tests should not contradict each other on clear cases."""
    data = load_strd_dataset(f"data/nist_strd/{name}.dat")
    assert anderson_darling(data).normal == shapiro_wilk(data).normal


def test_both_tests_reject_a_clearly_skewed_sample() -> None:
    data = np.random.default_rng(7).exponential(scale=2.0, size=200)
    assert anderson_darling(data).normal is False
    assert shapiro_wilk(data).normal is False


# ---------------------------------------------------------------------------
# assess_normality: the reporting contract
# ---------------------------------------------------------------------------


def test_assessment_of_normal_data_is_clean() -> None:
    report = assess_normality(_normal_sample(300))
    assert report.normal is True
    assert report.warnings == ()
    assert "defensible" in report.recommendation


def test_assessment_recommends_the_non_normal_path_on_rejection() -> None:
    data = np.random.default_rng(11).exponential(scale=2.0, size=200)
    report = assess_normality(data)
    assert report.normal is False
    assert "Box-Cox" in report.recommendation
    assert "ISO 22514" in report.recommendation


def test_assessment_warns_about_autocorrelation() -> None:
    """Mavro has a lag-1 autocorrelation of ~0.94, which invalidates both tests.

    A tool that reported only a p-value here would be actively misleading.
    """
    data = load_strd_dataset("data/nist_strd/Mavro.dat")
    report = assess_normality(data)

    assert report.lag1_autocorrelation == pytest.approx(0.937989183438248, rel=1e-9)
    assert any("autocorrelation" in w for w in report.warnings)
    assert any("independent observations" in w for w in report.warnings)


def test_assessment_warns_when_the_sample_is_too_small_to_have_power() -> None:
    report = assess_normality([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.5])
    assert report.n < 20
    assert any("little power" in w for w in report.warnings)


def test_assessment_warns_when_a_large_sample_makes_trivia_significant() -> None:
    data = load_strd_dataset("data/nist_strd/PiDigits.dat")
    report = assess_normality(data)
    assert report.n == 5000
    assert report.normal is False
    assert any("statistically significant" in w for w in report.warnings)


def test_assessment_surfaces_disagreement_between_the_tests() -> None:
    """A borderline sample: the verdict must not paper over a split decision.

    Mildly skewed gamma samples land near the rejection boundary, where the two
    tests have different power and can genuinely disagree. When they do, the
    assessment must fail closed (non-normal) and say so.
    """
    rng = np.random.default_rng(3)
    for _ in range(500):
        data = rng.gamma(shape=9.0, scale=1.0, size=50)
        report = assess_normality(data)
        if report.anderson_darling.normal != report.shapiro_wilk.normal:
            assert report.normal is False, "a split decision must fail closed"
            assert any("disagree" in w for w in report.warnings)
            return
    pytest.skip("no disagreeing sample found in 500 draws")


def test_assessment_fails_closed_when_only_one_test_rejects() -> None:
    """`normal` is the AND of both tests, never the OR."""
    data = np.random.default_rng(5).exponential(size=100)
    report = assess_normality(data)
    assert report.normal == (
        report.anderson_darling.normal and report.shapiro_wilk.normal
    )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_anderson_darling_requires_eight_observations() -> None:
    """Matches the guard in R's nortest::ad.test; the p-value is undefined below."""
    assert AD_MIN_SAMPLE_SIZE == 8
    with pytest.raises(ValueError, match="at least 8 observation"):
        anderson_darling([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])


def test_shapiro_wilk_requires_three_observations() -> None:
    with pytest.raises(ValueError, match="at least 3 observation"):
        shapiro_wilk([1.0, 2.0])


def test_assess_normality_requires_eight_observations() -> None:
    with pytest.raises(ValueError, match="at least 8 observation"):
        assess_normality([1.0, 2.0, 3.0, 4.0, 5.0])


@pytest.mark.parametrize("function", [anderson_darling, shapiro_wilk, assess_normality])
def test_constant_sample_is_rejected(function: object) -> None:
    with pytest.raises(ValueError, match="zero variance"):
        function([3.0] * 12)  # type: ignore[operator]


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.5])
def test_invalid_alpha_is_rejected(alpha: float) -> None:
    data = _normal_sample(30)
    with pytest.raises(ValueError, match=r"alpha must be in \(0.0, 1.0\)"):
        anderson_darling(data, alpha=alpha)
    with pytest.raises(ValueError, match=r"alpha must be in \(0.0, 1.0\)"):
        shapiro_wilk(data, alpha=alpha)
    with pytest.raises(ValueError, match=r"alpha must be in \(0.0, 1.0\)"):
        assess_normality(data, alpha=alpha)


def test_alpha_moves_the_verdict_not_the_pvalue() -> None:
    """alpha is the decision threshold; it must not touch the evidence."""
    data = _normal_sample(200)
    p = anderson_darling(data).p_value
    assert 0.0 < p < 1.0

    lenient = anderson_darling(data, alpha=p * 0.5)  # alpha below p -> not rejected
    strict = anderson_darling(data, alpha=p + (1.0 - p) / 2)  # alpha above p -> reject

    assert lenient.p_value == strict.p_value == p, "alpha must not move the p-value"
    assert lenient.normal is True
    assert strict.normal is False


def test_results_are_immutable() -> None:
    result = shapiro_wilk(_normal_sample(30))
    with pytest.raises(AttributeError):
        result.p_value = 1.0  # type: ignore[misc]
