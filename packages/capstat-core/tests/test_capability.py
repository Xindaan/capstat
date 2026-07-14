"""Capability indices and control-chart constants.

Sources and tolerances: ``references/capability.yaml``.

The formulas here are simple; the ways to get capability *wrong* are not. These
tests are aimed at the wrong ways: conflating the two sigmas, inventing a target,
reporting Cpk on a drifting process, and mistyping a constant.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import yaml
from capstat_core import c4, capability, d2
from capstat_core.capability import STABILITY_RATIO, _indices
from capstat_core.constants import MAX_SUBGROUP_SIZE
from conftest import REFERENCES

DOCUMENT = yaml.safe_load((REFERENCES / "capability.yaml").read_text())
CASES = {case["id"]: case for case in DOCUMENT["cases"]}

# mean = 16 exactly, sample sd (ddof=1) = 2 exactly:
#   deviations -2, -2, 0, 2, 2  ->  sum of squares 16, variance 16/4 = 4.
# This reproduces the NIST example's parameters from real data.
NIST_DATA = [14.0, 14.0, 16.0, 18.0, 18.0]


def _stable_subgroups(
    k: int = 30, n: int = 5, sigma: float = 1.0, seed: int = 20260714
) -> np.ndarray:
    """Subgroups from a process with no between-subgroup drift."""
    rng = np.random.default_rng(seed)
    return rng.normal(loc=100.0, scale=sigma, size=(k, n))


def _drifting_subgroups(
    k: int = 30, n: int = 5, sigma: float = 1.0, drift: float = 3.0, seed: int = 7
) -> np.ndarray:
    """Same within-subgroup noise, but the process mean wanders between them."""
    rng = np.random.default_rng(seed)
    within = rng.normal(loc=0.0, scale=sigma, size=(k, n))
    shifts = rng.normal(loc=0.0, scale=drift, size=(k, 1))
    return 100.0 + shifts + within


# ---------------------------------------------------------------------------
# Constants: computed from definitions, checked against independent sources
# ---------------------------------------------------------------------------


def test_d2_matches_the_published_table() -> None:
    case = CASES["d2-published-table"]
    tol = case["tolerance"]["abs"]
    for n, expected in case["expected"].items():
        assert d2(int(n)) == pytest.approx(expected, abs=tol), f"d2({n})"


def test_d2_recovered_from_the_nist_a2_table() -> None:
    """A2 = 3 / (d2 * sqrt(n)); NIST publishes A2 but never states d2.

    This checks our d2 against a table that was not written to contain it.
    """
    case = CASES["d2-recovered-from-nist-a2"]
    tol = case["tolerance"]["abs"]
    for n, a2 in case["input"]["a2"].items():
        recovered = 3.0 / (a2 * math.sqrt(int(n)))
        assert d2(int(n)) == pytest.approx(recovered, abs=tol), f"d2({n}) via A2"


def test_d2_agrees_with_a_monte_carlo_expected_range() -> None:
    """A check that shares no code path with the quadrature at all."""
    rng = np.random.default_rng(42)
    for n in (2, 5, 10):
        draws = rng.standard_normal(size=(400_000, n))
        empirical = float((draws.max(axis=1) - draws.min(axis=1)).mean())
        assert d2(n) == pytest.approx(empirical, rel=5e-3), f"d2({n}) vs Monte Carlo"


def test_c4_matches_published_values() -> None:
    case = CASES["c4-published-values"]
    tol = case["tolerance"]["abs"]
    for n, expected in case["expected"].items():
        assert c4(int(n)) == pytest.approx(expected, abs=tol), f"c4({n})"


def test_c4_approaches_one_for_large_subgroups() -> None:
    """The bias vanishes as n grows; it is a small-sample correction."""
    assert c4(2) < c4(10) < c4(100) < c4(1000) < 1.0
    assert c4(1000) == pytest.approx(1.0, abs=1e-3)


def test_c4_is_computable_at_pooled_degrees_of_freedom() -> None:
    """The pooled estimator calls c4 at df+1, which runs into the hundreds.

    A naive Gamma(n/2) implementation overflows here; ours uses lgamma.
    """
    assert 0.99 < c4(121) < 1.0
    assert math.isfinite(c4(10_000))


def test_constants_reject_impossible_subgroup_sizes() -> None:
    for bad in (0, 1, -3):
        with pytest.raises(ValueError, match="must be >= 2"):
            d2(bad)
    with pytest.raises(ValueError, match=f"must be <= {MAX_SUBGROUP_SIZE}"):
        d2(MAX_SUBGROUP_SIZE + 1)


# ---------------------------------------------------------------------------
# The NIST worked example: pins the index formulas
# ---------------------------------------------------------------------------


def test_index_formulas_match_the_nist_worked_example() -> None:
    case = CASES["nist-capability-worked-example"]
    tol = case["tolerance"]["abs"]
    given = case["input"]
    expected = case["expected"]

    cp, cpl, cpu, cpk = _indices(
        given["mean"], given["sigma"], given["lsl"], given["usl"]
    )

    assert cp == pytest.approx(expected["cp"], abs=tol)
    assert cpl == pytest.approx(expected["cpl"], abs=tol)
    assert cpu == pytest.approx(expected["cpu"], abs=tol)
    assert cpk == pytest.approx(expected["cpk"], abs=tol)


def test_nist_example_reproduced_end_to_end_from_data() -> None:
    """NIST estimates sigma with the sample standard deviation s.

    That is the *overall* sigma, so the NIST numbers land on capstat's Pp/Ppk
    family -- not, as one might carelessly assume, on Cp/Cpk. Getting this
    mapping wrong is precisely the confusion this module exists to prevent.
    """
    case = CASES["nist-capability-worked-example"]
    tol = case["tolerance"]["abs"]
    expected = case["expected"]

    report = capability(NIST_DATA, lsl=8.0, usl=20.0)

    assert report.mean == 16.0
    assert report.sigma_overall == pytest.approx(2.0, rel=1e-15)

    assert report.pp == pytest.approx(expected["cp"], abs=tol)
    assert report.ppk == pytest.approx(expected["cpk"], abs=tol)
    assert report.ppl == pytest.approx(expected["cpl"], abs=tol)
    assert report.ppu == pytest.approx(expected["cpu"], abs=tol)


def test_the_nist_example_is_centred_badly_not_spread_badly() -> None:
    """Cp = 1.0 but Cpk = 0.67: the tolerance is wide enough, the process is
    simply off-centre. If Cpk were not reported, this process would look fine."""
    report = capability(NIST_DATA, lsl=8.0, usl=20.0)
    assert report.pp == pytest.approx(1.0, abs=1e-4)
    assert report.ppk is not None and report.ppk < 0.7


# ---------------------------------------------------------------------------
# The within/overall distinction -- the reason this module exists
# ---------------------------------------------------------------------------


def test_stable_process_has_matching_sigmas() -> None:
    report = capability(_stable_subgroups(), lsl=95.0, usl=105.0)
    assert report.stability_ratio == pytest.approx(1.0, abs=0.1)
    assert report.cp == pytest.approx(report.pp, rel=0.1)
    assert report.cpk == pytest.approx(report.ppk, rel=0.15)


def test_drifting_process_makes_cpk_overstate_ppk() -> None:
    """The whole point. A process that wanders between subgroups has a small
    within-subgroup sigma and a large overall one, so Cpk flatters it. capstat
    must report both and say the process is not stable."""
    report = capability(_drifting_subgroups(), lsl=90.0, usl=110.0)

    assert report.sigma_within < report.sigma_overall
    assert report.stability_ratio > STABILITY_RATIO
    assert report.cpk is not None and report.ppk is not None
    assert report.cpk > report.ppk, "Cpk must exceed Ppk on a drifting process"
    assert any("not stable" in w for w in report.warnings)
    assert any("Pp/Ppk to the customer" in w for w in report.warnings)


@pytest.mark.parametrize("method", ["pooled", "rbar_d2", "sbar_c4"])
def test_every_within_estimator_recovers_the_true_sigma(method: str) -> None:
    """All three estimators target the same quantity and must agree on it."""
    true_sigma = 2.5
    data = _stable_subgroups(k=200, n=5, sigma=true_sigma)
    report = capability(data, lsl=90.0, usl=110.0, within_method=method)  # type: ignore[arg-type]
    assert report.sigma_within == pytest.approx(true_sigma, rel=0.05)


def test_within_estimators_agree_with_each_other() -> None:
    data = _stable_subgroups(k=200, n=5)
    sigmas = [
        capability(data, lsl=90.0, usl=110.0, within_method=m).sigma_within
        for m in ("pooled", "rbar_d2", "sbar_c4")
    ]
    assert max(sigmas) - min(sigmas) < 0.05 * min(sigmas)


def test_individuals_data_uses_the_moving_range_and_says_so() -> None:
    """Handed ungrouped data, capstat must NOT quietly reuse the overall sigma
    and still call the result Cpk."""
    rng = np.random.default_rng(3)
    data = rng.normal(loc=100.0, scale=2.0, size=100)
    report = capability(data, lsl=94.0, usl=106.0)

    assert report.within_method == "moving_range"
    assert report.subgroup_size == 1
    assert report.sigma_within == pytest.approx(2.0, rel=0.15)
    assert any("moving range" in w for w in report.warnings)
    assert any("time order" in w for w in report.warnings)


def test_moving_range_sigma_uses_d2_of_two() -> None:
    data = [10.0, 12.0, 11.0, 13.0, 12.0, 14.0, 13.0, 15.0]
    report = capability(data, lsl=5.0, usl=20.0)
    moving_ranges = np.abs(np.diff(data))
    assert report.sigma_within == pytest.approx(
        float(moving_ranges.mean()) / d2(2), rel=1e-12
    )


# ---------------------------------------------------------------------------
# Cpm
# ---------------------------------------------------------------------------


def test_cpm_equals_cp_when_the_process_is_on_target() -> None:
    """Algebraic identity: with mu == T the penalty term vanishes."""
    data = _stable_subgroups(k=50, n=5)
    on_target = float(data.mean())
    report = capability(data, lsl=95.0, usl=105.0, target=on_target)
    assert report.cpm == pytest.approx(report.cp, rel=1e-12)


def test_cpm_punishes_being_off_target_even_when_cp_does_not() -> None:
    """Cp ignores centring entirely; Cpm is designed not to."""
    data = _stable_subgroups(k=50, n=5)
    centred = capability(data, lsl=95.0, usl=105.0, target=float(data.mean()))
    off = capability(data, lsl=95.0, usl=105.0, target=float(data.mean()) + 2.0)

    assert centred.cp == pytest.approx(off.cp, rel=1e-12), "Cp must not move"
    assert off.cpm is not None and centred.cpm is not None
    assert off.cpm < centred.cpm, "Cpm must fall when the target is missed"


def test_cpm_is_not_computed_without_an_explicit_target() -> None:
    """capstat refuses to assume the target is the midpoint of the spec.

    For an asymmetric tolerance that assumption is simply wrong, and it would
    produce a confident, meaningless Cpm.
    """
    report = capability(_stable_subgroups(), lsl=95.0, usl=106.0)
    assert report.cpm is None
    assert any("does not assume the target" in w for w in report.warnings)


def test_cpm_matches_its_formula() -> None:
    data = _stable_subgroups(k=40, n=5)
    target = 101.0
    report = capability(data, lsl=95.0, usl=105.0, target=target)
    expected = (105.0 - 95.0) / (
        6.0 * math.sqrt(report.sigma_within**2 + (report.mean - target) ** 2)
    )
    assert report.cpm == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------------------
# One-sided specifications
# ---------------------------------------------------------------------------


def test_one_sided_upper_spec() -> None:
    report = capability(_stable_subgroups(), usl=105.0)
    assert report.cp is None and report.pp is None and report.cpm is None
    assert report.cpl is None and report.ppl is None
    assert report.cpu is not None and report.cpk == report.cpu
    assert any("only one specification limit" in w for w in report.warnings)


def test_one_sided_lower_spec() -> None:
    report = capability(_stable_subgroups(), lsl=95.0)
    assert report.cp is None and report.cpu is None
    assert report.cpl is not None and report.cpk == report.cpl


# ---------------------------------------------------------------------------
# The normality gate (T-0004 feeding T-0005)
# ---------------------------------------------------------------------------


def test_non_normal_data_is_flagged_loudly() -> None:
    rng = np.random.default_rng(9)
    data = rng.exponential(scale=2.0, size=(40, 5)) + 90.0
    report = capability(data, lsl=85.0, usl=115.0)

    assert report.normality is not None and report.normality.normal is False
    assert any("not conservative, they are" in w for w in report.warnings)
    assert any("Box-Cox" in w or "ISO 22514" in w for w in report.warnings)


def test_normal_data_carries_a_clean_assessment() -> None:
    # Seed chosen so the sample is actually accepted. This is not seed-shopping
    # to hide a defect: the tests are correctly calibrated (see
    # test_normality_gate_is_correctly_calibrated), so ~7.6 % of genuinely
    # normal samples are rejected by the combined verdict, and the default seed
    # happens to draw one of them (AD p = 0.0105, SW p = 0.0149).
    report = capability(_stable_subgroups(k=40, n=5, seed=101), lsl=95.0, usl=105.0)
    assert report.normality is not None and report.normality.normal is True
    assert not any("normal model was rejected" in w for w in report.warnings)


def test_normality_gate_is_correctly_calibrated() -> None:
    """The gate must reject truly normal data at roughly its nominal rate.

    No reference value can tell us this; it is a property of the whole pipeline
    and the only way to know the gate is neither trigger-happy nor asleep. Note
    the combined verdict rejects *more* than alpha, because it fails closed --
    see NormalityAssessment.
    """
    rejections = 0
    trials = 300
    for seed in range(trials):
        data = np.random.default_rng(seed).normal(loc=100.0, scale=1.0, size=100)
        report = capability(data, lsl=90.0, usl=110.0)
        assert report.normality is not None
        rejections += not report.normality.normal

    rate = rejections / trials
    assert 0.01 < rate < 0.20, (
        f"normality gate rejects {rate:.1%} of genuinely normal samples; "
        f"expected roughly 5-10 % at alpha=0.05"
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_at_least_one_limit_is_required() -> None:
    with pytest.raises(ValueError, match="at least one specification limit"):
        capability(_stable_subgroups())


def test_inverted_limits_are_rejected() -> None:
    with pytest.raises(ValueError, match="must be strictly below"):
        capability(_stable_subgroups(), lsl=105.0, usl=95.0)
    with pytest.raises(ValueError, match="must be strictly below"):
        capability(_stable_subgroups(), lsl=100.0, usl=100.0)


def test_zero_variance_is_rejected() -> None:
    with pytest.raises(ValueError, match="zero variance"):
        capability([[5.0] * 5] * 10, lsl=1.0, usl=9.0)


def test_constant_subgroups_with_between_variation_are_rejected() -> None:
    """Every subgroup constant -> sigma_within is 0 -> Cpk would be infinite."""
    data = [[float(i)] * 5 for i in range(10)]
    with pytest.raises(ValueError, match="within-subgroup sigma is zero"):
        capability(data, lsl=-5.0, usl=15.0, within_method="pooled")


def test_too_few_subgroups_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 2 subgroups"):
        capability([[1.0, 2.0, 3.0]], lsl=0.0, usl=5.0)


def test_non_finite_data_is_rejected() -> None:
    with pytest.raises(ValueError, match="NaN or infinite"):
        capability([1.0, 2.0, float("nan"), 4.0], lsl=0.0, usl=5.0)


def test_oversized_subgroups_reject_the_range_estimator() -> None:
    data = np.random.default_rng(1).normal(100.0, 1.0, size=(5, MAX_SUBGROUP_SIZE + 1))
    with pytest.raises(ValueError, match="poor scale estimator"):
        capability(data, lsl=95.0, usl=105.0, within_method="rbar_d2")
    # ...but the sd-based estimators are fine at that size.
    assert capability(data, lsl=95.0, usl=105.0, within_method="pooled").cpk is not None


def test_few_subgroups_warns_about_confidence() -> None:
    report = capability(_stable_subgroups(k=5, n=5), lsl=95.0, usl=105.0)
    assert any("25 subgroups" in w for w in report.warnings)


def test_report_is_immutable() -> None:
    report = capability(_stable_subgroups(), lsl=95.0, usl=105.0)
    with pytest.raises(AttributeError):
        report.cpk = 99.0  # type: ignore[misc]


def test_three_dimensional_data_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"1-D \(individuals\) or 2-D"):
        capability(np.zeros((2, 3, 4)), lsl=0.0, usl=1.0)


def test_subgroup_estimators_reject_subgroups_of_size_one() -> None:
    """A subgroup of one has no within-subgroup variation to measure."""
    data = np.random.default_rng(1).normal(100.0, 1.0, size=30)
    with pytest.raises(ValueError, match="needs subgroups of size >= 2"):
        capability(data, lsl=95.0, usl=105.0, within_method="pooled")


def test_unknown_within_method_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown within_method"):
        capability(
            _stable_subgroups(),
            lsl=95.0,
            usl=105.0,
            within_method="rbar",  # type: ignore[arg-type]
        )


def test_moving_range_on_subgrouped_data_warns_that_structure_is_ignored() -> None:
    report = capability(
        _stable_subgroups(), lsl=95.0, usl=105.0, within_method="moving_range"
    )
    assert any("ignores the subgroup structure" in w for w in report.warnings)


def test_constants_reject_a_non_integer_subgroup_size() -> None:
    # The `type: ignore` here is load-bearing: it proves mypy still sees d2's
    # real signature. Decorating d2 with @cache directly would erase it (the
    # wrapper's __call__ takes *args: Hashable), and this ignore would then be
    # flagged as unused -- which is exactly how that regression was caught.
    with pytest.raises(TypeError, match="must be an int"):
        d2(5.0)  # type: ignore[arg-type]

    # bool IS a subclass of int, so no type error here even so. That is why the
    # runtime guard checks isinstance(n, bool) explicitly: mypy cannot catch it.
    with pytest.raises(TypeError, match="must be an int"):
        c4(True)
