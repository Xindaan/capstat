"""Acceptance sampling: deciding a lot from a sample of it.

A single sampling plan by attributes is two numbers. Draw ``n`` items from the
lot, count the defectives, and accept the lot if that count is at most the
acceptance number ``Ac``. Everything else on this page is a consequence of those
two numbers, and every function here computes that consequence from its
definition rather than reading it out of a table.

The operating characteristic (OC) curve is the plan's whole personality: the
probability of accepting a lot, plotted against how defective the lot actually
is. Three models produce it, and which one is right depends on the lot, not on
taste:

``binomial`` (Type B)
    Sampling from a process, or from a lot so large that removing the sample
    does not change what is left. ``Pa = P(X <= Ac)``, ``X ~ Binomial(n, p)``.
``hypergeometric`` (Type A)
    Sampling from one finite lot of known size ``N``. The lot holds a whole
    number of defectives ``D``, so this OC curve is a step function in ``D``,
    defined only at ``p = D/N``. ``X ~ Hypergeometric(N, D, n)``.
``poisson``
    The classical approximation to the binomial, ``X ~ Poisson(n p)``. Offered
    explicitly, never applied silently: it is what the published unity-value
    tables are built on, so a plan designed from those tables can be reproduced
    only by asking for it.

From the OC curve follow the producer's risk (rejecting a lot as good as the
AQL), the consumer's risk (accepting a lot as bad as the LTPD), the indifference
quality, and -- under *rectifying* inspection, where rejected lots are screened
100 % and defectives replaced -- the average outgoing quality (AOQ), its
maximum the AOQL, and the average total inspection (ATI).

    AOQ = Pa(p) * p * (N - n) / N          ATI = n + (1 - Pa(p)) * (N - n)

Designing a plan runs the same OC function backwards: find the smallest
``(n, Ac)`` whose curve passes above ``1 - alpha`` at the AQL and below ``beta``
at the LTPD. That is a search over the definition, not a lookup.

What acceptance sampling does not do is the part users get wrong, so every
report says it out loud: a sampling plan bounds risk over a *stream* of lots and
asserts almost nothing about the single lot in front of you, and the AOQL is an
average over that stream, not a bound on any one outgoing lot.

References
----------
NIST/SEMATECH e-Handbook of Statistical Methods, section 6.2 (Test Product for
    Acceptability: Lot Acceptance Sampling), in particular 6.2.2 and 6.2.3.2 --
    the definitions above and the worked (n=52, c=3) plan the tests assert
    against.
ISO 2859-1: Sampling procedures for inspection by attributes -- Part 1
    (terminology: AQL, limiting quality, sample size code letters). The
    standard's master tables are *not* implemented here; see TASK.md T-0036.
Schilling, E. G. and Neubauer, D. V. *Acceptance Sampling in Quality Control*,
    3rd ed., 2017 (Type A vs Type B, rectifying inspection).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt
from scipy import optimize, stats

__all__ = [
    "AOQLimit",
    "LotDecision",
    "OCCurve",
    "SamplingModel",
    "SamplingPlan",
    "SamplingPlanReport",
    "aoq_limit",
    "average_outgoing_quality",
    "average_total_inspection",
    "design_single_sampling_plan",
    "evaluate_plan",
    "inspect_lot",
    "oc_curve",
    "probability_of_acceptance",
    "quality_for_acceptance",
]

SamplingModel = Literal["binomial", "hypergeometric", "poisson"]

# Where the default OC grid stops: the fraction defective a plan rejects with
# practical certainty. Derived from the plan itself rather than a fixed upper p,
# so a tight plan and a loose one both get a readable curve.
_OC_GRID_TAIL_PA = 0.001
_OC_GRID_POINTS = 201

# The textbook condition for treating a finite lot as infinite. Below it the
# binomial stands in for the hypergeometric; above it we say so.
_LARGE_LOT_RATIO = 0.1

# ISO 2859-1 names the quality a plan accepts only 10 % of the time the
# *limiting quality* (LQ). It is a property of the plan, not a choice, so
# capstat computes it by inverting the OC curve rather than asking for it --
# and reporting it next to the LTPD you asked for is how you find out whether
# the plan protects you where you thought it did.
_LIMITING_QUALITY_PA = 0.10


@dataclass(frozen=True, slots=True)
class SamplingPlan:
    """A single sampling plan by attributes: sample ``n``, accept on ``Ac``.

    ``lot_size`` is optional because the plan itself does not need it -- the
    binomial OC curve does not depend on the lot. It is required for anything
    that talks about the lot as a finite population: the hypergeometric model,
    AOQ, and ATI.
    """

    sample_size: int
    acceptance_number: int
    lot_size: int | None = None

    def __post_init__(self) -> None:
        if self.sample_size < 1:
            raise ValueError(f"sample_size must be >= 1, got {self.sample_size}")
        if self.acceptance_number < 0:
            raise ValueError(
                f"acceptance_number must be >= 0, got {self.acceptance_number}"
            )
        if self.acceptance_number > self.sample_size:
            raise ValueError(
                f"acceptance_number ({self.acceptance_number}) cannot exceed "
                f"sample_size ({self.sample_size}): a sample of {self.sample_size} "
                f"items cannot hold {self.acceptance_number} defectives"
            )
        if self.lot_size is not None and self.lot_size < self.sample_size:
            raise ValueError(
                f"lot_size ({self.lot_size}) must be at least sample_size "
                f"({self.sample_size})"
            )

    @property
    def rejection_number(self) -> int:
        """``Re``: the defect count at which the lot is rejected."""
        return self.acceptance_number + 1

    def accepts(self, defectives: int) -> bool:
        """The decision itself: accept exactly when ``defectives <= Ac``."""
        if defectives < 0:
            raise ValueError(f"defectives must be >= 0, got {defectives}")
        if defectives > self.sample_size:
            raise ValueError(
                f"defectives ({defectives}) cannot exceed the sample size "
                f"({self.sample_size})"
            )
        return defectives <= self.acceptance_number


@dataclass(frozen=True, slots=True)
class LotDecision:
    """The verdict on one lot, and what that verdict is and is not evidence of."""

    plan: SamplingPlan
    defectives: int
    accepted: bool
    sample_fraction_defective: float
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OCCurve:
    """The operating characteristic curve: ``Pa`` against fraction defective.

    The two series are plain tuples, as everywhere else in the public API: a
    frozen dataclass holding a mutable array would only be frozen in name, and
    every consumer -- the HTTP layer above all -- wants a sequence it can
    serialise without knowing about numpy.
    """

    plan: SamplingPlan
    model: SamplingModel
    fraction_defective: tuple[float, ...]
    probability_accept: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class AOQLimit:
    """The worst long-run outgoing quality, and the incoming quality causing it."""

    aoql: float
    at_fraction_defective: float


@dataclass(frozen=True, slots=True)
class SamplingPlanReport:
    """A plan judged at the two quality levels it is supposed to discriminate.

    ``producer_risk`` is the probability of *rejecting* a lot at the AQL,
    ``consumer_risk`` the probability of *accepting* one at the LTPD.
    ``indifference_quality`` is where the plan is a coin flip (``Pa = 0.5``),
    and ``limiting_quality`` is ISO 2859-1's LQ -- the quality this plan accepts
    only 10 % of the time. LQ is computed from the plan, not requested: reading
    it against the LTPD you asked for is how you learn whether the plan protects
    you where you believed it did.
    ``aoql`` and ``ati_at_aql`` are ``None`` unless a lot size is known, because
    both describe rectifying inspection of a finite lot.
    """

    plan: SamplingPlan
    model: SamplingModel
    aql: float
    ltpd: float
    producer_risk: float
    consumer_risk: float
    probability_accept_at_aql: float
    probability_accept_at_ltpd: float
    indifference_quality: float
    limiting_quality: float
    aoql: AOQLimit | None
    ati_at_aql: float | None
    warnings: tuple[str, ...]


def _check_fraction(p: float, name: str = "fraction_defective") -> float:
    value = float(p)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be a fraction in [0, 1], got {p}")
    return value


def _require_lot_size(plan: SamplingPlan, what: str) -> int:
    if plan.lot_size is None:
        raise ValueError(
            f"{what} is defined for a finite lot, so the plan needs a lot_size"
        )
    return plan.lot_size


def probability_of_acceptance(
    plan: SamplingPlan,
    fraction_defective: float,
    *,
    model: SamplingModel = "binomial",
) -> float:
    """``Pa``: the probability this plan accepts a lot that is ``p`` defective.

    For ``model="hypergeometric"`` the lot must hold a whole number of
    defectives, so ``p`` is realised as ``D = round(N * p)`` and the value
    returned is ``Pa`` for that ``D``. The Type A curve is a step function; this
    is the step ``p`` falls on, not an interpolation of it.
    """
    p = _check_fraction(fraction_defective)
    ac, n = plan.acceptance_number, plan.sample_size
    if model == "binomial":
        return float(stats.binom.cdf(ac, n, p))
    if model == "poisson":
        return float(stats.poisson.cdf(ac, n * p))
    if model == "hypergeometric":
        lot_size = _require_lot_size(plan, "the hypergeometric (Type A) model")
        defectives_in_lot = round(lot_size * p)
        return float(stats.hypergeom.cdf(ac, lot_size, defectives_in_lot, n))
    raise ValueError(f"unknown model {model!r}")


def quality_for_acceptance(
    plan: SamplingPlan,
    probability: float,
    *,
    model: SamplingModel = "binomial",
    tolerance: float = 1e-12,
) -> float:
    """Invert the OC curve: the ``p`` at which the plan accepts with ``Pa``.

    This is how the named quality levels are found rather than assumed -- the
    limiting quality (``Pa = 0.10``), the indifference quality (``Pa = 0.5``).
    ``Pa`` is non-increasing in ``p``, so a bisection is exact up to
    ``tolerance``; for the hypergeometric model the curve is a step function and
    the answer is the step boundary.
    """
    target = _check_fraction(probability, "probability")
    if probability_of_acceptance(plan, 1.0, model=model) >= target:
        # A plan that accepts a wholly defective lot (Ac == n) never gets below
        # the target; there is no such quality level.
        return 1.0
    low, high = 0.0, 1.0
    while high - low > tolerance:
        mid = 0.5 * (low + high)
        if probability_of_acceptance(plan, mid, model=model) >= target:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def oc_curve(
    plan: SamplingPlan,
    fraction_defective: npt.ArrayLike | None = None,
    *,
    model: SamplingModel = "binomial",
) -> OCCurve:
    """The OC curve over a grid of incoming quality levels.

    With no grid given, one is derived from the plan: ``_OC_GRID_POINTS`` points
    from zero to the quality the plan rejects with practical certainty
    (``Pa = 0.001``). That keeps the interesting part of the curve on screen for
    a tight plan and a loose one alike, without a hard-coded upper ``p``.
    """
    if fraction_defective is None:
        upper = min(1.0, quality_for_acceptance(plan, _OC_GRID_TAIL_PA, model=model))
        grid = np.linspace(0.0, max(upper, 1e-6), _OC_GRID_POINTS)
    else:
        grid = np.asarray(fraction_defective, dtype=np.float64)
        if grid.ndim != 1:
            raise ValueError("fraction_defective must be one-dimensional")
        if grid.size == 0:
            raise ValueError("fraction_defective must not be empty")
        for value in grid:
            _check_fraction(float(value))
    return OCCurve(
        plan=plan,
        model=model,
        fraction_defective=tuple(float(p) for p in grid),
        probability_accept=tuple(
            probability_of_acceptance(plan, float(p), model=model) for p in grid
        ),
    )


def average_outgoing_quality(
    plan: SamplingPlan,
    fraction_defective: float,
    *,
    model: SamplingModel = "binomial",
) -> float:
    """``AOQ = Pa * p * (N - n) / N`` -- outgoing quality under rectification.

    This assumes the rectifying scheme it is defined for: every rejected lot is
    100 % inspected and its defectives replaced with good units, so a rejected
    lot leaves perfect and only accepted lots carry defects onward.
    """
    lot_size = _require_lot_size(plan, "AOQ")
    p = _check_fraction(fraction_defective)
    pa = probability_of_acceptance(plan, p, model=model)
    return pa * p * (lot_size - plan.sample_size) / lot_size


def aoq_limit(
    plan: SamplingPlan,
    *,
    model: SamplingModel = "binomial",
) -> AOQLimit:
    """The AOQL: the maximum of the AOQ curve, found rather than tabulated.

    A coarse grid locates the peak and a bounded optimisation refines it inside
    the bracketing interval. The grid comes first on purpose: it does not assume
    the AOQ curve is unimodal, which is true for the plans anyone uses but is
    not something this function needs to bet on.
    """
    lot_size = _require_lot_size(plan, "the AOQL")
    if model == "hypergeometric" and lot_size <= 1000:
        # A finite lot has only N+1 attainable qualities, so search those rather
        # than a uniform grid that lands on the same steps over and over.
        grid = np.arange(lot_size + 1, dtype=np.float64) / lot_size
    else:
        grid = np.linspace(0.0, 1.0, 1001)
    values = np.array(
        [average_outgoing_quality(plan, float(p), model=model) for p in grid],
        dtype=np.float64,
    )
    peak = int(np.argmax(values))
    low = grid[max(peak - 1, 0)]
    high = grid[min(peak + 1, grid.size - 1)]
    if model == "hypergeometric" or high <= low:
        # A step function has no derivative to chase; the grid maximum is the
        # honest answer, and refining it would invent precision.
        return AOQLimit(
            aoql=float(values[peak]), at_fraction_defective=float(grid[peak])
        )
    result = optimize.minimize_scalar(
        lambda p: -average_outgoing_quality(plan, float(p), model=model),
        bounds=(float(low), float(high)),
        method="bounded",
        options={"xatol": 1e-10},
    )
    # Keep whichever is actually higher. The refinement should always win, but
    # "should" is not a reason to return an unchecked value.
    aoql, at_p = max(
        (float(-result.fun), float(result.x)),
        (float(values[peak]), float(grid[peak])),
    )
    return AOQLimit(aoql=aoql, at_fraction_defective=at_p)


def average_total_inspection(
    plan: SamplingPlan,
    fraction_defective: float,
    *,
    model: SamplingModel = "binomial",
) -> float:
    """``ATI = n + (1 - Pa) * (N - n)`` -- items inspected per lot, on average.

    Same rectifying scheme as :func:`average_outgoing_quality`: an accepted lot
    costs the sample, a rejected one costs the whole lot.
    """
    lot_size = _require_lot_size(plan, "ATI")
    p = _check_fraction(fraction_defective)
    pa = probability_of_acceptance(plan, p, model=model)
    return plan.sample_size + (1.0 - pa) * (lot_size - plan.sample_size)


def inspect_lot(
    plan: SamplingPlan,
    defectives: int,
    *,
    model: SamplingModel = "binomial",
) -> LotDecision:
    """Apply the plan to one observed sample. The decision is exact, not a score."""
    accepted = plan.accepts(defectives)
    warnings = list(_plan_warnings(plan, model))
    if accepted:
        warnings.append(
            "accepting this lot is a decision about a stream of lots, not "
            "evidence that this lot is good: a plan is chosen so that lots as "
            "bad as the LTPD are usually caught, and 'usually' is the whole "
            "guarantee."
        )
    else:
        warnings.append(
            "rejecting this lot says the sample was worse than the plan "
            "tolerates. It does not measure how defective the lot is; for that, "
            "estimate the fraction defective with a confidence interval."
        )
    return LotDecision(
        plan=plan,
        defectives=defectives,
        accepted=accepted,
        sample_fraction_defective=defectives / plan.sample_size,
        warnings=tuple(warnings),
    )


def design_single_sampling_plan(
    aql: float,
    ltpd: float,
    *,
    producer_risk: float = 0.05,
    consumer_risk: float = 0.10,
    model: SamplingModel = "binomial",
    lot_size: int | None = None,
    max_acceptance_number: int = 100,
    max_sample_size: int = 100_000,
) -> SamplingPlan:
    """The smallest plan meeting both risk conditions, by search over the OC curve.

    Find ``(n, Ac)`` with ``Pa(aql) >= 1 - producer_risk`` and
    ``Pa(ltpd) <= consumer_risk``. Acceptance numbers are tried in order; for
    each, the smallest ``n`` satisfying the consumer's condition is found by
    bisection (``Pa`` is non-increasing in ``n``), and the producer's condition
    is then checked. The first ``Ac`` that satisfies both gives the smallest
    ``n``, because the required ``n`` grows with ``Ac`` while the producer's
    condition only gets easier.

    Raises
    ------
    ValueError
        If the two points are not ordered (``aql < ltpd``), if the risks are not
        in ``(0, 1)``, or if no plan within the search bounds satisfies both --
        which happens when the two quality levels are too close to separate at
        the risks demanded, and is reported rather than approximated.
    """
    aql = _check_fraction(aql, "aql")
    ltpd = _check_fraction(ltpd, "ltpd")
    if not 0.0 < producer_risk < 1.0:
        raise ValueError(f"producer_risk must be in (0, 1), got {producer_risk}")
    if not 0.0 < consumer_risk < 1.0:
        raise ValueError(f"consumer_risk must be in (0, 1), got {consumer_risk}")
    if not aql < ltpd:
        raise ValueError(
            f"aql ({aql}) must be strictly below ltpd ({ltpd}): the plan has to "
            "tell an acceptable quality level from an unacceptable one"
        )
    if model == "hypergeometric" and lot_size is None:
        raise ValueError("designing on the hypergeometric model needs a lot_size")
    if model == "hypergeometric" and lot_size is not None:
        # A finite lot holds whole defectives. If the AQL rounds to none of
        # them, the producer's condition is satisfied by a perfect lot and stops
        # constraining anything -- the returned plan would look designed but be
        # driven entirely by the consumer's side. Refuse rather than mislead.
        for name, quality in (("aql", aql), ("ltpd", ltpd)):
            if quality > 0.0 and round(lot_size * quality) == 0:
                raise ValueError(
                    f"a lot of {lot_size} items cannot be {quality} defective: "
                    f"the nearest whole number of defectives is zero, so the "
                    f"{name} is indistinguishable from a perfect lot. The "
                    f"smallest quality level this lot can express is "
                    f"{1 / lot_size}."
                )

    required_at_aql = 1.0 - producer_risk
    if lot_size is not None:
        # You cannot inspect more items than the lot holds, under any model. The
        # search has to know that before it probes, not after: a candidate plan
        # with n > N is not merely a bad plan, it is not a plan.
        max_sample_size = min(max_sample_size, lot_size)

    def pa(n: int, ac: int, p: float) -> float:
        return probability_of_acceptance(
            SamplingPlan(sample_size=n, acceptance_number=ac, lot_size=lot_size),
            p,
            model=model,
        )

    for ac in range(max_acceptance_number + 1):
        # Smallest n meeting the consumer's condition, by bisection on n. The
        # bracket is found by doubling, and the doubling is clamped rather than
        # allowed to run past the ceiling: a probe that overshoots says nothing
        # about whether the *answer* fits under it, and treating the overshoot
        # as "no plan at this Ac" hid feasible plans behind the step size.
        low, high = ac + 1, ac + 1
        if high > max_sample_size:
            # Not even Ac + 1 items may be drawn, so no plan at this Ac can
            # reject anything -- and every higher Ac needs more.
            continue
        while high < max_sample_size and pa(high, ac, ltpd) > consumer_risk:
            low = high + 1
            high = min(high * 2, max_sample_size)
        if pa(high, ac, ltpd) > consumer_risk:
            # Even the largest sample allowed still accepts too much bad
            # quality. This Ac is genuinely out of reach, not merely overstepped.
            continue
        while low < high:
            mid = (low + high) // 2
            if pa(mid, ac, ltpd) <= consumer_risk:
                high = mid
            else:
                low = mid + 1
        if pa(low, ac, aql) >= required_at_aql:
            return SamplingPlan(
                sample_size=low, acceptance_number=ac, lot_size=lot_size
            )
    bounded_by_lot = (
        f" (the sample size was capped at the lot size, {lot_size})"
        if lot_size is not None and lot_size <= max_sample_size
        else ""
    )
    raise ValueError(
        f"no single sampling plan with acceptance number <= "
        f"{max_acceptance_number} and sample size <= {max_sample_size} meets "
        f"Pa({aql}) >= {required_at_aql} and Pa({ltpd}) <= {consumer_risk}"
        f"{bounded_by_lot}. The two quality levels are too close together for "
        "the risks demanded; widen them, accept more risk, or use a sequential "
        "scheme."
    )


def evaluate_plan(
    plan: SamplingPlan,
    aql: float,
    ltpd: float,
    *,
    model: SamplingModel = "binomial",
) -> SamplingPlanReport:
    """Judge a plan at the two quality levels it exists to discriminate."""
    aql = _check_fraction(aql, "aql")
    ltpd = _check_fraction(ltpd, "ltpd")
    if not aql < ltpd:
        raise ValueError(f"aql ({aql}) must be strictly below ltpd ({ltpd})")
    pa_aql = probability_of_acceptance(plan, aql, model=model)
    pa_ltpd = probability_of_acceptance(plan, ltpd, model=model)
    warnings = list(_plan_warnings(plan, model))
    warnings += _quantisation_warnings(plan, model, aql=aql, ltpd=ltpd)
    limit: AOQLimit | None = None
    ati: float | None = None
    if plan.lot_size is not None:
        limit = aoq_limit(plan, model=model)
        ati = average_total_inspection(plan, aql, model=model)
        warnings.append(
            "AOQ, the AOQL and ATI describe rectifying inspection -- rejected "
            "lots screened 100 % and their defectives replaced. Without that "
            "screening they do not apply."
        )
        warnings.append(
            f"the AOQL ({limit.aoql:.4f}) is the worst *average* outgoing "
            "quality over a stream of lots. Individual outgoing lots can be "
            "worse; it bounds no single lot."
        )
    if pa_aql < 0.5:
        warnings.append(
            f"this plan rejects more than half of the lots that are exactly at "
            f"the AQL (Pa = {pa_aql:.3f}). The AQL is meant to be the quality "
            "the producer can ship routinely; check that n and Ac are the ones "
            "you intended."
        )
    limiting_quality = quality_for_acceptance(plan, _LIMITING_QUALITY_PA, model=model)
    if limiting_quality > ltpd:
        warnings.append(
            f"this plan's limiting quality is {limiting_quality:.4f} -- the "
            f"quality it still accepts 10 % of the time (ISO 2859-1's LQ). That "
            f"is worse than the {ltpd} you named as unacceptable, so the plan "
            "does not give the protection the LTPD implies."
        )
    return SamplingPlanReport(
        plan=plan,
        model=model,
        aql=aql,
        ltpd=ltpd,
        producer_risk=1.0 - pa_aql,
        consumer_risk=pa_ltpd,
        probability_accept_at_aql=pa_aql,
        probability_accept_at_ltpd=pa_ltpd,
        indifference_quality=quality_for_acceptance(plan, 0.5, model=model),
        limiting_quality=limiting_quality,
        aoql=limit,
        ati_at_aql=ati,
        warnings=tuple(warnings),
    )


def _quantisation_warnings(
    plan: SamplingPlan,
    model: SamplingModel,
    *,
    aql: float,
    ltpd: float,
) -> list[str]:
    """A finite lot cannot be any fraction defective -- only ``D/N`` of them.

    Asking a Type A curve about ``p`` really asks it about the nearest whole
    number of defectives, and for a small lot that is a different question. It
    stays silent when the requested levels land exactly on the lot's own grid,
    which is the usual case.
    """
    out: list[str] = []
    if model != "hypergeometric" or plan.lot_size is None:
        return out
    for name, quality in (("AQL", aql), ("LTPD", ltpd)):
        defectives = round(plan.lot_size * quality)
        realised = defectives / plan.lot_size
        if realised != quality:
            out.append(
                f"a lot of {plan.lot_size} items cannot be exactly {quality} "
                f"defective; the {name} was evaluated at the nearest attainable "
                f"lot quality, {defectives}/{plan.lot_size} = {realised}."
            )
    return out


def _plan_warnings(plan: SamplingPlan, model: SamplingModel) -> list[str]:
    """What the model and the plan shape cost, said before anyone asks."""
    out: list[str] = []
    if plan.lot_size is not None and model == "binomial":
        ratio = plan.sample_size / plan.lot_size
        if ratio > _LARGE_LOT_RATIO:
            out.append(
                f"the sample is {100 * ratio:.0f}% of the lot, so the binomial "
                "(Type B) model no longer describes it: drawing without "
                "replacement from one finite lot is hypergeometric. Use "
                'model="hypergeometric" for a Type A curve.'
            )
    if model == "poisson":
        out.append(
            "the Poisson approximation is used. It is what the classical "
            "unity-value tables assume, and it drifts from the binomial as the "
            "fraction defective grows -- for a (52, 3) plan it is off by 0.016 "
            "in Pa at p = 0.12."
        )
    if plan.acceptance_number == 0:
        out.append(
            "this is an Ac = 0 plan: Pa = (1 - p)^n, a curve with no shoulder. "
            "It falls from the first defective onward, so it rejects lots of "
            "genuinely good quality far more often than the sample size "
            "suggests. That is a deliberate trade, not a free tightening."
        )
    if plan.acceptance_number == plan.sample_size:
        out.append(
            "Ac equals the sample size: this plan accepts every possible "
            "sample and can never reject a lot."
        )
    return out
