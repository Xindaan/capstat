"""capstat-core: reference-validated SPC, capability, and MSA statistics.

Every statistic exposed here is validated against published reference values;
see ``tests/references/`` for the sources and the certified numbers.

The public API is populated milestone by milestone (see TASK.md). Available
today: descriptive summary statistics, robust location/scale estimators, and
normality testing.
"""

from __future__ import annotations

from capstat_core.acceptance_sampling import (
    AOQLimit,
    LotDecision,
    OCCurve,
    SamplingPlan,
    SamplingPlanReport,
    aoq_limit,
    average_outgoing_quality,
    average_total_inspection,
    design_single_sampling_plan,
    evaluate_plan,
    inspect_lot,
    oc_curve,
    probability_of_acceptance,
    quality_for_acceptance,
)
from capstat_core.bias import (
    BiasReport,
    bias,
)
from capstat_core.capability import (
    CapabilityReport,
    capability,
)
from capstat_core.constants import A2, A3, B3, B4, D3, D4, E2, c4, d2, d2_star, d3
from capstat_core.control_charts import (
    ChartPair,
    ControlChart,
    ControlLimits,
    i_mr_chart,
    xbar_r_chart,
    xbar_s_chart,
)
from capstat_core.descriptive import (
    DescriptiveSummary,
    describe,
    kurtosis,
    lag1_autocorrelation,
    mean,
    skewness,
    std_dev,
    variance,
)
from capstat_core.gage_rr import (
    GageRRReport,
    gage_rr,
    gage_rr_range,
)
from capstat_core.linearity import (
    LinearityReport,
    linearity,
)
from capstat_core.nonnormal import (
    BoxCoxCapability,
    CapabilityAnalysis,
    DistributionFit,
    PercentileCapability,
    analyze_capability,
    box_cox_capability,
    fit_distribution,
    percentile_capability,
)
from capstat_core.normality import (
    NormalityAssessment,
    NormalityTestResult,
    anderson_darling,
    anderson_darling_pvalue,
    assess_normality,
    shapiro_wilk,
)
from capstat_core.robust import (
    MAD_NORMAL_CONSISTENCY,
    iqr,
    mad,
    median,
    trimmed_mean,
    winsorized_mean,
)
from capstat_core.rules import (
    NELSON_RULES,
    WESTERN_ELECTRIC_RULES,
    RuleViolation,
    nelson_rules,
    western_electric_rules,
)
from capstat_core.sampling_scheme import (
    InspectionSeverity,
    SchemeHistory,
    SchemeStep,
    SwitchingRules,
    apply_switching_rules,
)
from capstat_core.stability import (
    StabilityReport,
    stability,
)
from capstat_core.time_weighted import (
    CusumChart,
    EwmaChart,
    cusum_chart,
    ewma_chart,
)

__all__ = [
    "A2",
    "A3",
    "B3",
    "B4",
    "D3",
    "D4",
    "E2",
    "MAD_NORMAL_CONSISTENCY",
    "NELSON_RULES",
    "WESTERN_ELECTRIC_RULES",
    "AOQLimit",
    "BiasReport",
    "BoxCoxCapability",
    "CapabilityAnalysis",
    "CapabilityReport",
    "ChartPair",
    "ControlChart",
    "ControlLimits",
    "CusumChart",
    "DescriptiveSummary",
    "DistributionFit",
    "EwmaChart",
    "GageRRReport",
    "InspectionSeverity",
    "LinearityReport",
    "LotDecision",
    "NormalityAssessment",
    "NormalityTestResult",
    "OCCurve",
    "PercentileCapability",
    "RuleViolation",
    "SamplingPlan",
    "SamplingPlanReport",
    "SchemeHistory",
    "SchemeStep",
    "StabilityReport",
    "SwitchingRules",
    "__version__",
    "analyze_capability",
    "anderson_darling",
    "anderson_darling_pvalue",
    "aoq_limit",
    "apply_switching_rules",
    "assess_normality",
    "average_outgoing_quality",
    "average_total_inspection",
    "bias",
    "box_cox_capability",
    "c4",
    "capability",
    "cusum_chart",
    "d2",
    "d2_star",
    "d3",
    "describe",
    "design_single_sampling_plan",
    "evaluate_plan",
    "ewma_chart",
    "fit_distribution",
    "gage_rr",
    "gage_rr_range",
    "i_mr_chart",
    "inspect_lot",
    "iqr",
    "kurtosis",
    "lag1_autocorrelation",
    "linearity",
    "mad",
    "mean",
    "median",
    "nelson_rules",
    "oc_curve",
    "percentile_capability",
    "probability_of_acceptance",
    "quality_for_acceptance",
    "shapiro_wilk",
    "skewness",
    "stability",
    "std_dev",
    "trimmed_mean",
    "variance",
    "western_electric_rules",
    "winsorized_mean",
    "xbar_r_chart",
    "xbar_s_chart",
]

__version__ = "0.1.0"  # x-release-please-version
