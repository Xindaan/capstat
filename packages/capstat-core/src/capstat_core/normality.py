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
import warnings
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy import optimize, stats

from capstat_core._validation import as_sample
from capstat_core.caveats import Caveat
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


def _require_spread(arr: npt.NDArray[np.float64]) -> None:
    """Refuse a sample whose readings are all the same value.

    Decided on the range, not on the standard deviation: ``max == min`` is exact
    in floating point, while a standard deviation of identical readings is only
    zero when their mean happens to be representable. Twenty readings of 3.3
    have a mean one ulp off 3.3 and a standard deviation of about 5e-16, which
    an ``sd == 0`` test lets through -- and the tests then run on rounding noise
    (Shapiro-Wilk returns NaN with a RuntimeWarning, Anderson-Darling a
    confident p-value). See T-0096 / API-27 for the same defect elsewhere.
    """
    if np.ptp(arr) == 0.0:
        raise ValueError(
            "sample has zero variance; normality is undefined for a constant sample"
        )


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

    _require_spread(arr)
    spread = std_dev(arr)

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
    _require_spread(arr)

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

    One consequence of that rule is worth stating plainly: requiring *both*
    tests to pass rejects a genuinely normal sample more often than ``alpha``
    suggests, because a rejection by either test is enough. Measured over 2000
    truly normal samples at ``alpha=0.05``, Anderson-Darling alone rejects 5.8 %
    and Shapiro-Wilk alone 4.8 % (both at nominal), while this combined verdict
    rejects **7.6 %**. That is the deliberate price of failing closed: on
    capability work, wrongly trusting the normal model is the more expensive
    error. If you need a test at exactly ``alpha``, call one of the two tests
    directly.

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
    warnings: tuple[Caveat, ...]
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
    warnings: list[Caveat] = []

    if abs(r1) > MATERIAL_AUTOCORRELATION:
        warnings.append(
            Caveat(
                "normality.autocorrelation",
                f"lag-1 autocorrelation is {r1:.3f}; both tests assume independent "
                f"observations, so their p-values are unreliable here. Investigate "
                f"the time order of the data before trusting this verdict.",
            )
        )

    if ad.normal != sw.normal:
        warnings.append(
            Caveat(
                "normality.tests-disagree",
                f"the two tests disagree (Anderson-Darling p={ad.p_value:.4g}, "
                f"Shapiro-Wilk p={sw.p_value:.4g} at alpha={alpha}); the evidence is "
                f"borderline. Treat the data as non-normal unless a histogram and a "
                f"probability plot say otherwise.",
            )
        )

    if n < LOW_POWER_SAMPLE_SIZE and normal:
        warnings.append(
            Caveat(
                "normality.low-power",
                f"n={n} is small, so the tests have little power. 'Not rejected' "
                f"here means 'too little evidence to reject', not 'normal'.",
            )
        )

    if n > 1000 and not normal:
        warnings.append(
            Caveat(
                "normality.large-sample",
                f"n={n} is large, so even a practically irrelevant departure from "
                f"normality becomes statistically significant. Check the size of the "
                f"deviation on a probability plot before rejecting the normal model.",
            )
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


# ---------------------------------------------------------------------------
# Readings rounded to a gauge resolution (T-0097, CAP-6)
# ---------------------------------------------------------------------------

#: Relative tolerance for "this gap is a whole number of resolution steps".
#: Decimal readings are not exact in binary (10.01 - 10.00 is 0.0099999999999979),
#: so the test cannot be exact; 1e-6 is far above that representation noise and
#: far below anything a continuous sample produces by accident.
_GRID_TOLERANCE = 1e-6

#: Monte Carlo draws for :func:`_normality_at_resolution`. With 999 draws the
#: p-value has a resolution of 0.001 and, near alpha = 0.05, a Monte Carlo
#: standard error of about 0.007 -- small against the decision it informs.
RESOLUTION_DRAWS = 999

#: The largest sample the calibration is run on. Its cost is draws x n (40 MB
#: and about 0.7 s at n = 5000, measured 2026-10-21), and a request may carry
#: millions of readings. 5000 is also where scipy stops vouching for its
#: Shapiro-Wilk p-value, and beyond it the large-sample caveat of
#: :func:`assess_normality` already says that a rejection may not matter.
RESOLUTION_MAX_SAMPLE_SIZE = 5000


def _grid_resolution(x: npt.ArrayLike) -> float | None:
    """The gauge step the readings are rounded to, or ``None``.

    Returns the smallest gap between distinct readings when (a) some readings
    are tied and (b) every gap between neighbouring distinct readings is a whole
    multiple of that smallest gap -- i.e. the sample lies on a regular grid, as
    readings from a gauge with a fixed resolution do. A continuous sample has no
    ties; a sample with an odd duplicate does not lie on a grid. Both return
    ``None`` and keep the ordinary treatment.
    """
    arr = np.asarray(x, dtype=np.float64)
    values = np.unique(arr)
    if values.size < 2 or values.size == arr.size:
        return None
    gaps = np.diff(values)
    step = float(gaps.min())
    steps = gaps / step
    if np.all(np.abs(steps - np.round(steps)) <= _GRID_TOLERANCE * steps):
        return step
    return None


def _log_cell_probability(
    lower: npt.NDArray[np.float64], upper: npt.NDArray[np.float64]
) -> npt.NDArray[np.float64]:
    """``log(Phi(upper) - Phi(lower))``, accurate in both tails.

    Cells above the median are taken from the survival function, so a cell at
    z = 9 does not become ``log(1 - 1)``.
    """
    probability = np.where(
        lower > 0.0,
        stats.norm.sf(lower) - stats.norm.sf(upper),
        stats.norm.cdf(upper) - stats.norm.cdf(lower),
    )
    logs: npt.NDArray[np.float64] = np.log(
        np.maximum(probability, np.finfo(np.float64).tiny)
    )
    return logs


def _grouped_normal_fit(
    arr: npt.NDArray[np.float64], resolution: float
) -> tuple[float, float]:
    """Maximum-likelihood mean and sigma of a normal seen through a gauge.

    A reading ``v`` from a gauge of resolution ``r`` says only that the true
    value lies in ``[v - r/2, v + r/2]``, so the likelihood is the binned one::

        l(mu, sigma) = sum_i O_i * ln(Phi((b_i - mu)/sigma) - Phi((a_i - mu)/sigma))

    over the occupied cells ``[a_i, b_i]`` with counts ``O_i`` -- the "maximum
    likelihood estimate derived from the observed bin counts, not from the
    individual observations" of NIST/SEMATECH e-Handbook section 1.3.5.15.
    Maximised numerically on standardised data, so that the optimiser's
    tolerances do not depend on the unit.
    """
    centre = float(arr.mean())
    spread = float(arr.std(ddof=1))
    values, counts = np.unique((arr - centre) / spread, return_counts=True)
    half = resolution / spread / 2.0
    lower, upper = values - half, values + half

    def negative_log_likelihood(theta: npt.NDArray[np.float64]) -> float:
        sigma = math.exp(float(theta[1]))
        mu = float(theta[0])
        log_p = _log_cell_probability((lower - mu) / sigma, (upper - mu) / sigma)
        return -float(np.sum(counts * log_p))

    result = optimize.minimize(
        negative_log_likelihood,
        x0=np.zeros(2),
        method="Nelder-Mead",
        options={"xatol": 1e-9, "fatol": 1e-12, "maxiter": 4000},
    )
    mu, log_sigma = float(result.x[0]), float(result.x[1])
    return centre + spread * mu, spread * math.exp(log_sigma)


def _anderson_darling_statistics(
    samples: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    """The (unadjusted) Anderson-Darling ``A^2`` of every row, vectorised.

    The same formula as :func:`anderson_darling`; no row may be constant.
    """
    n = samples.shape[1]
    ordered = np.sort(samples, axis=1)
    z = (ordered - ordered.mean(axis=1, keepdims=True)) / ordered.std(
        axis=1, ddof=1, keepdims=True
    )
    i = np.arange(1, n + 1)
    weighted = (2 * i - 1) * (stats.norm.logcdf(z) + stats.norm.logsf(z)[:, ::-1])
    statistics: npt.NDArray[np.float64] = -n - weighted.mean(axis=1)
    return statistics


@dataclass(frozen=True, slots=True)
class _RoundedNormality:
    """Normality of rounded readings, judged against rounded normal data."""

    resolution: float
    distinct: int
    mu: float
    sigma: float
    draws: int
    anderson_darling_p: float
    shapiro_wilk_p: float
    normal: bool


def _normality_at_resolution(
    x: npt.ArrayLike,
    resolution: float,
    *,
    alpha: float = 0.05,
    draws: int = RESOLUTION_DRAWS,
    seed: int = 0,
) -> _RoundedNormality:
    """Anderson-Darling and Shapiro-Wilk, calibrated for a gauge's rounding.

    Both tests assume continuous data, and readings rounded to a gauge step are
    not: they tie. With enough readings the tests detect the ties themselves,
    and a perfectly normal process is "rejected" for having been measured.
    Measured on N(10, 0.05) rounded to 0.2 sigma (2026-10-21, 100 runs each):
    the combined verdict of :func:`assess_normality` rejects 18 % of samples at
    n = 100 and 100 % at n = 1000, where 5-8 % would be nominal.

    The remedy is a parametric bootstrap (Monte Carlo) test of the hypothesis
    that is actually in question -- *a normal process, read by this gauge*:

    1. Estimate ``mu`` and ``sigma`` of the process from the binned likelihood
       (:func:`_grouped_normal_fit`, NIST/SEMATECH e-Handbook 1.3.5.15).
    2. Draw ``draws`` samples of the same size from ``N(mu, sigma)`` and round
       each one to the same grid.
    3. Compute both statistics on every draw. The p-value of each test is the
       share of draws at least as extreme as the observed statistic,
       ``(1 + #{T* at least as extreme as T}) / (B + 1)``.

    The statistics themselves are unchanged, so the tests keep their power
    against skewness -- a skewed process is still skewed after rounding -- and
    only their null distribution now includes the rounding. A grouped
    chi-square test, the textbook alternative, held its size as well but
    detected a gamma(4) process at n = 100 in roughly half the runs where the
    unadjusted tests did (measured 2026-10-21); that loss of power would have
    sent skewed processes down the normal path.

    Draws whose readings all round to one value have no spread to test and are
    left out, so the p-value is conditional on a sample with a spread, as the
    observed one has. The generator is seeded: the verdict is reproducible.

    References
    ----------
    Davison, A. C., & Hinkley, D. V. (1997). *Bootstrap Methods and their
        Application*. Cambridge University Press, ch. 4 (parametric bootstrap
        and Monte Carlo tests).
    NIST/SEMATECH e-Handbook of Statistical Methods, section 1.3.5.15 (the
        binned maximum-likelihood estimate).
    """
    _check_alpha(alpha)
    arr = as_sample(x, minimum=AD_MIN_SAMPLE_SIZE)
    _require_spread(arr)
    n = arr.size

    mu, sigma = _grouped_normal_fit(arr, resolution)
    observed_ad = anderson_darling(arr).statistic
    observed_sw = float(stats.shapiro(arr).statistic)

    origin = float(arr.min())
    latent = np.random.default_rng(seed).normal(mu, sigma, size=(draws, n))
    rounded = origin + resolution * np.round((latent - origin) / resolution)
    usable = rounded[np.ptp(rounded, axis=1) > 0.0]
    if usable.shape[0] == 0:
        raise ValueError(
            f"at a resolution of {resolution:.6g} the fitted process (sigma = "
            f"{sigma:.3g}) never shows two different readings, so its normality "
            f"cannot be judged"
        )

    with warnings.catch_warnings():
        # Above n = 5000 scipy warns on every call that its p-value may be
        # inaccurate. Only the statistic is used here.
        warnings.simplefilter("ignore", UserWarning)
        simulated_sw = np.array([stats.shapiro(row).statistic for row in usable])
    simulated_ad = _anderson_darling_statistics(usable)

    total = usable.shape[0] + 1
    ad_p = float((1 + np.sum(simulated_ad >= observed_ad)) / total)
    sw_p = float((1 + np.sum(simulated_sw <= observed_sw)) / total)

    return _RoundedNormality(
        resolution=resolution,
        distinct=int(np.unique(arr).size),
        mu=mu,
        sigma=sigma,
        draws=int(usable.shape[0]),
        anderson_darling_p=ad_p,
        shapiro_wilk_p=sw_p,
        normal=ad_p >= alpha and sw_p >= alpha,
    )
