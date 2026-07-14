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
from capstat_core.constants import c4, d2
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
    "MAD_NORMAL_CONSISTENCY",
    "BoxCoxCapability",
    "CapabilityAnalysis",
    "CapabilityReport",
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
    "describe",
    "fit_distribution",
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
]

__version__ = "0.0.0"
