"""Switching rules: the part of ISO 2859-1 that makes it a scheme, not a plan.

A sampling plan judges one lot. A sampling *scheme* judges a supplier: it
inspects a stream of lots and changes severity as the evidence changes.
Tightening after repeated non-acceptances is where ISO 2859-1's protection
actually comes from -- a normal-inspection plan applied forever, with no
switching, does not deliver what the standard describes, however faithfully the
plan itself was looked up.

    normal ----- 2 non-acceptable within 5 consecutive --------> tightened
    tightened -- 5 consecutive acceptable ---------------------> normal
    tightened -- 5 non-accepted, cumulative ------------------> discontinued
    normal ----- switching score >= 30, and authorised --------> reduced
    reduced ---- one lot not accepted -------------------------> normal

Every one of those counts **original inspection only**: a lot resubmitted after
screening counts towards none of them. capstat cannot tell a resubmission from a
first presentation, so the caller must pass original-inspection outcomes, and
the report says so rather than assuming it was done.

Two of these need more than an accept/reject outcome, and capstat asks for what
it cannot know rather than guessing:

**The switching score** (clause 9.3.3.2) adds 3 for a lot whose plan has an
acceptance number of 2 or more *and which would still have been accepted one
AQL step tighter* -- a question only the standard's master table can answer, and
capstat has no master table. Supply that answer per lot via
:class:`LotResult`; without it the lot is scored on the Ac <= 1 rule, which adds
2 for an accepted lot. Scoring a lot too generously is what would let a scheme
relax early, so the conservative branch is the default.

**Reduced inspection** additionally requires steady production and the
responsible authority judging it desirable. Neither is a statistic. They are the
single ``reduced_inspection_authorised`` switch, and it defaults to *off*: left
alone, this scheme never relaxes.

References
----------
ISO 2859-1:1999, clauses 9.1 (start), 9.2 (per class of nonconformities),
    9.3.1-9.3.4 (the transitions), 9.4 (discontinuation). Cited by clause; the
    standard's text is not reproduced here and no test asserts against a copy of
    it. A third edition (2026) exists and was not consulted -- these are the
    1999 rules.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "InspectionSeverity",
    "LotResult",
    "SchemeHistory",
    "SchemeStep",
    "SwitchingRules",
    "apply_switching_rules",
]

InspectionSeverity = Literal["normal", "tightened", "reduced", "discontinued"]


@dataclass(frozen=True, slots=True)
class LotResult:
    """One lot's outcome on original inspection.

    ``accepted_at_tighter_aql`` answers the switching score's harder question
    (clause 9.3.3.2): for a plan with an acceptance number of 2 or more, would
    this lot still have been accepted under the plan for the next tighter AQL?
    Leave it ``None`` -- as a bare boolean outcome does -- and the lot is scored
    on the ``Ac <= 1`` rule instead, which is the conservative choice.
    """

    accepted: bool
    accepted_at_tighter_aql: bool | None = None

    def __post_init__(self) -> None:
        # A tighter AQL is a harder test, so a lot that was not accepted here
        # cannot have been accepted there. Left unchecked, the pair reached
        # ``_updated_score``, which asks the tighter-AQL question first and
        # therefore added 3 for a *rejected* lot -- the score moving up on the
        # evidence that should reset it (T-0066).
        if not self.accepted and self.accepted_at_tighter_aql:
            raise ValueError(
                "a lot that was not accepted cannot have been accepted one AQL "
                "step tighter: the tighter plan is the harder test. Set "
                "accepted_at_tighter_aql to False or None for a rejected lot."
            )


@dataclass(frozen=True, slots=True)
class SwitchingRules:
    """The thresholds, as parameters rather than as constants in the code.

    The defaults are ISO 2859-1:1999's. ``discontinue_on_non_accepted`` counts
    what clause 9.4 counts -- lots *not accepted* while on tightened inspection,
    cumulatively -- which is not the same as the number of lots inspected under
    tightened, and the difference is large.
    """

    tighten_on_non_acceptable: int = 2
    within_consecutive_lots: int = 5
    relax_after_consecutive_acceptable: int = 5
    discontinue_on_non_accepted: int = 5
    reduce_at_switching_score: int = 30

    def __post_init__(self) -> None:
        if self.tighten_on_non_acceptable < 1:
            raise ValueError("tighten_on_non_acceptable must be >= 1")
        if self.within_consecutive_lots < self.tighten_on_non_acceptable:
            raise ValueError(
                f"within_consecutive_lots ({self.within_consecutive_lots}) cannot "
                f"be smaller than tighten_on_non_acceptable "
                f"({self.tighten_on_non_acceptable}): the window has to be able "
                "to hold the non-acceptances it counts"
            )
        if self.relax_after_consecutive_acceptable < 1:
            raise ValueError("relax_after_consecutive_acceptable must be >= 1")
        if self.discontinue_on_non_accepted < 1:
            raise ValueError("discontinue_on_non_accepted must be >= 1")
        if self.reduce_at_switching_score < 1:
            raise ValueError("reduce_at_switching_score must be >= 1")


@dataclass(frozen=True, slots=True)
class SchemeStep:
    """One lot: the severity it was inspected under, and what that changed.

    ``severity`` is the severity in force *for this lot*, which is where its
    sample size and acceptance number came from. ``severity_after`` is what the
    next lot will be inspected under. A switch therefore takes effect on the lot
    *after* the one that triggered it -- confirmed by the worked sequence in the
    standard's own Annex A, and the off-by-one most worth being explicit about.

    ``switching_score`` is the score *after* this lot, or ``None`` wherever the
    standard does not maintain it (anywhere but original normal inspection).
    """

    lot: int
    accepted: bool
    severity: InspectionSeverity
    severity_after: InspectionSeverity
    switching_score: int | None

    @property
    def switched(self) -> bool:
        return self.severity != self.severity_after


@dataclass(frozen=True, slots=True)
class SchemeHistory:
    """The severity of every lot in a series, and what the series is not."""

    steps: tuple[SchemeStep, ...]
    final_severity: InspectionSeverity
    rules: SwitchingRules
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def switches(self) -> tuple[SchemeStep, ...]:
        """Just the lots at which the severity changed."""
        return tuple(step for step in self.steps if step.switched)


def _as_result(outcome: bool | LotResult) -> LotResult:
    return outcome if isinstance(outcome, LotResult) else LotResult(accepted=outcome)


def apply_switching_rules(
    outcomes: Iterable[bool | LotResult],
    *,
    rules: SwitchingRules | None = None,
    start: InspectionSeverity = "normal",
    reduced_inspection_authorised: bool = False,
) -> SchemeHistory:
    """Run a series of lot outcomes through the switching rules.

    ``outcomes`` is one entry per lot **on original inspection** -- a bare
    ``bool``, or a :class:`LotResult` when the switching score's tighter-AQL
    question can be answered. Resubmitted lots must not appear: the rules ignore
    them, and capstat cannot recognise one.

    ``reduced_inspection_authorised`` stands for the two conditions of clause
    9.3.3.1 that are not statistics -- steady production, and the responsible
    authority judging reduced inspection desirable. It defaults to ``False``, so
    a scheme left alone never relaxes.

    Raises
    ------
    ValueError
        If ``start`` is ``"discontinued"``, which is not a state a series can
        begin in.
    """
    applied = rules if rules is not None else SwitchingRules()
    if start == "discontinued":
        raise ValueError(
            "a series cannot start discontinued: discontinuation is an outcome "
            "of the rules, not an input to them"
        )

    severity: InspectionSeverity = start
    recent_non_acceptable: list[int] = []
    consecutive_acceptable = 0
    non_accepted_while_tightened = 0
    score = 0
    scored_any_lot = False
    tighter_aql_answered = False
    steps: list[SchemeStep] = []

    for index, outcome in enumerate(outcomes, start=1):
        lot = _as_result(outcome)
        inspected_under = severity
        score_after: int | None = None

        if severity == "normal":
            scored_any_lot = True
            tighter_aql_answered |= lot.accepted_at_tighter_aql is not None
            score_after = score = _updated_score(score, lot)
            if not lot.accepted:
                recent_non_acceptable.append(index)
            window_start = index - applied.within_consecutive_lots + 1
            recent_non_acceptable = [
                at for at in recent_non_acceptable if at >= window_start
            ]
            if len(recent_non_acceptable) >= applied.tighten_on_non_acceptable:
                severity = "tightened"
                recent_non_acceptable = []
                consecutive_acceptable = 0
                non_accepted_while_tightened = 0
                score = 0
            elif (
                reduced_inspection_authorised
                and score >= applied.reduce_at_switching_score
            ):
                severity = "reduced"
                score = 0
        elif severity == "tightened":
            consecutive_acceptable = consecutive_acceptable + 1 if lot.accepted else 0
            if not lot.accepted:
                non_accepted_while_tightened += 1
            if consecutive_acceptable >= applied.relax_after_consecutive_acceptable:
                severity = "normal"
                recent_non_acceptable = []
                consecutive_acceptable = 0
                non_accepted_while_tightened = 0
                score = 0
            elif non_accepted_while_tightened >= applied.discontinue_on_non_accepted:
                severity = "discontinued"
        elif severity == "reduced":
            # Clause 9.3.4: any non-accepted lot ends reduced inspection. The
            # other two triggers -- irregular production, and the authority
            # withdrawing its approval -- are judgements, not outcomes.
            if not lot.accepted:
                severity = "normal"
                recent_non_acceptable = []
                score = 0

        steps.append(
            SchemeStep(
                lot=index,
                accepted=lot.accepted,
                severity=inspected_under,
                severity_after=severity,
                switching_score=score_after,
            )
        )

    return SchemeHistory(
        steps=tuple(steps),
        final_severity=severity,
        rules=applied,
        warnings=tuple(
            _scheme_warnings(
                tuple(steps),
                severity,
                authorised=reduced_inspection_authorised,
                scored_any_lot=scored_any_lot,
                tighter_aql_answered=tighter_aql_answered,
            )
        ),
    )


def _updated_score(score: int, lot: LotResult) -> int:
    """Clause 9.3.3.2, on original normal inspection only.

    Three for a lot that would still have been accepted one AQL step tighter,
    two for an accepted lot scored on the ``Ac <= 1`` rule, and zero -- a reset,
    not a decrement -- for anything else.
    """
    if lot.accepted_at_tighter_aql is not None:
        return score + 3 if lot.accepted_at_tighter_aql else 0
    return score + 2 if lot.accepted else 0


def _scheme_warnings(
    steps: Sequence[SchemeStep],
    final_severity: InspectionSeverity,
    *,
    authorised: bool,
    scored_any_lot: bool,
    tighter_aql_answered: bool,
) -> list[str]:
    """What the severities do not say."""
    out: list[str] = [
        "these outcomes are read as original inspection only. A lot resubmitted "
        "after screening counts towards none of the rules, and capstat cannot "
        "tell one from the other -- if resubmissions were included, the "
        "severities below are wrong.",
        "the switching rules are applied per class of nonconformities. A series "
        "mixing classes together is not the scheme the standard describes; run "
        "one series per class.",
    ]
    if any(step.severity == "normal" for step in steps) and not authorised:
        out.append(
            "reduced inspection was never entered because it was not "
            "authorised. That is the default on purpose: the standard also "
            "requires steady production and the responsible authority judging "
            "reduced inspection desirable, and neither is something capstat can "
            "observe."
        )
    if scored_any_lot and not tighter_aql_answered:
        out.append(
            "every lot was scored on the Ac <= 1 rule (+2), because no lot said "
            "whether it would still have been accepted one AQL step tighter. "
            "That under-counts the score for plans with an acceptance number of "
            "2 or more, so reduced inspection is reached later than the "
            "standard would reach it -- the safe direction, but not the "
            "standard's."
        )
    if final_severity == "tightened":
        out.append(
            "the series ends on tightened inspection: the supplier has not yet "
            "earned normal inspection back. Reporting the last lot's result "
            "without its severity would overstate what was accepted."
        )
    if final_severity == "discontinued":
        out.append(
            "inspection was discontinued. The standard's remedy is not a "
            "smaller sample but a better process: acceptance does not resume "
            "until the supplier has acted and the responsible authority accepts "
            "that the action will work -- and it then resumes on *tightened* "
            "inspection, not normal."
        )
    if final_severity == "reduced":
        out.append(
            "the series ends on reduced inspection, which samples fewer items. "
            "It rests on the authorisation you gave, not on anything capstat "
            "verified: if production is no longer steady, the standard's answer "
            "is to return to normal inspection."
        )
    if steps and not any(step.switched for step in steps):
        out.append(
            "no switch occurred in this series, so these lots were all judged at "
            "one severity. That is a result, not a reason to stop applying the "
            "rules: the protection comes from switching when the evidence "
            "demands it."
        )
    return out
