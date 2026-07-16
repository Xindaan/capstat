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
    warnings: list[str]
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
    warnings: list[str]
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


class ChartPairOut(_CoreModel):
    location: ControlChartOut
    dispersion: ControlChartOut
    sigma_within: float
    subgroup_size: int
    subgroups: int
    warnings: list[str]
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
    warnings: list[str]


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
    warnings: list[str]


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
    warnings: list[str]


# ---------------------------------------------------------------------------
# gage_rr.py
# ---------------------------------------------------------------------------

GageRRMethod = Literal["anova", "average_range"]


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
    warnings: list[str]
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
    warnings: list[str]
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
    warnings: list[str]
    linearity_significant: bool


class StabilityReportOut(_CoreModel):
    chart: ChartPairOut
    warnings: list[str]
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
    warnings: list[str]
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
    warnings: list[str]
    in_control: bool
