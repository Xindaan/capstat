"""Robust estimators: hand-computed values plus a scipy cross-check.

NIST does not certify robust statistics, so validation rests on two
independent legs:

1. A small sample whose expected values are worked out by hand below, so a
   reader can audit them without running anything.
2. Agreement with scipy -- an independent, widely-scrutinised implementation --
   on the same real-world datasets used for the NIST tests.
"""

from __future__ import annotations

import numpy as np
import pytest
from capstat_core import (
    MAD_NORMAL_CONSISTENCY,
    iqr,
    mad,
    median,
    trimmed_mean,
    winsorized_mean,
)
from conftest import load_strd_dataset
from scipy import stats

# ---------------------------------------------------------------------------
# Hand-computed reference sample.
#
# SAMPLE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]   (n = 10, one gross outlier)
#
#   mean            = 145 / 10                       = 14.5   <- wrecked
#   median          = (5 + 6) / 2                    = 5.5
#   |y - median|    = 4.5 3.5 2.5 1.5 0.5 0.5 1.5 2.5 3.5 94.5
#     sorted        = 0.5 0.5 1.5 1.5 2.5 2.5 3.5 3.5 4.5 94.5
#   MAD (raw)       = (2.5 + 2.5) / 2                = 2.5
#   MAD (normal)    = 2.5 * 1.482602218505602        = 3.706505546264005
#   Q1 (type 7)     = 3 + 0.25 * (4 - 3)             = 3.25
#   Q3 (type 7)     = 7 + 0.75 * (8 - 7)             = 7.75
#   IQR             = 7.75 - 3.25                    = 4.5
#   trimmed  (0.1)  = mean(2..9)   = 44 / 8          = 5.5
#   winsorized(0.1) = mean(2,2,3,4,5,6,7,8,9,9) = 55 / 10 = 5.5
# ---------------------------------------------------------------------------
SAMPLE = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 100.0]

STRD_DATASETS = ["Lottery", "Lew", "Mavro", "Michelso", "PiDigits"]


def test_mad_normal_consistency_constant() -> None:
    """The constant must be 1 / Phi^-1(0.75), not a copied-down decimal."""
    assert (
        pytest.approx(1.0 / stats.norm.ppf(0.75), rel=1e-15) == MAD_NORMAL_CONSISTENCY
    )


def test_hand_computed_median() -> None:
    assert median(SAMPLE) == 5.5


def test_hand_computed_mad() -> None:
    assert mad(SAMPLE, normal_consistent=False) == 2.5
    assert mad(SAMPLE) == pytest.approx(3.706505546264005, rel=1e-15)


def test_hand_computed_iqr() -> None:
    assert iqr(SAMPLE) == pytest.approx(4.5, rel=1e-15)


def test_hand_computed_trimmed_mean() -> None:
    assert trimmed_mean(SAMPLE, 0.1) == pytest.approx(5.5, rel=1e-15)


def test_hand_computed_winsorized_mean() -> None:
    assert winsorized_mean(SAMPLE, 0.1) == pytest.approx(5.5, rel=1e-15)


def test_robust_estimators_resist_the_outlier() -> None:
    """The point of the exercise: the outlier moves the mean, not the median."""
    assert float(np.mean(SAMPLE)) == 14.5
    for estimator in (median, trimmed_mean, winsorized_mean):
        assert estimator(SAMPLE) == pytest.approx(5.5)


@pytest.mark.parametrize("name", STRD_DATASETS)
def test_mad_matches_scipy(name: str) -> None:
    data = load_strd_dataset(f"data/nist_strd/{name}.dat")
    assert mad(data, normal_consistent=False) == pytest.approx(
        stats.median_abs_deviation(data), rel=1e-14
    )
    assert mad(data) == pytest.approx(
        stats.median_abs_deviation(data, scale="normal"), rel=1e-14
    )


@pytest.mark.parametrize("name", STRD_DATASETS)
def test_iqr_matches_scipy(name: str) -> None:
    data = load_strd_dataset(f"data/nist_strd/{name}.dat")
    assert iqr(data) == pytest.approx(stats.iqr(data), rel=1e-14)


@pytest.mark.parametrize("name", STRD_DATASETS)
@pytest.mark.parametrize("proportion", [0.0, 0.05, 0.1, 0.25])
def test_trimmed_mean_matches_scipy(name: str, proportion: float) -> None:
    data = load_strd_dataset(f"data/nist_strd/{name}.dat")
    assert trimmed_mean(data, proportion) == pytest.approx(
        stats.trim_mean(data, proportion), rel=1e-14
    )


def test_zero_proportion_reproduces_the_mean() -> None:
    data = load_strd_dataset("data/nist_strd/Lew.dat")
    expected = float(np.mean(data))
    assert trimmed_mean(data, 0.0) == pytest.approx(expected, rel=1e-14)
    assert winsorized_mean(data, 0.0) == pytest.approx(expected, rel=1e-14)


def test_winsorized_mean_lies_between_trimmed_and_raw_mean() -> None:
    """Winsorizing pulls extremes in; trimming drops them. On a right-skewed
    sample the winsorized mean must sit between the trimmed and the raw mean."""
    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 1000.0])
    assert trimmed_mean(data, 0.1) <= winsorized_mean(data, 0.1) <= float(data.mean())


def test_mad_is_zero_when_the_majority_is_constant() -> None:
    """Documented property of the estimator, not a bug."""
    assert mad([5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 1.0, 99.0]) == 0.0


@pytest.mark.parametrize("proportion", [-0.01, 0.5, 1.0])
def test_invalid_proportion_is_rejected(proportion: float) -> None:
    with pytest.raises(ValueError, match=r"proportion must be in \[0.0, 0.5\)"):
        trimmed_mean(SAMPLE, proportion)
    with pytest.raises(ValueError, match=r"proportion must be in \[0.0, 0.5\)"):
        winsorized_mean(SAMPLE, proportion)


def test_trimming_always_leaves_at_least_one_observation() -> None:
    """`proportion < 0.5` guarantees a non-empty trimmed sample for any n."""
    for n in range(1, 12):
        data = np.arange(float(n))
        assert trimmed_mean(data, 0.49) == pytest.approx(
            stats.trim_mean(data, 0.49), rel=1e-14
        )


def test_winsorized_mean_does_not_mutate_its_input() -> None:
    data = np.array(SAMPLE)
    before = data.copy()
    winsorized_mean(data, 0.1)
    np.testing.assert_array_equal(data, before)
