"""capstat-core: reference-validated SPC, capability, and MSA statistics.

Every statistic exposed here is validated against published reference values;
see ``tests/references/`` for the sources and the certified numbers.

The public API is populated milestone by milestone (see TASK.md). Available
today: descriptive summary statistics and robust location/scale estimators.
"""

from __future__ import annotations

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
    "DescriptiveSummary",
    "__version__",
    "describe",
    "iqr",
    "kurtosis",
    "lag1_autocorrelation",
    "mad",
    "mean",
    "median",
    "skewness",
    "std_dev",
    "trimmed_mean",
    "variance",
    "winsorized_mean",
]

__version__ = "0.0.0"
