"""Switching rules: the state machine, validated by simulation.

There are no published reference *values* here of the kind the OC curve has --
switching is a procedure, not a number. So the rules are validated the way
T-0009 validated the run rules: by constructing the lot sequences on which two
plausible readings of a rule disagree, and asserting the severity exactly.

A tolerance would be meaningless here. Every assertion in this file is a
decision: which severity a given lot was inspected under.
"""

from __future__ import annotations

import pytest
from capstat_core import (
    SchemeHistory,
    SwitchingRules,
    apply_switching_rules,
)

A = True  # acceptable on original inspection
R = False  # not acceptable


def severities(history: SchemeHistory) -> list[str]:
    """The severity each lot was actually inspected under."""
    return [step.severity for step in history.steps]


# ---------------------------------------------------------------------------
# normal -> tightened: two non-acceptable within five consecutive
# ---------------------------------------------------------------------------


def test_two_non_acceptable_inside_the_window_tightens() -> None:
    # Lots 1 and 5: the second falls on the last lot of the window, so the rule
    # fires. Lot 5 is still inspected under normal; the switch binds lot 6.
    history = apply_switching_rules([R, A, A, A, R, A])
    assert severities(history) == [
        "normal",
        "normal",
        "normal",
        "normal",
        "normal",
        "tightened",
    ]
    assert history.steps[4].severity_after == "tightened"
    assert history.final_severity == "tightened"


def test_the_same_two_rejects_one_lot_further_apart_do_not_tighten() -> None:
    """The discriminating sequence, and the reason this test file exists.

    Lots 1 and 6 are two non-acceptable lots, exactly as in the test above --
    but six apart, so no window of five consecutive lots contains both. A
    cumulative reading ("two rejects, ever") would switch here; the windowed
    reading does not. Nothing downstream would reveal which reading was
    implemented, because both produce a plausible-looking severity column.
    """
    history = apply_switching_rules([R, A, A, A, A, R, A])
    assert severities(history) == ["normal"] * 7
    assert history.final_severity == "normal"
    assert history.switches == ()


def test_two_non_acceptable_in_a_row_tightens_immediately() -> None:
    # "Two out of five *or fewer*": the rule does not wait for five lots to
    # accumulate before it is allowed to fire.
    history = apply_switching_rules([R, R, A])
    assert severities(history) == ["normal", "normal", "tightened"]
    assert history.steps[1].switched is True


def test_a_single_non_acceptable_lot_never_tightens() -> None:
    history = apply_switching_rules([A, A, R, A, A, A, A, A])
    assert history.final_severity == "normal"
    assert history.switches == ()


# ---------------------------------------------------------------------------
# tightened -> normal: five consecutive acceptable, and the run must be unbroken
# ---------------------------------------------------------------------------


def test_five_consecutive_acceptable_lots_restore_normal() -> None:
    history = apply_switching_rules([R, R] + [A] * 5 + [A])
    # Lots 1-2 tighten; lots 3-7 are the five acceptable lots, all inspected
    # under tightened; lot 8 is back on normal.
    assert severities(history) == ["normal", "normal"] + ["tightened"] * 5 + ["normal"]
    assert history.steps[6].severity_after == "normal"


def test_a_rejection_restarts_the_run_rather_than_denting_it() -> None:
    """Four acceptable, one not, then five: normal returns only after the five.

    A counter that merely decremented, or that counted acceptances cumulatively,
    would restore normal one lot early. This sequence is built so that the two
    readings disagree by exactly one lot.
    """
    #          tighten | four acceptable | one not | five acceptable | one more
    outcomes = [R, R, A, A, A, A, R, A, A, A, A, A, A]
    history = apply_switching_rules(outcomes)
    steps = history.steps
    # The four acceptable lots before the rejection do not accumulate.
    assert steps[5].severity == "tightened"
    assert steps[6].severity == "tightened"  # the rejection, still tightened
    # Five unbroken acceptable lots: lots 8-12.
    assert [s.severity for s in steps[7:12]] == ["tightened"] * 5
    assert steps[11].severity_after == "normal"
    assert steps[12].severity == "normal"


def test_a_switch_binds_the_next_lot_not_the_one_that_caused_it() -> None:
    """The off-by-one worth being explicit about.

    The lot whose result triggers a switch was already inspected under the old
    severity -- its sample size came from there. Recording it under the new
    severity would misreport what was actually done.
    """
    history = apply_switching_rules([R, R, A])
    trigger = history.steps[1]
    assert trigger.severity == "normal"
    assert trigger.severity_after == "tightened"
    assert history.steps[2].severity == "tightened"


# ---------------------------------------------------------------------------
# Re-entering normal: an assumption, labelled as one
# ---------------------------------------------------------------------------


def test_returning_to_normal_starts_a_fresh_window() -> None:
    """Assumption, not quotation.

    ISO 2859-1 does not state that the "two out of five" window restarts when
    normal inspection is re-instated. A fresh normal phase being fresh evidence
    is the natural reading, and it is what capstat implements -- so it is pinned
    here, named as an assumption, rather than left as an accident of the code.
    """
    # Tighten, earn normal back, then a single rejection. Under a window that
    # carried the old non-acceptances over, this would immediately re-tighten.
    outcomes = [R, R] + [A] * 5 + [R, A, A, A]
    history = apply_switching_rules(outcomes)
    assert history.steps[7].severity == "normal"  # first lot of the new phase
    assert history.final_severity == "normal"
    assert history.steps[7].switched is False


# ---------------------------------------------------------------------------
# Discontinuation: only when the caller supplies the threshold
# ---------------------------------------------------------------------------


def test_inspection_is_never_discontinued_by_default() -> None:
    # Twenty consecutive non-acceptable lots, and the scheme still only tightens
    # -- because capstat will not invent a threshold whose sources disagree.
    history = apply_switching_rules([R] * 20)
    assert history.final_severity == "tightened"
    assert any("discontinuation" in w for w in history.warnings)


def test_discontinuation_fires_at_the_threshold_the_caller_sets() -> None:
    rules = SwitchingRules(discontinue_after_tightened_lots=5)
    history = apply_switching_rules([R] * 10, rules=rules)
    # Lots 1-2 on normal, then five lots on tightened: the fifth discontinues.
    assert severities(history)[:2] == ["normal", "normal"]
    assert severities(history)[2:7] == ["tightened"] * 5
    assert history.steps[6].severity_after == "discontinued"
    assert history.final_severity == "discontinued"
    assert any("discontinued" in w for w in history.warnings)


def test_lots_after_discontinuation_stay_discontinued() -> None:
    rules = SwitchingRules(discontinue_after_tightened_lots=3)
    history = apply_switching_rules([R] * 8, rules=rules)
    assert history.steps[-1].severity == "discontinued"
    assert history.steps[-1].severity_after == "discontinued"


# ---------------------------------------------------------------------------
# The rules themselves, and what the report refuses to imply
# ---------------------------------------------------------------------------


def test_custom_thresholds_are_honoured() -> None:
    rules = SwitchingRules(
        tighten_on_non_acceptable=3,
        within_consecutive_lots=4,
        relax_after_consecutive_acceptable=2,
    )
    # Two rejections no longer suffice; three within four lots do.
    assert apply_switching_rules([R, R, A], rules=rules).final_severity == "normal"
    history = apply_switching_rules([R, A, R, R, A, A, A], rules=rules)
    assert history.steps[3].severity_after == "tightened"
    # And two acceptable lots are enough to come back.
    assert history.final_severity == "normal"


def test_impossible_rule_combinations_are_rejected() -> None:
    with pytest.raises(ValueError, match="tighten_on_non_acceptable must be >= 1"):
        SwitchingRules(tighten_on_non_acceptable=0)
    with pytest.raises(ValueError, match="cannot be smaller than"):
        SwitchingRules(tighten_on_non_acceptable=3, within_consecutive_lots=2)
    with pytest.raises(ValueError, match="relax_after"):
        SwitchingRules(relax_after_consecutive_acceptable=0)
    with pytest.raises(ValueError, match="discontinue_after"):
        SwitchingRules(discontinue_after_tightened_lots=0)


def test_a_series_cannot_start_discontinued() -> None:
    with pytest.raises(ValueError, match="cannot start discontinued"):
        apply_switching_rules([A], start="discontinued")


def test_a_series_can_start_on_tightened() -> None:
    # Picking up a supplier already on tightened inspection is normal practice.
    history = apply_switching_rules([A] * 5 + [A], start="tightened")
    assert history.steps[0].severity == "tightened"
    assert history.steps[4].severity_after == "normal"


def test_an_empty_series_is_not_an_error() -> None:
    history = apply_switching_rules([])
    assert history.steps == ()
    assert history.final_severity == "normal"


def test_the_report_says_what_it_cannot_know() -> None:
    history = apply_switching_rules([A, A, A])
    assert any("original inspection only" in w for w in history.warnings)
    assert any("reduced inspection is not implemented" in w for w in history.warnings)
    assert any("no switch occurred" in w for w in history.warnings)


def test_ending_on_tightened_is_said_out_loud() -> None:
    history = apply_switching_rules([R, R, A])
    assert any("ends on tightened" in w for w in history.warnings)
