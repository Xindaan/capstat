"""Stability study.

Stability is a control chart on a master part, so the numbers are the
control-chart numbers -- validated against NIST in ``test_control_charts.py``.
These tests pin the wrapper: that it dispatches individuals vs subgroups to the
right chart, that its verdict is the chart's in-control status, and that it
reframes an out-of-control master as gage instability.
"""

from __future__ import annotations

import numpy as np
import pytest
from capstat_core import StabilityReport, i_mr_chart, stability, xbar_r_chart


def _steady(n: int = 30) -> np.ndarray:
    # Deterministic and gentle: a smooth low-amplitude wave stays well inside the
    # control limits, so a genuinely stable master never false-alarms.
    return 10.0 + 0.05 * np.sin(np.arange(n))


def test_steady_master_is_stable() -> None:
    report = stability(_steady())
    assert report.stable is True
    assert report.warnings == ()


def test_drifting_master_is_flagged_unstable() -> None:
    data = _steady().copy()
    data[-1] = 12.0  # a clear excursion: the gage moved, the part did not
    report = stability(data)
    assert report.stable is False
    assert any("not stable" in w for w in report.warnings)


def test_individuals_match_i_mr_chart() -> None:
    data = _steady()
    report = stability(data)
    direct = i_mr_chart(data)
    assert report.chart.location.points == direct.location.points
    assert report.chart.location.limits.upper == direct.location.limits.upper
    assert report.chart.in_control == direct.in_control


def test_subgroups_use_xbar_r_chart() -> None:
    rng = np.random.default_rng(5)
    subgroups = 10.0 + rng.normal(0.0, 0.1, (20, 3))
    report = stability(subgroups)
    direct = xbar_r_chart(subgroups)
    assert report.chart.subgroup_size == 3
    assert report.chart.location.limits.center == direct.location.limits.center


def test_three_dimensional_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"1-D .* or 2-D"):
        stability(np.zeros((2, 2, 2)))


def test_report_is_immutable() -> None:
    report = stability(_steady())
    with pytest.raises(AttributeError):
        report.warnings = ()  # type: ignore[misc]
    assert isinstance(report, StabilityReport)
