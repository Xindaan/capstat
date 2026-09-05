"""Pydantic models mirroring the capstat-core dataclasses one-to-one.

These models are the API contract. Two properties of the core are deliberately
load-bearing and must survive serialisation intact:

* the ``warnings`` tuples -- the core says what the numbers cannot; a schema
  that dropped them would undo most of what the library is for;
* the nullable capability indices (``cp``, ``cpk`` ... ) -- ``None`` means
  "undefined for this spec", which is not the same as ``0.0``.

Faithfulness mechanism: every model uses ``from_attributes=True`` and is built
with ``Model.model_validate(core_obj)``. That reads fields *and* the core's
``@property`` outputs (``in_control``, ``stability_ratio``) by attribute, so
the derived values are not silently lost the way ``dataclasses.asdict`` loses
them.

Non-finite floats (a zero-variance sample yields ``nan`` skewness) are coerced
to ``null``: JSON has no ``NaN``/``Infinity`` and an invalid document would
break every client. The coercion is confined to the fields that can actually
be non-finite, via the ``SafeFloat`` alias.
"""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict


def _finite_or_none(value: object) -> object:
    """Map a non-finite float to ``None``; pass everything else through."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


# A float that becomes ``null`` when the core produces ``nan``/``inf``.
SafeFloat = Annotated[float | None, BeforeValidator(_finite_or_none)]


class _CoreModel(BaseModel):
    """Base for every mirror model: read core dataclasses by attribute."""

    model_config = ConfigDict(from_attributes=True)


class CaveatOut(_CoreModel):
    """One warning: the code a program branches on, the prose a person reads.

    The core's ``Caveat`` is a ``str`` subclass, so a Python caller still sees
    a sentence. Over HTTP that would flatten to a bare string and the code
    would be lost -- which is the half a client needs to react to a warning
    rather than merely display it (T-0074).
    """

    code: str
    message: str


def _as_caveat(value: object) -> object:
    """Split a core ``Caveat`` into its two halves.

    It arrives as a string, so pydantic would otherwise try to validate the
    sentence *as* the model. A plain string with no code is not expected -- the
    core has a test forbidding it -- and is passed through with an empty code
    rather than raising, because a 500 on an uncoded warning would hide the
    report a caller asked for behind a defect in its footnotes.
    """
    if isinstance(value, str):
        return {"code": getattr(value, "code", ""), "message": str(value)}
    return value


#: A warning as it crosses the wire.
CaveatField = Annotated[CaveatOut, BeforeValidator(_as_caveat)]


# ---------------------------------------------------------------------------
# normality.py
# ---------------------------------------------------------------------------


class NormalityTestResultOut(_CoreModel):
    test: str
    n: int
    statistic: SafeFloat
    p_value: float
    alpha: float
    normal: bool


class NormalityAssessmentOut(_CoreModel):
    n: int
    alpha: float
    anderson_darling: NormalityTestResultOut
    shapiro_wilk: NormalityTestResultOut
    lag1_autocorrelation: SafeFloat
    normal: bool
    warnings: list[CaveatField]
    recommendation: str


# ---------------------------------------------------------------------------
# descriptive.py
# ---------------------------------------------------------------------------


class DescriptiveSummaryOut(_CoreModel):
    n: int
    mean: float
    variance: float
    std_dev: float
    minimum: float
    maximum: float
    range: float
    median: float
    q1: float
    q3: float
    iqr: float
    skewness: SafeFloat
    kurtosis: SafeFloat
    lag1_autocorrelation: SafeFloat


# ---------------------------------------------------------------------------
# capability.py
# ---------------------------------------------------------------------------

WithinMethod = Literal["pooled", "rbar_d2", "sbar_c4", "moving_range"]


class CapabilityReportOut(_CoreModel):
    n: int
    subgroup_size: int
    subgroups: int
    mean: float
    sigma_within: float
    sigma_overall: float
    within_method: WithinMethod
    lsl: float | None
    usl: float | None
    target: float | None
    cp: float | None
    cpl: float | None
    cpu: float | None
    cpk: float | None
    cpm: float | None
    pp: float | None
    ppl: float | None
    ppu: float | None
    ppk: float | None
    normality: NormalityAssessmentOut | None
    warnings: list[CaveatField]
    # Derived property on the core dataclass; read via from_attributes.
    stability_ratio: SafeFloat


# ---------------------------------------------------------------------------
# control_charts.py
# ---------------------------------------------------------------------------


class ControlLimitsOut(_CoreModel):
    center: float
    lower: float
    upper: float


class ControlChartOut(_CoreModel):
    name: str
    points: list[float]
    limits: ControlLimitsOut
    violations: list[int]
    in_control: bool


Phase = Literal["I", "II"]


class ChartPairOut(_CoreModel):
    location: ControlChartOut
    dispersion: ControlChartOut
    sigma_within: float
    subgroup_size: int
    subgroups: int
    # "I" when the limits were estimated from the data plotted, "II" when they
    # came from a supplied baseline. The difference decides what a signal means.
    phase: Phase
    warnings: list[CaveatField]
    in_control: bool


# ---------------------------------------------------------------------------
# nonnormal.py
# ---------------------------------------------------------------------------


class DistributionFitOut(_CoreModel):
    name: str
    params: list[float]
    fit_score: SafeFloat


class PercentileCapabilityOut(_CoreModel):
    n: int
    distribution: str
    params: list[float]
    fit_score: SafeFloat
    lsl: float | None
    usl: float | None
    p_lower: float
    p_median: float
    p_upper: float
    pp: float | None
    ppl: float | None
    ppu: float | None
    ppk: float | None
    warnings: list[CaveatField]


class BoxCoxCapabilityOut(_CoreModel):
    lmbda: float
    n: int
    lsl: float | None
    usl: float | None
    target: float | None
    lsl_transformed: float | None
    usl_transformed: float | None
    target_transformed: float | None
    normality_after: NormalityAssessmentOut
    transform_successful: bool
    capability: CapabilityReportOut
    warnings: list[CaveatField]


CapabilityPath = Literal["normal", "box-cox", "percentile"]


class CapabilityAnalysisOut(_CoreModel):
    path: CapabilityPath
    rationale: str
    normality: NormalityAssessmentOut
    normal: CapabilityReportOut | None
    box_cox: BoxCoxCapabilityOut | None
    percentile: PercentileCapabilityOut | None
    pp: float | None
    ppk: float | None
    warnings: list[CaveatField]


# ---------------------------------------------------------------------------
# gage_rr.py
# ---------------------------------------------------------------------------

GageRRMethod = Literal["anova", "average_range"]
# Restated like every other literal in this module (see the module docstring):
# what is mirrored here is the *type*, three words. The boundaries that decide
# which word applies live only in the core -- that is the whole point of
# T-0058, and moving a number here would undo it.
GageRRVerdict = Literal["good", "marginal", "unacceptable"]


class GageRRReportOut(_CoreModel):
    method: GageRRMethod
    n_parts: int
    n_operators: int
    n_trials: int
    interaction_included: bool
    # None for the average-and-range method, which models no interaction.
    interaction_pvalue: float | None
    var_repeatability: float
    var_operator: float
    var_interaction: float
    var_part: float
    study_var_multiplier: float
    tolerance: float | None
    warnings: list[CaveatField]
    # Derived properties on the core dataclass; read via from_attributes. The
    # percentages are nan (-> null) when the sample has no variation at all.
    var_reproducibility: float
    var_gage_rr: float
    var_total: float
    pct_contribution_gage_rr: SafeFloat
    pct_contribution_repeatability: SafeFloat
    pct_contribution_reproducibility: SafeFloat
    pct_contribution_part: SafeFloat
    pct_study_var_gage_rr: SafeFloat
    pct_study_var_repeatability: SafeFloat
    pct_study_var_reproducibility: SafeFloat
    pct_study_var_part: SafeFloat
    pct_tolerance_gage_rr: float | None
    ndc: int | None
    # The AIAG band, stated by the core rather than re-thresholded by each
    # client. Null when there is no measurement variation to judge, which is not
    # the same as "good" (T-0058).
    verdict: GageRRVerdict | None
    ndc_adequate: bool | None


# ---------------------------------------------------------------------------
# bias.py / linearity.py / stability.py
# ---------------------------------------------------------------------------


class BiasReportOut(_CoreModel):
    n: int
    reference: float
    mean: float
    bias: float
    repeatability: float
    std_error: float
    # Undefined (inf/nan) when every reading is identical; the verdict below
    # still holds, because it comes from the interval, not the statistic.
    t_statistic: SafeFloat
    p_value: SafeFloat
    alpha: float
    ci_lower: float
    ci_upper: float
    warnings: list[CaveatField]
    bias_significant: bool


class LinearityReportOut(_CoreModel):
    n: int
    n_parts: int
    slope: float
    intercept: float
    # nan when the bias never varies; inf/nan when the fit is exact.
    r_squared: SafeFloat
    slope_std_error: float
    slope_t_statistic: SafeFloat
    slope_p_value: SafeFloat
    alpha: float
    percent_linearity: float
    process_variation: float | None
    linearity: float | None
    references: list[float]
    part_mean_biases: list[float]
    warnings: list[CaveatField]
    linearity_significant: bool


class StabilityReportOut(_CoreModel):
    chart: ChartPairOut
    warnings: list[CaveatField]
    stable: bool


# ---------------------------------------------------------------------------
# rules.py
# ---------------------------------------------------------------------------


class RuleViolationOut(_CoreModel):
    rule_set: str
    rule: int
    description: str
    point: int
    window: list[int]


# ---------------------------------------------------------------------------
# time_weighted.py
# ---------------------------------------------------------------------------


class EwmaChartOut(_CoreModel):
    lmbda: float
    L: float
    target: float
    sigma: float
    points: list[float]
    upper: list[float]
    lower: list[float]
    steady_state_limits: tuple[float, float]
    violations: list[int]
    warnings: list[CaveatField]
    in_control: bool


class CusumChartOut(_CoreModel):
    target: float
    sigma: float
    k: float
    h: float
    K: float
    H: float
    upper: list[float]
    lower: list[float]
    violations: list[int]
    warnings: list[CaveatField]
    in_control: bool


# ---------------------------------------------------------------------------
# acceptance_sampling.py
# ---------------------------------------------------------------------------

SamplingModel = Literal["binomial", "hypergeometric", "poisson"]


class SamplingPlanOut(_CoreModel):
    sample_size: int
    acceptance_number: int
    # Absent unless the caller is talking about one finite lot; the binomial OC
    # curve does not need it.
    lot_size: int | None
    # Derived property on the core dataclass; read via from_attributes.
    rejection_number: int


class AOQLimitOut(_CoreModel):
    aoql: float
    at_fraction_defective: float


class OCCurveOut(_CoreModel):
    plan: SamplingPlanOut
    model: SamplingModel
    fraction_defective: list[float]
    probability_accept: list[float]


class LotDecisionOut(_CoreModel):
    plan: SamplingPlanOut
    defectives: int
    accepted: bool
    sample_fraction_defective: float
    warnings: list[CaveatField]


class SamplingPlanReportOut(_CoreModel):
    plan: SamplingPlanOut
    model: SamplingModel
    aql: float
    ltpd: float
    producer_risk: float
    consumer_risk: float
    probability_accept_at_aql: float
    probability_accept_at_ltpd: float
    indifference_quality: float
    # ISO 2859-1's limiting quality: the quality the plan still accepts 10 % of
    # the time. Computed from the plan, never requested.
    limiting_quality: float
    # Both are None without a lot size: they describe rectifying inspection of
    # a finite lot, and "not applicable" is not the same as zero.
    aoql: AOQLimitOut | None
    ati_at_aql: float | None
    warnings: list[CaveatField]


# ---------------------------------------------------------------------------
# sampling_scheme.py
# ---------------------------------------------------------------------------

InspectionSeverity = Literal["normal", "tightened", "reduced", "discontinued"]


class SwitchingRulesOut(_CoreModel):
    tighten_on_non_acceptable: int
    within_consecutive_lots: int
    relax_after_consecutive_acceptable: int
    discontinue_on_non_accepted: int
    reduce_at_switching_score: int


class SchemeStepOut(_CoreModel):
    lot: int
    accepted: bool
    # The severity this lot was inspected under, and the one the next lot will
    # be. They differ exactly on the lots where a switch took effect.
    severity: InspectionSeverity
    severity_after: InspectionSeverity
    # None wherever the standard does not maintain the score -- anywhere but
    # original normal inspection. Not zero: absent.
    switching_score: int | None
    # Derived property on the core dataclass; read via from_attributes.
    switched: bool


class SchemeHistoryOut(_CoreModel):
    steps: list[SchemeStepOut]
    final_severity: InspectionSeverity
    rules: SwitchingRulesOut
    warnings: list[CaveatField]
