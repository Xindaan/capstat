"""Linearity: does the bias stay the same across the operating range?

Bias answers "is the gage right *here*?" for a single reference. Linearity asks
whether it is right *everywhere*: measure several masters spanning the range,
find the bias at each, and see whether that bias drifts as the value grows.

The bias of every individual reading is regressed on the reference value::

    bias_ij = a * reference_i + b + error

A non-zero slope ``a`` means the bias changes with the measured value -- the gage
stretches or compresses the scale. AIAG summarises this as::

    %linearity = |a| * 100

and, given a process variation, an absolute ``linearity = |a| * process_variation``.
The slope's significance is a t-test with ``N - 2`` degrees of freedom.

The regression is fit from the individual readings, not the per-part averages,
so the residual scatter (repeatability) sizes the standard errors correctly. On
a balanced study the slope and intercept are identical either way; the
degrees of freedom are not.

References
----------
AIAG. *Measurement Systems Analysis (MSA)*, 4th ed., 2010, ch. III sec. B
    (Linearity).
NIST/SEMATECH e-Handbook of Statistical Methods, section 4.5 (linear regression
    and the t-test on the slope).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy import stats

from capstat_core._validation import as_sample

__all__ = [
    "LinearityReport",
    "linearity",
]


@dataclass(frozen=True, slots=True)
class LinearityReport:
    """A linearity study: the bias-vs-reference line and what it means.

    A significant non-zero ``slope`` is the finding of interest -- it says the
    bias is not constant across the range. ``percent_linearity`` is AIAG's
    headline figure; ``linearity`` is its absolute form, present only when a
    ``process_variation`` was supplied.
    """

    n: int
    n_parts: int
    slope: float
    intercept: float
    r_squared: float
    slope_std_error: float
    slope_t_statistic: float
    slope_p_value: float
    alpha: float
    percent_linearity: float
    process_variation: float | None
    linearity: float | None
    references: tuple[float, ...]
    part_mean_biases: tuple[float, ...]
    warnings: tuple[str, ...]

    @property
    def linearity_significant(self) -> bool:
        """True when the slope differs significantly from zero."""
        return self.slope_p_value < self.alpha


def linearity(
    references: Sequence[float],
    measurements: Sequence[npt.ArrayLike],
    *,
    process_variation: float | None = None,
    alpha: float = 0.05,
) -> LinearityReport:
    """Gage linearity study.

    Parameters
    ----------
    references
        The known value of each master part; at least two, and not all equal.
    measurements
        Repeated readings of each master, aligned with ``references``.
    process_variation
        The study's process variation (e.g. ``6 * sigma`` from a capability or
        Gage R&R study). Only the absolute ``linearity`` needs it; the
        percentage does not.
    alpha
        Significance level for the slope's t-test.

    Raises
    ------
    ValueError
        If fewer than two parts are given, the two sequences differ in length,
        the references are all equal, there are fewer than three readings in
        total, any data is non-finite, or ``alpha`` is not in ``(0, 1)``.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")
    if len(references) != len(measurements):
        raise ValueError(
            f"references ({len(references)}) and measurements "
            f"({len(measurements)}) must have the same length"
        )
    if len(references) < 2:
        raise ValueError(f"need at least 2 reference parts, got {len(references)}")

    refs = np.asarray(references, dtype=np.float64)
    if not np.all(np.isfinite(refs)):
        raise ValueError("references contain NaN or infinite values")
    if np.ptp(refs) == 0.0:
        raise ValueError("references are all equal; a slope is undefined")

    xs: list[float] = []
    ys: list[float] = []
    part_mean_biases: list[float] = []
    for reference, raw in zip(refs, measurements, strict=True):
        sample = as_sample(raw, minimum=1)
        biases = sample - reference
        xs.extend([float(reference)] * sample.size)
        ys.extend(float(b) for b in biases)
        part_mean_biases.append(float(biases.mean()))

    n = len(xs)
    if n < 3:
        raise ValueError(f"need at least 3 readings in total for a fit, got {n}")

    x = np.asarray(xs)
    y = np.asarray(ys)
    x_mean = float(x.mean())
    y_mean = float(y.mean())
    s_xx = float(((x - x_mean) ** 2).sum())
    s_xy = float(((x - x_mean) * (y - y_mean)).sum())
    slope = s_xy / s_xx
    intercept = y_mean - slope * x_mean

    residuals = y - (slope * x + intercept)
    ss_res = float((residuals**2).sum())
    ss_tot = float(((y - y_mean) ** 2).sum())
    df = n - 2

    warnings: list[str] = []

    # r^2 is the fraction of bias variation the line explains; undefined when the
    # bias never varies (a perfectly flat, zero-scatter study).
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else math.nan

    # df >= 1 always: n >= 3 is enforced above.
    residual_std_error = math.sqrt(ss_res / df)
    slope_std_error = residual_std_error / math.sqrt(s_xx)
    if slope_std_error > 0.0:
        slope_t = slope / slope_std_error
        slope_p = float(2.0 * stats.t.sf(abs(slope_t), df))
    else:
        # A perfect fit (no residual scatter): the slope is exact.
        slope_t = math.copysign(math.inf, slope) if slope != 0.0 else math.nan
        slope_p = 0.0 if slope != 0.0 else math.nan
        warnings.append(
            "the readings fall exactly on a line (no residual scatter); the "
            "slope test is degenerate"
        )

    percent_linearity = abs(slope) * 100.0
    absolute_linearity = (
        abs(slope) * process_variation if process_variation is not None else None
    )

    if slope_p < alpha:
        warnings.append(
            f"bias changes across the range (slope {slope:.4g}, p = {slope_p:.3g}); "
            "the measurement system is not linear"
        )

    return LinearityReport(
        n=n,
        n_parts=len(references),
        slope=slope,
        intercept=intercept,
        r_squared=r_squared,
        slope_std_error=slope_std_error,
        slope_t_statistic=slope_t,
        slope_p_value=slope_p,
        alpha=alpha,
        percent_linearity=percent_linearity,
        process_variation=process_variation,
        linearity=absolute_linearity,
        references=tuple(float(r) for r in refs),
        part_mean_biases=tuple(part_mean_biases),
        warnings=tuple(warnings),
    )
