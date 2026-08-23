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
from capstat_core.normality import (
    AD_MIN_SAMPLE_SIZE,
    NormalityAssessment,
    anderson_darling,
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

    ``fit_score`` is an Anderson-Darling statistic computed on the probability
    integral transform of the data (if ``X ~ F`` then ``Phi^-1(F(X))`` is
    standard normal). Lower is better.

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
    """Anderson-Darling statistic on the probability integral transform."""
    u = np.clip(frozen.cdf(data), 1e-12, 1 - 1e-12)  # type: ignore[attr-defined]
    z = stats.norm.ppf(u)
    if not np.all(np.isfinite(z)):
        return math.inf
    try:
        return anderson_darling(z).statistic
    except ValueError:
        return math.inf


def fit_distribution(
    data: npt.ArrayLike,
    candidates: tuple[str, ...] = DEFAULT_CANDIDATES,
) -> DistributionFit:
    """Fit each candidate distribution and return the best-scoring one.

    Raises
    ------
    ValueError
        If no candidate could be fitted to the data.
    """
    arr = as_sample(data, minimum=AD_MIN_SAMPLE_SIZE)

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
                params = distribution.fit(arr)
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
    warnings: tuple[str, ...]


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

    if isinstance(distribution, DistributionFit):
        fit = distribution
    elif isinstance(distribution, str):
        family = getattr(stats, distribution, None)
        if family is None:
            raise ValueError(f"unknown scipy distribution {distribution!r}")
        params = tuple(family.fit(arr))
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

    warnings: list[str] = [
        "the percentile method yields long-term (Pp/Ppk) indices only. It reads "
        "percentiles off the overall fitted distribution and has no within/"
        "between subgroup split, so no Cp or Cpk exists for it."
    ]
    if arr.size < 100:
        warnings.append(
            f"n={arr.size}: the indices depend on the 0.135 % and 99.865 % "
            f"percentiles, which sit far out in the tails where a fitted "
            f"distribution is least reliable. Treat them as indicative."
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
    warnings: tuple[str, ...]


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

    normality_after = assess_normality(transformed, alpha=alpha)
    successful = normality_after.normal

    report = capability(
        transformed,
        lsl=lsl_t,
        usl=usl_t,
        target=target_t,
        alpha=alpha,
    )

    warnings: list[str] = []
    if not successful:
        warnings.append(
            "the Box-Cox transformation did NOT achieve normality (the normal "
            "model is still rejected after transforming). These indices are not "
            "trustworthy; use the percentile method instead."
        )
    warnings.append(
        f"indices are computed on the Box-Cox scale (lambda = {lmbda:.4f}) "
        f"against the transformed limits. They are dimensionless and comparable "
        f"to ordinary indices, but the underlying mean and sigma are NOT in the "
        f"original units."
    )

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
    warnings: tuple[str, ...]


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
    """
    _check_limits(lsl, usl)
    arr = as_sample(data, minimum=AD_MIN_SAMPLE_SIZE)

    normality = assess_normality(arr, alpha=alpha)

    if normality.normal:
        report = capability(arr, lsl=lsl, usl=usl, target=target, alpha=alpha)
        return CapabilityAnalysis(
            path="normal",
            rationale=(
                "the normal model was not rejected "
                f"(Anderson-Darling p={normality.anderson_darling.p_value:.4g}, "
                f"Shapiro-Wilk p={normality.shapiro_wilk.p_value:.4g}), so the "
                f"standard indices apply."
            ),
            normality=normality,
            normal=report,
            box_cox=None,
            percentile=None,
            pp=report.pp,
            ppk=report.ppk,
            warnings=report.warnings,
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
                    "the normal model was rejected, but a Box-Cox transformation "
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
                warnings=transformed.warnings,
            )
        if box_cox_failure is not None:
            reason = (
                "the normal model was rejected, and Box-Cox could not be applied "
                f"here at all: {box_cox_failure} The ISO 22514 percentile method "
                f"was used instead."
            )
        else:
            assert transformed is not None  # narrowed: no failure means a result
            reason = (
                "the normal model was rejected and a Box-Cox transformation "
                f"(lambda = {transformed.lmbda:.4f}) failed to fix it, so the "
                f"ISO 22514 percentile method was used instead."
            )
    else:
        reason = (
            "the normal model was rejected, and Box-Cox is undefined here because "
            "the data or the limits are not strictly positive, so the ISO 22514 "
            "percentile method was used. (capstat will not shift the data to make "
            "Box-Cox applicable: the offset changes the indices and must be your "
            "recorded decision, not a silent one.)"
        )

    percentile = percentile_capability(arr, lsl=lsl, usl=usl)
    warnings = list(percentile.warnings)
    if target is not None:
        # The other two paths feed the target into Cpm. This one has no
        # within/overall split and so no Cpm to compute -- an honest answer, and
        # a silent one would not be. A user who states a target and is handed
        # indices that ignore it has nothing in the output to notice it by.
        warnings.append(
            f"the target ({target:.6g}) was not used. Cpm needs a short-term "
            "sigma, which the percentile method does not have, so no "
            "target-based index was computed. Pp and Ppk below measure spread "
            "and distance to the nearer limit, not distance to the target."
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
