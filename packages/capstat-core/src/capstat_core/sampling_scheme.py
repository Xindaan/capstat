"""Switching rules: the part of ISO 2859-1 that makes it a scheme, not a plan.

A sampling plan judges one lot. A sampling *scheme* judges a supplier: it
inspects a stream of lots and changes severity as the evidence changes.
Tightening after repeated non-acceptances is where ISO 2859-1's protection
actually comes from -- a normal-inspection plan applied forever, with no
switching, does not deliver what the standard describes, however faithfully the
plan itself was looked up.

This module implements that state machine for the two transitions whose
thresholds we could establish with confidence:

    normal ---- 2 non-acceptable lots within 5 consecutive ----> tightened
    tightened -- 5 consecutive acceptable lots ----------------> normal

Both count *original* inspection only: a lot resubmitted after screening does
not count towards either rule. capstat cannot tell a resubmission from a first
presentation, so the caller must pass original-inspection outcomes only, and
the report says so rather than assuming it was done.

What is deliberately absent
---------------------------
**Reduced inspection.** Qualifying for it cannot be decided from the accept and
reject outcomes alone: it depends either on the standard's limit numbers, or on
a switching score whose main branch asks whether a lot *would* have been
accepted under the plan for the next tighter AQL. Both are master-table
questions, and capstat has no master table -- see TASK.md T-0036. Guessing here
would produce a scheme that relaxes when the standard would not, which is the
one direction of error that costs the consumer rather than the producer.

**Discontinuation of inspection.** The rule exists -- inspection stops until the
supplier improves -- but published restatements of the threshold disagree, and
the source arm that would have settled it did not complete. So there is no
default: set ``discontinue_after_tightened_lots`` to the value your own
authority applies, or leave it unset and the scheme will not discontinue.

References
----------
ISO 2859-1:1999, clause 9.3.1 (normal to tightened) and clause 9.3.2 (tightened
    to normal). Cited by clause; the standard's text is not reproduced here,
    and no capstat test asserts against a copy of it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "InspectionSeverity",
    "SchemeHistory",
    "SchemeStep",
    "SwitchingRules",
    "apply_switching_rules",
]

InspectionSeverity = Literal["normal", "tightened", "discontinued"]


@dataclass(frozen=True, slots=True)
class SwitchingRules:
    """The thresholds, as parameters rather than as constants in the code.

    The ISO 2859-1 values are the defaults for the two transitions we could
    establish. ``discontinue_after_tightened_lots`` deliberately has no default:
    see the module docstring.
    """

    tighten_on_non_acceptable: int = 2
    within_consecutive_lots: int = 5
    relax_after_consecutive_acceptable: int = 5
    discontinue_after_tightened_lots: int | None = None

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
        if (
            self.discontinue_after_tightened_lots is not None
            and self.discontinue_after_tightened_lots < 1
        ):
            raise ValueError("discontinue_after_tightened_lots must be >= 1")


@dataclass(frozen=True, slots=True)
class SchemeStep:
    """One lot: the severity it was inspected under, and what that changed.

    ``severity`` is the severity in force *for this lot*, which is the one its
    sample size and acceptance number came from. ``severity_after`` is what the
    next lot will be inspected under. A switch therefore takes effect on the
    lot *after* the one that triggered it, which is what the standard's
    "shall be implemented" means and is the off-by-one worth being explicit
    about.
    """

    lot: int
    accepted: bool
    severity: InspectionSeverity
    severity_after: InspectionSeverity

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


def apply_switching_rules(
    outcomes: Iterable[bool],
    *,
    rules: SwitchingRules | None = None,
    start: InspectionSeverity = "normal",
) -> SchemeHistory:
    """Run a series of lot outcomes through the switching rules.

    ``outcomes`` is one boolean per lot -- ``True`` accepted, ``False`` not
    acceptable -- **on original inspection**. Resubmitted lots must not appear:
    the rules ignore them, and capstat cannot recognise one.

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
    # Non-acceptances inside the sliding window, as lot indices. The window is
    # re-started whenever normal inspection is (re-)entered: the standard does
    # not say so explicitly, and this is the natural reading -- a fresh normal
    # phase is fresh evidence. It is pinned by a test that names it an
    # assumption rather than a quotation.
    recent_non_acceptable: list[int] = []
    consecutive_acceptable = 0
    lots_on_tightened = 0
    steps: list[SchemeStep] = []

    for index, accepted in enumerate(outcomes, start=1):
        inspected_under = severity
        if severity == "discontinued":
            steps.append(
                SchemeStep(
                    lot=index,
                    accepted=accepted,
                    severity=severity,
                    severity_after=severity,
                )
            )
            continue

        if severity == "normal":
            if not accepted:
                recent_non_acceptable.append(index)
            # Only non-acceptances still inside the window can trigger.
            window_start = index - applied.within_consecutive_lots + 1
            recent_non_acceptable = [
                lot for lot in recent_non_acceptable if lot >= window_start
            ]
            if len(recent_non_acceptable) >= applied.tighten_on_non_acceptable:
                severity = "tightened"
                recent_non_acceptable = []
                consecutive_acceptable = 0
                lots_on_tightened = 0
        else:  # tightened
            lots_on_tightened += 1
            consecutive_acceptable = consecutive_acceptable + 1 if accepted else 0
            if consecutive_acceptable >= applied.relax_after_consecutive_acceptable:
                severity = "normal"
                recent_non_acceptable = []
                consecutive_acceptable = 0
                lots_on_tightened = 0
            elif (
                applied.discontinue_after_tightened_lots is not None
                and lots_on_tightened >= applied.discontinue_after_tightened_lots
            ):
                severity = "discontinued"

        steps.append(
            SchemeStep(
                lot=index,
                accepted=accepted,
                severity=inspected_under,
                severity_after=severity,
            )
        )

    return SchemeHistory(
        steps=tuple(steps),
        final_severity=severity,
        rules=applied,
        warnings=tuple(_scheme_warnings(applied, tuple(steps), severity)),
    )


def _scheme_warnings(
    rules: SwitchingRules,
    steps: Sequence[SchemeStep],
    final_severity: InspectionSeverity,
) -> list[str]:
    """What the severities do not say."""
    out: list[str] = [
        "these outcomes are read as original inspection only. A lot resubmitted "
        "after screening does not count towards either rule, and capstat cannot "
        "tell one from the other -- if resubmissions were included, the "
        "severities below are wrong.",
        "reduced inspection is not implemented: qualifying for it depends on the "
        "standard's limit numbers, or on a switching score that asks whether a "
        "lot would have been accepted under the next tighter AQL. Both need the "
        "master table. A scheme that relaxed on a guess would err in the "
        "direction that costs the consumer.",
    ]
    if rules.discontinue_after_tightened_lots is None:
        out.append(
            "discontinuation of inspection is not enforced, because published "
            "restatements of its threshold disagree and capstat will not pick "
            "one for you. Set discontinue_after_tightened_lots to the value your "
            "own authority applies."
        )
    if final_severity == "tightened":
        out.append(
            "the series ends on tightened inspection: the supplier has not yet "
            "earned normal inspection back. Reporting the last lot's result "
            "without its severity would overstate what was accepted."
        )
    if final_severity == "discontinued":
        out.append(
            "inspection was discontinued. The standard's remedy is not a smaller "
            "sample but a better process: inspection resumes when the supplier's "
            "quality has improved, which is a judgement no library can make."
        )
    if steps and not any(step.switched for step in steps):
        out.append(
            "no switch occurred in this series, so these lots were all judged at "
            "one severity. That is a result, not a reason to stop applying the "
            "rules: the protection comes from switching when the evidence "
            "demands it."
        )
    return out
