"""EWMA and CUSUM charts: the charts that see what Shewhart misses.

A Shewhart chart looks at one point at a time, so it is excellent at catching a
large sudden jump and close to blind to a small sustained drift. A shift of one
sigma takes an X-bar chart about 44 subgroups to detect on average -- by which
time a great deal of product has been made. EWMA and CUSUM accumulate evidence
across points, and detect the same shift in roughly 10.

The price is memory: both charts carry the past forward, so a signal says
"something changed recently", not "this point is bad".

Estimating sigma is where these charts are usually broken
---------------------------------------------------------
Both need a sigma. The obvious choice -- the standard deviation of all the data
-- is a trap: if the data contain the very shift you are looking for, that shift
inflates sigma, which widens the limits, which hides the shift. The chart
politely reports that everything is fine.

So capstat estimates sigma from the *moving range* by default, which measures
only point-to-point variation and is therefore largely immune to a sustained
level change. If you have a known in-control sigma from a stable period, pass it
explicitly; that is better still, and the chart says so when you do not.

References
----------
Roberts, S. W. (1959). Control chart tests based on geometric moving averages.
    *Technometrics*, 1(3), 239-250. (EWMA.)
Page, E. S. (1954). Continuous inspection schemes. *Biometrika*, 41(1/2),
    100-115. (CUSUM.)
Montgomery, D. C. *Introduction to Statistical Quality Control*, ch. 9.
NIST/SEMATECH e-Handbook of Statistical Methods, sections 6.3.2.3 (CUSUM) and
    6.3.2.4 (EWMA).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from capstat_core._validation import as_sample
from capstat_core.constants import d2

__all__ = [
    "CusumChart",
    "EwmaChart",
    "cusum_chart",
    "ewma_chart",
]


def _moving_range_sigma(values: npt.NDArray[np.float64]) -> float:
    """Short-term sigma from the moving range.

    Resistant to a sustained level shift in a way the overall standard deviation
    is not -- which is the whole point, since a sustained shift is what these
    charts exist to find.
    """
    return float(np.abs(np.diff(values)).mean()) / d2(2)


def _resolve(
    values: npt.NDArray[np.float64],
    target: float | None,
    sigma: float | None,
) -> tuple[float, float, list[str]]:
    warnings: list[str] = []

    if target is None:
        target = float(values.mean())
        warnings.append(
            "no target was given, so the mean of these data was used. If the data "
            "already contain the shift you are looking for, that shift has pulled "
            "the centre line towards it and the chart is less sensitive than it "
            "looks. A target from a known in-control period is better."
        )

    if sigma is None:
        sigma = _moving_range_sigma(values)
        warnings.append(
            "no sigma was given, so it was estimated from the moving range of "
            "these data. That is the safe default -- the overall standard "
            "deviation would absorb any sustained shift and hide it -- but a "
            "sigma from a known in-control period is better still."
        )
    if sigma <= 0.0:
        raise ValueError(f"sigma must be strictly positive, got {sigma}")

    return target, sigma, warnings


@dataclass(frozen=True, slots=True)
class EwmaChart:
    """An EWMA chart.

    ``points`` are the EWMA statistics ``z_i = lambda*x_i + (1-lambda)*z_{i-1}``,
    started at ``z_0 = target``.

    ``upper`` and ``lower`` are per-point, because the limits are *not* constant:
    the variance of ``z_i`` grows from nearly zero towards its steady state, so
    the correct limits widen with i::

        sigma_z(i) = sigma * sqrt( lambda/(2-lambda) * (1 - (1-lambda)^(2i)) )

    Using the steady-state limits everywhere -- as many textbooks and the NIST
    e-Handbook do -- makes the first few limits too wide, and an early shift can
    slip through. At i = 1 with lambda = 0.3 the steady-state limit is 40 % wider
    than the correct one. ``steady_state_limits`` is exposed so that published
    examples can still be reproduced.
    """

    lmbda: float
    L: float
    target: float
    sigma: float
    points: tuple[float, ...]
    upper: tuple[float, ...]
    lower: tuple[float, ...]
    steady_state_limits: tuple[float, float]
    violations: tuple[int, ...]
    warnings: tuple[str, ...]

    @property
    def in_control(self) -> bool:
        return not self.violations


def ewma_chart(
    data: npt.ArrayLike,
    *,
    target: float | None = None,
    sigma: float | None = None,
    lmbda: float = 0.2,
    L: float = 3.0,
    time_varying_limits: bool = True,
) -> EwmaChart:
    """Exponentially weighted moving average chart.

    Parameters
    ----------
    lmbda:
        The weight on the newest observation, in ``(0, 1]``. Small values give a
        long memory and detect small shifts; ``lmbda = 1`` reduces the chart to a
        Shewhart individuals chart, which is the sanity check that the recursion
        is right. Montgomery's usual pairing is ``lmbda = 0.1, L = 2.7``.
    L:
        Limit width in sigma units.
    time_varying_limits:
        ``True`` (default) uses the exact per-point limits. ``False`` uses the
        steady-state width everywhere, which is what the NIST e-Handbook example
        does -- convenient for reproducing published tables, but too wide at the
        start.

    Raises
    ------
    ValueError
        If ``lmbda`` is outside ``(0, 1]``, if ``L`` is not positive, or if fewer
        than two observations are given.
    """
    if not 0.0 < lmbda <= 1.0:
        raise ValueError(f"lmbda must be in (0, 1], got {lmbda}")
    if L <= 0.0:
        raise ValueError(f"L must be strictly positive, got {L}")

    values = as_sample(data, minimum=2)
    target, sigma, warnings = _resolve(values, target, sigma)

    statistics: list[float] = []
    z = target
    for value in values:
        z = lmbda * float(value) + (1.0 - lmbda) * z
        statistics.append(z)

    asymptotic = sigma * math.sqrt(lmbda / (2.0 - lmbda))
    steady = (target - L * asymptotic, target + L * asymptotic)

    uppers: list[float] = []
    lowers: list[float] = []
    for i in range(1, values.size + 1):
        if time_varying_limits:
            width = asymptotic * math.sqrt(1.0 - (1.0 - lmbda) ** (2 * i))
        else:
            width = asymptotic
        uppers.append(target + L * width)
        lowers.append(target - L * width)

    violations = tuple(
        i
        for i, (z_i, lo, hi) in enumerate(zip(statistics, lowers, uppers, strict=True))
        if z_i < lo or z_i > hi
    )

    if not time_varying_limits:
        warnings.append(
            "steady-state limits were used for every point. The early limits are "
            "therefore too wide and a shift present at the start of the series can "
            "be missed. This mode exists to reproduce published examples."
        )

    return EwmaChart(
        lmbda=lmbda,
        L=L,
        target=target,
        sigma=sigma,
        points=tuple(statistics),
        upper=tuple(uppers),
        lower=tuple(lowers),
        steady_state_limits=steady,
        violations=violations,
        warnings=tuple(warnings),
    )


@dataclass(frozen=True, slots=True)
class CusumChart:
    """A tabular CUSUM chart.

    Two one-sided cumulative sums, each accumulating only the deviation that
    exceeds a slack ``k``::

        S_hi(i) = max(0, S_hi(i-1) + x_i - target - K)
        S_lo(i) = max(0, S_lo(i-1) + target - K - x_i)

    A signal is raised when either exceeds the decision interval ``H``. The slack
    is what makes the chart ignore ordinary noise while still accumulating a
    persistent bias: only the part of a deviation beyond ``K`` is banked.

    ``k`` and ``h`` are in sigma units (the design convention); ``K`` and ``H``
    are the same quantities in the data's own units.
    """

    target: float
    sigma: float
    k: float
    h: float
    K: float
    H: float
    upper: tuple[float, ...]
    lower: tuple[float, ...]
    violations: tuple[int, ...]
    warnings: tuple[str, ...]

    @property
    def in_control(self) -> bool:
        return not self.violations


def cusum_chart(
    data: npt.ArrayLike,
    *,
    target: float | None = None,
    sigma: float | None = None,
    k: float = 0.5,
    h: float = 5.0,
) -> CusumChart:
    """Tabular CUSUM chart.

    Parameters
    ----------
    k:
        Slack, in sigma units. The standard choice is half the shift you want to
        detect: ``k = 0.5`` is tuned for a one-sigma shift, which is the usual
        design. Larger ``k`` ignores more noise but detects small shifts slower.
    h:
        Decision interval, in sigma units. The classic ``k = 0.5, h = 5`` pairing
        gives an in-control ARL of about 465 -- roughly comparable to a Shewhart
        chart's 370 -- while detecting a one-sigma shift in about 10 points
        instead of 44.

    Raises
    ------
    ValueError
        If ``k`` or ``h`` is not strictly positive, or fewer than two
        observations are given.
    """
    if k <= 0.0:
        raise ValueError(f"k must be strictly positive, got {k}")
    if h <= 0.0:
        raise ValueError(f"h must be strictly positive, got {h}")

    values = as_sample(data, minimum=2)
    target, sigma, warnings = _resolve(values, target, sigma)

    slack = k * sigma
    interval = h * sigma

    highs: list[float] = []
    lows: list[float] = []
    high = low = 0.0
    for value in values:
        x = float(value)
        high = max(0.0, high + x - target - slack)
        low = max(0.0, low + target - slack - x)
        highs.append(high)
        lows.append(low)

    violations = tuple(
        i
        for i, (hi, lo) in enumerate(zip(highs, lows, strict=True))
        if hi > interval or lo > interval
    )

    return CusumChart(
        target=target,
        sigma=sigma,
        k=k,
        h=h,
        K=slack,
        H=interval,
        upper=tuple(highs),
        lower=tuple(lows),
        violations=violations,
        warnings=tuple(warnings),
    )
