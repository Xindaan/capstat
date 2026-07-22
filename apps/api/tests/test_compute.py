"""Compute endpoints: shape, and fidelity to the core they wrap.

The recurring assertion is not "the endpoint returns 200" but "the endpoint
returns exactly what the core computed" -- same numbers, same warnings, same
nulls. The API is a serialisation layer; a test that only checked status codes
would let it quietly diverge from the library.
"""

from __future__ import annotations

import math
from typing import ClassVar

from capstat_core import (
    SamplingPlan,
    apply_switching_rules,
    bias,
    capability,
    cusum_chart,
    describe,
    design_single_sampling_plan,
    evaluate_plan,
    ewma_chart,
    gage_rr,
    gage_rr_range,
    i_mr_chart,
    inspect_lot,
    linearity,
    oc_curve,
    stability,
    xbar_r_chart,
    xbar_s_chart,
)
from fastapi.testclient import TestClient

# A mildly non-normal but well-behaved series reused across cases.
SERIES = [10.0 + (i % 5) * 0.1 + (i % 3) * 0.05 for i in range(60)]

# A balanced Gage R&R layout (parts x operators x trials); the SPC/AIAG example.
GAGE_DATA = [
    [[3.29, 3.41, 3.64], [3.08, 3.25, 3.07], [3.04, 2.89, 2.85]],
    [[2.44, 2.32, 2.42], [2.53, 1.78, 2.32], [1.62, 1.87, 2.04]],
    [[4.34, 4.17, 4.27], [4.19, 3.94, 4.34], [3.88, 4.09, 3.67]],
    [[3.47, 3.50, 3.64], [3.01, 4.03, 3.20], [3.14, 3.20, 3.11]],
    [[2.20, 2.08, 2.16], [2.44, 1.80, 1.72], [1.54, 1.93, 1.55]],
]


def test_descriptive_matches_core(client: TestClient) -> None:
    body = client.post("/compute/descriptive", json={"data": SERIES}).json()
    core = describe(SERIES)
    assert body["n"] == core.n
    assert body["mean"] == core.mean
    assert body["std_dev"] == core.std_dev
    assert body["skewness"] == core.skewness


def test_capability_matches_core_and_keeps_warnings(client: TestClient) -> None:
    resp = client.post(
        "/compute/capability",
        json={"data": SERIES, "lsl": 9.5, "usl": 11.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    core = capability(SERIES, lsl=9.5, usl=11.0)
    assert body["cpk"] == core.cpk
    assert body["within_method"] == core.within_method
    # The warnings tuple must survive as a JSON array, not be flattened away.
    assert body["warnings"] == list(core.warnings)
    # The derived property is not a dataclass field; it must still be present.
    assert body["stability_ratio"] == core.stability_ratio


def test_capability_one_sided_spec_yields_null_indices(client: TestClient) -> None:
    # Only an upper limit: cp/cpl are undefined and must serialise as null,
    # which is not the same as 0.0.
    body = client.post(
        "/compute/capability",
        json={"data": SERIES, "usl": 11.0},
    ).json()
    assert body["cp"] is None
    assert body["cpl"] is None
    assert body["cpu"] is not None
    assert body["lsl"] is None


def test_capability_accepts_subgroups(client: TestClient) -> None:
    subgroups = [[10.0, 10.1, 9.9, 10.2, 10.0] for _ in range(20)]
    resp = client.post(
        "/compute/capability",
        json={"data": subgroups, "lsl": 9.0, "usl": 11.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["subgroup_size"] == 5
    assert body["subgroups"] == 20


def test_capability_analyze_reports_path(client: TestClient) -> None:
    body = client.post(
        "/compute/capability/analyze",
        json={"data": SERIES, "lsl": 9.5, "usl": 11.0},
    ).json()
    assert body["path"] in {"normal", "box-cox", "percentile"}
    assert body["normality"] is not None
    # Exactly the branch named by `path` is populated; the others are null.
    populated = [k for k in ("normal", "box_cox", "percentile") if body[k]]
    assert len(populated) == 1


def test_i_mr_chart_shape_and_nesting(client: TestClient) -> None:
    body = client.post("/compute/control-chart/i-mr", json={"data": SERIES}).json()
    core = i_mr_chart(SERIES)
    assert body["location"]["in_control"] == core.location.in_control
    assert body["dispersion"]["limits"]["center"] == core.dispersion.limits.center
    assert body["in_control"] == core.in_control


def test_xbar_r_matches_core(client: TestClient) -> None:
    subgroups = [[10.0 + (i % 3) * 0.1, 10.1, 9.9, 10.2] for i in range(15)]
    body = client.post(
        "/compute/control-chart/xbar-r", json={"subgroups": subgroups}
    ).json()
    core = xbar_r_chart(subgroups)
    assert body["location"]["points"] == list(core.location.points)
    assert body["dispersion"]["name"] == core.dispersion.name
    assert body["subgroup_size"] == 4


def test_xbar_s_matches_core(client: TestClient) -> None:
    subgroups = [[10.0, 10.1, 9.9, 10.2, 10.05, 9.95] for _ in range(12)]
    body = client.post(
        "/compute/control-chart/xbar-s", json={"subgroups": subgroups}
    ).json()
    core = xbar_s_chart(subgroups)
    assert body["sigma_within"] == core.sigma_within
    assert body["in_control"] == core.in_control


def test_ewma_matches_core(client: TestClient) -> None:
    body = client.post(
        "/compute/control-chart/ewma",
        json={"data": SERIES, "target": 10.0, "sigma": 0.2},
    ).json()
    core = ewma_chart(SERIES, target=10.0, sigma=0.2)
    assert body["points"] == list(core.points)
    assert body["steady_state_limits"] == list(core.steady_state_limits)
    assert body["violations"] == list(core.violations)


def test_cusum_matches_core(client: TestClient) -> None:
    body = client.post(
        "/compute/control-chart/cusum",
        json={"data": SERIES, "target": 10.0, "sigma": 0.2},
    ).json()
    core = cusum_chart(SERIES, target=10.0, sigma=0.2)
    assert body["upper"] == list(core.upper)
    assert body["H"] == core.H


def test_nan_serialises_as_null(client: TestClient) -> None:
    # A constant series has zero variance -> skewness/kurtosis are nan, which
    # JSON cannot hold; the API coerces them to null.
    body = client.post(
        "/compute/descriptive", json={"data": [5.0, 5.0, 5.0, 5.0]}
    ).json()
    assert body["skewness"] is None
    assert body["kurtosis"] is None
    assert body["mean"] == 5.0
    assert not math.isnan(body["mean"])


class TestRules:
    """The 8-vs-9 discriminant, carried through the HTTP layer.

    Western Electric rule 4 fires on eight consecutive points on one side;
    Nelson rule 2 needs nine. A run of exactly eight must trip one and not the
    other -- the off-by-one that nothing downstream would reveal.
    """

    LIMITS: ClassVar[dict[str, float]] = {
        "center": 0.0,
        "lower": -3.0,
        "upper": 3.0,
    }

    def test_eight_points_fire_we_not_nelson(self, client: TestClient) -> None:
        points = [0.5] * 8
        we = client.post(
            "/compute/rules/western-electric",
            json={"points": points, "limits": self.LIMITS},
        ).json()
        nelson = client.post(
            "/compute/rules/nelson",
            json={"points": points, "limits": self.LIMITS},
        ).json()
        assert 4 in {v["rule"] for v in we}
        assert nelson == []

    def test_nine_points_fire_nelson_rule_2(self, client: TestClient) -> None:
        points = [0.5] * 9
        nelson = client.post(
            "/compute/rules/nelson",
            json={"points": points, "limits": self.LIMITS},
        ).json()
        assert 2 in {v["rule"] for v in nelson}


def test_gage_rr_anova_matches_core(client: TestClient) -> None:
    resp = client.post("/compute/gage-rr", json={"data": GAGE_DATA})
    assert resp.status_code == 200
    body = resp.json()
    core = gage_rr(GAGE_DATA)
    assert body["method"] == "anova"
    assert body["var_repeatability"] == core.var_repeatability
    assert body["var_part"] == core.var_part
    # Derived properties are not dataclass fields; they must still serialise.
    assert body["var_gage_rr"] == core.var_gage_rr
    assert body["pct_study_var_gage_rr"] == core.pct_study_var_gage_rr
    assert body["ndc"] == core.ndc
    assert body["interaction_pvalue"] == core.interaction_pvalue
    assert body["warnings"] == list(core.warnings)


def test_gage_rr_average_range_matches_core(client: TestClient) -> None:
    resp = client.post(
        "/compute/gage-rr", json={"data": GAGE_DATA, "method": "average_range"}
    )
    assert resp.status_code == 200
    body = resp.json()
    core = gage_rr_range(GAGE_DATA)
    assert body["method"] == "average_range"
    # The average-and-range method models no interaction.
    assert body["interaction_pvalue"] is None
    assert body["var_gage_rr"] == core.var_gage_rr
    assert body["ndc"] == core.ndc


def test_gage_rr_no_variation_serialises_nan_as_null(client: TestClient) -> None:
    # Every value identical -> undefined percentages must be null, not a 500.
    flat = [[[5.0, 5.0], [5.0, 5.0]], [[5.0, 5.0], [5.0, 5.0]]]
    resp = client.post("/compute/gage-rr", json={"data": flat})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pct_contribution_gage_rr"] is None
    assert body["ndc"] is None


def test_gage_rr_too_few_operators_maps_core_error_to_422(client: TestClient) -> None:
    # Two parts but a single operator: passes the schema, the core rejects it,
    # and that ValueError must surface as a 422, not a 500.
    resp = client.post("/compute/gage-rr", json={"data": [[[1.0, 2.0]], [[3.0, 4.0]]]})
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)


BIAS_READINGS = [36.1, 35.9, 36.0, 36.05, 35.95, 36.2, 35.85]
LINEARITY_REFS = [7.0, 9.0, 11.0, 13.0, 15.0]
LINEARITY_READINGS = [
    [7.5, 7.4],
    [9.2, 9.1],
    [11.0, 11.05],
    [12.7, 12.75],
    [14.4, 14.35],
]


def test_bias_matches_core(client: TestClient) -> None:
    resp = client.post(
        "/compute/bias", json={"measurements": BIAS_READINGS, "reference": 36.0}
    )
    assert resp.status_code == 200
    body = resp.json()
    core = bias(BIAS_READINGS, 36.0)
    assert body["bias"] == core.bias
    assert body["t_statistic"] == core.t_statistic
    assert body["p_value"] == core.p_value
    assert body["ci_lower"] == core.ci_lower
    # A derived property, not a field.
    assert body["bias_significant"] == core.bias_significant
    assert body["warnings"] == list(core.warnings)


def test_bias_degenerate_serialises_infinite_t_as_null(client: TestClient) -> None:
    # Identical readings off the reference: t is infinite, which JSON cannot
    # hold. The verdict is interval-based and survives.
    body = client.post(
        "/compute/bias", json={"measurements": [7.0, 7.0, 7.0], "reference": 5.0}
    ).json()
    assert body["t_statistic"] is None
    assert body["bias_significant"] is True


def test_linearity_matches_core(client: TestClient) -> None:
    resp = client.post(
        "/compute/linearity",
        json={
            "references": LINEARITY_REFS,
            "measurements": LINEARITY_READINGS,
            "process_variation": 6.0,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    core = linearity(LINEARITY_REFS, LINEARITY_READINGS, process_variation=6.0)
    assert body["slope"] == core.slope
    assert body["intercept"] == core.intercept
    assert body["percent_linearity"] == core.percent_linearity
    assert body["linearity"] == core.linearity
    assert body["part_mean_biases"] == list(core.part_mean_biases)
    assert body["linearity_significant"] == core.linearity_significant


def test_linearity_without_process_variation_is_null(client: TestClient) -> None:
    body = client.post(
        "/compute/linearity",
        json={"references": LINEARITY_REFS, "measurements": LINEARITY_READINGS},
    ).json()
    assert body["linearity"] is None
    assert body["percent_linearity"] is not None


def test_linearity_equal_references_maps_core_error_to_422(
    client: TestClient,
) -> None:
    resp = client.post(
        "/compute/linearity",
        json={"references": [5.0, 5.0], "measurements": [[5.0, 5.1], [5.2, 4.9]]},
    )
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)


def test_stability_matches_core_and_nests_the_chart(client: TestClient) -> None:
    readings = [10.0 + 0.05 * (i % 3 - 1) for i in range(25)]
    resp = client.post("/compute/stability", json={"measurements": readings})
    assert resp.status_code == 200
    body = resp.json()
    core = stability(readings)
    assert body["stable"] == core.stable
    # The whole ChartPair must survive nesting, derived properties included.
    assert body["chart"]["in_control"] == core.chart.in_control
    assert body["chart"]["location"]["limits"]["center"] == (
        core.chart.location.limits.center
    )


def test_stability_accepts_subgroups(client: TestClient) -> None:
    subgroups = [[10.0, 10.1, 9.9] for _ in range(15)]
    body = client.post("/compute/stability", json={"measurements": subgroups}).json()
    assert body["chart"]["subgroup_size"] == 3


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"


def test_rules_catalogue(client: TestClient) -> None:
    body = client.get("/rules/catalogue").json()
    assert set(body) == {"nelson", "western_electric"}
    # Nelson has eight rules, Western Electric four.
    assert len(body["nelson"]) == 8
    assert len(body["western_electric"]) == 4


# ---------------------------------------------------------------------------
# Acceptance sampling
# ---------------------------------------------------------------------------

# The NIST handbook's worked plan, the one the core's reference tests use.
SAMPLING_PLAN = {"sample_size": 52, "acceptance_number": 3, "lot_size": 10000}


def test_acceptance_sampling_evaluate_matches_core(client: TestClient) -> None:
    resp = client.post(
        "/compute/acceptance-sampling/evaluate",
        json={"plan": SAMPLING_PLAN, "aql": 0.01, "ltpd": 0.09},
    )
    assert resp.status_code == 200
    body = resp.json()
    core = evaluate_plan(SamplingPlan(52, 3, lot_size=10000), 0.01, 0.09)
    assert body["producer_risk"] == core.producer_risk
    assert body["consumer_risk"] == core.consumer_risk
    assert body["probability_accept_at_aql"] == core.probability_accept_at_aql
    assert body["indifference_quality"] == core.indifference_quality
    assert body["limiting_quality"] == core.limiting_quality
    assert core.aoql is not None
    assert body["aoql"]["aoql"] == core.aoql.aoql
    assert body["aoql"]["at_fraction_defective"] == core.aoql.at_fraction_defective
    assert body["ati_at_aql"] == core.ati_at_aql
    assert body["warnings"] == list(core.warnings)
    # rejection_number is a derived property, not a dataclass field.
    assert body["plan"]["rejection_number"] == core.plan.rejection_number


def test_acceptance_sampling_without_a_lot_size_nulls_the_finite_lot_fields(
    client: TestClient,
) -> None:
    # AOQL and ATI describe rectifying inspection of a finite lot. Without a lot
    # size they are not zero, they are absent.
    resp = client.post(
        "/compute/acceptance-sampling/evaluate",
        json={
            "plan": {"sample_size": 52, "acceptance_number": 3},
            "aql": 0.01,
            "ltpd": 0.09,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["aoql"] is None
    assert body["ati_at_aql"] is None
    assert body["plan"]["lot_size"] is None
    assert body["producer_risk"] is not None


def test_acceptance_sampling_design_matches_core(client: TestClient) -> None:
    resp = client.post(
        "/compute/acceptance-sampling/design",
        json={"aql": 0.01, "ltpd": 0.05, "producer_risk": 0.02, "consumer_risk": 0.15},
    )
    assert resp.status_code == 200
    body = resp.json()
    core = design_single_sampling_plan(
        0.01, 0.05, producer_risk=0.02, consumer_risk=0.15
    )
    # A plan is a decision, so it is asserted exactly on both sides of the wire.
    assert body["sample_size"] == core.sample_size == 144
    assert body["acceptance_number"] == core.acceptance_number == 4
    assert body["rejection_number"] == core.rejection_number


def test_acceptance_sampling_oc_curve_matches_core(client: TestClient) -> None:
    grid = [0.01, 0.05, 0.1]
    resp = client.post(
        "/compute/acceptance-sampling/oc-curve",
        json={"plan": SAMPLING_PLAN, "fraction_defective": grid, "model": "poisson"},
    )
    assert resp.status_code == 200
    body = resp.json()
    core = oc_curve(SamplingPlan(52, 3, lot_size=10000), grid, model="poisson")
    assert body["model"] == "poisson"
    assert body["fraction_defective"] == list(core.fraction_defective)
    assert body["probability_accept"] == list(core.probability_accept)


def test_acceptance_sampling_oc_curve_derives_its_own_grid(client: TestClient) -> None:
    resp = client.post(
        "/compute/acceptance-sampling/oc-curve", json={"plan": SAMPLING_PLAN}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["fraction_defective"]) == len(body["probability_accept"]) > 1
    assert body["probability_accept"][0] == 1.0


def test_acceptance_sampling_inspect_carries_the_decision(client: TestClient) -> None:
    accepted = client.post(
        "/compute/acceptance-sampling/inspect",
        json={"plan": SAMPLING_PLAN, "defectives": 3},
    ).json()
    rejected = client.post(
        "/compute/acceptance-sampling/inspect",
        json={"plan": SAMPLING_PLAN, "defectives": 4},
    ).json()
    core = inspect_lot(SamplingPlan(52, 3, lot_size=10000), 3)
    # The boundary is the whole point of the endpoint; it survives the wire.
    assert accepted["accepted"] is True
    assert rejected["accepted"] is False
    assert accepted["sample_fraction_defective"] == core.sample_fraction_defective
    assert accepted["warnings"] == list(core.warnings)


def test_acceptance_sampling_impossible_plan_maps_core_error_to_422(
    client: TestClient,
) -> None:
    # Passes the schema (both are non-negative ints), and the core rejects it.
    resp = client.post(
        "/compute/acceptance-sampling/evaluate",
        json={
            "plan": {"sample_size": 5, "acceptance_number": 9},
            "aql": 0.01,
            "ltpd": 0.09,
        },
    )
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)


def test_acceptance_sampling_rejects_a_percentage_where_a_fraction_belongs(
    client: TestClient,
) -> None:
    # 15 meaning "15 %" is the likeliest caller mistake; it must not be read as
    # a fraction of 1500 %.
    resp = client.post(
        "/compute/acceptance-sampling/evaluate",
        json={"plan": SAMPLING_PLAN, "aql": 0.01, "ltpd": 15},
    )
    assert resp.status_code == 422


# The series the standard's own worked example follows: two non-acceptable lots
# four apart, then a long acceptable run.
SWITCHING_LOTS = [{"accepted": a} for a in [True, True, False, True, True, False]]


def test_switching_rules_match_core(client: TestClient) -> None:
    resp = client.post(
        "/compute/acceptance-sampling/switching-rules", json={"lots": SWITCHING_LOTS}
    )
    assert resp.status_code == 200
    body = resp.json()
    core = apply_switching_rules([lot["accepted"] for lot in SWITCHING_LOTS])
    assert body["final_severity"] == core.final_severity
    assert [s["severity"] for s in body["steps"]] == [s.severity for s in core.steps]
    assert [s["severity_after"] for s in body["steps"]] == [
        s.severity_after for s in core.steps
    ]
    assert [s["switching_score"] for s in body["steps"]] == [
        s.switching_score for s in core.steps
    ]
    # switched is a derived property, not a dataclass field.
    assert [s["switched"] for s in body["steps"]] == [s.switched for s in core.steps]
    assert body["warnings"] == list(core.warnings)
    assert body["rules"]["discontinue_on_non_accepted"] == 5


def test_switching_score_is_null_where_the_standard_does_not_keep_it(
    client: TestClient,
) -> None:
    # Lots 1-2 are normal and scored; everything after the switch is tightened,
    # where the score is not maintained -- null, not zero.
    resp = client.post(
        "/compute/acceptance-sampling/switching-rules",
        json={"lots": [{"accepted": False}, {"accepted": False}, {"accepted": True}]},
    )
    body = resp.json()
    assert body["steps"][0]["switching_score"] == 0
    assert body["steps"][2]["switching_score"] is None


def test_switching_rules_never_relax_without_authorisation(
    client: TestClient,
) -> None:
    lots = [{"accepted": True} for _ in range(20)]
    unauthorised = client.post(
        "/compute/acceptance-sampling/switching-rules", json={"lots": lots}
    ).json()
    assert unauthorised["final_severity"] == "normal"

    authorised = client.post(
        "/compute/acceptance-sampling/switching-rules",
        json={"lots": lots, "reduced_inspection_authorised": True},
    ).json()
    assert authorised["final_severity"] == "reduced"


def test_switching_rules_accept_custom_thresholds(client: TestClient) -> None:
    resp = client.post(
        "/compute/acceptance-sampling/switching-rules",
        json={
            "lots": SWITCHING_LOTS,
            "rules": {"tighten_on_non_acceptable": 3, "within_consecutive_lots": 4},
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rules"]["tighten_on_non_acceptable"] == 3
    # Two non-acceptable lots no longer suffice.
    assert body["final_severity"] == "normal"


def test_switching_rules_cannot_start_discontinued(client: TestClient) -> None:
    # The schema allows the value so the core can reject it with its own words.
    resp = client.post(
        "/compute/acceptance-sampling/switching-rules",
        json={"lots": SWITCHING_LOTS, "start": "discontinued"},
    )
    assert resp.status_code == 422
    assert isinstance(resp.json()["detail"], str)
