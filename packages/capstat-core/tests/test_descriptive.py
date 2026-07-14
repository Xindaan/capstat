"""Descriptive statistics: scipy cross-checks, contracts, and edge cases.

The certified-value tests live in ``test_nist_strd_univariate.py``. This module
covers the statistics NIST does not certify (shape, quartiles) by cross-checking
against scipy, and pins the input-validation contract.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from capstat_core import (
    describe,
    kurtosis,
    lag1_autocorrelation,
    mean,
    skewness,
    std_dev,
    variance,
)
from conftest import load_strd_dataset
from scipy import stats

STRD_DATASETS = ["Lottery", "Lew", "Mavro", "Michelso", "PiDigits"]

CONSTANT = [7.0, 7.0, 7.0, 7.0, 7.0]


@pytest.fixture
def sample() -> np.ndarray:
    return load_strd_dataset("data/nist_strd/Lew.dat")


# ---------------------------------------------------------------------------
# Cross-checks against scipy for the non-certified statistics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", STRD_DATASETS)
@pytest.mark.parametrize("bias", [True, False])
def test_skewness_matches_scipy(name: str, bias: bool) -> None:
    data = load_strd_dataset(f"data/nist_strd/{name}.dat")
    assert skewness(data, bias=bias) == pytest.approx(
        stats.skew(data, bias=bias), rel=1e-12
    )


@pytest.mark.parametrize("name", STRD_DATASETS)
@pytest.mark.parametrize("bias", [True, False])
@pytest.mark.parametrize("fisher", [True, False])
def test_kurtosis_matches_scipy(name: str, bias: bool, fisher: bool) -> None:
    data = load_strd_dataset(f"data/nist_strd/{name}.dat")
    assert kurtosis(data, bias=bias, fisher=fisher) == pytest.approx(
        stats.kurtosis(data, bias=bias, fisher=fisher), rel=1e-12
    )


@pytest.mark.parametrize("name", STRD_DATASETS)
def test_quartiles_match_numpy(name: str) -> None:
    data = load_strd_dataset(f"data/nist_strd/{name}.dat")
    summary = describe(data)
    q1, med, q3 = np.percentile(data, [25.0, 50.0, 75.0])
    assert summary.q1 == pytest.approx(float(q1), rel=1e-15)
    assert summary.median == pytest.approx(float(med), rel=1e-15)
    assert summary.q3 == pytest.approx(float(q3), rel=1e-15)
    assert summary.iqr == pytest.approx(float(q3 - q1), rel=1e-15)


def test_pearson_kurtosis_is_excess_plus_three(sample: np.ndarray) -> None:
    excess = kurtosis(sample, fisher=True)
    pearson = kurtosis(sample, fisher=False)
    assert pearson == pytest.approx(excess + 3.0, rel=1e-15)


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------


def test_variance_ddof(sample: np.ndarray) -> None:
    n = sample.size
    population = variance(sample, ddof=0)
    unbiased = variance(sample, ddof=1)
    assert unbiased == pytest.approx(population * n / (n - 1), rel=1e-14)
    assert variance(sample) == unbiased, "ddof=1 must be the default"


def test_std_dev_is_sqrt_of_variance(sample: np.ndarray) -> None:
    assert std_dev(sample) == pytest.approx(math.sqrt(variance(sample)), rel=1e-15)


def test_describe_fields_agree_with_standalone_functions(sample: np.ndarray) -> None:
    summary = describe(sample)
    assert summary.n == sample.size
    assert summary.mean == pytest.approx(mean(sample), rel=1e-15)
    assert summary.variance == pytest.approx(variance(sample), rel=1e-15)
    assert summary.std_dev == pytest.approx(std_dev(sample), rel=1e-15)
    assert summary.skewness == pytest.approx(skewness(sample), rel=1e-15)
    assert summary.kurtosis == pytest.approx(kurtosis(sample), rel=1e-15)
    assert summary.lag1_autocorrelation == pytest.approx(
        lag1_autocorrelation(sample), rel=1e-15
    )
    assert summary.minimum == float(sample.min())
    assert summary.maximum == float(sample.max())
    assert summary.range == pytest.approx(float(sample.max() - sample.min()))


def test_summary_is_immutable(sample: np.ndarray) -> None:
    summary = describe(sample)
    with pytest.raises(AttributeError):
        summary.mean = 0.0  # type: ignore[misc]


def test_mean_accepts_plain_python_sequences() -> None:
    assert mean([1, 2, 3, 4]) == 2.5
    assert mean((1.0, 2.0)) == 1.5


# ---------------------------------------------------------------------------
# Degenerate input: zero variance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("function", [skewness, kurtosis, lag1_autocorrelation])
def test_zero_variance_returns_nan(function: object) -> None:
    """Undefined (0/0), so NaN -- matching scipy, rather than raising or lying."""
    assert math.isnan(function(CONSTANT))  # type: ignore[operator]


def test_zero_variance_still_has_a_defined_mean_and_spread() -> None:
    summary = describe(CONSTANT)
    assert summary.mean == 7.0
    assert summary.variance == 0.0
    assert summary.std_dev == 0.0
    assert summary.range == 0.0
    assert math.isnan(summary.skewness)
    assert math.isnan(summary.kurtosis)
    assert math.isnan(summary.lag1_autocorrelation)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_rejects_two_dimensional_input() -> None:
    with pytest.raises(ValueError, match="one-dimensional"):
        mean([[1.0, 2.0], [3.0, 4.0]])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_values(bad: float) -> None:
    with pytest.raises(ValueError, match="NaN or infinite"):
        mean([1.0, 2.0, bad])


def test_rejects_empty_sample() -> None:
    with pytest.raises(ValueError, match="at least 1 observation"):
        mean([])


def test_variance_needs_two_observations() -> None:
    with pytest.raises(ValueError, match="at least 2 observation"):
        variance([1.0])
    assert variance([1.0], ddof=0) == 0.0


def test_lag1_autocorrelation_needs_two_observations() -> None:
    with pytest.raises(ValueError, match="at least 2 observation"):
        lag1_autocorrelation([1.0])


def test_bias_corrected_shape_statistics_need_more_observations() -> None:
    with pytest.raises(ValueError, match="at least 3 observation"):
        skewness([1.0, 2.0], bias=False)
    with pytest.raises(ValueError, match="at least 4 observation"):
        kurtosis([1.0, 2.0, 3.0], bias=False)


def test_describe_needs_two_observations() -> None:
    with pytest.raises(ValueError, match="at least 2 observation"):
        describe([1.0])
