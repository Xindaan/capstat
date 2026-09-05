"""Bias: is the gage reading high or low against a known reference?

Repeatability (Gage R&R) asks whether a measurement system is *consistent*. Bias
asks whether it is *right*: measure a part whose true value is known -- a
calibrated master or reference standard -- several times, and see whether the
average lands on that value.

    bias = mean(measurements) - reference

A non-zero bias is expected from noise alone, so the question is whether it is
*significantly* non-zero. This is a one-sample t-test of the measurements
against the reference::

    t = bias / (s / sqrt(n))          df = n - 1

with ``s`` the repeatability standard deviation. Equivalently, build a
confidence interval for the bias and ask whether it straddles zero -- AIAG uses
exactly this, and the two verdicts always agree. capstat reports both.

The verdict here is deliberately CI-based rather than p-based, because it stays
meaningful in the degenerate case (every reading identical, zero repeatability),
where the t-statistic is not defined but "the interval is a point, and it is not
zero" still is.

References
----------
AIAG. *Measurement Systems Analysis (MSA)*, 4th ed., 2010, ch. III sec. B
    (Bias -- independent sample method).
NIST/SEMATECH e-Handbook of Statistical Methods, section 2.4 (calibration and
    the one-sample t-test).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy.typing as npt
from scipy import stats

from capstat_core._validation import as_sample
from capstat_core.caveats import Caveat
from capstat_core.descriptive import mean as _mean
from capstat_core.descriptive import std_dev

__all__ = [
    "BiasReport",
    "bias",
]


@dataclass(frozen=True, slots=True)
class BiasReport:
    """A bias study: the offset from a reference, and whether it is real.

    ``ci_lower``/``ci_upper`` bound the *bias* (not the mean). The system is
    called biased when that interval does not contain zero.
    """

    n: int
    reference: float
    mean: float
    bias: float
    repeatability: float
    std_error: float
    t_statistic: float
    p_value: float
    alpha: float
    ci_lower: float
    ci_upper: float
    warnings: tuple[Caveat, ...]

    @property
    def bias_significant(self) -> bool:
        """True when the confidence interval for the bias excludes zero."""
        return not (self.ci_lower <= 0.0 <= self.ci_upper)


def bias(
    measurements: npt.ArrayLike,
    reference: float,
    *,
    alpha: float = 0.05,
) -> BiasReport:
    """Bias study by the independent-sample method.

    Parameters
    ----------
    measurements
        Repeated readings of one part. At least two, so repeatability is
        defined.
    reference
        The part's known/calibrated value.
    alpha
        Significance level for the test and the ``1 - alpha`` interval.

    Raises
    ------
    ValueError
        If fewer than two measurements are given, the data is non-finite, or
        ``alpha`` is not in ``(0, 1)``.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")

    x = as_sample(measurements, minimum=2)
    n = int(x.size)
    df = n - 1
    x_bar = _mean(x)
    bias_value = x_bar - reference
    repeatability = std_dev(x, ddof=1)
    std_error = repeatability / math.sqrt(n)

    warnings: list[Caveat] = []

    if std_error > 0.0:
        t_statistic = bias_value / std_error
        p_value = float(2.0 * stats.t.sf(abs(t_statistic), df))
    else:
        # Every reading identical: the t-statistic is undefined. The interval
        # collapses to the bias itself, which still answers the question.
        t_statistic = (
            math.copysign(math.inf, bias_value) if bias_value != 0.0 else math.nan
        )
        p_value = 0.0 if bias_value != 0.0 else math.nan
        warnings.append(
            Caveat(
                "bias.degenerate-t-test",
                "every measurement is identical (zero repeatability); the t-test is "
                "degenerate and the verdict rests on the bias alone",
            )
        )

    t_crit = float(stats.t.ppf(1.0 - alpha / 2.0, df))
    half_width = t_crit * std_error
    ci_lower = bias_value - half_width
    ci_upper = bias_value + half_width

    if not (ci_lower <= 0.0 <= ci_upper):
        direction = "high" if bias_value > 0.0 else "low"
        warnings.append(
            Caveat(
                "bias.significant",
                f"the measurement system is biased by {bias_value:.4g} (reads "
                f"{direction}); zero is outside the {1 - alpha:.0%} interval",
            )
        )

    return BiasReport(
        n=n,
        reference=reference,
        mean=x_bar,
        bias=bias_value,
        repeatability=repeatability,
        std_error=std_error,
        t_statistic=t_statistic,
        p_value=p_value,
        alpha=alpha,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        warnings=tuple(warnings),
    )
