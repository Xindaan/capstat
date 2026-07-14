"""EWMA and CUSUM charts.

Sources and tolerances: ``references/time_weighted.yaml``.

Both NIST worked examples are reproduced. Beyond that, the tests check the
property that justifies these charts existing at all -- that they catch a small
sustained shift a Shewhart chart sleeps through -- and the trap that most often
breaks them in practice: estimating sigma from data that already contain the
shift.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pytest
import yaml
from capstat_core.time_weighted import CusumChart, cusum_chart, ewma_chart
from conftest import REFERENCES
from scipy import stats

DOCUMENT = yaml.safe_load((REFERENCES / "time_weighted.yaml").read_text())
CASES = {case["id"]: case for case in DOCUMENT["cases"]}


def _shifted(
    n: int = 60, shift: float = 1.0, at: int = 30, seed: int = 3
) -> np.ndarray:
    """A process that steps up by `shift` sigma at index `at` and stays there."""
    rng = np.random.default_rng(seed)
    values = rng.normal(loc=100.0, scale=1.0, size=n)
    values[at:] += shift
    return values


# ---------------------------------------------------------------------------
# The NIST worked examples
# ---------------------------------------------------------------------------


def test_ewma_reproduces_the_nist_worked_example() -> None:
    case = CASES["nist-ewma-worked-example"]
    given, expected = case["input"], case["expected"]
    tol = case["tolerance"]["abs"]
    limit_tol = case["tolerance"]["limits_abs"]

    chart = ewma_chart(
        given["data"],
        target=given["target"],
        sigma=given["sigma"],
        lmbda=given["lmbda"],
        L=given["L"],
        time_varying_limits=False,  # NIST uses the steady-state width throughout
    )

    for i, (got, want) in enumerate(
        zip(chart.points, expected["ewma"], strict=True), start=1
    ):
        assert got == pytest.approx(want, abs=tol), f"EWMA at point {i}"

    lcl, ucl = chart.steady_state_limits
    assert ucl == pytest.approx(expected["ucl"], abs=limit_tol)
    assert lcl == pytest.approx(expected["lcl"], abs=limit_tol)
    assert chart.in_control is expected["in_control"]


def test_cusum_reproduces_the_nist_worked_example() -> None:
    case = CASES["nist-cusum-worked-example"]
    given, expected = case["input"], case["expected"]
    tol = case["tolerance"]["abs"]
    design_tol = case["tolerance"]["design_abs"]

    chart = cusum_chart(
        given["data"],
        target=given["target"],
        sigma=given["sigma"],
        k=given["k"],
        h=given["h"],
    )

    # The design constants, converted from sigma units into the data's units.
    assert pytest.approx(expected["K"], abs=design_tol) == chart.K
    assert pytest.approx(expected["H"], abs=design_tol) == chart.H

    for i, (got, want) in enumerate(
        zip(chart.upper, expected["s_hi"], strict=True), start=1
    ):
        assert got == pytest.approx(want, abs=tol), f"S_hi at group {i}"
    for i, (got, want) in enumerate(
        zip(chart.lower, expected["s_lo"], strict=True), start=1
    ):
        assert got == pytest.approx(want, abs=tol), f"S_lo at group {i}"


def test_cusum_signals_at_exactly_the_group_nist_says() -> None:
    """The values carry a tolerance because NIST's printed inputs are rounded and
    a cumulative sum compounds that rounding. The *decision* carries none: NIST
    signals at group 14, and so must we -- exactly."""
    case = CASES["nist-cusum-worked-example"]
    given, expected = case["input"], case["expected"]

    chart = cusum_chart(
        given["data"],
        target=given["target"],
        sigma=given["sigma"],
        k=given["k"],
        h=given["h"],
    )

    first_signal_group = chart.violations[0] + 1  # violations are 0-indexed
    assert first_signal_group == expected["first_signal_group"]
    assert chart.in_control is False


def test_the_cusum_tolerance_really_is_input_rounding_not_slack() -> None:
    """Guards the tolerance itself, so it cannot quietly hide a defect.

    NIST prints its inputs to two decimals, so each is uncertain by up to 0.005.
    A CUSUM is a cumulative sum, so that uncertainty *accumulates* rather than
    averaging out. The worst case is a systematic offset in one direction -- and
    a +0.005 shift on every input moves the final S_hi by 0.040.

    Our actual disagreement with NIST's printed table is 0.0275, comfortably
    inside that bound. So the 3e-2 tolerance is fully explained by the rounding
    of their published inputs, and does not have room to conceal an error.

    (Note the subtlety: *random* jitter of the same magnitude only moves S_hi by
    ~0.017, because random errors partially cancel in the sum. The systematic
    case is the right bound to argue from, and the looser one.)
    """
    case = CASES["nist-cusum-worked-example"]
    given = case["input"]
    tolerance = case["tolerance"]["abs"]

    def chart_for(data: object) -> CusumChart:
        return cusum_chart(
            data,  # type: ignore[arg-type]
            target=given["target"],
            sigma=given["sigma"],
            k=given["k"],
            h=given["h"],
        )

    base = chart_for(given["data"])
    offset = chart_for(np.asarray(given["data"], dtype=float) + 0.005)

    reachable = abs(offset.upper[-1] - base.upper[-1])
    assert reachable >= tolerance, (
        f"a systematic +0.005 rounding of the inputs moves S_hi by only "
        f"{reachable:.4f}, which does not reach the {tolerance} tolerance. The "
        f"tolerance is therefore NOT explained by input rounding, and something "
        f"else is wrong."
    )


# ---------------------------------------------------------------------------
# Why these charts exist: they see what Shewhart misses
# ---------------------------------------------------------------------------


def test_shewhart_needs_about_44_points_to_see_a_one_sigma_shift() -> None:
    """The analytic baseline these charts are competing against."""
    per_point = float(stats.norm.sf(3.0 - 1.0) + stats.norm.cdf(-3.0 - 1.0))
    assert 1.0 / per_point == pytest.approx(43.9, abs=0.5)


def test_cusum_detects_a_one_sigma_shift_in_about_ten_points() -> None:
    """Simulated, not taken on trust. k=0.5, h=5 is the classic design."""
    rng = np.random.default_rng(7)

    def run_length(shift: float, cap: int = 2000) -> int:
        high = low = 0.0
        for i in range(1, cap + 1):
            x = float(rng.normal(shift, 1.0))
            high = max(0.0, high + x - 0.5)
            low = max(0.0, low - 0.5 - x)
            if high > 5.0 or low > 5.0:
                return i
        return cap

    arl1 = float(np.mean([run_length(1.0) for _ in range(2000)]))
    assert 8.0 < arl1 < 13.0, f"CUSUM ARL1 = {arl1:.1f}, expected ~10"


def test_cusum_does_not_cry_wolf_when_nothing_has_changed() -> None:
    """Sensitivity is worthless without a long in-control ARL. The k=0.5, h=5
    design should run ~465 points between false alarms."""
    rng = np.random.default_rng(21)

    def run_length(cap: int = 3000) -> int:
        high = low = 0.0
        for i in range(1, cap + 1):
            x = float(rng.normal(0.0, 1.0))
            high = max(0.0, high + x - 0.5)
            low = max(0.0, low - 0.5 - x)
            if high > 5.0 or low > 5.0:
                return i
        return cap

    arl0 = float(np.mean([run_length() for _ in range(800)]))
    assert arl0 > 300.0, f"CUSUM false-alarms every {arl0:.0f} points; too jumpy"


@pytest.mark.parametrize("chart", [ewma_chart, cusum_chart])
def test_both_charts_catch_a_sustained_shift(chart: object) -> None:
    """A single series, so the bound is generous: the detection delay is a random
    variable with a mean near 8 but a 95th percentile around 16 and a long tail.
    The *statistical* claim lives in the ARL tests above; this one only asserts
    that the shift is found, and never before it happened.
    """
    values = _shifted(n=100, shift=1.0, at=30)
    result = chart(values, target=100.0, sigma=1.0)  # type: ignore[operator]

    assert result.in_control is False
    first = result.violations[0]
    assert first >= 30, "must not signal before the shift happens"
    assert first < 60, f"took {first - 30} points to see a 1-sigma shift; too slow"


def test_ewma_false_alarm_rate_is_low_but_not_zero() -> None:
    """A three-sigma EWMA has an in-control ARL of roughly 500, so on a stable
    process it *will* eventually cry wolf -- about a third of 200-point series
    contain a false alarm. Asserting that any one series is clean would be
    asserting something false. The rate is what must be small.
    """
    alarms = points = 0
    for seed in range(120):
        values = np.random.default_rng(seed).normal(100.0, 1.0, size=200)
        chart = ewma_chart(values, target=100.0, sigma=1.0)
        alarms += len(chart.violations)
        points += values.size

    rate = alarms / points
    assert rate < 0.01, (
        f"EWMA flags {rate:.2%} of points on a stable process; with an ARL0 near "
        f"500 it should flag well under 1 %"
    )


# ---------------------------------------------------------------------------
# The sigma trap
# ---------------------------------------------------------------------------


def test_sigma_from_the_overall_sd_would_hide_the_very_shift_being_hunted() -> None:
    """The failure this module's default is built to avoid.

    A sustained shift inflates the overall standard deviation. Feed that inflated
    sigma back in as the chart's sigma and the limits widen to swallow the shift
    -- the chart then reports that all is well.

    The moving-range estimate is nearly immune, because it only ever looks at
    *consecutive* differences: a level change contributes one large moving range
    and nothing more. Averaged over 200 seeds, with a 2-sigma sustained shift in
    data of true sigma 1.0, the moving-range estimate lands on 1.002 while the
    overall standard deviation is inflated to 1.406.
    """
    true_sigma = 1.0
    overall: list[float] = []
    moving_range: list[float] = []

    for seed in range(200):
        rng = np.random.default_rng(seed)
        values = rng.normal(100.0, true_sigma, size=80)
        values[40:] += 2.0 * true_sigma

        overall.append(float(np.std(values, ddof=1)))
        moving_range.append(cusum_chart(values, target=100.0).sigma)

    mean_overall = float(np.mean(overall))
    mean_moving_range = float(np.mean(moving_range))

    assert mean_moving_range == pytest.approx(true_sigma, rel=0.05), (
        "the moving-range estimate must survive a sustained shift almost intact"
    )
    assert mean_overall > 1.25 * true_sigma, (
        "the overall sd must be materially inflated by the shift; if it is not, "
        "this test proves nothing"
    )

    # And the consequence: the chart built on the inflated sigma sees less.
    rng = np.random.default_rng(0)
    values = rng.normal(100.0, true_sigma, size=80)
    values[40:] += 2.0 * true_sigma

    naive = cusum_chart(values, target=100.0, sigma=mean_overall)
    careful = cusum_chart(values, target=100.0)
    assert len(careful.violations) > len(naive.violations)


def test_the_moving_range_default_is_announced_not_assumed() -> None:
    chart = cusum_chart(_shifted(), target=100.0)
    assert any("moving range" in w for w in chart.warnings)
    assert any("absorb any sustained shift" in w for w in chart.warnings)


def test_a_target_taken_from_the_data_is_flagged() -> None:
    """If the data contain the shift, the mean is pulled towards it and the chart
    is desensitised. capstat uses the mean when it must, but says so."""
    chart = ewma_chart(_shifted())
    assert any("no target was given" in w for w in chart.warnings)
    assert any("less sensitive than it looks" in w for w in chart.warnings)


def test_no_warnings_when_target_and_sigma_are_supplied() -> None:
    chart = ewma_chart(_shifted(), target=100.0, sigma=1.0)
    assert chart.warnings == ()


# ---------------------------------------------------------------------------
# EWMA limits
# ---------------------------------------------------------------------------


def test_ewma_limits_widen_towards_the_steady_state() -> None:
    """The variance of z_i grows with i, so the correct limits are not constant."""
    chart = ewma_chart(
        np.random.default_rng(1).normal(0.0, 1.0, size=50),
        target=0.0,
        sigma=1.0,
        lmbda=0.3,
    )
    widths = [u - lo for u, lo in zip(chart.upper, chart.lower, strict=True)]

    assert widths[0] < widths[1] < widths[2]
    assert all(a <= b + 1e-12 for a, b in itertools.pairwise(widths))

    steady_width = chart.steady_state_limits[1] - chart.steady_state_limits[0]
    assert widths[-1] == pytest.approx(steady_width, rel=1e-6)
    assert all(w <= steady_width + 1e-12 for w in widths)


def test_the_steady_state_limit_is_forty_percent_too_wide_at_the_first_point() -> None:
    """Which is why capstat does not use it by default, and NIST's example does.

    A shift already present at the start of the series can hide under a limit
    that is 40 % wider than it should be.
    """
    lmbda = 0.3
    correct_factor = math.sqrt(1.0 - (1.0 - lmbda) ** 2)
    assert 1.0 / correct_factor == pytest.approx(1.40, abs=0.01)

    exact = ewma_chart([1.0, 2.0], target=0.0, sigma=1.0, lmbda=lmbda)
    steady = ewma_chart(
        [1.0, 2.0], target=0.0, sigma=1.0, lmbda=lmbda, time_varying_limits=False
    )
    assert steady.upper[0] == pytest.approx(exact.upper[0] / correct_factor, rel=1e-12)


def test_steady_state_mode_warns_that_early_limits_are_too_wide() -> None:
    chart = ewma_chart(_shifted(), target=100.0, sigma=1.0, time_varying_limits=False)
    assert any("early limits are therefore too wide" in w for w in chart.warnings)


def test_lambda_one_reduces_ewma_to_a_shewhart_individuals_chart() -> None:
    """The sanity check on the recursion: with all the weight on the newest
    point, the EWMA *is* the data, and its limits are plain three-sigma limits."""
    values = np.random.default_rng(5).normal(0.0, 1.0, size=40)
    chart = ewma_chart(values, target=0.0, sigma=1.0, lmbda=1.0, L=3.0)

    assert chart.points == pytest.approx(tuple(values), rel=1e-12)
    for lo, hi in zip(chart.lower, chart.upper, strict=True):
        assert lo == pytest.approx(-3.0, rel=1e-12)
        assert hi == pytest.approx(3.0, rel=1e-12)


def test_smaller_lambda_gives_a_longer_memory() -> None:
    """A step input: a small lambda approaches the new level more slowly."""
    step = np.concatenate([np.zeros(5), np.ones(20)])
    slow = ewma_chart(step, target=0.0, sigma=1.0, lmbda=0.1)
    fast = ewma_chart(step, target=0.0, sigma=1.0, lmbda=0.8)

    assert slow.points[6] < fast.points[6]
    assert fast.points[-1] == pytest.approx(1.0, abs=1e-3)


# ---------------------------------------------------------------------------
# CUSUM mechanics
# ---------------------------------------------------------------------------


def test_cusum_slack_absorbs_noise_below_k() -> None:
    """A deviation smaller than the slack banks nothing; that is what stops the
    chart accumulating ordinary noise into a false signal."""
    on_target = [100.0] * 20
    chart = cusum_chart(on_target, target=100.0, sigma=1.0)
    assert all(v == 0.0 for v in chart.upper)
    assert all(v == 0.0 for v in chart.lower)


def test_cusum_banks_only_the_excess_beyond_the_slack() -> None:
    chart = cusum_chart([102.0, 102.0], target=100.0, sigma=1.0, k=0.5)
    # each point contributes (102 - 100 - 0.5) = 1.5
    assert chart.upper[0] == pytest.approx(1.5, rel=1e-12)
    assert chart.upper[1] == pytest.approx(3.0, rel=1e-12)


def test_cusum_detects_a_downward_shift_on_the_lower_arm() -> None:
    values = _shifted(shift=-2.0, at=25)
    chart = cusum_chart(values, target=100.0, sigma=1.0)

    assert chart.in_control is False
    first = chart.violations[0]
    assert chart.lower[first] > chart.H
    assert chart.upper[first] == 0.0


def test_cusum_arms_reset_to_zero_and_never_go_negative() -> None:
    values = np.random.default_rng(6).normal(100.0, 1.0, size=100)
    chart = cusum_chart(values, target=100.0, sigma=1.0)
    assert all(v >= 0.0 for v in chart.upper)
    assert all(v >= 0.0 for v in chart.lower)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.5])
def test_invalid_lambda_is_rejected(bad: float) -> None:
    with pytest.raises(ValueError, match=r"lmbda must be in \(0, 1\]"):
        ewma_chart([1.0, 2.0, 3.0], lmbda=bad)


def test_invalid_L_is_rejected() -> None:
    with pytest.raises(ValueError, match="L must be strictly positive"):
        ewma_chart([1.0, 2.0, 3.0], L=0.0)


@pytest.mark.parametrize("field", ["k", "h"])
def test_invalid_cusum_design_is_rejected(field: str) -> None:
    with pytest.raises(ValueError, match=f"{field} must be strictly positive"):
        cusum_chart([1.0, 2.0, 3.0], **{field: 0.0})


@pytest.mark.parametrize("chart", [ewma_chart, cusum_chart])
def test_non_positive_sigma_is_rejected(chart: object) -> None:
    with pytest.raises(ValueError, match="sigma must be strictly positive"):
        chart([1.0, 2.0, 3.0], target=1.0, sigma=0.0)  # type: ignore[operator]


@pytest.mark.parametrize("chart", [ewma_chart, cusum_chart])
def test_charts_need_two_observations(chart: object) -> None:
    with pytest.raises(ValueError, match="at least 2 observation"):
        chart([1.0])  # type: ignore[operator]


@pytest.mark.parametrize("chart", [ewma_chart, cusum_chart])
def test_charts_reject_non_finite_data(chart: object) -> None:
    with pytest.raises(ValueError, match="NaN or infinite"):
        chart([1.0, 2.0, float("nan")])  # type: ignore[operator]


@pytest.mark.parametrize("chart", [ewma_chart, cusum_chart])
def test_charts_are_immutable(chart: object) -> None:
    result = chart([1.0, 2.0, 3.0], target=2.0, sigma=1.0)  # type: ignore[operator]
    with pytest.raises(AttributeError):
        result.target = 0.0
