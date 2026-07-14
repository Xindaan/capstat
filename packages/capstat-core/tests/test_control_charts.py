"""Control-chart constants and Shewhart charts.

Sources and tolerances: ``references/control_charts.yaml``.

The constants are validated against published tables they were not copied from.
The charts are validated by the identity that every Shewhart limit is a
three-sigma limit: if a limit formula were mis-wired, ``A2 * Rbar`` would stop
equalling ``3 * sigma_within / sqrt(n)``.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import yaml
from capstat_core.constants import (
    A2,
    A3,
    B3,
    B4,
    D3,
    D4,
    E2,
    MAX_SUBGROUP_SIZE,
    c4,
    d2,
    d3,
)
from capstat_core.control_charts import (
    i_mr_chart,
    xbar_r_chart,
    xbar_s_chart,
)
from conftest import REFERENCES
from scipy import integrate, stats

DOCUMENT = yaml.safe_load((REFERENCES / "control_charts.yaml").read_text())
CASES = {case["id"]: case for case in DOCUMENT["cases"]}

CONSTANT_ORDER = ("A2", "d2", "d3", "D3", "D4", "A3", "c4", "B3", "B4")
FUNCTIONS = {
    "A2": A2,
    "d2": d2,
    "d3": d3,
    "D3": D3,
    "D4": D4,
    "A3": A3,
    "c4": c4,
    "B3": B3,
    "B4": B4,
}


def _stable(
    k: int = 30, n: int = 5, sigma: float = 1.0, seed: int = 20260714
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(loc=100.0, scale=sigma, size=(k, n))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", range(2, 11))
def test_all_constants_match_the_published_table(n: int) -> None:
    case = CASES["control-chart-constants-table"]
    tol = case["tolerance"]["abs"]
    expected = dict(zip(CONSTANT_ORDER, case["expected"][n], strict=True))

    for name, value in expected.items():
        got = FUNCTIONS[name](n)
        assert got == pytest.approx(value, abs=tol), f"{name}({n})"


def test_d3_derivation_reproduces_d2_from_the_same_joint_density() -> None:
    """Internal consistency: d3 comes from the joint density of the sample
    minimum and maximum. Integrating that same density against (y - x) rather
    than (y - x)^2 must give back d2 -- which is computed by a completely
    different single integral. If the joint density were wrong, d3 would be
    wrong and this check would catch it.
    """

    def expected_range(n: int) -> float:
        def integrand(y: float, x: float) -> float:
            gap = float(stats.norm.cdf(y)) - float(stats.norm.cdf(x))
            return (
                (y - x)
                * n
                * (n - 1)
                * float(stats.norm.pdf(x))
                * float(stats.norm.pdf(y))
                * gap ** (n - 2)
            )

        value, _ = integrate.dblquad(
            integrand, -8.0, 8.0, lambda x: x, lambda _x: 8.0, epsabs=1e-10
        )
        return float(value)

    for n in (2, 5, 10):
        assert expected_range(n) == pytest.approx(d2(n), rel=1e-8), f"n={n}"


def test_e2_published_value_is_slightly_wrong_and_we_do_not_copy_it() -> None:
    """The tables print 2.660. They computed 3/d2 from a rounded d2 = 1.128.

    Our value is the exact one. The gap is 1.3e-3 -- larger than the table's own
    three-decimal rounding can account for, i.e. it is their error, not noise.
    """
    case = CASES["e2-published-value-is-slightly-wrong"]
    tol = case["tolerance"]["abs"]

    assert E2(2) == pytest.approx(case["expected"]["e2_exact"], abs=tol)
    assert E2(2) == pytest.approx(3.0 / d2(2), rel=1e-15)

    published = case["expected"]["e2_as_published"]
    assert abs(E2(2) - published) > 1e-3, (
        "the published E2 should differ from the exact value by more than "
        "rounding; if it no longer does, this note is stale"
    )
    # And here is where their value came from: 3 / (d2 rounded to 3 decimals).
    assert pytest.approx(published, abs=5e-4) == 3.0 / 1.128


def test_lower_dispersion_limits_are_floored_at_zero_for_small_subgroups() -> None:
    """D3 and B3 are zero for small n because the unclamped value is negative --
    and a range or standard deviation cannot be. Not a rounding convention."""
    for n in range(2, 7):
        assert D3(n) == 0.0
        assert 1.0 - 3.0 * d3(n) / d2(n) <= 0.0, f"unclamped D3({n}) should be <= 0"
    for n in range(2, 6):
        assert B3(n) == 0.0

    assert D3(7) > 0.0
    assert B3(6) > 0.0


def test_a2_and_a3_are_three_sigma_over_root_n() -> None:
    for n in range(2, 11):
        assert A2(n) == pytest.approx(3.0 / (d2(n) * math.sqrt(n)), rel=1e-15)
        assert A3(n) == pytest.approx(3.0 / (c4(n) * math.sqrt(n)), rel=1e-15)


def test_d4_and_b4_bracket_one_and_shrink_towards_it() -> None:
    """The limits tighten as subgroups grow: more data, less uncertainty."""
    assert D4(2) > D4(5) > D4(10) > 1.0
    assert B4(2) > B4(5) > B4(10) > 1.0


def test_range_constants_refuse_oversized_subgroups() -> None:
    with pytest.raises(ValueError, match="poor scale estimator"):
        d3(MAX_SUBGROUP_SIZE + 1)


# ---------------------------------------------------------------------------
# Every Shewhart limit is a three-sigma limit
# ---------------------------------------------------------------------------


def test_xbar_r_limits_are_three_sigma_limits() -> None:
    tol = CASES["xbar-limits-are-three-sigma-limits"]["tolerance"]["rel"]
    data = _stable()
    pair = xbar_r_chart(data)
    n = pair.subgroup_size

    half_width = pair.location.limits.upper - pair.location.limits.center
    assert half_width == pytest.approx(3.0 * pair.sigma_within / math.sqrt(n), rel=tol)


def test_xbar_s_limits_are_three_sigma_limits() -> None:
    tol = CASES["xbar-limits-are-three-sigma-limits"]["tolerance"]["rel"]
    data = _stable()
    pair = xbar_s_chart(data)
    n = pair.subgroup_size

    half_width = pair.location.limits.upper - pair.location.limits.center
    assert half_width == pytest.approx(3.0 * pair.sigma_within / math.sqrt(n), rel=tol)


def test_individuals_limits_are_three_sigma_limits() -> None:
    tol = CASES["xbar-limits-are-three-sigma-limits"]["tolerance"]["rel"]
    values = np.random.default_rng(1).normal(100.0, 2.0, size=100)
    pair = i_mr_chart(values)

    half_width = pair.location.limits.upper - pair.location.limits.center
    assert half_width == pytest.approx(3.0 * pair.sigma_within, rel=tol)

    # ...which is also E2 * MRbar, the form the textbooks state.
    mrbar = pair.dispersion.limits.center
    assert half_width == pytest.approx(E2(2) * mrbar, rel=tol)


# ---------------------------------------------------------------------------
# The charts recover the process they were given
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("chart", [xbar_r_chart, xbar_s_chart])
def test_charts_recover_the_true_sigma(chart: object) -> None:
    data = _stable(k=200, n=5, sigma=2.5)
    pair = chart(data)  # type: ignore[operator]
    assert pair.sigma_within == pytest.approx(2.5, rel=0.05)


def test_xbar_r_and_xbar_s_agree_on_sigma() -> None:
    data = _stable(k=200, n=5)
    assert xbar_r_chart(data).sigma_within == pytest.approx(
        xbar_s_chart(data).sigma_within, rel=0.05
    )


def test_individuals_chart_recovers_the_true_sigma() -> None:
    values = np.random.default_rng(2).normal(50.0, 3.0, size=500)
    assert i_mr_chart(values).sigma_within == pytest.approx(3.0, rel=0.1)


def test_a_stable_process_is_in_control() -> None:
    pair = xbar_r_chart(_stable(k=25, n=5))
    assert pair.in_control is True
    assert pair.location.in_control and pair.dispersion.in_control


def test_false_alarm_rate_is_about_three_per_thousand() -> None:
    """Three-sigma limits should flag roughly 0.27 % of points on a process that
    is genuinely stable. No reference value gives us this; it is a property of
    the whole pipeline, and the only way to know the chart is neither
    trigger-happy nor blind."""
    flagged = total = 0
    for seed in range(60):
        pair = xbar_r_chart(_stable(k=25, n=5, seed=seed))
        flagged += len(pair.location.violations)
        total += pair.subgroups

    rate = flagged / total
    assert rate < 0.02, f"X-bar chart flags {rate:.2%} of a stable process"


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


def test_a_shifted_subgroup_is_flagged_on_the_location_chart() -> None:
    data = _stable(k=30, n=5)
    data[17] += 10.0  # a large, sudden shift in one subgroup

    pair = xbar_r_chart(data)
    assert 17 in pair.location.violations
    assert pair.in_control is False
    assert pair.dispersion.in_control is True
    assert any("process centre has moved" in w for w in pair.warnings)


def test_a_burst_of_spread_is_flagged_on_the_dispersion_chart() -> None:
    data = _stable(k=30, n=5)
    data[9] = 100.0 + np.array([-15.0, -7.0, 0.0, 7.0, 15.0])  # same mean, huge spread

    pair = xbar_r_chart(data)
    assert 9 in pair.dispersion.violations
    assert pair.in_control is False


def test_an_unstable_spread_invalidates_the_location_chart_and_says_so() -> None:
    """The classic mistake this pair is built to prevent.

    The X-bar limits are computed from Rbar. If R itself is out of control, Rbar
    is an average of incomparable things and the X-bar limits derived from it
    mean nothing. The dispersion chart is judged first, loudly.
    """
    data = _stable(k=30, n=5)
    data[9] = 100.0 + np.array([-15.0, -7.0, 0.0, 7.0, 15.0])

    pair = xbar_r_chart(data)
    assert pair.dispersion.in_control is False
    assert any("Judge this first" in w for w in pair.warnings)
    assert any("mean nothing" in w for w in pair.warnings)


def test_in_control_is_the_and_of_both_charts() -> None:
    """A wandering spread means out of control even if every average lands
    inside limits that the wandering spread itself inflated."""
    data = _stable(k=30, n=5)
    data[9] = 100.0 + np.array([-15.0, -7.0, 0.0, 7.0, 15.0])

    pair = xbar_r_chart(data)
    assert pair.location.in_control is True
    assert pair.dispersion.in_control is False
    assert pair.in_control is False


def test_individuals_chart_flags_an_outlier() -> None:
    values = np.random.default_rng(3).normal(50.0, 1.0, size=60)
    values[40] = 70.0

    pair = i_mr_chart(values)
    assert 40 in pair.location.violations
    assert pair.in_control is False


# ---------------------------------------------------------------------------
# The honesty warnings
# ---------------------------------------------------------------------------


def test_individuals_chart_always_warns_about_time_order() -> None:
    """Shuffle the data and the limits still look perfectly reasonable. capstat
    cannot detect that, so it never stops saying so."""
    pair = i_mr_chart(np.random.default_rng(4).normal(10.0, 1.0, size=50))
    assert any("time order" in w for w in pair.warnings)
    assert any("nothing about them will look wrong" in w for w in pair.warnings)


def test_small_subgroups_warn_that_improvement_cannot_be_detected() -> None:
    pair = xbar_r_chart(_stable(k=25, n=5))
    assert pair.dispersion.limits.lower == 0.0
    assert any("cannot signal an *improvement*" in w for w in pair.warnings)


def test_larger_subgroups_regain_a_lower_limit() -> None:
    pair = xbar_r_chart(_stable(k=25, n=8))
    assert pair.dispersion.limits.lower > 0.0
    assert not any("cannot signal an *improvement*" in w for w in pair.warnings)


def test_too_few_subgroups_warns_about_phase_one_limits() -> None:
    pair = xbar_r_chart(_stable(k=6, n=5))
    assert any("Phase I trial limits" in w for w in pair.warnings)
    assert any("20-25" in w for w in pair.warnings)


def test_large_subgroups_recommend_the_s_chart() -> None:
    pair = xbar_r_chart(_stable(k=25, n=12))
    assert any("Prefer xbar_s_chart" in w for w in pair.warnings)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_xbar_r_rejects_oversized_subgroups() -> None:
    data = _stable(k=5, n=MAX_SUBGROUP_SIZE + 1)
    with pytest.raises(ValueError, match="poor scale estimator"):
        xbar_r_chart(data)
    # ...but the s chart handles them.
    assert xbar_s_chart(data).sigma_within > 0.0


def test_subgroup_charts_reject_one_dimensional_data() -> None:
    with pytest.raises(ValueError, match="expected 2-D data"):
        xbar_r_chart([1.0, 2.0, 3.0, 4.0])


def test_subgroup_charts_reject_subgroups_of_one() -> None:
    with pytest.raises(ValueError, match="use i_mr_chart"):
        xbar_s_chart([[1.0], [2.0], [3.0]])


def test_subgroup_charts_need_at_least_two_subgroups() -> None:
    with pytest.raises(ValueError, match="at least 2 subgroups"):
        xbar_r_chart([[1.0, 2.0, 3.0]])


def test_charts_reject_non_finite_data() -> None:
    with pytest.raises(ValueError, match="NaN or infinite"):
        xbar_r_chart([[1.0, 2.0], [3.0, float("nan")]])
    with pytest.raises(ValueError, match="NaN or infinite"):
        i_mr_chart([1.0, 2.0, float("inf")])


def test_charts_are_immutable() -> None:
    pair = xbar_r_chart(_stable())
    with pytest.raises(AttributeError):
        pair.sigma_within = 1.0  # type: ignore[misc]
    with pytest.raises(AttributeError):
        pair.location.limits.center = 0.0  # type: ignore[misc]
