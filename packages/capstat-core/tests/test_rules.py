"""Nelson and Western Electric run rules.

Sources and rule wordings: ``references/rules.yaml``.

Every rule here is a *count* -- nine points, six points, two of three. An
off-by-one produces a chart that looks entirely plausible and is permanently
wrong, and nothing in the output would reveal it. So each rule is tested twice:
with a sequence that must fire it, and with the same sequence one point short,
which must not.
"""

from __future__ import annotations

import numpy as np
import pytest
import yaml
from capstat_core.control_charts import ControlChart, ControlLimits, xbar_r_chart
from capstat_core.rules import (
    NELSON_RULES,
    WESTERN_ELECTRIC_RULES,
    nelson_rules,
    western_electric_rules,
)
from conftest import REFERENCES

DOCUMENT = yaml.safe_load((REFERENCES / "rules.yaml").read_text())
CASES = {case["id"]: case for case in DOCUMENT["cases"]}


def chart(points: list[float]) -> ControlChart:
    """A symmetric chart with centre 0 and three-sigma limits at +/-3, so the
    point values ARE their sigma values and every test below reads directly."""
    return ControlChart(
        name="X-bar",
        points=tuple(points),
        limits=ControlLimits(center=0.0, lower=-3.0, upper=3.0),
        violations=(),
    )


def fired(violations: tuple[object, ...]) -> set[int]:
    return {v.rule for v in violations}  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# The discriminating case: 8 vs 9 on one side
# ---------------------------------------------------------------------------


def test_eight_on_one_side_fires_western_electric_but_not_nelson() -> None:
    """The two standards genuinely disagree, and the disagreement is a gift.

    Western Electric rule 4 needs eight consecutive points on one side; Nelson's
    rule 2 needs nine. A run of exactly eight must fire one and not the other. An
    off-by-one in either implementation breaks this, so it is asserted exactly.
    """
    case = CASES["eight-versus-nine-on-one-side"]
    given, expected = case["input"], case["expected"]

    eight = chart(given["eight_points"])
    nine = chart(given["nine_points"])

    assert (4 in fired(western_electric_rules(eight))) is expected[
        "eight_fires_western_electric_4"
    ]
    assert (2 in fired(nelson_rules(eight))) is expected["eight_fires_nelson_2"]
    assert (2 in fired(nelson_rules(nine))) is expected["nine_fires_nelson_2"]


# ---------------------------------------------------------------------------
# Every Nelson rule: fires on the pattern, silent one point short
# ---------------------------------------------------------------------------


def test_nelson_1_one_point_beyond_three_sigma() -> None:
    assert 1 in fired(nelson_rules(chart([0.0, 0.0, 3.5, 0.0]), [1]))
    assert 1 not in fired(nelson_rules(chart([0.0, 0.0, 2.9, 0.0]), [1]))


def test_nelson_2_nine_points_on_the_same_side() -> None:
    assert 2 in fired(nelson_rules(chart([0.5] * 9), [2]))
    assert 2 not in fired(nelson_rules(chart([0.5] * 8), [2]))
    # ...and a point exactly on the centre line breaks the run.
    assert 2 not in fired(nelson_rules(chart([0.5] * 4 + [0.0] + [0.5] * 4), [2]))
    # Works below the line too.
    assert 2 in fired(nelson_rules(chart([-0.5] * 9), [2]))


def test_nelson_3_six_points_trending() -> None:
    assert 3 in fired(nelson_rules(chart([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]), [3]))
    assert 3 not in fired(nelson_rules(chart([0.1, 0.2, 0.3, 0.4, 0.5]), [3]))
    assert 3 in fired(nelson_rules(chart([0.6, 0.5, 0.4, 0.3, 0.2, 0.1]), [3]))
    # A flat step breaks the trend: "continually increasing" means strictly.
    assert 3 not in fired(nelson_rules(chart([0.1, 0.2, 0.2, 0.3, 0.4, 0.5]), [3]))


def test_nelson_4_fourteen_points_alternating() -> None:
    alternating = [0.5 if i % 2 else -0.5 for i in range(14)]
    assert 4 in fired(nelson_rules(chart(alternating), [4]))
    assert 4 not in fired(nelson_rules(chart(alternating[:13]), [4]))


def test_a_repeated_value_breaks_the_alternation() -> None:
    """Two equal points in a row are a step of zero, which is neither up nor
    down. The run of fourteen is broken, not continued through it."""
    flat = [0.5 if i % 2 else -0.5 for i in range(14)]
    flat[7] = flat[6]  # a flat step in the middle
    assert 4 not in fired(nelson_rules(chart(flat), [4]))


def test_nelson_5_two_of_three_beyond_two_sigma() -> None:
    assert 5 in fired(nelson_rules(chart([2.5, 0.1, 2.5]), [5]))
    assert 5 not in fired(nelson_rules(chart([2.5, 0.1, 0.1]), [5]))
    # "in the same direction": one high and one low is not a signal.
    assert 5 not in fired(nelson_rules(chart([2.5, 0.1, -2.5]), [5]))


def test_nelson_6_four_of_five_beyond_one_sigma() -> None:
    assert 6 in fired(nelson_rules(chart([1.5, 1.5, 0.1, 1.5, 1.5]), [6]))
    assert 6 not in fired(nelson_rules(chart([1.5, 1.5, 0.1, 0.1, 1.5]), [6]))
    assert 6 not in fired(nelson_rules(chart([1.5, 1.5, 0.1, -1.5, -1.5]), [6]))


def test_nelson_7_fifteen_points_hugging_the_centre_line() -> None:
    """Too *little* variation is also a signal -- usually a sign that the data
    are being massaged, or the subgroups wrongly formed."""
    assert 7 in fired(nelson_rules(chart([0.3] * 15), [7]))
    assert 7 not in fired(nelson_rules(chart([0.3] * 14), [7]))
    # One point outside the inner zone breaks it.
    assert 7 not in fired(nelson_rules(chart([0.3] * 7 + [1.2] + [0.3] * 7), [7]))


def test_nelson_8_eight_points_avoiding_the_centre_on_both_sides() -> None:
    avoiding = [1.5, -1.5, 1.5, -1.5, 1.5, -1.5, 1.5, -1.5]
    assert 8 in fired(nelson_rules(chart(avoiding), [8]))
    assert 8 not in fired(nelson_rules(chart(avoiding[:7]), [8]))
    # All on one side is NOT rule 8: it demands points in both directions.
    assert 8 not in fired(nelson_rules(chart([1.5] * 8), [8]))
    # A point inside the inner zone breaks it.
    assert 8 not in fired(nelson_rules(chart([1.5, -1.5, 0.5, -1.5] * 2), [8]))


# ---------------------------------------------------------------------------
# Western Electric
# ---------------------------------------------------------------------------


def test_western_electric_rules_1_to_3_coincide_with_nelson_1_5_6() -> None:
    """They are the same tests, so they must agree point for point."""
    rng = np.random.default_rng(4)
    values = list(rng.normal(0.0, 1.0, size=300))
    c = chart(values)

    for we_rule, nelson_rule in ((1, 1), (2, 5), (3, 6)):
        we_points = {v.point for v in western_electric_rules(c, [we_rule])}
        nelson_points = {v.point for v in nelson_rules(c, [nelson_rule])}
        assert we_points == nelson_points, f"WE {we_rule} vs Nelson {nelson_rule}"


def test_western_electric_4_needs_eight_not_nine() -> None:
    assert 4 in fired(western_electric_rules(chart([0.5] * 8), [4]))
    assert 4 not in fired(western_electric_rules(chart([0.5] * 7), [4]))


# ---------------------------------------------------------------------------
# The rule that fires is the one that completes the pattern
# ---------------------------------------------------------------------------


def test_a_rule_fires_on_the_point_that_completes_the_pattern() -> None:
    violations = nelson_rules(chart([0.5] * 9), [2])
    assert len(violations) == 1
    assert violations[0].point == 8  # the ninth point, 0-indexed
    assert violations[0].window == tuple(range(9))


def test_a_stale_pattern_does_not_flag_an_innocent_point() -> None:
    """Without requiring the last point of the window to qualify, a window like
    [3.1, 2.5, 0.2] would report the harmless final point as a violation, long
    after the pattern it belongs to has passed."""
    violations = nelson_rules(chart([2.5, 2.5, 0.2]), [5])
    assert all(v.point != 2 for v in violations), (
        "point 2 is well inside the limits and must not be flagged just because "
        "the two points before it were not"
    )


def test_violations_carry_the_whole_window_not_just_the_signal_point() -> None:
    violations = nelson_rules(chart([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]), [3])
    assert violations[0].window == (0, 1, 2, 3, 4, 5)
    assert violations[0].point == 5


def test_one_point_may_complete_several_patterns() -> None:
    """A point that both breaches the limit and ends a run is reported by both
    rules. That is information, not duplication."""
    values = [1.5] * 8 + [3.5]
    violations = nelson_rules(chart(values), [1, 2])
    at_last = {v.rule for v in violations if v.point == 8}
    assert at_last == {1, 2}


# ---------------------------------------------------------------------------
# The cost of switching rules on
# ---------------------------------------------------------------------------


def test_false_alarm_rates_are_what_we_claim_they_are() -> None:
    """Measured, not quoted. Turning on all eight Nelson rules makes the chart
    roughly eight times as jumpy as the limit test alone -- an alarm on one point
    in forty-four of a process that is behaving perfectly.
    """
    case = CASES["false-alarm-rates"]
    expected = case["expected"]
    tol = case["tolerance"]["rel"]

    rng = np.random.default_rng(42)
    series, length = 200, 500
    counts = {"rule_1": 0, "nelson": 0, "we": 0}

    for _ in range(series):
        values = list(rng.normal(0.0, 1.0, size=length))
        c = chart(values)
        counts["rule_1"] += len({v.point for v in nelson_rules(c, [1])})
        counts["nelson"] += len({v.point for v in nelson_rules(c)})
        counts["we"] += len({v.point for v in western_electric_rules(c)})

    total = series * length
    assert counts["rule_1"] / total == pytest.approx(
        expected["nelson_rule_1_only"], rel=tol
    )
    assert counts["nelson"] / total == pytest.approx(
        expected["all_nelson_rules"], rel=tol
    )
    assert counts["we"] / total == pytest.approx(
        expected["all_western_electric_rules"], rel=tol
    )

    # The headline: the full set is far jumpier than the limit test alone.
    assert counts["nelson"] > 5 * counts["rule_1"]


def test_run_rules_find_a_drift_the_limits_never_catch() -> None:
    """The reason run rules exist. A slow ramp stays inside three sigma the whole
    way, so the chart's own `violations` are empty -- and rule 3 sees it."""
    values = [float(v) for v in np.linspace(-0.5, 2.5, 20)]
    c = chart(values)

    assert c.violations == (), "the ramp never leaves the limits"
    assert 3 in fired(nelson_rules(c, [3])), "but it is plainly a trend"


# ---------------------------------------------------------------------------
# Zones need a symmetric chart
# ---------------------------------------------------------------------------


def test_rules_refuse_a_dispersion_chart() -> None:
    """An R chart's limits are D3*Rbar and D4*Rbar -- not equidistant from Rbar --
    so the 1- and 2-sigma zones these rules speak of do not exist there."""
    data = np.random.default_rng(1).normal(100.0, 1.0, size=(30, 5))
    pair = xbar_r_chart(data)

    with pytest.raises(ValueError, match="not symmetric about its centre line"):
        nelson_rules(pair.dispersion)
    with pytest.raises(ValueError, match="belong on the location chart"):
        western_electric_rules(pair.dispersion)


def test_rules_work_on_a_real_location_chart() -> None:
    """A sustained shift leaves a long run on one side of the centre line, which
    rule 2 reads even when the points themselves stay inside the limits.

    The design (40 subgroups, shift of 1.5 sigma after 20) is chosen so the run
    is unambiguous: it fires for 100 of 100 seeds. A weaker shift, or fewer
    points after it, makes the run a coin toss -- noise pushes one subgroup back
    across the line and the run of nine never completes.
    """
    data = np.random.default_rng(2).normal(100.0, 1.0, size=(40, 5))
    data[20:] += 1.5

    pair = xbar_r_chart(data)
    violations = nelson_rules(pair.location)

    assert any(v.rule == 2 for v in violations), (
        "a sustained shift should produce a run on one side of the centre line"
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_rule_catalogues_are_complete() -> None:
    assert sorted(NELSON_RULES) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert sorted(WESTERN_ELECTRIC_RULES) == [1, 2, 3, 4]
    assert all(NELSON_RULES.values())
    assert all(WESTERN_ELECTRIC_RULES.values())


def test_violations_describe_themselves() -> None:
    violation = nelson_rules(chart([0.5] * 9), [2])[0]
    assert violation.rule_set == "nelson"
    assert violation.rule == 2
    assert violation.description == NELSON_RULES[2]


def test_unknown_rules_are_rejected() -> None:
    c = chart([0.0] * 10)
    with pytest.raises(ValueError, match=r"unknown Nelson rule\(s\) \[9\]"):
        nelson_rules(c, [1, 9])
    with pytest.raises(ValueError, match=r"unknown Western Electric rule\(s\) \[5\]"):
        western_electric_rules(c, [5])


def test_selecting_no_rules_at_all_is_allowed_and_silent() -> None:
    assert nelson_rules(chart([5.0] * 20), []) == ()


def test_default_applies_every_rule() -> None:
    c = chart([3.5] + [0.0] * 5)
    assert 1 in fired(nelson_rules(c))
    assert 1 in fired(western_electric_rules(c))


def test_violations_are_immutable() -> None:
    violation = nelson_rules(chart([0.5] * 9), [2])[0]
    with pytest.raises(AttributeError):
        violation.rule = 3  # type: ignore[misc]


def test_a_short_series_simply_fires_nothing() -> None:
    """Fewer points than a rule's window is not an error; the pattern just cannot
    have occurred."""
    assert nelson_rules(chart([0.5, 0.5, 0.5]), [2, 3, 4, 7, 8]) == ()
