"""Acceptance sampling: single sampling plans by attributes.

Sources and tolerances: ``references/acceptance_sampling.yaml``.

The NIST/SEMATECH e-Handbook works one plan -- (n=52, c=3), N=10000 -- through
its OC, AOQ, AOQL and ATI tables, and those four tables are asserted here. Two
of them disagree with the handbook's own formulas; the tests reproduce the
disagreement exactly rather than widening a tolerance over it, because that is
where a real bug would hide. See the YAML header for the diagnosis.

Everything else is validated by identity: against scipy's distributions (which
did not produce the handbook's numbers), against the closed form of the Ac=0
plan, and -- for plan design -- by proving the returned plan is the *smallest*
one meeting both risk conditions, which no published table is needed to check.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import yaml
from capstat_core import (
    SamplingPlan,
    aoq_limit,
    average_outgoing_quality,
    average_total_inspection,
    design_single_sampling_plan,
    evaluate_plan,
    inspect_lot,
    oc_curve,
    probability_of_acceptance,
    quality_for_acceptance,
)
from conftest import REFERENCES
from scipy import stats

DOCUMENT = yaml.safe_load((REFERENCES / "acceptance_sampling.yaml").read_text())
CASES = {case["id"]: case for case in DOCUMENT["cases"]}


def _plan(case: dict[str, object]) -> SamplingPlan:
    inp = case["input"]
    assert isinstance(inp, dict)
    return SamplingPlan(
        sample_size=inp["sample_size"],
        acceptance_number=inp["acceptance_number"],
        lot_size=inp.get("lot_size"),
    )


# ---------------------------------------------------------------------------
# The OC curve against the NIST table
# ---------------------------------------------------------------------------


def test_oc_curve_matches_nist_table() -> None:
    case = CASES["oc-nist-52-3-binomial"]
    plan = _plan(case)
    loose = set(case["loose_rows"])
    wide = case["tolerance"]["abs"]
    tight = case["tolerance"]["per_statistic"]["tight_rows"]["abs"]
    for p, published in zip(
        case["input"]["fraction_defective"],
        case["expected"]["probability_accept"],
        strict=True,
    ):
        computed = probability_of_acceptance(plan, p)
        # Every row agrees to the handbook's printed precision...
        assert computed == pytest.approx(published, abs=wide)
        # ...and every row but the two named ones agrees to twice that, which
        # keeps the known table noise from quietly spreading.
        if p not in loose:
            assert computed == pytest.approx(published, abs=tight)


def test_no_single_model_explains_the_two_loose_rows() -> None:
    """The rows needing the full 1e-3 are table noise, not a model choice.

    My first version of this test claimed the binomial was the closest of the
    three models at both rows. It is not: the hypergeometric is closer at
    p=0.05 (0.00042 vs 0.00068) and worse at p=0.04 (0.00146 vs 0.00099). That
    is the actual argument -- *switching* model does not reconcile the table,
    because no one model wins both rows.
    """
    case = CASES["oc-nist-52-3-binomial"]
    plan = SamplingPlan(52, 3, lot_size=10_000)
    published = dict(
        zip(
            case["input"]["fraction_defective"],
            case["expected"]["probability_accept"],
            strict=True,
        )
    )
    deviations = {
        model: [
            abs(probability_of_acceptance(plan, p, model=model) - published[p])
            for p in case["loose_rows"]
        ]
        for model in ("binomial", "poisson", "hypergeometric")
    }
    # The binomial -- the model the page names -- beats the Poisson at both rows.
    binomial_beats_poisson = zip(
        deviations["binomial"], deviations["poisson"], strict=True
    )
    assert all(b < po for b, po in binomial_beats_poisson)
    # The hypergeometric wins one row and loses the other, so it is not a better
    # explanation of the column; the rows are simply printed imprecisely.
    against_binomial = zip(
        deviations["hypergeometric"], deviations["binomial"], strict=True
    )
    wins = [h < b for h, b in against_binomial]
    assert any(wins) and not all(wins)

    # And the Poisson approximation is decisively wrong further out, which is
    # what the module's warning tells the caller.
    gap = probability_of_acceptance(plan, 0.12, model="poisson") - (
        probability_of_acceptance(plan, 0.12, model="binomial")
    )
    assert gap == pytest.approx(0.0158, abs=5e-4)


def test_probability_of_acceptance_is_the_distribution_cdf() -> None:
    plan = SamplingPlan(52, 3, lot_size=10_000)
    assert probability_of_acceptance(plan, 0.03) == pytest.approx(
        stats.binom.cdf(3, 52, 0.03), rel=1e-15
    )
    assert probability_of_acceptance(plan, 0.03, model="poisson") == pytest.approx(
        stats.poisson.cdf(3, 52 * 0.03), rel=1e-15
    )
    assert probability_of_acceptance(
        plan, 0.03, model="hypergeometric"
    ) == pytest.approx(stats.hypergeom.cdf(3, 10_000, 300, 52), rel=1e-15)


def test_ac_zero_plan_is_the_closed_form() -> None:
    """Pa = (1-p)^n exactly -- the identity behind the Ac=0 warning."""
    plan = SamplingPlan(20, 0)
    for p in (0.0, 0.01, 0.05, 0.5, 1.0):
        assert probability_of_acceptance(plan, p) == pytest.approx(
            (1.0 - p) ** 20, rel=1e-12, abs=1e-15
        )


def test_oc_curve_end_points_and_monotonicity() -> None:
    plan = SamplingPlan(52, 3)
    assert probability_of_acceptance(plan, 0.0) == pytest.approx(1.0, abs=1e-15)
    assert probability_of_acceptance(plan, 1.0) == pytest.approx(0.0, abs=1e-15)
    curve = oc_curve(plan)
    assert np.all(np.diff(curve.probability_accept) <= 1e-15)
    assert curve.fraction_defective[0] == 0.0
    # The default grid stops where the plan rejects with practical certainty.
    assert curve.probability_accept[-1] == pytest.approx(0.001, abs=1e-9)


def test_type_a_and_type_b_agree_for_a_large_lot_and_part_for_a_small_one() -> None:
    """The textbook n/N <= 0.1 rule, shown rather than quoted."""
    large = SamplingPlan(52, 3, lot_size=100_000)
    small = SamplingPlan(52, 3, lot_size=200)
    for p in (0.02, 0.05, 0.1):
        assert probability_of_acceptance(large, p, model="hypergeometric") == (
            pytest.approx(probability_of_acceptance(large, p), abs=2e-3)
        )
    # At n/N = 0.26 the two models are visibly different, which is exactly when
    # the module warns.
    gap = abs(
        probability_of_acceptance(small, 0.08, model="hypergeometric")
        - probability_of_acceptance(small, 0.08)
    )
    assert gap > 0.01
    assert any("hypergeometric" in w for w in evaluate_plan(small, 0.01, 0.08).warnings)


# ---------------------------------------------------------------------------
# AOQ: reproducing a published table that used a different formula
# ---------------------------------------------------------------------------


def test_published_aoq_column_is_the_large_lot_approximation() -> None:
    """The diagnosis, asserted to the printed digit: the column is Pa*p.

    No tolerance is spent on the published values here. Every row but the two
    documented exceptions is reproduced *exactly* by rounding Pa*p to the four
    decimals the handbook prints -- which is a far stronger statement than
    "agrees within 5e-5", and it is what makes the two exceptions visible
    instead of absorbed.
    """
    case = CASES["aoq-nist-52-3"]
    plan = _plan(case)
    exceptions = set(case["expected"]["approximation_exceptions"])
    for p, published in zip(
        case["input"]["fraction_defective"],
        case["expected"]["published_aoq"],
        strict=True,
    ):
        approximation = probability_of_acceptance(plan, p) * p
        if p not in exceptions:
            assert round(approximation, 4) == pytest.approx(published, abs=1e-12)
        # Whatever the handbook printed, our exact value is the approximation
        # scaled by the finite-lot factor. That identity holds at every row.
        assert average_outgoing_quality(plan, p) == pytest.approx(
            approximation * (10_000 - 52) / 10_000, rel=1e-14
        )


def test_the_p_003_aoq_row_comes_from_the_prose_example_not_the_column() -> None:
    """One row has a different provenance -- and the difference is one digit."""
    case = CASES["aoq-nist-52-3"]
    plan = _plan(case)
    p = case["expected"]["prose_row_p"]
    published = case["expected"]["published_aoq"][
        case["input"]["fraction_defective"].index(p)
    ]
    # The page's prose: exact formula, but with Pa rounded to the printed 0.930.
    prose = round(probability_of_acceptance(plan, p), 3) * p * (10_000 - 52) / 10_000
    assert prose == pytest.approx(
        case["expected"]["prose_row_aoq"],
        abs=case["tolerance"]["per_statistic"]["prose_row_aoq"]["abs"],
    )
    assert round(prose, 4) == pytest.approx(published, abs=1e-12)
    # The column's own formula would have printed 0.0279 in this row.
    assert round(probability_of_acceptance(plan, p) * p, 4) == pytest.approx(
        0.0279, abs=1e-12
    )
    # Ours differs from the prose value only because our Pa is not rounded.
    assert average_outgoing_quality(plan, p) == pytest.approx(prose, abs=5e-5)


def test_the_first_aoq_row_is_a_transposition_error() -> None:
    """0.0010 where the formula gives 0.0100 -- the same digits, reordered."""
    case = CASES["aoq-nist-52-3"]
    plan = _plan(case)
    p = case["expected"]["transposed_row_p"]
    approximation = probability_of_acceptance(plan, p) * p
    assert round(approximation, 4) == pytest.approx(
        case["expected"]["transposed_row_approximation"], abs=1e-12
    )
    exact = average_outgoing_quality(plan, p)
    assert exact == pytest.approx(
        case["expected"]["transposed_row_exact"],
        abs=case["tolerance"]["per_statistic"]["transposed_row_exact"]["abs"],
    )
    # Neither formula can be reconciled with what was printed: they differ by
    # an order of magnitude, not by rounding.
    published = case["expected"]["transposed_row_published"]
    assert abs(exact - published) > 0.008
    assert exact / published == pytest.approx(9.93, abs=0.01)


def test_aoql_is_a_maximum_and_matches_the_published_reading() -> None:
    case = CASES["aoql-nist-52-3"]
    plan = _plan(case)
    limit = aoq_limit(plan)

    # An identity first: it dominates the whole curve. True for any plan, and
    # it does not depend on anyone's published number.
    grid = np.linspace(0.0, 1.0, 501)
    highest_on_grid = max(average_outgoing_quality(plan, float(p)) for p in grid)
    assert limit.aoql >= highest_on_grid - 1e-12

    assert limit.aoql == pytest.approx(
        case["expected"]["exact_aoql"], abs=case["tolerance"]["abs"]
    )
    assert limit.at_fraction_defective == pytest.approx(
        case["expected"]["exact_at_fraction_defective"],
        abs=case["tolerance"]["per_statistic"]["exact_at_fraction_defective"]["abs"],
    )
    # The handbook's 0.0372 at p=0.06 is the same peak read off a 0.01 grid
    # under the Pa*p approximation -- reproduced on its own terms.
    published_reading = (
        probability_of_acceptance(
            plan, case["expected"]["published_at_fraction_defective"]
        )
        * case["expected"]["published_at_fraction_defective"]
    )
    assert published_reading == pytest.approx(
        case["expected"]["published_aoql"], abs=case["tolerance"]["abs"]
    )


def test_aoql_on_the_hypergeometric_model_stays_on_the_grid() -> None:
    """A step function has no peak to refine; the grid maximum is the answer."""
    plan = SamplingPlan(20, 1, lot_size=200)
    limit = aoq_limit(plan, model="hypergeometric")
    assert limit.aoql > 0.0
    assert limit.at_fraction_defective == pytest.approx(
        round(limit.at_fraction_defective, 3), abs=1e-12
    )


# ---------------------------------------------------------------------------
# ATI
# ---------------------------------------------------------------------------


def test_ati_matches_nist_table_and_needs_unrounded_pa() -> None:
    """Asserted exactly: each printed integer is floor or round of our value.

    The column is truncated, not rounded -- 5007.62 prints as 5007 -- with the
    p=0.03 row rounded because the page works it through in prose. Rather than
    tolerate up to a full unit everywhere, each entry has to be one of the two
    integers our value can legitimately print as.
    """
    case = CASES["ati-nist-52-3"]
    plan = _plan(case)
    residual_bound = case["expected"]["max_residual"]
    for p, published in zip(
        case["input"]["fraction_defective"],
        case["expected"]["average_total_inspection"],
        strict=True,
    ):
        computed = average_total_inspection(plan, p)
        assert published in (math.floor(computed), round(computed))
        assert abs(computed - published) < residual_bound

    # The handbook says 753 "was obtained using more decimal places". Using its
    # own rounded Pa = 0.930 gives 748.4 -- neither floor nor round of anything
    # this plan produces, so the table checks the precision of Pa as well as the
    # ATI formula.
    from_rounded = 52 + (1 - 0.930) * (10_000 - 52)
    assert from_rounded == pytest.approx(
        case["expected"]["ati_from_rounded_pa_at_003"],
        abs=case["tolerance"]["per_statistic"]["ati_from_rounded_pa_at_003"]["abs"],
    )
    assert abs(from_rounded - 753) > residual_bound


def test_ati_end_points() -> None:
    plan = SamplingPlan(52, 3, lot_size=10_000)
    assert average_total_inspection(plan, 0.0) == pytest.approx(52.0)
    assert average_total_inspection(plan, 1.0) == pytest.approx(10_000.0)


# ---------------------------------------------------------------------------
# Independent implementations, at eight significant digits
# ---------------------------------------------------------------------------


def test_r_acceptancesampling_assess_of_the_20_0_plan() -> None:
    """Eight digits from an unrelated implementation -- and from algebra."""
    case = CASES["oc-r-acceptancesampling-20-0"]
    plan = _plan(case)
    tol = case["tolerance"]["abs"]
    prp_quality, prp_required = case["input"]["producer_risk_point"]
    crp_quality, crp_allowed = case["input"]["consumer_risk_point"]

    expected = case["expected"]
    pa_prp = probability_of_acceptance(plan, prp_quality)
    pa_crp = probability_of_acceptance(plan, crp_quality)
    assert pa_prp == pytest.approx(expected["probability_accept_at_prp"], abs=tol)
    assert pa_crp == pytest.approx(expected["probability_accept_at_crp"], abs=tol)

    # The same two numbers from the closed form, which no software produced.
    assert pa_prp == pytest.approx((1 - prp_quality) ** 20, rel=1e-15)
    assert pa_crp == pytest.approx((1 - crp_quality) ** 20, rel=1e-15)

    # "Plan CANNOT meet desired risk point(s)" -- a verdict, asserted exactly.
    assert (pa_prp >= prp_required) is expected["meets_producer_risk_point"]
    assert (pa_crp <= crp_allowed) is expected["meets_consumer_risk_point"]


def test_design_matches_r_acceptancesampling_find_plan() -> None:
    case = CASES["design-r-acceptancesampling-binom"]
    inp, exp = case["input"], case["expected"]
    plan = design_single_sampling_plan(
        inp["aql"],
        inp["ltpd"],
        producer_risk=inp["producer_risk"],
        consumer_risk=inp["consumer_risk"],
    )
    assert plan.sample_size == exp["sample_size"]
    assert plan.acceptance_number == exp["acceptance_number"]
    assert plan.rejection_number == exp["rejection_number"]


def test_design_matches_accsamplingdesign_including_the_achieved_risks() -> None:
    case = CASES["design-accsamplingdesign-binom"]
    inp, exp, tol = case["input"], case["expected"], case["tolerance"]["abs"]
    plan = design_single_sampling_plan(
        inp["aql"],
        inp["ltpd"],
        producer_risk=inp["producer_risk"],
        consumer_risk=inp["consumer_risk"],
    )
    assert plan.sample_size == exp["sample_size"]
    assert plan.acceptance_number == exp["acceptance_number"]
    report = evaluate_plan(plan, inp["aql"], inp["ltpd"])
    assert report.producer_risk == pytest.approx(exp["achieved_producer_risk"], abs=tol)
    assert report.consumer_risk == pytest.approx(exp["achieved_consumer_risk"], abs=tol)
    assert probability_of_acceptance(plan, 0.03) == pytest.approx(
        exp["probability_accept_at_003"], abs=tol
    )


def test_rectifying_quantities_match_minitab() -> None:
    """The only independent AOQL found that also publishes where it occurs."""
    case = CASES["rectifying-minitab-5000-52-2"]
    plan = _plan(case)
    inp, exp = case["input"], case["expected"]
    per = case["tolerance"]["per_statistic"]

    assert probability_of_acceptance(plan, inp["aql"]) == pytest.approx(
        exp["probability_accept_at_aql"], abs=per["probability_accept_at_aql"]["abs"]
    )
    assert probability_of_acceptance(plan, inp["rql"]) == pytest.approx(
        exp["probability_accept_at_rql"], abs=per["probability_accept_at_rql"]["abs"]
    )
    assert 100 * average_outgoing_quality(plan, inp["aql"]) == pytest.approx(
        exp["aoq_percent_at_aql"], abs=case["tolerance"]["abs"]
    )
    assert 100 * average_outgoing_quality(plan, inp["rql"]) == pytest.approx(
        exp["aoq_percent_at_rql"], abs=case["tolerance"]["abs"]
    )
    assert average_total_inspection(plan, inp["aql"]) == pytest.approx(
        exp["ati_at_aql"], abs=per["ati_at_aql"]["abs"]
    )
    assert average_total_inspection(plan, inp["rql"]) == pytest.approx(
        exp["ati_at_rql"], abs=per["ati_at_rql"]["abs"]
    )

    limit = aoq_limit(plan)
    assert 100 * limit.aoql == pytest.approx(
        exp["aoql_percent"], abs=case["tolerance"]["abs"]
    )
    assert 100 * limit.at_fraction_defective == pytest.approx(
        exp["aoql_at_percent_defective"], abs=per["aoql_at_percent_defective"]["abs"]
    )


def test_design_on_a_finite_lot_is_also_the_smallest_plan() -> None:
    """Type A design, validated by minimality rather than by a citation.

    No published Type A worked example with c>0 turned up (see the YAML), so
    this proves the property directly: the plan meets both risk points, and one
    item less at the same acceptance number does not.
    """
    plan = design_single_sampling_plan(
        0.05,
        0.15,
        producer_risk=0.05,
        consumer_risk=0.20,
        model="hypergeometric",
        lot_size=500,
    )
    assert plan.lot_size == 500
    assert probability_of_acceptance(plan, 0.05, model="hypergeometric") >= 0.95
    assert probability_of_acceptance(plan, 0.15, model="hypergeometric") <= 0.20
    smaller = SamplingPlan(plan.sample_size - 1, plan.acceptance_number, lot_size=500)
    assert probability_of_acceptance(smaller, 0.15, model="hypergeometric") > 0.20


def test_design_gives_up_when_the_lot_is_too_small_to_sample_enough() -> None:
    """A finite lot bounds n -- and the search has to know that up front.

    Found by writing this test: separating 1 % from 3 % at these risks needs 76
    items at Ac=0 and more at every higher Ac, none of which a lot of 200 can
    supply. The search used to build a candidate plan with n > N and die inside
    the constructor -- "lot_size (200) must be at least sample_size (256)" --
    a message about an internal probe, not about the request. It now caps the
    sample size at the lot and reports the real answer.
    """
    with pytest.raises(ValueError, match="too close together") as raised:
        design_single_sampling_plan(
            0.01,
            0.03,
            producer_risk=0.05,
            consumer_risk=0.10,
            lot_size=200,
            max_acceptance_number=8,
        )
    assert "capped at the lot size, 200" in str(raised.value)
    # Unbounded, the same request has an answer -- it just needs more items than
    # that lot contains.
    unbounded = design_single_sampling_plan(
        0.01, 0.03, producer_risk=0.05, consumer_risk=0.10, max_acceptance_number=8
    )
    assert unbounded.sample_size > 200


def test_a_small_lot_cannot_express_every_quality_level() -> None:
    """Found by a failing test of my own: the Type A quantisation trap.

    A lot of 50 items cannot be 1 % defective -- the nearest whole number of
    defectives is zero. Designing against such an AQL used to return a
    confident-looking plan whose producer's condition was satisfied by a
    *perfect* lot and therefore constrained nothing at all. It now refuses, and
    a plan merely evaluated at such a level says which quality was really used.
    """
    with pytest.raises(ValueError, match="indistinguishable from a perfect lot"):
        design_single_sampling_plan(0.01, 0.05, model="hypergeometric", lot_size=50)
    # The same trap on the consumer's side.
    with pytest.raises(ValueError, match="nearest whole number of defectives"):
        design_single_sampling_plan(0.001, 0.005, model="hypergeometric", lot_size=80)

    report = evaluate_plan(
        SamplingPlan(20, 1, lot_size=50), 0.01, 0.11, model="hypergeometric"
    )
    assert any("nearest attainable lot quality, 0/50" in w for w in report.warnings)
    assert any("6/50" in w for w in report.warnings)
    # And it stays quiet when the levels do land on the lot's own grid.
    quiet = evaluate_plan(
        SamplingPlan(20, 1, lot_size=100), 0.01, 0.10, model="hypergeometric"
    )
    assert not any("nearest attainable" in w for w in quiet.warnings)


def test_hypergeometric_matches_a_hand_written_enumeration() -> None:
    """No published Type A example with c>0 exists in our sources; enumerate it.

    The reference YAML says so plainly. In its place the definition itself is
    the second source: Pa = sum_d C(D,d) C(N-D,n-d) / C(N,n), written out here
    with integer arithmetic that shares nothing with scipy's implementation.
    """
    lot_size, defectives_in_lot, sample, acceptance = 200, 24, 20, 3
    plan = SamplingPlan(sample, acceptance, lot_size=lot_size)
    enumerated = sum(
        math.comb(defectives_in_lot, d)
        * math.comb(lot_size - defectives_in_lot, sample - d)
        for d in range(acceptance + 1)
    ) / math.comb(lot_size, sample)
    assert probability_of_acceptance(
        plan, defectives_in_lot / lot_size, model="hypergeometric"
    ) == pytest.approx(enumerated, rel=1e-14)
    # And it is a real test of the sum: c=0 would have been a single term.
    assert acceptance > 0


# ---------------------------------------------------------------------------
# The decision -- exact, never approximate
# ---------------------------------------------------------------------------


def test_decision_boundary_is_exact() -> None:
    case = CASES["decision-nist-52-3"]
    plan = _plan(case)
    assert plan.rejection_number == case["expected"]["rejection_number"]
    for defectives in case["expected"]["accept_on"]:
        decision = inspect_lot(plan, defectives)
        assert decision.accepted is True
        assert decision.defectives == defectives
    for defectives in case["expected"]["reject_on"]:
        assert inspect_lot(plan, defectives).accepted is False
    assert inspect_lot(plan, 2).sample_fraction_defective == pytest.approx(2 / 52)


def test_decision_carries_what_it_does_not_mean() -> None:
    plan = SamplingPlan(52, 3)
    accepted = inspect_lot(plan, 1)
    rejected = inspect_lot(plan, 9)
    assert any("not evidence that this lot is good" in w for w in accepted.warnings)
    assert any("does not measure how defective" in w for w in rejected.warnings)


# ---------------------------------------------------------------------------
# Plan design: validated by minimality, not by a table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("aql", "ltpd", "alpha", "beta"),
    [
        (0.01, 0.06, 0.05, 0.10),
        (0.018, 0.09, 0.05, 0.10),
        (0.005, 0.02, 0.05, 0.10),
        (0.02, 0.08, 0.10, 0.05),
    ],
)
def test_designed_plan_is_the_smallest_meeting_both_risks(
    aql: float, ltpd: float, alpha: float, beta: float
) -> None:
    plan = design_single_sampling_plan(
        aql, ltpd, producer_risk=alpha, consumer_risk=beta
    )
    # It meets both conditions...
    assert probability_of_acceptance(plan, aql) >= 1 - alpha
    assert probability_of_acceptance(plan, ltpd) <= beta

    # ...one fewer item, same Ac, fails the consumer's condition...
    smaller = SamplingPlan(plan.sample_size - 1, plan.acceptance_number)
    assert probability_of_acceptance(smaller, ltpd) > beta

    # ...and no smaller acceptance number admits any plan at all, so this really
    # is the minimum. (For each lower Ac, the smallest n meeting the consumer's
    # condition still fails the producer's.)
    for ac in range(plan.acceptance_number):
        n = ac + 1
        while probability_of_acceptance(SamplingPlan(n, ac), ltpd) > beta:
            n += 1
        assert probability_of_acceptance(SamplingPlan(n, ac), aql) < 1 - alpha


def test_design_round_trips_through_evaluate() -> None:
    plan = design_single_sampling_plan(0.01, 0.06, lot_size=5_000)
    report = evaluate_plan(plan, 0.01, 0.06, model="binomial")
    assert report.producer_risk <= 0.05
    assert report.consumer_risk <= 0.10
    assert report.aql < report.indifference_quality < report.ltpd
    assert report.aoql is not None
    assert report.ati_at_aql is not None


def test_quality_for_acceptance_inverts_the_oc_curve() -> None:
    plan = SamplingPlan(52, 3)
    for target in (0.95, 0.5, 0.10, 0.01):
        p = quality_for_acceptance(plan, target)
        assert probability_of_acceptance(plan, p) == pytest.approx(target, abs=1e-9)


def test_quality_for_acceptance_has_no_answer_for_a_plan_that_never_rejects() -> None:
    assert quality_for_acceptance(SamplingPlan(5, 5), 0.10) == 1.0


# ---------------------------------------------------------------------------
# Warnings: saying what the numbers do not say
# ---------------------------------------------------------------------------


def test_report_warns_about_the_ac_zero_shape() -> None:
    report = evaluate_plan(SamplingPlan(50, 0), 0.001, 0.05)
    assert any("Ac = 0 plan" in w for w in report.warnings)


def test_report_warns_that_a_plan_can_never_reject() -> None:
    report = evaluate_plan(SamplingPlan(5, 5), 0.01, 0.10)
    assert any("can never reject" in w for w in report.warnings)


def test_report_warns_about_the_poisson_approximation() -> None:
    report = evaluate_plan(SamplingPlan(52, 3), 0.01, 0.09, model="poisson")
    assert any("Poisson approximation" in w for w in report.warnings)


def test_report_warns_that_the_aoql_bounds_no_single_lot() -> None:
    report = evaluate_plan(SamplingPlan(52, 3, lot_size=10_000), 0.01, 0.09)
    assert any("bounds no single lot" in w for w in report.warnings)
    assert any("rectifying inspection" in w for w in report.warnings)


def test_report_warns_when_the_plan_rejects_most_lots_at_the_aql() -> None:
    report = evaluate_plan(SamplingPlan(200, 1), 0.02, 0.05)
    assert any("rejects more than half" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_plan_rejects_impossible_parameters() -> None:
    with pytest.raises(ValueError, match="sample_size must be >= 1"):
        SamplingPlan(0, 0)
    with pytest.raises(ValueError, match="acceptance_number must be >= 0"):
        SamplingPlan(10, -1)
    with pytest.raises(ValueError, match="cannot exceed sample_size"):
        SamplingPlan(5, 6)
    with pytest.raises(ValueError, match="at least sample_size"):
        SamplingPlan(50, 1, lot_size=20)


def test_defective_counts_outside_the_sample_are_rejected() -> None:
    plan = SamplingPlan(10, 1)
    with pytest.raises(ValueError, match="defectives must be >= 0"):
        plan.accepts(-1)
    with pytest.raises(ValueError, match="cannot exceed the sample size"):
        plan.accepts(11)


def test_fraction_defective_must_be_a_fraction() -> None:
    plan = SamplingPlan(10, 1)
    with pytest.raises(ValueError, match="must be a fraction"):
        probability_of_acceptance(plan, 1.5)
    with pytest.raises(ValueError, match="must be a fraction"):
        probability_of_acceptance(plan, float("nan"))


def test_finite_lot_quantities_need_a_lot_size() -> None:
    plan = SamplingPlan(10, 1)
    with pytest.raises(ValueError, match="needs a lot_size"):
        average_outgoing_quality(plan, 0.05)
    with pytest.raises(ValueError, match="needs a lot_size"):
        average_total_inspection(plan, 0.05)
    with pytest.raises(ValueError, match="needs a lot_size"):
        aoq_limit(plan)
    with pytest.raises(ValueError, match="needs a lot_size"):
        probability_of_acceptance(plan, 0.05, model="hypergeometric")


def test_unknown_model_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown model"):
        probability_of_acceptance(SamplingPlan(10, 1), 0.05, model="normal")  # type: ignore[arg-type]


def test_oc_curve_validates_its_grid() -> None:
    plan = SamplingPlan(10, 1)
    with pytest.raises(ValueError, match="one-dimensional"):
        oc_curve(plan, [[0.1, 0.2]])
    with pytest.raises(ValueError, match="must not be empty"):
        oc_curve(plan, [])
    with pytest.raises(ValueError, match="must be a fraction"):
        oc_curve(plan, [0.1, 2.0])
    curve = oc_curve(plan, [0.0, 0.1])
    assert curve.fraction_defective.tolist() == [0.0, 0.1]
    assert curve.model == "binomial"


def test_design_rejects_unusable_requests() -> None:
    with pytest.raises(ValueError, match="must be in"):
        design_single_sampling_plan(0.01, 0.06, producer_risk=0.0)
    with pytest.raises(ValueError, match="must be in"):
        design_single_sampling_plan(0.01, 0.06, consumer_risk=1.0)
    with pytest.raises(ValueError, match="strictly below"):
        design_single_sampling_plan(0.06, 0.01)
    with pytest.raises(ValueError, match="needs a lot_size"):
        design_single_sampling_plan(0.01, 0.06, model="hypergeometric")
    with pytest.raises(ValueError, match="too close together"):
        design_single_sampling_plan(
            0.01,
            0.0101,
            producer_risk=0.01,
            consumer_risk=0.01,
            max_acceptance_number=3,
            max_sample_size=500,
        )


def test_evaluate_rejects_unordered_quality_levels() -> None:
    with pytest.raises(ValueError, match="strictly below"):
        evaluate_plan(SamplingPlan(52, 3), 0.06, 0.01)
