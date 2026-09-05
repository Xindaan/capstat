"""Every warning carries a code, and the codes are well formed (T-0074).

This is the guard that makes the warnings checkable rather than merely
readable. It runs the entry points rather than reading the source: a grep for
``Caveat(`` would prove only that somebody typed it, which is precisely the
class of test this project distrusts. What is asserted here is what a caller
actually receives.
"""

from __future__ import annotations

import re

import numpy as np
import pytest
from capstat_core import (
    Caveat,
    LotResult,
    analyze_capability,
    apply_switching_rules,
    bias,
    capability,
    cusum_chart,
    design_single_sampling_plan,
    evaluate_plan,
    ewma_chart,
    gage_rr,
    gage_rr_range,
    i_mr_chart,
    inspect_lot,
    linearity,
    percentile_capability,
    stability,
    xbar_r_chart,
    xbar_s_chart,
)
from capstat_core.acceptance_sampling import SamplingPlan

#: ``subject.what-happened``: lower case, hyphenated, exactly one dot.
CODE = re.compile(r"^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*$")


def _reports() -> list[tuple[str, tuple[Caveat, ...]]]:
    """One call per warning-producing entry point, with its warnings."""
    rng = np.random.default_rng(11)
    drifting = np.concatenate([rng.normal(10.0, 1.0, 40), rng.normal(14.0, 1.0, 40)])
    subgroups = rng.normal(10.0, 1.0, size=(12, 4))
    lognormal = np.exp(rng.normal(3.0, 0.4, 200))
    bimodal = np.concatenate([rng.normal(10.0, 0.5, 200), rng.normal(40.0, 0.5, 200)])
    grid = rng.normal(10.0, 1.0, size=(5, 3, 3))
    plan = SamplingPlan(sample_size=52, acceptance_number=3, lot_size=1000)
    zero_ac = SamplingPlan(sample_size=20, acceptance_number=0)

    out: list[tuple[str, tuple[Caveat, ...]]] = [
        ("capability/individuals", capability(drifting, lsl=5.0, usl=15.0).warnings),
        ("capability/subgroups", capability(subgroups, lsl=5.0, usl=15.0).warnings),
        (
            "capability/tiny",
            capability([1.0, 2.0, 3.0, 4.5], lsl=0.0, usl=6.0).warnings,
        ),
        ("analyze/box-cox", analyze_capability(lognormal, lsl=5.0, usl=90.0).warnings),
        (
            "analyze/percentile",
            analyze_capability(bimodal, lsl=1.0, usl=60.0, target=20.0).warnings,
        ),
        (
            "percentile",
            percentile_capability(bimodal[:50], lsl=1.0, usl=60.0).warnings,
        ),
        ("i-mr", i_mr_chart(drifting).warnings),
        ("xbar-r", xbar_r_chart(subgroups).warnings),
        ("xbar-s", xbar_s_chart(subgroups).warnings),
        ("ewma", ewma_chart(drifting, time_varying_limits=False).warnings),
        ("cusum", cusum_chart(drifting).warnings),
        ("gage-rr/anova", gage_rr(grid).warnings),
        ("gage-rr/range", gage_rr_range(grid).warnings),
        ("bias", bias([36.5] * 6, reference=36.0).warnings),
        (
            "linearity",
            linearity(
                [7.0, 9.0, 11.0], [[7.4, 7.5], [9.1, 9.2], [10.9, 11.0]]
            ).warnings,
        ),
        ("stability", stability(drifting).warnings),
        ("evaluate", evaluate_plan(plan, 0.01, 0.10).warnings),
        ("evaluate/poisson", evaluate_plan(plan, 0.01, 0.10, model="poisson").warnings),
        ("evaluate/ac0", evaluate_plan(zero_ac, 0.01, 0.10).warnings),
        ("inspect", inspect_lot(plan, 2).warnings),
        ("scheme/tightened", apply_switching_rules([True, False, False]).warnings),
        (
            "scheme/reduced",
            apply_switching_rules(
                [LotResult(accepted=True, accepted_at_tighter_aql=True)] * 12,
                reduced_inspection_authorised=True,
            ).warnings,
        ),
        ("scheme/discontinued", apply_switching_rules([False] * 12).warnings),
    ]
    designed = design_single_sampling_plan(0.01, 0.05, lot_size=200)
    out.append(("designed", evaluate_plan(designed, 0.01, 0.05).warnings))
    return out


REPORTS = _reports()


def test_the_battery_actually_produces_warnings() -> None:
    """Guards the guard: an empty battery would pass every test below."""
    total = sum(len(warnings) for _, warnings in REPORTS)
    assert total > 40, f"only {total} warnings collected; the battery is not exercising"


@pytest.mark.parametrize(("label", "warnings"), REPORTS, ids=[r[0] for r in REPORTS])
def test_every_warning_is_a_coded_caveat(
    label: str, warnings: tuple[Caveat, ...]
) -> None:
    for warning in warnings:
        assert isinstance(warning, Caveat), f"{label}: {warning!r} is bare prose"
        assert CODE.match(warning.code), f"{label}: malformed code {warning.code!r}"
        # The sentence is still the sentence: nothing downstream has to learn a
        # new type to print one.
        assert isinstance(warning, str)
        assert warning.message == str(warning)
        assert warning.message.strip()


def test_a_code_names_a_kind_of_warning_not_one_sentence() -> None:
    """The same code may recur with different wording, and must.

    `_clamp` emits `gage-rr.negative-variance` once per component, naming the
    component in the sentence. That is one kind of finding reported four times,
    not four findings -- so codes are deliberately not unique per message.
    """
    forced = np.array([[[1.0, 1.0], [1.0, 1.0]], [[1.0, 1.0], [1.0, 1.0]]], dtype=float)
    report = gage_rr(forced + np.array([[[0.0, 0.1]], [[0.0, 0.1]]]))
    clamped = [w for w in report.warnings if w.code == "gage-rr.negative-variance"]
    assert len(clamped) >= 1
    assert len({str(w) for w in clamped}) == len(clamped)


def test_codes_are_namespaced_by_subject() -> None:
    """A caller filtering on a subject gets everything from that subject."""
    seen = {w.code.split(".", 1)[0] for _, warnings in REPORTS for w in warnings}
    assert {
        "capability",
        "control-chart",
        "gage-rr",
        "nonnormal",
        "sampling",
        "scheme",
        "time-weighted",
    } <= seen


def test_an_uncoded_caveat_cannot_be_built() -> None:
    with pytest.raises(ValueError, match="needs a code"):
        Caveat("", "a warning nobody can act on")


def test_a_caveat_shows_both_halves_when_debugged() -> None:
    """repr keeps the code visible; str is what a reader sees."""
    caveat = Caveat("capability.no-target", "no target was given")
    assert repr(caveat) == "Caveat('capability.no-target', 'no target was given')"
    assert str(caveat) == "no target was given"
