"""Stability: does the measurement system hold still over time?

Bias and linearity are snapshots. Stability is the movie: measure the *same*
master part again and again over days or weeks and watch whether the readings
stay put. It is not new statistics -- it is a control chart on a master.

Measure the master once per time point and the readings are individuals (an I-MR
chart); measure it several times per point and they are subgroups (an X-bar & R
chart). Either way the verdict is the control chart's: the measurement system is
stable exactly when the chart is in control. An out-of-control point is the gage
drifting, not the part -- the part's true value never changed.

This is a thin, deliberately honest wrapper over :func:`~capstat_core.i_mr_chart`
and :func:`~capstat_core.xbar_r_chart`; those carry the reference-validated
limits. What it adds is the framing: a single ``stable`` verdict and a warning
that reads the out-of-control points as instability of the *gage*.

References
----------
AIAG. *Measurement Systems Analysis (MSA)*, 4th ed., 2010, ch. II sec. C
    (Stability) and ch. III sec. B.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from capstat_core.caveats import Caveat
from capstat_core.control_charts import ChartPair, i_mr_chart, xbar_r_chart

__all__ = [
    "StabilityReport",
    "stability",
]


@dataclass(frozen=True, slots=True)
class StabilityReport:
    """A stability study: the control chart of a master part, framed as a verdict.

    Everything quantitative lives on ``chart`` (the same :class:`ChartPair` the
    control-chart functions return). ``stable`` is its in-control status, read as
    a statement about the measurement system.
    """

    chart: ChartPair
    warnings: tuple[Caveat, ...]

    @property
    def stable(self) -> bool:
        return self.chart.in_control


def stability(measurements: npt.ArrayLike) -> StabilityReport:
    """Stability study: a control chart on repeated readings of one master.

    Parameters
    ----------
    measurements
        Time-ordered readings of a single master part. A 1-D sequence is treated
        as individuals (I-MR); a 2-D sequence is treated as subgroups over time,
        one row per time point (X-bar & R).

    Raises
    ------
    ValueError
        If the data is neither 1-D nor 2-D, or the underlying control chart
        rejects it (too few points, non-finite values).
    """
    arr = np.asarray(measurements, dtype=np.float64)
    if arr.ndim == 1:
        chart = i_mr_chart(arr)
    elif arr.ndim == 2:
        chart = xbar_r_chart(arr)
    else:
        raise ValueError(
            f"expected 1-D (individuals) or 2-D (subgroups over time) data, "
            f"got {arr.ndim} dimensions"
        )

    warnings: list[Caveat] = []
    if not chart.in_control:
        out = len(chart.location.violations) + len(chart.dispersion.violations)
        warnings.append(
            Caveat(
                "stability.not-stable",
                f"the measurement system is not stable: {out} out-of-control "
                "point(s) on the master's control chart -- the gage drifted, the "
                "part did not",
            )
        )

    return StabilityReport(chart=chart, warnings=tuple(warnings))
