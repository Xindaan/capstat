"""Run rules: Nelson (1984) and Western Electric (1956).

A point outside the control limits is the only signal a bare Shewhart chart
gives, and it is the one a real process rarely offers first. Processes drift,
trend, and hug the centre line long before they throw a point past three sigma.
The run rules read those patterns.

They are applied *to* a chart, not baked into it: the zones are derived from the
chart's own limits, so ``nelson_rules(pair.location)`` needs nothing else. That
also means :attr:`ControlChart.violations` keeps meaning exactly what it always
meant -- points beyond the limits, which is Nelson rule 1 and Western Electric
rule 1 -- and nothing is reported twice under two names.

Zones only make sense on a symmetric chart
------------------------------------------
Rules 5-8 talk about one- and two-sigma zones either side of the centre line. An
R, s or moving-range chart has no such symmetry: its limits are ``D3*Rbar`` and
``D4*Rbar``, which are not equidistant from ``Rbar``. Applying zone rules there
would be arithmetic without meaning, so these functions refuse. Run rules belong
on the location chart.

The price of more rules
----------------------
Every rule added is another chance to cry wolf, and the cost is far steeper than
it looks. On a perfectly stable process:

* the 3-sigma test alone signals about once in 370 points (measured: 1 in 351);
* all four Western Electric rules together, about once in 61;
* all eight Nelson rules together, about once in **44**.

So switching the full Nelson set on makes the chart roughly *eight times* as
jumpy as the limit test alone -- not a little more sensitive, but an alarm on one
point in forty-four of a process that is behaving perfectly. This is why Nelson
himself advised against running all eight at once, and why both functions here
take a subset. Choose the rules that match the failure you are actually looking
for; do not switch them all on because they are there.

(These rates are simulated in the test suite, not quoted from a textbook.)

References
----------
Nelson, L. S. (1984). The Shewhart control chart -- tests for special causes.
    *Journal of Quality Technology*, 16(4), 237-239.
Western Electric Company (1956). *Statistical Quality Control Handbook*.
NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from capstat_core.control_charts import ControlChart

__all__ = [
    "NELSON_RULES",
    "WESTERN_ELECTRIC_RULES",
    "RuleViolation",
    "nelson_rules",
    "western_electric_rules",
]

#: Nelson's eight tests, exactly as published (JQT 16(4), 1984).
NELSON_RULES: dict[int, str] = {
    1: "one point more than 3 sigma from the centre line",
    2: "nine points in a row on the same side of the centre line",
    3: "six points in a row all increasing, or all decreasing",
    4: "fourteen points in a row alternating up and down",
    5: "two out of three points in a row more than 2 sigma from the centre "
    "line, on the same side",
    6: "four out of five points in a row more than 1 sigma from the centre "
    "line, on the same side",
    7: "fifteen points in a row all within 1 sigma of the centre line",
    8: "eight points in a row none within 1 sigma of the centre line, on both sides",
}

#: The four Western Electric rules as stated by the NIST e-Handbook (6.3.2).
#:
#: Note rule 4: **eight** consecutive points on one side. Nelson's equivalent
#: (his rule 2) requires **nine**. The two standards genuinely disagree, and a
#: run of exactly eight is the sequence that tells them apart -- which is
#: precisely how an off-by-one in either would be caught.
WESTERN_ELECTRIC_RULES: dict[int, str] = {
    1: "one point beyond 3 sigma",
    2: "two out of the last three points beyond 2 sigma, on the same side",
    3: "four out of the last five points beyond 1 sigma, on the same side",
    4: "eight consecutive points on one side of the centre line",
}


@dataclass(frozen=True, slots=True)
class RuleViolation:
    """One firing of one rule.

    ``point`` is the index at which the rule fires -- the point that *completes*
    the pattern. ``window`` is every index the pattern is made of, so a chart can
    highlight the run and not just its final point.
    """

    rule_set: str
    rule: int
    description: str
    point: int
    window: tuple[int, ...]


def _standardise(chart: ControlChart) -> npt.NDArray[np.float64]:
    """Points expressed in sigma units from the centre line.

    Sigma is recovered from the chart's own limits, which are three-sigma limits
    by construction.

    Raises
    ------
    ValueError
        If the chart's limits are not symmetric about its centre line. On an R,
        s or moving-range chart they are not, and the sigma zones the rules are
        written in terms of simply do not exist there.
    """
    center = chart.limits.center
    above = chart.limits.upper - center
    below = center - chart.limits.lower

    # atol=0.0 on purpose: numpy's default absolute tolerance is 1e-8, which is
    # larger than the entire chart when the measurements are small (nanometres,
    # strain, ppm). A chart with limits at -1e-9 and +3e-9 is three times as far
    # above the centre line as below it, and the default tolerance called that
    # symmetric -- so the zone rules ran on a dispersion chart's limits and
    # reported patterns that do not exist (T-0069). The relative tolerance is
    # what this comparison always meant; it survives the last-ulp difference
    # between ``center + spread`` and ``center - spread``.
    if above <= 0.0 or not np.isclose(above, below, rtol=1e-9, atol=0.0):
        raise ValueError(
            f"the {chart.name} chart's limits are not symmetric about its centre "
            f"line (upper is {above:.4g} above, lower is {below:.4g} below), so "
            f"the 1- and 2-sigma zones these rules are defined on do not exist. "
            f"Run rules belong on the location chart (X-bar or individuals), not "
            f"on a dispersion chart."
        )

    sigma = above / 3.0
    return (np.asarray(chart.points, dtype=np.float64) - center) / sigma


def _resolve(
    requested: Sequence[int] | None, available: dict[int, str], rule_set: str
) -> list[int]:
    if requested is None:
        return sorted(available)
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise ValueError(
            f"unknown {rule_set} rule(s) {unknown}; available are {sorted(available)}"
        )
    return sorted(set(requested))


def _runs_on_one_side(z: npt.NDArray[np.float64], length: int) -> list[tuple[int, ...]]:
    """Windows of `length` consecutive points strictly on one side of zero."""
    found: list[tuple[int, ...]] = []
    for start in range(len(z) - length + 1):
        window = z[start : start + length]
        if np.all(window > 0.0) or np.all(window < 0.0):
            found.append(tuple(range(start, start + length)))
    return found


def _k_of_m_beyond(
    z: npt.NDArray[np.float64], k: int, m: int, threshold: float
) -> list[tuple[int, ...]]:
    """Windows of `m` points holding at least `k` beyond `threshold` sigma on the
    same side, reported at the point that completes the pattern.

    The signal belongs on the *last qualifying* point, which is what the caller
    derives from the returned indices -- not on the last point of the window.
    Those are two different things, and conflating them costs alarms: a window
    like ``[2.5, 2.5, 0.1]`` completes at its second point, and demanding that
    the third one qualify too means the pattern never signals at all. The stale
    case this once guarded against (``[3.1, 2.5, 0.2]`` must not flag the
    harmless point 2) is already handled by reporting ``max(qualifying)``, which
    is point 1 there.

    A pattern spanning several overlapping windows completes once, so windows
    resolving to the same signal point are reported once -- keeping the earliest,
    which carries the fullest run.
    """
    by_signal: dict[int, tuple[int, ...]] = {}
    for start in range(len(z) - m + 1):
        window = z[start : start + m]
        for sign in (1.0, -1.0):
            qualifying = np.flatnonzero(sign * window > threshold)
            if qualifying.size >= k:
                indices = tuple(int(start + i) for i in qualifying)
                by_signal.setdefault(max(indices), indices)
                break
    return [by_signal[point] for point in sorted(by_signal)]


def _monotone_runs(
    values: npt.NDArray[np.float64], length: int
) -> list[tuple[int, ...]]:
    """Windows of `length` points strictly increasing or strictly decreasing."""
    found: list[tuple[int, ...]] = []
    for start in range(len(values) - length + 1):
        window = values[start : start + length]
        steps = np.diff(window)
        if np.all(steps > 0.0) or np.all(steps < 0.0):
            found.append(tuple(range(start, start + length)))
    return found


def _alternating_runs(
    values: npt.NDArray[np.float64], length: int
) -> list[tuple[int, ...]]:
    """Windows of `length` points whose direction flips at every step."""
    found: list[tuple[int, ...]] = []
    for start in range(len(values) - length + 1):
        steps = np.diff(values[start : start + length])
        if np.any(steps == 0.0):
            continue
        if all(a * b < 0.0 for a, b in itertools.pairwise(steps)):
            found.append(tuple(range(start, start + length)))
    return found


def _violations(
    rule_set: str,
    descriptions: dict[int, str],
    rule: int,
    windows: list[tuple[int, ...]],
    signal_at: list[int],
) -> list[RuleViolation]:
    return [
        RuleViolation(
            rule_set=rule_set,
            rule=rule,
            description=descriptions[rule],
            point=point,
            window=window,
        )
        for window, point in zip(windows, signal_at, strict=True)
    ]


def nelson_rules(
    chart: ControlChart, rules: Sequence[int] | None = None
) -> tuple[RuleViolation, ...]:
    """Apply Nelson's eight tests to a chart.

    Parameters
    ----------
    rules:
        Which of the eight to apply. ``None`` applies all of them, which is the
        most sensitive and the most trigger-happy setting; see the note on false
        alarms in the module docstring.

    Returns
    -------
    tuple[RuleViolation, ...]
        Sorted by the point at which each rule fires, then by rule number. A
        single point may appear more than once if it completes more than one
        pattern -- that is information, not duplication.
    """
    wanted = _resolve(rules, NELSON_RULES, "Nelson")
    z = _standardise(chart)
    values = np.asarray(chart.points, dtype=np.float64)
    found: list[RuleViolation] = []

    def add(rule: int, windows: list[tuple[int, ...]]) -> None:
        found.extend(
            _violations(
                "nelson", NELSON_RULES, rule, windows, [max(w) for w in windows]
            )
        )

    if 1 in wanted:
        add(1, [(int(i),) for i in np.flatnonzero(np.abs(z) > 3.0)])
    if 2 in wanted:
        add(2, _runs_on_one_side(z, 9))
    if 3 in wanted:
        add(3, _monotone_runs(values, 6))
    if 4 in wanted:
        add(4, _alternating_runs(values, 14))
    if 5 in wanted:
        add(5, _k_of_m_beyond(z, 2, 3, 2.0))
    if 6 in wanted:
        add(6, _k_of_m_beyond(z, 4, 5, 1.0))
    if 7 in wanted:
        windows = [
            tuple(range(start, start + 15))
            for start in range(len(z) - 14)
            if np.all(np.abs(z[start : start + 15]) < 1.0)
        ]
        add(7, windows)
    if 8 in wanted:
        windows = []
        for start in range(len(z) - 7):
            window = z[start : start + 8]
            outside = np.all(np.abs(window) > 1.0)
            both_sides = np.any(window > 0.0) and np.any(window < 0.0)
            if outside and both_sides:
                windows.append(tuple(range(start, start + 8)))
        add(8, windows)

    return tuple(sorted(found, key=lambda v: (v.point, v.rule)))


def western_electric_rules(
    chart: ControlChart, rules: Sequence[int] | None = None
) -> tuple[RuleViolation, ...]:
    """Apply the four Western Electric rules to a chart.

    These predate Nelson's set and are the ones most factory floors were trained
    on. Rules 1-3 coincide with Nelson's 1, 5 and 6. Rule 4 does *not* coincide
    with Nelson's rule 2: Western Electric signals on **eight** consecutive points
    on one side, Nelson on **nine**. A run of exactly eight fires this rule and
    not Nelson's, which is the sequence that would expose an off-by-one in either.
    """
    wanted = _resolve(rules, WESTERN_ELECTRIC_RULES, "Western Electric")
    z = _standardise(chart)
    found: list[RuleViolation] = []

    def add(rule: int, windows: list[tuple[int, ...]]) -> None:
        found.extend(
            _violations(
                "western-electric",
                WESTERN_ELECTRIC_RULES,
                rule,
                windows,
                [max(w) for w in windows],
            )
        )

    if 1 in wanted:
        add(1, [(int(i),) for i in np.flatnonzero(np.abs(z) > 3.0)])
    if 2 in wanted:
        add(2, _k_of_m_beyond(z, 2, 3, 2.0))
    if 3 in wanted:
        add(3, _k_of_m_beyond(z, 4, 5, 1.0))
    if 4 in wanted:
        add(4, _runs_on_one_side(z, 8))

    return tuple(sorted(found, key=lambda v: (v.point, v.rule)))
