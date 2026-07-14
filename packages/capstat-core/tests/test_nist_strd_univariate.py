"""Reference validation against the NIST StRD Univariate Summary Statistics.

Source, certified values, per-dataset tolerances and the rationale for the two
loosened ones: ``references/nist_strd_univariate.yaml``. The datasets
themselves are archived verbatim (headers included) under
``references/data/nist_strd/``, so each expected value can be traced to its
source without leaving the repository.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from capstat_core import describe, lag1_autocorrelation, mean, std_dev
from conftest import (
    ReferenceCase,
    assert_within_tolerance,
    load_reference_cases,
)

CASES = load_reference_cases("nist_strd_univariate.yaml")

# The statistics NIST certifies, mapped to the capstat function under test.
CERTIFIED_STATISTICS = {
    "mean": mean,
    "std_dev": std_dev,
    "lag1_autocorrelation": lag1_autocorrelation,
}


def _case_id(case: ReferenceCase) -> str:
    return case.id


@pytest.mark.parametrize("case", CASES, ids=_case_id)
@pytest.mark.parametrize("statistic", sorted(CERTIFIED_STATISTICS))
def test_matches_nist_certified_value(case: ReferenceCase, statistic: str) -> None:
    data = case.data()
    got = CERTIFIED_STATISTICS[statistic](data)
    expected = float(case.expected[statistic])
    rel, abs_ = case.tolerance_for(statistic)
    assert_within_tolerance(got, expected, rel, abs_, label=f"{case.id}/{statistic}")


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_sample_size_matches_certificate(case: ReferenceCase) -> None:
    assert case.data().size == int(case.expected["n"])


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_describe_agrees_with_certified_values(case: ReferenceCase) -> None:
    """`describe` must agree with the standalone functions it aggregates."""
    summary = describe(case.data())
    for statistic in CERTIFIED_STATISTICS:
        rel, abs_ = case.tolerance_for(statistic)
        assert_within_tolerance(
            getattr(summary, statistic),
            float(case.expected[statistic]),
            rel,
            abs_,
            label=f"{case.id}/describe.{statistic}",
        )
    assert summary.n == int(case.expected["n"])


def test_exact_cases_match_bit_for_bit() -> None:
    """NumAcc1's certified values are exact; a zero tolerance must hold."""
    case = next(c for c in CASES if c.id == "nist-strd-numacc1")
    rel, abs_ = case.tolerance_for("std_dev")
    assert (rel, abs_) == (0.0, 0.0), "NumAcc1 must be pinned to an exact match"

    data = case.data()
    assert mean(data) == 10000002.0
    assert std_dev(data) == 1.0
    assert lag1_autocorrelation(data) == -0.5


# ---------------------------------------------------------------------------
# Regression guard for the *class* of bug these datasets exist to expose:
# catastrophic cancellation in centered-moment computations.
# ---------------------------------------------------------------------------


def _naive_variance(x: np.ndarray) -> float:
    """The textbook one-pass formula capstat deliberately does NOT use."""
    n = x.size
    return float((np.sum(x**2) - n * np.mean(x) ** 2) / (n - 1))


def test_naive_one_pass_variance_breaks_down_on_numacc4() -> None:
    """Pins the algorithm choice, not just the result.

    On NumAcc4 the one-pass formula does not merely lose precision: it returns
    a *negative* variance (about -0.032), which is mathematically impossible.
    If anyone ever "optimizes" `variance` back into a single pass, the
    certified-value tests would fail -- but this test says *why*.
    """
    case = next(c for c in CASES if c.id == "nist-strd-numacc4")
    data = case.data()
    certified_variance = 0.01  # (0.1)^2

    naive = _naive_variance(data)
    assert naive < 0.0, (
        "NumAcc4 no longer drives the naive formula negative; the regression "
        "guard has lost its teeth"
    )

    capstat_error = abs(math.sqrt(certified_variance) - std_dev(data)) / 0.1
    assert capstat_error < 1e-8


@pytest.mark.parametrize(
    "statistic",
    ["variance", "std_dev", "skewness", "kurtosis", "lag1_autocorrelation"],
)
def test_centered_moments_are_shift_stable(statistic: str) -> None:
    """Isomorphy check across the whole family of centered moments.

    Every statistic below is a function of deviations from the mean, so every
    one of them is exposed to the same cancellation failure mode. Each must be
    (near-)invariant when a large constant is added to the data -- the naive
    formulas are not.
    """
    import capstat_core

    rng = np.random.default_rng(20260714)
    base = rng.normal(loc=0.0, scale=1.0, size=500)
    shifted = base + 1e8

    function = getattr(capstat_core, statistic)
    got, expected = function(shifted), function(base)
    assert got == pytest.approx(expected, rel=1e-6), (
        f"{statistic} is not shift-stable: {got!r} vs {expected!r}. "
        f"This is the NumAcc4 failure mode in a sibling statistic."
    )
