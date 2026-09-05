"""Request bodies for the compute endpoints.

All compute is stateless: every request carries its own data as JSON arrays.
File parsing is a separate concern (see the ingest router); these models never
touch pandas.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from capstat_api.schemas import (
    GageRRMethod,
    InspectionSeverity,
    SamplingModel,
    WithinMethod,
)


class _Request(BaseModel):
    # Reject unknown keys: a mistyped field (``smaple`` for ``sample``) becomes
    # a 422 the caller can see, not a silently ignored default.
    model_config = ConfigDict(extra="forbid")


# A non-empty series of measurements. The core validates ranges and lengths and
# raises ValueError, which the router maps to HTTP 422; here we only guarantee
# the shape and that at least one value is present.
Series = Field(min_length=1)


class DescriptiveRequest(_Request):
    data: list[float] = Series


class CapabilityRequest(_Request):
    # 1D = individuals (within-sigma from the moving range); 2D = subgroups
    # (rows are subgroups), which is what unlocks a genuine within-subgroup Cp.
    data: list[float] | list[list[float]] = Series
    lsl: float | None = None
    usl: float | None = None
    target: float | None = None
    within_method: WithinMethod | None = None
    alpha: float = 0.05


class AnalyzeCapabilityRequest(_Request):
    data: list[float] = Series
    lsl: float | None = None
    usl: float | None = None
    target: float | None = None
    alpha: float = 0.05


class _Baseline(_Request):
    """A known in-control centre and sigma, for a Phase II chart.

    Both or neither (T-0076). One without the other mixes a parameter from a
    stable period with one estimated from the data under test, which is neither
    phase; the core rejects it with its own message.
    """

    center: float | None = None
    sigma: float | None = None


class IMRRequest(_Baseline):
    data: list[float] = Series


class SubgroupRequest(_Baseline):
    # Rows are subgroups, columns are observations within a subgroup.
    subgroups: list[list[float]] = Field(min_length=1)


class EwmaRequest(_Request):
    data: list[float] = Series
    target: float | None = None
    sigma: float | None = None
    lmbda: float = 0.2
    L: float = 3.0
    time_varying_limits: bool = True


class CusumRequest(_Request):
    data: list[float] = Series
    target: float | None = None
    sigma: float | None = None
    k: float = 0.5
    h: float = 5.0


class ControlLimitsIn(_Request):
    center: float
    lower: float
    upper: float


class BiasRequest(_Request):
    """Repeated readings of one part whose true value is known."""

    measurements: list[float] = Field(min_length=2)
    reference: float
    alpha: float = 0.05


class LinearityRequest(_Request):
    """Readings of several masters spanning the range, one list per master."""

    references: list[float] = Field(min_length=2)
    measurements: list[list[float]] = Field(min_length=2)
    process_variation: float | None = None
    alpha: float = 0.05


class StabilityRequest(_Request):
    """Time-ordered readings of one master: 1-D individuals or 2-D subgroups."""

    measurements: list[float] | list[list[float]] = Field(min_length=2)


class GageRRRequest(_Request):
    """A balanced Gage R&R layout: parts x operators x trials.

    Each innermost list is the trials for one part-operator cell. The core
    validates the shape (>= 2 of each) and balance and raises ValueError, mapped
    to 422. ``interaction_alpha`` is ignored by the average-and-range method.
    """

    data: list[list[list[float]]] = Field(min_length=2)
    method: GageRRMethod = "anova"
    tolerance: float | None = None
    study_var_multiplier: float = 6.0
    interaction_alpha: float = 0.25


class RulesRequest(_Request):
    """Run run-rules against an already-computed chart.

    The rules are a lens over a chart: they derive their sigma zones from the
    chart's own limits, so the client passes the plotted points and the limits
    rather than raw data. ``rules`` selects a subset (Nelson himself advised
    against enabling all eight at once); ``None`` means all rules in the set.
    """

    points: list[float] = Series
    limits: ControlLimitsIn
    rules: list[int] | None = None


class SamplingPlanIn(_Request):
    """A single sampling plan by attributes: sample ``n``, accept on ``Ac``.

    ``lot_size`` is optional here for the same reason it is optional in the
    core: the binomial (Type B) curve does not depend on the lot. The core
    rejects the impossible combinations (Ac above n, a lot smaller than the
    sample) with a ValueError, which becomes a 422.
    """

    sample_size: int = Field(ge=1)
    acceptance_number: int = Field(ge=0)
    lot_size: int | None = Field(default=None, ge=1)


# A fraction defective, not a percentage. Bounded here so an obvious unit
# mix-up (15 for "15 %") is a 422 about the field rather than a core message.
Fraction = Field(ge=0.0, le=1.0)


class AcceptanceSamplingRequest(_Request):
    """Judge a plan at the two quality levels it exists to discriminate."""

    plan: SamplingPlanIn
    aql: float = Fraction
    ltpd: float = Fraction
    model: SamplingModel = "binomial"


class OCCurveRequest(_Request):
    """The plan's OC curve. Omit the grid and the core derives one."""

    plan: SamplingPlanIn
    model: SamplingModel = "binomial"
    fraction_defective: list[float] | None = None


class SamplingPlanDesignRequest(_Request):
    """Two risk points in, the smallest plan meeting both out."""

    aql: float = Fraction
    ltpd: float = Fraction
    producer_risk: float = 0.05
    consumer_risk: float = 0.10
    model: SamplingModel = "binomial"
    lot_size: int | None = Field(default=None, ge=1)


class LotInspectionRequest(_Request):
    """Apply a plan to one observed sample. The result is a decision."""

    plan: SamplingPlanIn
    defectives: int = Field(ge=0)
    model: SamplingModel = "binomial"


class LotResultIn(_Request):
    """One lot's outcome on original inspection.

    ``accepted_at_tighter_aql`` answers the switching score's harder question
    (ISO 2859-1 clause 9.3.3.2). Omit it and the lot is scored on the
    conservative ``Ac <= 1`` rule, which is what a caller without the standard's
    master table can honestly supply.
    """

    accepted: bool
    accepted_at_tighter_aql: bool | None = None


class SwitchingRulesIn(_Request):
    """The thresholds. Defaults are ISO 2859-1:1999's."""

    tighten_on_non_acceptable: int = Field(default=2, ge=1)
    within_consecutive_lots: int = Field(default=5, ge=1)
    relax_after_consecutive_acceptable: int = Field(default=5, ge=1)
    discontinue_on_non_accepted: int = Field(default=5, ge=1)
    reduce_at_switching_score: int = Field(default=30, ge=1)


class SwitchingSchemeRequest(_Request):
    """A series of lots, in the order they were presented.

    ``start`` accepts ``"discontinued"`` only so that the core can reject it
    with its own message: a series cannot begin in a state that is an outcome of
    the rules.
    """

    lots: list[LotResultIn] = Field(min_length=1)
    start: InspectionSeverity = "normal"
    reduced_inspection_authorised: bool = False
    rules: SwitchingRulesIn | None = None
