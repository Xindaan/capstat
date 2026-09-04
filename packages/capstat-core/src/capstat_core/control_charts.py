"""Shewhart control charts: I-MR, X-bar-R, X-bar-S.

A control chart asks one question: is this process doing anything other than
what it did yesterday? The limits are *not* specification limits. They are the
voice of the process, computed from its own variation, and a point outside them
means something changed -- not that a part is bad.

Read the dispersion chart first
-------------------------------
Every pair here has a location chart (X-bar, or the individuals chart) and a
dispersion chart (R, s, or the moving range). They are not equals. The location
chart's limits are computed *from* the dispersion estimate: ``xbarbar +/- A2 *
Rbar``. If the spread is itself out of control, ``Rbar`` is an average of
incomparable things, the limits derived from it are meaningless, and any verdict
about the location chart is worthless. So the dispersion chart is judged first,
and :attr:`ChartPair.in_control` is false if *either* chart signals. The pair
warns explicitly when the dispersion chart is the one out of control.

These are Phase I (trial) limits
--------------------------------
The limits are estimated from the very data being plotted. That is what you do
when establishing a chart, but it means a large excursion inflates the limits
that are supposed to catch it. Once the process is shown to be stable, freeze
the limits and use them to judge *future* data (Phase II). capstat computes
Phase I limits; it does not pretend they are Phase II limits.

What a violation here is, and is not
-----------------------------------
:attr:`ControlChart.violations` means one thing only: points beyond the control
limits. The run-based rules that catch drifts and trends never crossing a limit
live in :mod:`capstat_core.rules` and are applied *to* a chart, deriving their
zones from its own limits. Keeping them apart is deliberate -- it is what stops
the same signal being reported twice under two names, and it leaves this
attribute meaning what it has always meant.

References
----------
Montgomery, D. C. *Introduction to Statistical Quality Control*, ch. 6.
NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from capstat_core._validation import as_sample
from capstat_core.constants import A2, A3, B3, B4, D3, D4, MAX_SUBGROUP_SIZE, c4, d2

__all__ = [
    "ChartPair",
    "ControlChart",
    "ControlLimits",
    "i_mr_chart",
    "xbar_r_chart",
    "xbar_s_chart",
]


@dataclass(frozen=True, slots=True)
class ControlLimits:
    """Centre line and three-sigma limits of one chart."""

    center: float
    lower: float
    upper: float


@dataclass(frozen=True, slots=True)
class ControlChart:
    """One chart: the plotted points, its limits, and which points signal."""

    name: str
    points: tuple[float, ...]
    limits: ControlLimits
    violations: tuple[int, ...]

    @property
    def in_control(self) -> bool:
        """True when no point lies beyond a control limit."""
        return not self.violations


def _violations(
    points: npt.NDArray[np.float64], limits: ControlLimits
) -> tuple[int, ...]:
    beyond = (points < limits.lower) | (points > limits.upper)
    return tuple(int(i) for i in np.flatnonzero(beyond))


def _chart(
    name: str, points: npt.NDArray[np.float64], limits: ControlLimits
) -> ControlChart:
    return ControlChart(
        name=name,
        points=tuple(float(p) for p in points),
        limits=limits,
        violations=_violations(points, limits),
    )


@dataclass(frozen=True, slots=True)
class ChartPair:
    """A location chart and its dispersion chart, judged together.

    ``in_control`` is the AND of both charts. It is deliberately not just the
    location chart: a process whose *spread* is wandering is out of control even
    if every average happens to land inside limits that its own wandering spread
    inflated.
    """

    location: ControlChart
    dispersion: ControlChart
    sigma_within: float
    subgroup_size: int
    subgroups: int
    warnings: tuple[str, ...]

    @property
    def in_control(self) -> bool:
        return self.location.in_control and self.dispersion.in_control


def _as_subgroups(x: npt.ArrayLike) -> npt.NDArray[np.float64]:
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(
            f"expected 2-D data (subgroups x size), got {arr.ndim} dimension(s)"
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError("data contains NaN or infinite values")
    k, n = arr.shape
    if k < 2:
        raise ValueError(f"need at least 2 subgroups, got {k}")
    if n < 2:
        raise ValueError(
            f"subgroups must hold at least 2 observations, got {n}. For individual "
            f"measurements use i_mr_chart()."
        )
    return arr


def _pair_warnings(
    *,
    location: ControlChart,
    dispersion: ControlChart,
    subgroups: int,
    lower_limit_is_floored: bool,
    extra: tuple[str, ...] = (),
) -> tuple[str, ...]:
    messages: list[str] = []

    if not dispersion.in_control:
        messages.append(
            f"the {dispersion.name} chart is out of control at "
            f"{list(dispersion.violations)}. Judge this first: the "
            f"{location.name} limits are computed from the dispersion estimate, "
            f"so while the spread is unstable those limits -- and any verdict "
            f"drawn from them -- mean nothing. Fix the spread, then re-chart."
        )
    elif not location.in_control:
        messages.append(
            f"the {location.name} chart is out of control at "
            f"{list(location.violations)}, while the spread is stable. The "
            f"process centre has moved."
        )

    if lower_limit_is_floored:
        messages.append(
            "the lower limit of the dispersion chart is zero (the unclamped value "
            "is negative for a subgroup this small). The chart therefore cannot "
            "signal an *improvement* in spread -- there is no lower limit to "
            "cross. Larger subgroups would restore that ability."
        )

    if subgroups < 20:
        messages.append(
            f"only {subgroups} subgroups: these are Phase I trial limits estimated "
            f"from the data being plotted, and with this few they are unstable. "
            f"Montgomery recommends 20-25 before trusting them."
        )

    messages.extend(extra)
    return tuple(messages)


def xbar_r_chart(subgroups: npt.ArrayLike) -> ChartPair:
    """X-bar and R charts: subgroup averages, with spread from the range.

    ``sigma_within = Rbar / d2(n)``. Limits::

        X-bar:  xbarbar +/- A2 * Rbar        (equivalently +/- 3 sigma / sqrt(n))
        R:      D3 * Rbar  ..  D4 * Rbar

    The range uses only the largest and smallest value of each subgroup, so it
    discards information and loses efficiency as n grows. Beyond n = 10, prefer
    :func:`xbar_s_chart`.
    """
    groups = _as_subgroups(subgroups)
    k, n = groups.shape

    if n > MAX_SUBGROUP_SIZE:
        raise ValueError(
            f"subgroup size {n} exceeds {MAX_SUBGROUP_SIZE}; the range is a poor "
            f"scale estimator that large. Use xbar_s_chart()."
        )

    means = groups.mean(axis=1)
    ranges = groups.max(axis=1) - groups.min(axis=1)

    grand_mean = float(means.mean())
    rbar = float(ranges.mean())
    sigma_within = rbar / d2(n)

    location = _chart(
        "X-bar",
        means,
        ControlLimits(
            center=grand_mean,
            lower=grand_mean - A2(n) * rbar,
            upper=grand_mean + A2(n) * rbar,
        ),
    )
    dispersion = _chart(
        "R",
        ranges,
        ControlLimits(center=rbar, lower=D3(n) * rbar, upper=D4(n) * rbar),
    )

    extra: tuple[str, ...] = ()
    if n > 10:
        extra = (
            f"subgroup size {n}: the range is an inefficient scale estimator this "
            f"large, because it uses only two of the {n} observations. Prefer "
            f"xbar_s_chart().",
        )

    return ChartPair(
        location=location,
        dispersion=dispersion,
        sigma_within=sigma_within,
        subgroup_size=n,
        subgroups=k,
        warnings=_pair_warnings(
            location=location,
            dispersion=dispersion,
            subgroups=k,
            lower_limit_is_floored=D3(n) == 0.0,
            extra=extra,
        ),
    )


def xbar_s_chart(subgroups: npt.ArrayLike) -> ChartPair:
    """X-bar and s charts: subgroup averages, with spread from the standard
    deviation.

    ``sigma_within = sbar / c4(n)``. Limits::

        X-bar:  xbarbar +/- A3 * sbar
        s:      B3 * sbar  ..  B4 * sbar

    Uses every observation in each subgroup rather than just two, so it is the
    better choice whenever the subgroups are big enough for it to matter.
    """
    groups = _as_subgroups(subgroups)
    k, n = groups.shape

    means = groups.mean(axis=1)
    sds = groups.std(axis=1, ddof=1)

    grand_mean = float(means.mean())
    sbar = float(sds.mean())
    sigma_within = sbar / c4(n)

    location = _chart(
        "X-bar",
        means,
        ControlLimits(
            center=grand_mean,
            lower=grand_mean - A3(n) * sbar,
            upper=grand_mean + A3(n) * sbar,
        ),
    )
    dispersion = _chart(
        "s",
        sds,
        ControlLimits(center=sbar, lower=B3(n) * sbar, upper=B4(n) * sbar),
    )

    return ChartPair(
        location=location,
        dispersion=dispersion,
        sigma_within=sigma_within,
        subgroup_size=n,
        subgroups=k,
        warnings=_pair_warnings(
            location=location,
            dispersion=dispersion,
            subgroups=k,
            lower_limit_is_floored=B3(n) == 0.0,
        ),
    )


def i_mr_chart(data: npt.ArrayLike) -> ChartPair:
    """Individuals and moving-range charts, for data that come one at a time.

    ``sigma_within = MRbar / d2(2)``, where the moving ranges are the absolute
    differences between consecutive observations. Limits::

        individuals:   xbar +/- E2 * MRbar   (E2 = 3 / d2(2) = 2.6587)
        moving range:  0  ..  D4(2) * MRbar

    The moving range is the *only* estimate of short-term variation available
    without subgroups, and it buys that at a price: it assumes the observations
    are in time order. Handed a shuffled sample, this function will return
    limits that look perfectly reasonable and mean nothing at all. capstat
    cannot detect that, so it says so, every time.
    """
    values = as_sample(data, minimum=2)
    n = values.size

    moving_ranges = np.abs(np.diff(values))
    mrbar = float(moving_ranges.mean())
    sigma_within = mrbar / d2(2)

    center = float(values.mean())
    spread = 3.0 * sigma_within  # == E2(2) * mrbar

    location = _chart(
        "individuals",
        values,
        ControlLimits(center=center, lower=center - spread, upper=center + spread),
    )
    dispersion = _chart(
        "moving range",
        moving_ranges,
        ControlLimits(center=mrbar, lower=D3(2) * mrbar, upper=D4(2) * mrbar),
    )

    warnings = _pair_warnings(
        location=location,
        dispersion=dispersion,
        subgroups=n,
        lower_limit_is_floored=D3(2) == 0.0,
        extra=(
            "individuals chart: the limits rest on the moving range, which assumes "
            "the data are in time order. If they are not, these limits are "
            "meaningless -- and nothing about them will look wrong.",
        ),
    )

    return ChartPair(
        location=location,
        dispersion=dispersion,
        sigma_within=sigma_within,
        subgroup_size=1,
        subgroups=n,
        warnings=warnings,
    )
