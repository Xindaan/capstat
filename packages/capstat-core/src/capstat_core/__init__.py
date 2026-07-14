"""capstat-core: reference-validated SPC, capability, and MSA statistics.

Every statistic exposed here is validated against published reference values;
see ``tests/references/`` for the sources and the certified numbers.

The public API is populated milestone by milestone (see TASK.md). Available
today: descriptive summary statistics, robust location/scale estimators, and
normality testing.
"""

from __future__ import annotations

from capstat_core.capability import (
    CapabilityReport,
    capability,
)
from capstat_core.constants import A2, A3, B3, B4, D3, D4, E2, c4, d2, d3
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

__all__ = [
    "A2",
    "A3",
    "B3",
    "B4",
    "D3",
    "D4",
    "E2",
    "MAD_NORMAL_CONSISTENCY",
    "BoxCoxCapability",
    "CapabilityAnalysis",
    "CapabilityReport",
    "ChartPair",
    "ControlChart",
    "ControlLimits",
    "DescriptiveSummary",
    "DistributionFit",
    "NormalityAssessment",
    "NormalityTestResult",
    "PercentileCapability",
    "__version__",
    "analyze_capability",
    "anderson_darling",
    "anderson_darling_pvalue",
    "assess_normality",
    "box_cox_capability",
    "c4",
    "capability",
    "d2",
    "d3",
    "describe",
    "fit_distribution",
    "i_mr_chart",
    "iqr",
    "kurtosis",
    "lag1_autocorrelation",
    "mad",
    "mean",
    "median",
    "percentile_capability",
    "shapiro_wilk",
    "skewness",
    "std_dev",
    "trimmed_mean",
    "variance",
    "winsorized_mean",
    "xbar_r_chart",
    "xbar_s_chart",
]

__version__ = "0.0.0"
