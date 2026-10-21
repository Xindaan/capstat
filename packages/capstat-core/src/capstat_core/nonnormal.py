"""Capability for processes that are not normally distributed.

When the normal model is rejected, the standard indices are not merely
imprecise -- they are wrong, and usually optimistic, because Cpk extrapolates
into a tail the normal model gets badly wrong. Many real processes are
legitimately skewed (flatness, roundness, concentricity, contamination counts:
anything bounded at zero), so "the data are not normal" is a routine finding,
not an exotic one. It needs a route forward, not a warning nobody acts on.

Two routes, and this module implements both plus the decision between them:

* **Box-Cox** (:func:`box_cox_capability`) transforms the data to normality and
  then applies the ordinary machinery. It is preferable when it works, because
  everything downstream -- Cp, Cpk, the within/overall split -- keeps working.
* **The ISO 22514 percentile method** (:func:`percentile_capability`) fits a
  distribution and replaces the 6-sigma span with the span between the 0.135 %
  and 99.865 % percentiles. It needs no transformation, but it yields only
  performance (long-term) indices: it has no within/between split, so it cannot
  produce a Cp or Cpk at all.

:func:`analyze_capability` runs the decision path and reports which branch it
took and why -- the point being that the choice is recorded, not silent.

The mistake this module exists to prevent
-----------------------------------------
Transforming the data but not the specification limits. The limits live in the
original units; on the transformed scale they are meaningless, and the indices
computed against them are confident nonsense. :func:`box_cox_capability` always
transforms the limits with the same lambda. (Box-Cox is strictly increasing for
every lambda -- its derivative is ``x**(lambda-1) > 0`` for ``x > 0`` -- so the
limits keep their order and LSL stays the lower one.)

The two methods are NOT interchangeable
---------------------------------------
Run both on the same data and you will usually get different numbers. This is
not a defect in either; they compute different quantities::

    Box-Cox     Ppu = (ln(USL) - mu) / (3 * sigma)          linear, log scale
    percentile  Ppu = (USL - X50) / (X99.865 - X50)
                    = (e**U - 1) / (e**(3*sigma) - 1)       nonlinear, original

with ``U = ln(USL) - mu``. Put ``U = 3*sigma`` -- the limit exactly on the
99.865 % percentile -- and both equal 1: at the "just capable" point the two
definitions coincide. Away from it they diverge, and not subtly. With the limit
far out in the tail of a lognormal process we measure Box-Cox ``Ppu = 1.61``
against percentile ``Ppu = 2.44`` on identical data.

So: pick a method, record which one (:func:`analyze_capability` does), and do
not compare an index produced by one against a threshold calibrated on the
other.

References
----------
Box, G. E. P., & Cox, D. R. (1964). An analysis of transformations. *JRSS B*,
    26(2), 211-252.
ISO 22514-4. *Statistical methods in process management -- Capability and
    performance -- Part 4: Process capability estimates and performance
    measures.*
NIST/SEMATECH e-Handbook of Statistical Methods, section 6.5.2.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt
from scipy import stats

from capstat_core._validation import as_sample
from capstat_core.capability import CapabilityReport, capability
from capstat_core.caveats import Caveat
from capstat_core.normality import (
    AD_MIN_SAMPLE_SIZE,
    RESOLUTION_MAX_SAMPLE_SIZE,
    NormalityAssessment,
    _grid_resolution,
    _normality_at_resolution,
    _RoundedNormality,
    assess_normality,
)

__all__ = [
    "DEFAULT_CANDIDATES",
    "LOWER_PERCENTILE",
    "UPPER_PERCENTILE",
    "BoxCoxCapability",
    "CapabilityAnalysis",
    "DistributionFit",
    "PercentileCapability",
    "analyze_capability",
    "box_cox_capability",
    "fit_distribution",
    "percentile_capability",
]

#: ISO 22514's tail percentiles. They are the +/- 3 sigma points of a normal
#: distribution (``norm.cdf(-3) = 0.001349898``), which is precisely why the
#: method reduces to the classic indices when the data happen to be normal.
LOWER_PERCENTILE = 0.00135
UPPER_PERCENTILE = 0.99865

#: Distributions tried by :func:`fit_distribution`. All are supported on a
#: half-line, which is where genuinely skewed process data live.
DEFAULT_CANDIDATES = ("lognorm", "weibull_min", "gamma", "expon")


@dataclass(frozen=True, slots=True)
class DistributionFit:
    """A fitted distribution and how well it fits.

    ``fit_score`` is the Anderson-Darling statistic of the data against the
    fitted distribution itself, taken as fully specified (see
    :func:`_fit_score`): if ``X ~ F`` then ``F(X)`` is uniform, and the
    statistic measures how far the transformed sample is from that. Lower is
    better. Because ``F`` is used as it stands, a fit in the wrong place or of
    the wrong width scores badly -- which is the point of the score.

    It is deliberately *not* accompanied by a p-value. The parameters were
    estimated from the same data, which makes any such p-value anticonservative
    by an unknown amount. Use ``fit_score`` to rank candidates against each
    other -- never as evidence that the winner is a good fit in absolute terms.
    Look at a probability plot for that.
    """

    name: str
    params: tuple[float, ...]
    fit_score: float

    def frozen(self) -> stats.rv_continuous:
        """The scipy distribution with these parameters bound."""
        return getattr(stats, self.name)(*self.params)


def _fit_score(data: npt.NDArray[np.float64], frozen: object) -> float:
    """Anderson-Darling statistic of ``data`` against a fully specified ``F``.

    ``A^2 = -n - (1/n) * sum_i (2i - 1) * [ln F(x_(i)) + ln(1 - F(x_(n+1-i)))]``

    with ``x_(i)`` the ordered data and ``F`` the fitted CDF, used as it stands
    (NIST/SEMATECH e-Handbook 1.3.5.14: "F is the cumulative distribution
    function of the specified distribution"). ``F(x)`` is clipped to
    ``[1e-12, 1 - 1e-12]`` so that a reading the fit calls impossible costs a
    large, finite penalty rather than an infinite one.

    Not the Anderson-Darling *normality* test (CAP-1). That one standardises its
    input by the input's own mean and standard deviation, so feeding it the
    normal scores ``Phi^-1(F(x))`` -- as this score once did -- hid every error
    of location and scale in the fit: a fitted distribution whose median sat at
    half the data's median scored as well as the right one, because only the
    *shape* of the transformed sample was judged. That is precisely the error a
    stalled optimiser makes, so the score could not see the fits that most
    needed rejecting.
    """
    u = np.sort(np.clip(frozen.cdf(data), 1e-12, 1 - 1e-12))  # type: ignore[attr-defined]
    if not np.all(np.isfinite(u)):
        return math.inf
    n = int(u.size)
    i = np.arange(1, n + 1)
    weighted = (2 * i - 1) * (np.log(u) + np.log1p(-u[::-1]))
    return -n - float(weighted.mean())


def _fit_family(family: object, arr: npt.NDArray[np.float64]) -> tuple[float, ...]:
    """Maximum-likelihood parameters of ``family``, independent of the unit.

    Every scipy continuous distribution is a location-scale family: its last two
    parameters are ``loc`` and ``scale``. For such a family maximum likelihood
    is equivariant -- with ``y = a + b*x`` (``b > 0``) the likelihood of the
    ``y`` sample is ``b**-n`` times that of the ``x`` sample at ``loc_x = (loc_y
    - a)/b``, ``scale_x = scale_y/b``, so the maximiser moves with the data. The
    fit is therefore made on the standardised sample ``(x - mean)/sd`` and
    ``loc``/``scale`` are mapped back; the shape parameters are unchanged.

    In exact arithmetic this changes nothing. In floating point it is the
    difference between a result and an accident (CAP-1): scipy's optimiser
    works with absolute tolerances, and on raw readings near 1e-5 -- a length in
    metres, a capacitance in farads -- it stopped early, so the same data gave
    Ppk 1.09 in one unit and -121 in another.
    """
    centre = float(arr.mean())
    spread = float(arr.std(ddof=1))
    # The standardised sample straddles zero, so scipy's search over loc takes
    # log() of negative numbers on the way, for every half-line family. That is
    # the search working, not failing; the NaNs it meets are discarded there.
    # Silenced for this one call, not globally.
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        fitted = family.fit((arr - centre) / spread)  # type: ignore[attr-defined]
    *shapes, loc, scale = (float(p) for p in fitted)
    return (*shapes, centre + spread * loc, spread * scale)


#: The fewest distinct readings from which a distribution is estimated at all.
MIN_DISTINCT_VALUES = 3


def _require_distinct_values(arr: npt.NDArray[np.float64]) -> None:
    """Refuse a sample with fewer than :data:`MIN_DISTINCT_VALUES` values.

    Two distinct values are what a gauge too coarse for the process reports:
    nearly every reading on one step, a few on the next. Read as interval data
    -- what they are -- two cells fix a single boundary and cannot separate the
    process's location from its spread; read as continuous data, the likelihood
    of a fitted distribution grows without bound as it piles its mass onto the
    tied value. Either way the fitted tails are an artefact of the ties: on
    29 readings of 5.0 and one of 5.1 the percentile method reported Pp 2e7
    (CAP-6), the fitted 99.865 % point lying below the largest reading. There is
    no defensible index to give, so none is given.
    """
    values = np.unique(arr)
    if values.size >= MIN_DISTINCT_VALUES:
        return
    if values.size == 1:
        raise ValueError(
            f"sample has zero variance: all {arr.size} readings are "
            f"{values[0]:.6g}, and capability is undefined for a constant sample"
        )
    raise ValueError(
        f"the {arr.size} readings take only two distinct values ({values[0]:.6g} "
        f"and {values[1]:.6g}). Neither the shape nor the spread of the process "
        f"can be estimated from two values -- if they are a gauge's resolution "
        f"steps, the gauge is too coarse to resolve this process -- so no "
        f"normality verdict and no percentile index would be defensible. "
        f"Measure with a finer resolution."
    )


def fit_distribution(
    data: npt.ArrayLike,
    candidates: tuple[str, ...] = DEFAULT_CANDIDATES,
) -> DistributionFit:
    """Fit each candidate distribution and return the best-scoring one.

    Each candidate is fitted by maximum likelihood on the standardised sample
    (:func:`_fit_family`), so the choice and the fitted percentiles do not
    depend on the unit the data are in, and ranked by :func:`_fit_score`.

    Raises
    ------
    ValueError
        If the data hold fewer than three distinct values, or if no candidate
        could be fitted to them.
    """
    arr = as_sample(data, minimum=AD_MIN_SAMPLE_SIZE)
    _require_distinct_values(arr)

    best: DistributionFit | None = None
    for name in candidates:
        distribution = getattr(stats, name, None)
        if distribution is None:
            continue
        # Probing a candidate that does not suit the data is the normal course of
        # events here, not an anomaly: fitting lognorm to data straddling zero
        # takes log() of a negative number inside scipy. We want the resulting
        # NaN -- it scores the candidate out below -- but not the noise, and the
        # suppression is scoped to this one probe rather than set globally.
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            try:
                params = _fit_family(distribution, arr)
                score = _fit_score(arr, distribution(*params))
            except (ValueError, RuntimeError, FloatingPointError):
                continue
        if not math.isfinite(score):
            continue
        if best is None or score < best.fit_score:
            best = DistributionFit(name=name, params=tuple(params), fit_score=score)

    if best is None:
        raise ValueError(
            f"none of the candidate distributions {candidates} could be fitted "
            f"to the data"
        )
    return best


@dataclass(frozen=True, slots=True)
class PercentileCapability:
    """ISO 22514 percentile capability. Long-term indices only.

    There is no ``cp``/``cpk`` here, and their absence is the point: the method
    reads percentiles off the *overall* fitted distribution, so it has no notion
    of within-subgroup variation and cannot express a short-term potential.
    Anything claiming to be a percentile-method Cpk is conflating the two.
    """

    n: int
    distribution: str
    params: tuple[float, ...]
    fit_score: float
    lsl: float | None
    usl: float | None
    p_lower: float
    p_median: float
    p_upper: float
    pp: float | None
    ppl: float | None
    ppu: float | None
    ppk: float | None
    warnings: tuple[Caveat, ...]


def _check_limits(lsl: float | None, usl: float | None) -> None:
    if lsl is None and usl is None:
        raise ValueError("at least one specification limit (lsl or usl) is required")
    if lsl is not None and usl is not None and lsl >= usl:
        raise ValueError(f"lsl ({lsl}) must be strictly below usl ({usl})")


def percentile_capability(
    data: npt.ArrayLike,
    *,
    lsl: float | None = None,
    usl: float | None = None,
    distribution: str | DistributionFit | None = None,
) -> PercentileCapability:
    """Capability by the ISO 22514 percentile method.

    ``Pp  = (USL - LSL) / (X_99.865 - X_0.135)``
    ``Ppk = min( (USL - X_50) / (X_99.865 - X_50),
                 (X_50 - LSL) / (X_50 - X_0.135) )``

    The denominators are one-sided spreads measured from the median, which is
    what lets the method cope with asymmetry: a long right tail widens the upper
    denominator without touching the lower one.

    Parameters
    ----------
    distribution:
        A scipy distribution name, a :class:`DistributionFit`, or ``None`` to
        pick the best-scoring candidate automatically via :func:`fit_distribution`.
    """
    _check_limits(lsl, usl)
    arr = as_sample(data, minimum=AD_MIN_SAMPLE_SIZE)
    _require_distinct_values(arr)

    if isinstance(distribution, DistributionFit):
        fit = distribution
    elif isinstance(distribution, str):
        family = getattr(stats, distribution, None)
        if family is None:
            raise ValueError(f"unknown scipy distribution {distribution!r}")
        params = _fit_family(family, arr)
        fit = DistributionFit(
            name=distribution,
            params=params,
            fit_score=_fit_score(arr, family(*params)),
        )
    else:
        fit = fit_distribution(arr)

    frozen = fit.frozen()
    p_lower = float(frozen.ppf(LOWER_PERCENTILE))
    p_median = float(frozen.ppf(0.5))
    p_upper = float(frozen.ppf(UPPER_PERCENTILE))

    if not all(math.isfinite(v) for v in (p_lower, p_median, p_upper)):
        raise ValueError(
            f"the fitted {fit.name} distribution has non-finite percentiles; "
            f"it is not usable for capability"
        )

    pp = (
        (usl - lsl) / (p_upper - p_lower)
        if lsl is not None and usl is not None
        else None
    )
    ppu = (usl - p_median) / (p_upper - p_median) if usl is not None else None
    ppl = (p_median - lsl) / (p_median - p_lower) if lsl is not None else None

    available = [v for v in (ppl, ppu) if v is not None]
    ppk = min(available) if available else None

    warnings: list[Caveat] = [
        Caveat(
            "nonnormal.percentile-no-cpk",
            "the percentile method yields long-term (Pp/Ppk) indices only. It reads "
            "percentiles off the overall fitted distribution and has no within/"
            "between subgroup split, so no Cp or Cpk exists for it.",
        )
    ]
    if arr.size < 100:
        warnings.append(
            Caveat(
                "nonnormal.small-sample-tails",
                f"n={arr.size}: the indices depend on the 0.135 % and 99.865 % "
                f"percentiles, which sit far out in the tails where a fitted "
                f"distribution is least reliable. Treat them as indicative.",
            )
        )

    return PercentileCapability(
        n=int(arr.size),
        distribution=fit.name,
        params=fit.params,
        fit_score=fit.fit_score,
        lsl=lsl,
        usl=usl,
        p_lower=p_lower,
        p_median=p_median,
        p_upper=p_upper,
        pp=pp,
        ppl=ppl,
        ppu=ppu,
        ppk=ppk,
        warnings=tuple(warnings),
    )


def _box_cox(x: float, lmbda: float) -> float:
    """Box-Cox transform of a single positive value."""
    if x <= 0.0:
        raise ValueError(f"Box-Cox is undefined for non-positive values, got {x}")
    if lmbda == 0.0:
        return math.log(x)
    # math.pow, not `x ** lmbda`: typeshed types `float ** float` as Any (a
    # negative base may yield a complex result), which --strict then rejects.
    # Same wrinkle as in descriptive.skewness.
    return (math.pow(x, lmbda) - 1.0) / lmbda


@dataclass(frozen=True, slots=True)
class BoxCoxCapability:
    """Capability after a Box-Cox transformation to normality.

    ``capability`` holds the ordinary :class:`~capstat_core.capability.CapabilityReport`
    computed on the transformed scale, against the *transformed* limits. All the
    usual indices are available there, including Cp/Cpk, because on that scale
    the data are (if the transform worked) normal.

    ``transform_successful`` is the number to check first. If it is ``False``,
    the transformation did not achieve normality and the indices below are as
    untrustworthy as the untransformed ones would have been: use the percentile
    method instead.
    """

    lmbda: float
    n: int
    lsl: float | None
    usl: float | None
    target: float | None
    lsl_transformed: float | None
    usl_transformed: float | None
    target_transformed: float | None
    normality_after: NormalityAssessment
    transform_successful: bool
    capability: CapabilityReport
    warnings: tuple[Caveat, ...]


def box_cox_capability(
    data: npt.ArrayLike,
    *,
    lsl: float | None = None,
    usl: float | None = None,
    target: float | None = None,
    lmbda: float | None = None,
    alpha: float = 0.05,
) -> BoxCoxCapability:
    """Transform to normality with Box-Cox, then compute capability.

    The specification limits are transformed with the *same* lambda. This is not
    a detail: computing indices against untransformed limits on transformed data
    is the classic way to produce a confidently wrong Cpk.

    Parameters
    ----------
    lmbda:
        The transformation exponent. If ``None`` it is estimated by maximum
        likelihood. Pass ``0.0`` to force a log transform.

    Raises
    ------
    ValueError
        If any observation, or any specification limit, is not strictly
        positive. Box-Cox is undefined there; the data must be shifted first
        (and shifting is a decision for the user to make and document, not for
        capstat to make silently).
    """
    _check_limits(lsl, usl)
    arr = as_sample(data, minimum=AD_MIN_SAMPLE_SIZE)

    if np.any(arr <= 0.0):
        raise ValueError(
            "Box-Cox requires strictly positive data, and this sample contains "
            "values <= 0. Shift the data yourself if that is defensible for your "
            "process, or use the percentile method, which has no such "
            "restriction. capstat will not shift silently: the offset changes "
            "the indices and must be a recorded decision."
        )

    for name, limit in (("lsl", lsl), ("usl", usl), ("target", target)):
        if limit is not None and limit <= 0.0:
            raise ValueError(
                f"Box-Cox requires a strictly positive {name}, got {limit}; it "
                f"must be transformed on the same scale as the data"
            )

    if lmbda is None:
        _, fitted = stats.boxcox(arr)
        lmbda = float(fitted)

    transformed = stats.boxcox(arr, lmbda=lmbda)

    # The same lambda, applied to the limits. Box-Cox is strictly increasing for
    # every lambda on x > 0, so LSL remains the lower limit and no reordering is
    # needed.
    lsl_t = _box_cox(lsl, lmbda) if lsl is not None else None
    usl_t = _box_cox(usl, lmbda) if usl is not None else None
    target_t = _box_cox(target, lmbda) if target is not None else None

    # ... strictly increasing in exact arithmetic. In floating point a large
    # |lambda| saturates: x**lambda underflows to ~0 for every x in the range, so
    # (x**lambda - 1) / lambda collapses to -1/lambda for *both* limits and the
    # spec width vanishes. The indices would then be computed against a
    # zero-width specification, which is meaningless -- so say so, naming the
    # limits the caller actually passed rather than their transformed ghosts.
    if lsl_t is not None and usl_t is not None and lsl_t >= usl_t:
        raise ValueError(
            f"the Box-Cox transform (lambda = {lmbda:.4g}) is degenerate for this "
            f"specification: it maps lsl={lsl} and usl={usl} to the same value "
            f"({lsl_t:.6g}) in floating point, leaving no spec width to compute "
            f"an index against. Use the percentile method, which does not "
            f"transform the limits."
        )

    # The same saturation hits the data, and with one limit (or limits far
    # apart) nothing above catches it: the transformed sample collapses onto a
    # handful of floats -- or one -- while its spread is pure rounding noise.
    # Fed on, it made Shapiro-Wilk return NaN and the inner capability() say
    # "every subgroup is constant" about data that are not (UX-10 / ARCH-16).
    # Box-Cox is strictly increasing, so in exact arithmetic distinct readings
    # stay distinct; any two that merge were merged by floating point alone,
    # and the transformed sample no longer carries the data's spread.
    distinct_before = int(np.unique(arr).size)
    distinct_after = int(np.unique(transformed).size)
    if distinct_after < distinct_before:
        raise ValueError(
            f"the Box-Cox transform (lambda = {lmbda:.4g}) is degenerate for these "
            f"data: in floating point it maps the {distinct_before} distinct "
            f"readings onto {distinct_after} distinct value(s), so the transformed "
            f"sample no longer carries the data's spread, and neither a normality "
            f"test nor an index computed on it would mean anything."
        )

    normality_after = assess_normality(transformed, alpha=alpha)
    successful = normality_after.normal

    report = capability(
        transformed,
        lsl=lsl_t,
        usl=usl_t,
        target=target_t,
        alpha=alpha,
    )

    warnings: list[Caveat] = []
    if not successful:
        warnings.append(
            Caveat(
                "nonnormal.transform-failed",
                "the Box-Cox transformation did NOT achieve normality (the normal "
                "model is still rejected after transforming). These indices are not "
                "trustworthy; use the percentile method instead.",
            )
        )
    warnings.append(
        Caveat(
            "nonnormal.transformed-scale",
            f"indices are computed on the Box-Cox scale (lambda = {lmbda:.4f}) "
            f"against the transformed limits. They are dimensionless and comparable "
            f"to ordinary indices, but the underlying mean and sigma are NOT in the "
            f"original units.",
        )
    )
    # Everything the inner report has to say applies here too, and saying it
    # here is what makes it reach a caller (T-0064). The transformation changes
    # the scale, not the study: an unstable process is still unstable, the
    # moving-range sigma still assumes time order, and Cpm is still absent
    # without a target. Those warnings were being dropped -- the analysis on the
    # Box-Cox path carried two sentences about the transform and nothing about
    # the data, so a drifting process showed a flattering Cpk with no sign that
    # its own report had objected.
    warnings.extend(w for w in report.warnings if w not in warnings)

    return BoxCoxCapability(
        lmbda=lmbda,
        n=int(arr.size),
        lsl=lsl,
        usl=usl,
        target=target,
        lsl_transformed=lsl_t,
        usl_transformed=usl_t,
        target_transformed=target_t,
        normality_after=normality_after,
        transform_successful=successful,
        capability=report,
        warnings=tuple(warnings),
    )


CapabilityPath = Literal["normal", "box-cox", "percentile"]


@dataclass(frozen=True, slots=True)
class CapabilityAnalysis:
    """The result of the documented decision path.

    ``path`` and ``rationale`` record *why* these numbers were produced this
    way. That record is the deliverable: a capability figure whose method was
    chosen silently cannot be audited, and an unauditable capability figure is
    the thing this library exists to replace.
    """

    path: CapabilityPath
    rationale: str
    normality: NormalityAssessment
    normal: CapabilityReport | None
    box_cox: BoxCoxCapability | None
    percentile: PercentileCapability | None
    pp: float | None
    ppk: float | None
    warnings: tuple[Caveat, ...]


def _calibrated_tests(rounded: _RoundedNormality) -> str:
    return (
        f"Anderson-Darling p={rounded.anderson_darling_p:.3g}, Shapiro-Wilk "
        f"p={rounded.shapiro_wilk_p:.3g} on {rounded.draws} simulated samples"
    )


def _resolution_caveat(rounded: _RoundedNormality, n: int) -> Caveat:
    return Caveat(
        "nonnormal.resolution-limited",
        f"the readings are rounded to a resolution of {rounded.resolution:.6g}: "
        f"{rounded.distinct} distinct values in {n} readings, a step of "
        f"{rounded.resolution / rounded.sigma:.2g} times the estimated process "
        f"sigma. Normality tests that assume continuous data reject rounded "
        f"readings for their ties alone, so the verdict was taken against normal "
        f"data rounded to the same resolution. The coarser the step relative to "
        f"sigma, the less the readings say about the shape of the distribution: "
        f"at a step of about one sigma or more, a skewed process can pass as "
        f"normal.",
    )


def analyze_capability(
    data: npt.ArrayLike,
    *,
    lsl: float | None = None,
    usl: float | None = None,
    target: float | None = None,
    alpha: float = 0.05,
) -> CapabilityAnalysis:
    """Choose a capability method, apply it, and record the reasoning.

    The path::

        1. Is the data normal?                  -> normal indices. Done.
        2. Not normal. Does Box-Cox fix it?     -> Box-Cox indices.
        3. Box-Cox did not fix it either        -> ISO 22514 percentile method.

    Box-Cox is preferred over the percentile method when it works, because it
    preserves the within/overall split (and therefore Cp and Cpk); the
    percentile method cannot. Box-Cox is skipped outright when the data are not
    strictly positive, since it is undefined there.

    ``pp`` and ``ppk`` on the result are the headline numbers from whichever
    branch was taken, so a caller who does not care about the machinery can read
    those two and the ``rationale``.

    Readings rounded to a gauge resolution
    --------------------------------------
    Both normality tests assume continuous data. Readings from a gauge with a
    fixed resolution tie, and with enough of them the tests reject a perfectly
    normal process for the ties alone: N(10, 0.05) read to 0.01 took the
    percentile path in 40 of 40 runs at n = 1000 (CAP-6), losing Cp and Cpk and
    being called "not normal" for having been measured. So when the tests
    reject and the readings lie on a regular grid with ties, the verdict is
    re-taken with the same two statistics calibrated against normal data
    rounded to the same grid (``normality._normality_at_resolution``, a
    parametric bootstrap). If the departure is then not significant -- the
    rounding was the only departure found -- the normal path is taken after
    all, and the rationale and a ``nonnormal.resolution-limited`` caveat say
    so. If it still is, the path continues as before, and says that the
    resolution was allowed for. At a step of 0.2 sigma or finer the calibrated
    tests keep nearly all their power against skewness (gamma and lognormal
    processes at n = 100 detected in 86-98 % of runs, against 88-99 %
    uncalibrated -- part of which was the ties; 100 runs each, 2026-10-21); at
    coarser steps the readings themselves carry less information about the
    shape of the distribution, and the caveat states the step relative to
    sigma. Samples above ``RESOLUTION_MAX_SAMPLE_SIZE`` (5000) readings are not
    calibrated -- the cost grows with n -- and keep the uncalibrated verdict.
    Not calibrated either: Box-Cox's own check that the *transformed* readings
    are normal. Carrying the rounding through the transform is not done, so on
    coarsely rounded skewed data Box-Cox can be judged a failure for the ties
    and the percentile path taken instead -- a loss of Cp/Cpk, not a wrong
    number.

    Fewer than three distinct readings are refused outright (ValueError): no
    distribution can be estimated from them (see
    :func:`_require_distinct_values`).
    """
    _check_limits(lsl, usl)
    arr = as_sample(data, minimum=AD_MIN_SAMPLE_SIZE)
    _require_distinct_values(arr)

    normality = assess_normality(arr, alpha=alpha)

    rounded: _RoundedNormality | None = None
    if not normality.normal and arr.size <= RESOLUTION_MAX_SAMPLE_SIZE:
        resolution = _grid_resolution(arr)
        if resolution is not None:
            rounded = _normality_at_resolution(arr, resolution, alpha=alpha)
    rounding_caveats = (
        [_resolution_caveat(rounded, int(arr.size))] if rounded is not None else []
    )

    if normality.normal or (rounded is not None and rounded.normal):
        report = capability(arr, lsl=lsl, usl=usl, target=target, alpha=alpha)
        tests = (
            f"Anderson-Darling p={normality.anderson_darling.p_value:.4g}, "
            f"Shapiro-Wilk p={normality.shapiro_wilk.p_value:.4g}"
        )
        inner = report.warnings
        if rounded is None:
            rationale = (
                f"the normal model was not rejected ({tests}), so the standard "
                f"indices apply."
            )
        else:
            # capability() runs the uncalibrated tests itself and, on rounded
            # readings, warns that the normal model was rejected and its numbers
            # are wrong. The calibrated verdict above supersedes that: passing
            # it on would contradict the path just taken, in the same response.
            inner = tuple(w for w in inner if w.code != "capability.non-normal")
            rationale = (
                f"the normality tests rejected the normal model ({tests}), but "
                f"they assume continuous data, and these readings are rounded to "
                f"a resolution of {rounded.resolution:.6g} ({rounded.distinct} "
                f"distinct values in {arr.size} readings). Judged against normal "
                f"data rounded to the same resolution, the departure is not "
                f"significant ({_calibrated_tests(rounded)}): the rounding is the "
                f"only departure found, so the standard indices apply."
            )
        return CapabilityAnalysis(
            path="normal",
            rationale=rationale,
            normality=normality,
            normal=report,
            box_cox=None,
            percentile=None,
            pp=report.pp,
            ppk=report.ppk,
            warnings=(*rounding_caveats, *inner),
        )

    rejected = "the normal model was rejected"
    if rounded is not None:
        rejected += (
            f", also when judged against normal data rounded to the readings' "
            f"resolution of {rounded.resolution:.6g} ({_calibrated_tests(rounded)})"
        )

    positive = bool(np.all(arr > 0.0)) and all(
        limit is None or limit > 0.0 for limit in (lsl, usl, target)
    )

    if positive:
        # Box-Cox can fail outright, not just fail to fix the normality -- an
        # extreme lambda collapses the transformed spec limits onto each other.
        # Choosing a path that works is this function's whole job, so a failure
        # here routes to the percentile method rather than reaching the caller.
        # The `positive` guard above already rules out the other ValueErrors
        # box_cox_capability raises, so what is caught here is a genuine
        # "Box-Cox is unusable for this data" and nothing else.
        try:
            transformed = box_cox_capability(
                arr, lsl=lsl, usl=usl, target=target, alpha=alpha
            )
        except ValueError as exc:
            transformed = None
            box_cox_failure: str | None = str(exc)
        else:
            box_cox_failure = None

        if transformed is not None and transformed.transform_successful:
            return CapabilityAnalysis(
                path="box-cox",
                rationale=(
                    f"{rejected}, but a Box-Cox transformation "
                    f"with lambda = {transformed.lmbda:.4f} achieved normality, "
                    f"so the standard indices were computed on the transformed "
                    f"scale against the transformed specification limits. Box-Cox "
                    f"is preferred over the percentile method because it preserves "
                    f"the within/overall split, and hence Cp and Cpk."
                ),
                normality=normality,
                normal=None,
                box_cox=transformed,
                percentile=None,
                pp=transformed.capability.pp,
                ppk=transformed.capability.ppk,
                warnings=(*rounding_caveats, *transformed.warnings),
            )
        if box_cox_failure is not None:
            # The failure is a sentence of its own; end it before the next one
            # starts (UX-10 showed "...undefined The ISO 22514 ..." on screen).
            reason = (
                f"{rejected}, and Box-Cox could not be applied here at all: "
                f"{box_cox_failure.rstrip('. ')}. The ISO 22514 percentile method "
                f"was used instead."
            )
        else:
            assert transformed is not None  # narrowed: no failure means a result
            reason = (
                f"{rejected} and a Box-Cox transformation "
                f"(lambda = {transformed.lmbda:.4f}) failed to fix it, so the "
                f"ISO 22514 percentile method was used instead."
            )
    else:
        reason = (
            f"{rejected}, and Box-Cox is undefined here because "
            "the data or the limits are not strictly positive, so the ISO 22514 "
            "percentile method was used. (capstat will not shift the data to make "
            "Box-Cox applicable: the offset changes the indices and must be your "
            "recorded decision, not a silent one.)"
        )

    percentile = percentile_capability(arr, lsl=lsl, usl=usl)
    warnings = [*rounding_caveats, *percentile.warnings]
    if target is not None:
        # The other two paths feed the target into Cpm. This one has no
        # within/overall split and so no Cpm to compute -- an honest answer, and
        # a silent one would not be. A user who states a target and is handed
        # indices that ignore it has nothing in the output to notice it by.
        warnings.append(
            Caveat(
                "nonnormal.target-unused",
                f"the target ({target:.6g}) was not used. Cpm needs a short-term "
                "sigma, which the percentile method does not have, so no "
                "target-based index was computed. Pp and Ppk below measure spread "
                "and distance to the nearer limit, not distance to the target.",
            )
        )
    return CapabilityAnalysis(
        path="percentile",
        rationale=(
            f"{reason} A {percentile.distribution} distribution was the best fit "
            f"of the candidates tried."
            + (
                " The target plays no part on this path; see the warnings."
                if target is not None
                else ""
            )
        ),
        normality=normality,
        normal=None,
        box_cox=None,
        percentile=percentile,
        pp=percentile.pp,
        ppk=percentile.ppk,
        warnings=tuple(warnings),
    )
