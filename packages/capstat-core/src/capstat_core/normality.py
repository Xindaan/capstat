"""Normality tests, and an honest verdict on what they mean.

Capability indices such as Cp and Cpk assume a normal process distribution. If
that assumption is wrong, the indices are wrong -- often badly, because they
extrapolate into the tails where the misfit is worst. So the point of this
module is not to produce a p-value; it is to decide, defensibly, whether the
normal path may be taken at all (see :func:`assess_normality`).

Three traps this module refuses to walk into silently:

* **Both tests assume independent observations.** Process data frequently are
  not independent -- the NIST ``Mavro`` dataset has a lag-1 autocorrelation of
  0.94. Under autocorrelation the p-values of both tests are meaningless, so
  :func:`assess_normality` measures it and says so.
* **With a large n, any real process fails.** No physical process is exactly
  normal, and the tests' power grows with n, so at n = 5000 a practically
  irrelevant deviation still yields p < 0.001. Statistical significance is not
  practical significance; the report says which one it has found.
* **With a small n, nothing fails.** Below roughly 20 observations the tests
  have so little power that "not rejected" carries almost no information. It
  must not be read as "normal".

References
----------
Anderson, T. W., & Darling, D. A. (1954). A test of goodness of fit. *JASA*,
    49(268), 765-769.
Stephens, M. A. (1974). EDF statistics for goodness of fit and some
    comparisons. *JASA*, 69(347), 730-737.
D'Agostino, R. B., & Stephens, M. A. (1986). *Goodness-of-Fit Techniques*.
    Marcel Dekker. (Anderson-Darling p-value approximation.)
Royston, P. (1995). Remark AS R94: A remark on Algorithm AS 181: The W test for
    normality. *Applied Statistics*, 44(4), 547-551. (Shapiro-Wilk.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy import stats

from capstat_core._validation import as_sample
from capstat_core.descriptive import lag1_autocorrelation, std_dev

__all__ = [
    "AD_MIN_SAMPLE_SIZE",
    "LOW_POWER_SAMPLE_SIZE",
    "MATERIAL_AUTOCORRELATION",
    "NormalityAssessment",
    "NormalityTestResult",
    "anderson_darling",
    "anderson_darling_pvalue",
    "assess_normality",
    "shapiro_wilk",
]

#: Below this n, the Anderson-Darling p-value approximation is not defined.
#: Matches the guard in R's ``nortest::ad.test``.
AD_MIN_SAMPLE_SIZE = 8

#: Below this n, a "normal" verdict means "too little evidence to reject",
#: not "normal". Reported as a warning rather than enforced.
LOW_POWER_SAMPLE_SIZE = 20

#: |lag-1 autocorrelation| above which the independence assumption underlying
#: both tests is considered violated, making their p-values untrustworthy.
MATERIAL_AUTOCORRELATION = 0.2


def anderson_darling_pvalue(adjusted_statistic: float) -> float:
    """p-value for the adjusted Anderson-Darling statistic ``A*^2``.

    Implements the four-branch approximation of D'Agostino & Stephens (1986),
    transcribed verbatim from the canonical R implementation
    (CRAN ``nortest`` 1.0-4, ``ad.test``)::

        A*^2 <  0.20 : p = 1 - exp(-13.436 + 101.14 A - 223.73 A^2)
        A*^2 <  0.34 : p = 1 - exp( -8.318 +  42.796 A -  59.938 A^2)
        A*^2 <  0.60 : p =     exp( 0.9177 -   4.279 A -    1.38 A^2)
        A*^2 < 10    : p =     exp( 1.2937 -   5.709 A +  0.0186 A^2)
        otherwise    : p = 3.7e-24   (the published floor)

    Parameters
    ----------
    adjusted_statistic:
        ``A*^2 = A^2 * (1 + 0.75/n + 2.25/n^2)``, i.e. the statistic *after*
        the small-sample adjustment for having estimated the mean and variance
        from the data. Passing a raw ``A^2`` here silently overstates the
        p-value.

    Notes
    -----
    The branches are fitted separately and do not join exactly; the jumps at
    the boundaries reach 3.3e-03. That is a property of the published
    approximation, not of this transcription.
    """
    a = adjusted_statistic
    if a < 0.2:
        p = 1.0 - math.exp(-13.436 + 101.14 * a - 223.73 * a**2)
    elif a < 0.34:
        p = 1.0 - math.exp(-8.318 + 42.796 * a - 59.938 * a**2)
    elif a < 0.6:
        p = math.exp(0.9177 - 4.279 * a - 1.38 * a**2)
    elif a < 10.0:
        p = math.exp(1.2937 - 5.709 * a + 0.0186 * a**2)
    else:
        p = 3.7e-24
    return min(max(p, 0.0), 1.0)


@dataclass(frozen=True, slots=True)
class NormalityTestResult:
    """The outcome of a single normality test.

    ``normal`` is ``p_value >= alpha``, i.e. "the test failed to reject
    normality". That is not the same as "the data are normal" -- see
    :class:`NormalityAssessment`, which is the interface you should prefer.
    """

    test: str
    n: int
    statistic: float
    p_value: float
    alpha: float
    normal: bool


def _check_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0.0, 1.0), got {alpha}")


def anderson_darling(x: npt.ArrayLike, *, alpha: float = 0.05) -> NormalityTestResult:
    """Anderson-Darling test for normality, with a p-value.

    The statistic weights the tails of the distribution more heavily than the
    Kolmogorov-Smirnov statistic does, which is why it is the preferred EDF
    test in capability work: the tails are exactly where Cpk lives.

    ``A^2 = -n - (1/n) * sum_i (2i - 1) * [ln F(z_i) + ln(1 - F(z_{n+1-i}))]``

    with ``z`` the sorted sample standardised by its own mean and standard
    deviation (denominator n-1). Because those parameters are estimated rather
    than known, the statistic is adjusted before the p-value is taken:

    ``A*^2 = A^2 * (1 + 0.75/n + 2.25/n^2)``   (Stephens 1974)

    ``statistic`` on the returned result is the *unadjusted* ``A^2``, matching
    ``scipy.stats.anderson`` and the value quoted in the literature; the
    adjustment is applied internally when computing ``p_value``.

    Raises
    ------
    ValueError
        If ``n < 8`` (the p-value approximation is undefined below that), or if
        the sample has zero variance.
    """
    _check_alpha(alpha)
    arr = as_sample(x, minimum=AD_MIN_SAMPLE_SIZE)
    n = arr.size

    spread = std_dev(arr)
    if spread == 0.0:
        raise ValueError(
            "sample has zero variance; normality is undefined for a constant sample"
        )

    ordered = np.sort(arr)
    z = (ordered - ordered.mean()) / spread

    # Work in log space: for |z| beyond ~8 the survival function underflows to
    # 0.0 in linear space, and log(0) would poison the sum. logcdf/logsf stay
    # accurate far into the tails -- the same approach scipy and nortest take.
    log_cdf = stats.norm.logcdf(z)
    log_sf = stats.norm.logsf(z)

    i = np.arange(1, n + 1)
    weighted = (2 * i - 1) * (log_cdf + log_sf[::-1])
    a_squared = -n - float(weighted.mean())

    adjusted = a_squared * (1.0 + 0.75 / n + 2.25 / n**2)
    p_value = anderson_darling_pvalue(adjusted)

    return NormalityTestResult(
        test="anderson-darling",
        n=n,
        statistic=a_squared,
        p_value=p_value,
        alpha=alpha,
        normal=p_value >= alpha,
    )


def shapiro_wilk(x: npt.ArrayLike, *, alpha: float = 0.05) -> NormalityTestResult:
    """Shapiro-Wilk test for normality.

    Delegates to ``scipy.stats.shapiro``, which implements Royston's AS R94 --
    the same algorithm behind R's ``shapiro.test``. capstat does not
    reimplement it: AS R94 is a carefully tuned polynomial approximation, and a
    hand-rolled version would be strictly worse. What capstat adds is the
    surrounding judgement (see :func:`assess_normality`).

    ``W`` is the ratio of the squared best linear unbiased estimate of the
    standard deviation to the usual sum of squares; it approaches 1 for normal
    data and falls away as the sample departs from normality.

    Raises
    ------
    ValueError
        If ``n < 3``, or if the sample has zero variance.
    """
    _check_alpha(alpha)
    arr = as_sample(x, minimum=3)

    if std_dev(arr) == 0.0:
        raise ValueError(
            "sample has zero variance; normality is undefined for a constant sample"
        )

    result = stats.shapiro(arr)
    p_value = float(result.pvalue)

    return NormalityTestResult(
        test="shapiro-wilk",
        n=arr.size,
        statistic=float(result.statistic),
        p_value=p_value,
        alpha=alpha,
        normal=p_value >= alpha,
    )


@dataclass(frozen=True, slots=True)
class NormalityAssessment:
    """A verdict on normality, with the caveats attached rather than omitted.

    ``normal`` is the recommendation to act on: it is ``True`` only when *both*
    tests fail to reject normality. Disagreement between the two is itself
    informative and is surfaced in ``warnings`` rather than resolved silently.

    ``warnings`` holds every reason the verdict might be misleading -- material
    autocorrelation, a sample too small to have power, a sample so large that
    trivial deviations become significant. An empty tuple means the verdict can
    be taken at face value.
    """

    n: int
    alpha: float
    anderson_darling: NormalityTestResult
    shapiro_wilk: NormalityTestResult
    lag1_autocorrelation: float
    normal: bool
    warnings: tuple[str, ...]
    recommendation: str


def assess_normality(x: npt.ArrayLike, *, alpha: float = 0.05) -> NormalityAssessment:
    """Run both normality tests and return an actionable, caveated verdict.

    This is the entry point capability code should use. It exists because the
    honest answer to "is this process normal?" is rarely just a p-value.

    Raises
    ------
    ValueError
        If ``n < 8``. Below that the Anderson-Darling p-value is undefined; call
        :func:`shapiro_wilk` directly if you must test such a sample, but treat
        the result with great suspicion.
    """
    _check_alpha(alpha)
    arr = as_sample(x, minimum=AD_MIN_SAMPLE_SIZE)
    n = arr.size

    ad = anderson_darling(arr, alpha=alpha)
    sw = shapiro_wilk(arr, alpha=alpha)
    r1 = lag1_autocorrelation(arr)

    normal = ad.normal and sw.normal
    warnings: list[str] = []

    if abs(r1) > MATERIAL_AUTOCORRELATION:
        warnings.append(
            f"lag-1 autocorrelation is {r1:.3f}; both tests assume independent "
            f"observations, so their p-values are unreliable here. Investigate "
            f"the time order of the data before trusting this verdict."
        )

    if ad.normal != sw.normal:
        warnings.append(
            f"the two tests disagree (Anderson-Darling p={ad.p_value:.4g}, "
            f"Shapiro-Wilk p={sw.p_value:.4g} at alpha={alpha}); the evidence is "
            f"borderline. Treat the data as non-normal unless a histogram and a "
            f"probability plot say otherwise."
        )

    if n < LOW_POWER_SAMPLE_SIZE and normal:
        warnings.append(
            f"n={n} is small, so the tests have little power. 'Not rejected' "
            f"here means 'too little evidence to reject', not 'normal'."
        )

    if n > 1000 and not normal:
        warnings.append(
            f"n={n} is large, so even a practically irrelevant departure from "
            f"normality becomes statistically significant. Check the size of the "
            f"deviation on a probability plot before rejecting the normal model."
        )

    if normal:
        recommendation = (
            "Normal model not rejected; the standard (normal) capability indices "
            "are defensible."
        )
    else:
        recommendation = (
            "Normal model rejected; do not use the standard capability indices. "
            "Use the non-normal path: a Box-Cox transformation, or the ISO 22514 "
            "percentile method."
        )

    return NormalityAssessment(
        n=n,
        alpha=alpha,
        anderson_darling=ad,
        shapiro_wilk=sw,
        lag1_autocorrelation=r1,
        normal=normal,
        warnings=tuple(warnings),
        recommendation=recommendation,
    )
