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
import yaml
from capstat_core import (
    LotResult,
    SchemeHistory,
    SwitchingRules,
    apply_switching_rules,
)
from conftest import REFERENCES

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

    The windowed reading is the one ISO 2859-1:1999 Annex A demonstrates: its
    worked sequence tightens on non-acceptable lots four apart, which only the
    "as soon as the second lands inside the window" reading produces.
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

    This was implemented as an interpretation and has since been *confirmed*
    against the worked sequence in ISO 2859-1:1999 Annex A, which shows the
    rejected lot that triggers tightening still evaluated under normal, with
    tightened inspection beginning on the following lot -- and likewise the
    fifth acceptable lot still evaluated under tightened, with normal resuming
    on the one after it.
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


def test_discontinuation_counts_lots_not_accepted_not_lots_inspected() -> None:
    """The distinction that a first version of this module got wrong.

    Clause 9.4 counts *lots not accepted* while on tightened inspection, not
    lots inspected under it. Here forty lots pass through tightened inspection
    with only four non-accepted among them, and the scheme must not discontinue
    -- a counter that measured time on tightened would have stopped inspection
    long before.
    """
    # Tighten on lots 1-2, then a long stretch that never earns normal back
    # (no run of five acceptable) and never reaches five non-accepted.
    tail: list[bool] = []
    for _ in range(4):
        tail += [A, A, A, A, R]  # four acceptable, one not: run always broken
    tail += [A] * 4
    history = apply_switching_rules([R, R, *tail])
    assert history.final_severity == "tightened"
    assert len(history.steps) > 20
    assert all(step.severity != "discontinued" for step in history.steps)


def test_discontinuation_is_cumulative_and_survives_acceptances() -> None:
    # Five non-accepted lots on tightened, spread out so that acceptances sit
    # between them. "Cumulative in a sequence" means those do not reset it.
    history = apply_switching_rules([R, R, R, A, R, A, R, A, R, A, R])
    assert history.final_severity == "discontinued"
    discontinued_at = next(
        s.lot for s in history.switches if s.severity_after == "discontinued"
    )
    assert discontinued_at == 11
    assert any("discontinued" in w for w in history.warnings)


def test_lots_after_discontinuation_stay_discontinued() -> None:
    history = apply_switching_rules([R] * 12)
    assert history.steps[-1].severity == "discontinued"
    assert history.steps[-1].severity_after == "discontinued"
    # Resumption is a human decision and returns to *tightened*, so the report
    # says so rather than implying the series could simply carry on.
    assert any("resumes on *tightened*" in w for w in history.warnings)


# ---------------------------------------------------------------------------
# The switching score, and reduced inspection
# ---------------------------------------------------------------------------


def test_reduced_inspection_needs_an_authorisation_capstat_cannot_give() -> None:
    # Twenty accepted lots score 40 on the Ac <= 1 rule, well past 30 -- and the
    # scheme still does not relax, because steady production and the authority's
    # approval are not statistics.
    unauthorised = apply_switching_rules([A] * 20)
    assert unauthorised.final_severity == "normal"
    assert any("not authorised" in w for w in unauthorised.warnings)

    authorised = apply_switching_rules([A] * 20, reduced_inspection_authorised=True)
    assert authorised.final_severity == "reduced"


def test_the_score_adds_two_for_an_accepted_lot_and_resets_on_one_that_is_not() -> None:
    history = apply_switching_rules([A, A, A, R, A])
    assert [s.switching_score for s in history.steps] == [2, 4, 6, 0, 2]


def test_the_score_adds_three_when_the_tighter_aql_question_is_answered() -> None:
    """Clause 9.3.3.2's other branch -- the one that needs the master table.

    A lot that says it would still have been accepted one AQL step tighter
    scores three. capstat never infers this: a bare boolean outcome is scored on
    the conservative rule instead.
    """
    lots = [LotResult(accepted=True, accepted_at_tighter_aql=True)] * 3
    history = apply_switching_rules(lots)
    assert [s.switching_score for s in history.steps] == [3, 6, 9]

    # Accepted, but not at the tighter AQL: the score resets rather than adding.
    mixed = apply_switching_rules(
        [
            LotResult(accepted=True, accepted_at_tighter_aql=True),
            LotResult(accepted=True, accepted_at_tighter_aql=False),
            LotResult(accepted=True, accepted_at_tighter_aql=True),
        ]
    )
    assert [s.switching_score for s in mixed.steps] == [3, 0, 3]


def test_the_score_is_not_maintained_outside_normal_inspection() -> None:
    history = apply_switching_rules([R, R, A, A, A])
    # Lots 1-2 are normal and scored; lots 3-5 are tightened and are not.
    assert history.steps[0].switching_score == 0
    assert history.steps[2].switching_score is None
    assert history.steps[4].switching_score is None


def test_reduced_inspection_ends_on_a_lot_that_is_not_accepted() -> None:
    outcomes: list[bool] = [A] * 20 + [R, A]
    history = apply_switching_rules(outcomes, reduced_inspection_authorised=True)
    reduced_lots = [s.lot for s in history.steps if s.severity == "reduced"]
    assert reduced_lots  # it did relax
    # The non-accepted lot is judged under reduced and sends the next one back.
    assert history.steps[20].severity == "reduced"
    assert history.steps[20].severity_after == "normal"
    assert history.final_severity == "normal"


def test_scoring_every_lot_on_the_conservative_rule_is_said_out_loud() -> None:
    history = apply_switching_rules([A] * 6)
    assert any("Ac <= 1 rule" in w for w in history.warnings)


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
    with pytest.raises(ValueError, match="discontinue_on_non_accepted"):
        SwitchingRules(discontinue_on_non_accepted=0)
    with pytest.raises(ValueError, match="reduce_at_switching_score"):
        SwitchingRules(reduce_at_switching_score=0)


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
    assert any("per class of nonconformities" in w for w in history.warnings)
    assert any("no switch occurred" in w for w in history.warnings)


def test_ending_on_tightened_is_said_out_loud() -> None:
    history = apply_switching_rules([R, R, A])
    assert any("ends on tightened" in w for w in history.warnings)


def test_the_restatement_names_the_reset_not_only_the_additions() -> None:
    """The prose is the artefact under test here, and it has already misled once.

    An external review (2026-08-22) read `_updated_score` resetting to zero as a
    conformance defect, and cited this note as its evidence: it said the score
    "adds three or two per accepted lot" and stopped there, which reads as if an
    accepted lot could never lower the score. The code was right and the
    sentence was incomplete -- so the sentence is what gets pinned. (T-0062)
    """
    document = yaml.safe_load((REFERENCES / "sampling_scheme.yaml").read_text())
    note = document["sources"]["iso_2859_1_switching"]["note"]
    assert "resets the score to zero" in note
    assert "Ac >= 2" in note and "Ac <= 1" in note
    # And the behaviour it describes is the behaviour that runs.
    mixed = apply_switching_rules(
        [
            LotResult(accepted=True, accepted_at_tighter_aql=True),
            LotResult(accepted=True, accepted_at_tighter_aql=False),
        ]
    )
    assert [s.switching_score for s in mixed.steps] == [3, 0]
