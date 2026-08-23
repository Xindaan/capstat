"""Gage R&R (ANOVA method).

Sources and tolerances: ``references/gage_rr.yaml``.

The published worked example (SPC for Excel, AIAG method) pins the whole
pipeline on the *hard* path: an insignificant interaction that gets pooled, and
a negative interaction variance that gets clamped. The constructed cases pin the
other branch (a real interaction, kept) and the algebraic identities that must
hold for any input.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import yaml
from capstat_core import GageRRReport, d2, d2_star, gage_rr, gage_rr_range
from capstat_core.gage_rr import NDC_MULTIPLIER
from conftest import REFERENCES

DOCUMENT = yaml.safe_load((REFERENCES / "gage_rr.yaml").read_text())
CASES = {case["id"]: case for case in DOCUMENT["cases"]}


def _anova_components(data: np.ndarray) -> dict[str, float]:
    """A second, independent two-way-ANOVA implementation, for cross-checking.

    Full model, no pooling, negatives clamped to zero -- the same estimators the
    module uses, written separately so a bug in one would not hide in the other.
    """
    p, o, r = data.shape
    grand = data.mean()
    cell = data.mean(axis=2)
    pm = data.mean(axis=(1, 2))
    om = data.mean(axis=(0, 2))
    ss_p = o * r * ((pm - grand) ** 2).sum()
    ss_o = p * r * ((om - grand) ** 2).sum()
    ss_i = r * ((cell - pm[:, None] - om[None, :] + grand) ** 2).sum()
    ss_e = ((data - cell[:, :, None]) ** 2).sum()
    ms_p = ss_p / (p - 1)
    ms_o = ss_o / (o - 1)
    ms_i = ss_i / ((p - 1) * (o - 1))
    ms_e = ss_e / (p * o * (r - 1))
    return {
        "repeatability": ms_e,
        "interaction": max((ms_i - ms_e) / r, 0.0),
        "operator": max((ms_o - ms_i) / (p * r), 0.0),
        "part": max((ms_p - ms_i) / (o * r), 0.0),
        "ss_total": ((data - grand) ** 2).sum(),
        "ss_sum": ss_p + ss_o + ss_i + ss_e,
    }


def _strong_interaction() -> np.ndarray:
    """4 parts x 2 operators x 3 trials with a large part*operator interaction.

    Operator 1 reads high on odd parts and low on even ones; operator 0 is flat.
    Tiny within-cell noise, so the interaction dominates and stays significant.
    """
    part_base = np.array([10.0, 20.0, 30.0, 40.0])
    inter = np.array([[0.0, 2.0], [0.0, -2.0], [0.0, 2.0], [0.0, -2.0]])
    trial_noise = np.array([-0.1, 0.0, 0.1])
    data = np.empty((4, 2, 3))
    for i in range(4):
        for j in range(2):
            data[i, j, :] = part_base[i] + inter[i, j] + trial_noise
    return data


# ---------------------------------------------------------------------------
# Published worked example: the pooled / negative-variance path
# ---------------------------------------------------------------------------


def test_spc_worked_example_matches_published_values() -> None:
    case = CASES["spc-anova-gage-rr-pooled"]
    tol = case["tolerance"]
    exp = case["expected"]
    report = gage_rr(np.array(case["input"]["data"]))

    assert report.interaction_included is exp["interaction_included"]
    assert report.interaction_pvalue == pytest.approx(
        exp["interaction_pvalue"], abs=tol["pvalue"]
    )
    for field in ("repeatability", "operator", "interaction", "part"):
        assert getattr(report, f"var_{field}") == pytest.approx(
            exp[f"var_{field}"], abs=tol["var"]
        ), field
    assert report.var_gage_rr == pytest.approx(exp["var_gage_rr"], abs=tol["var"])
    assert report.var_total == pytest.approx(exp["var_total"], abs=tol["var"])
    for field in (
        "pct_contribution_gage_rr",
        "pct_contribution_repeatability",
        "pct_contribution_reproducibility",
        "pct_contribution_part",
        "pct_study_var_gage_rr",
        "pct_study_var_repeatability",
        "pct_study_var_reproducibility",
        "pct_study_var_part",
    ):
        assert getattr(report, field) == pytest.approx(exp[field], abs=tol["pct"]), (
            field
        )
    assert report.ndc == exp["ndc"]  # a decision -- exact, no tolerance


def test_insignificant_interaction_is_pooled_and_announced() -> None:
    report = gage_rr(np.array(CASES["spc-anova-gage-rr-pooled"]["input"]["data"]))
    assert report.interaction_included is False
    assert report.var_interaction == 0.0
    assert any("pooled into repeatability" in w for w in report.warnings)


def test_worked_example_verdict_is_stated() -> None:
    report = gage_rr(np.array(CASES["spc-anova-gage-rr-pooled"]["input"]["data"]))
    # 33% study variation and 4 categories -- both below AIAG's bars.
    assert any("unacceptable" in w for w in report.warnings)
    assert any("distinct categories" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# Constructed cases: the interaction-kept path and the identities
# ---------------------------------------------------------------------------


def test_significant_interaction_is_kept_and_matches_independent_anova() -> None:
    data = _strong_interaction()
    report = gage_rr(data)
    oracle = _anova_components(data)

    assert report.interaction_included is True
    assert report.var_interaction > 0.0
    assert report.var_repeatability == pytest.approx(oracle["repeatability"], rel=1e-9)
    assert report.var_interaction == pytest.approx(oracle["interaction"], rel=1e-9)
    assert report.var_operator == pytest.approx(oracle["operator"], abs=1e-12)
    assert report.var_part == pytest.approx(oracle["part"], rel=1e-9)
    # AIAG counts the interaction inside reproducibility.
    assert report.var_reproducibility == pytest.approx(
        report.var_operator + report.var_interaction, rel=1e-12
    )


def test_variance_components_sum_to_total() -> None:
    report = gage_rr(_strong_interaction())
    assert report.var_total == pytest.approx(
        report.var_repeatability
        + report.var_operator
        + report.var_interaction
        + report.var_part,
        rel=1e-12,
    )


def test_percent_contributions_sum_to_100() -> None:
    report = gage_rr(_strong_interaction())
    total = report.pct_contribution_gage_rr + report.pct_contribution_part
    assert total == pytest.approx(100.0, rel=1e-12)


def test_ss_decomposition_is_exact() -> None:
    oracle = _anova_components(_strong_interaction())
    assert oracle["ss_sum"] == pytest.approx(oracle["ss_total"], rel=1e-12)


def test_ndc_uses_the_aiag_multiplier() -> None:
    report = gage_rr(_strong_interaction())
    expected = int(
        NDC_MULTIPLIER * np.sqrt(report.var_part) / np.sqrt(report.var_gage_rr)
    )
    assert report.ndc == expected


# ---------------------------------------------------------------------------
# Negative-variance clamp, tolerance, degenerate gage
# ---------------------------------------------------------------------------


def test_negative_component_is_clamped_to_zero_with_a_warning() -> None:
    # Pure interaction with no operator main effect -> the operator variance
    # estimate goes slightly negative and must be clamped.
    report = gage_rr(_strong_interaction())
    assert report.var_operator == 0.0
    assert any("operator" in w and "clamped to zero" in w for w in report.warnings)


def test_tolerance_gives_precision_to_tolerance_ratio() -> None:
    data = np.array(CASES["spc-anova-gage-rr-pooled"]["input"]["data"])
    report = gage_rr(data, tolerance=6.0)
    expected = 100.0 * 6.0 * np.sqrt(report.var_gage_rr) / 6.0
    assert report.pct_tolerance_gage_rr == pytest.approx(expected, rel=1e-12)


def test_no_tolerance_means_no_ratio() -> None:
    report = gage_rr(_strong_interaction())
    assert report.pct_tolerance_gage_rr is None


def test_good_gage_earns_no_verdict_warning() -> None:
    # Widely spread parts, near-zero measurement noise, identical operators:
    # GRR is a tiny fraction of the study variation, so neither the marginal nor
    # the unacceptable verdict fires and ndc is comfortably above 5.
    part_base = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    noise = np.array([-0.01, 0.0, 0.01])
    data = np.empty((6, 3, 3))
    for i in range(6):
        for j in range(3):
            data[i, j, :] = part_base[i] + noise
    report = gage_rr(data)
    assert report.pct_study_var_gage_rr < 10.0
    assert report.ndc is not None and report.ndc >= 5
    assert not any(
        "unacceptable" in w or "marginal" in w or "distinct categories" in w
        for w in report.warnings
    )


def test_no_variation_at_all_gives_nan_percentages_not_a_crash() -> None:
    # Every measurement identical -> total variance is zero. The percentages are
    # genuinely undefined (0/0) and must be nan, not a ZeroDivisionError.
    report = gage_rr(np.full((3, 3, 3), 5.0))
    assert report.var_total == 0.0
    assert math.isnan(report.pct_contribution_gage_rr)
    assert math.isnan(report.pct_study_var_part)
    assert report.ndc is None


def test_perfect_gage_has_no_distinct_category_ceiling() -> None:
    # Every operator and trial identical -> zero measurement variance -> ndc
    # undefined (infinitely many categories).
    parts = np.array([10.0, 20.0, 30.0])
    data = np.repeat(parts[:, None, None], 2, axis=1).repeat(3, axis=2)
    report = gage_rr(data)
    assert report.var_gage_rr == 0.0
    assert report.ndc is None


# ---------------------------------------------------------------------------
# Average-and-range method (and its d2* constant)
# ---------------------------------------------------------------------------


def _average_range_oracle(data: np.ndarray) -> dict[str, float]:
    """Independent average-and-range computation, for cross-checking the module."""
    p, o, r = data.shape
    rbar = (data.max(axis=2) - data.min(axis=2)).mean()
    op = data.mean(axis=(0, 2))
    part = data.mean(axis=(1, 2))
    x_diff = op.max() - op.min()
    rp = part.max() - part.min()
    ev = rbar / d2(r)
    av = math.sqrt(max(0.0, (x_diff / d2_star(o, 1)) ** 2 - ev**2 / (p * r)))
    pv = rp / d2_star(p, 1)
    return {"ev": ev, "av": av, "pv": pv}


def test_d2_star_matches_duncan_table() -> None:
    case = CASES["d2-star-duncan-table"]
    tol = case["tolerance"]["abs"]
    for n, expected in case["expected"].items():
        assert d2_star(int(n), 1) == pytest.approx(expected, abs=tol), f"d2*({n},1)"


def test_d2_star_collapses_to_d2_for_many_ranges() -> None:
    # With infinitely many ranges the finite-g correction vanishes.
    for n in (2, 3, 5, 10):
        assert d2_star(n, 10**9) == pytest.approx(d2(n), rel=1e-6)


def test_d2_star_rejects_bad_range_count() -> None:
    with pytest.raises(ValueError, match="number of ranges must be >= 1"):
        d2_star(3, 0)
    with pytest.raises(TypeError, match="number of ranges must be an int"):
        d2_star(3, 1.5)  # type: ignore[arg-type]


def test_average_range_reproduces_published_aiag_summary() -> None:
    # AIAG's 10-part example, pinned at the range-summary level: this checks the
    # constants (d2, d2*) and the EV/AV/PV/GRR formulas against AIAG's numbers.
    case = CASES["average-range-aiag-10part-summary"]
    inp, exp, tol = case["input"], case["expected"], case["tolerance"]
    p, o, r = inp["parts"], inp["operators"], inp["trials"]
    ev = inp["rbar_bar"] / d2(r)
    av = math.sqrt((inp["x_diff"] / d2_star(o, 1)) ** 2 - ev**2 / (p * r))
    pv = inp["range_parts"] / d2_star(p, 1)
    grr = math.sqrt(ev**2 + av**2)
    total = math.sqrt(grr**2 + pv**2)
    assert ev == pytest.approx(exp["ev"], abs=tol["sd"])
    assert av == pytest.approx(exp["av"], abs=tol["sd"])
    assert pv == pytest.approx(exp["pv"], abs=tol["sd"])
    assert grr == pytest.approx(exp["gage_rr"], abs=tol["sd"])
    assert total == pytest.approx(exp["total"], abs=tol["sd"])
    assert 100.0 * grr / total == pytest.approx(
        exp["pct_study_var_gage_rr"], abs=tol["pct"]
    )


def test_average_range_pipeline_matches_independent_oracle() -> None:
    data = np.array(CASES["spc-anova-gage-rr-pooled"]["input"]["data"])
    report = gage_rr_range(data)
    oracle = _average_range_oracle(data)

    assert report.method == "average_range"
    assert report.interaction_pvalue is None
    assert report.interaction_included is False
    assert report.var_interaction == 0.0
    assert math.sqrt(report.var_repeatability) == pytest.approx(oracle["ev"], rel=1e-12)
    assert math.sqrt(report.var_operator) == pytest.approx(oracle["av"], rel=1e-12)
    assert math.sqrt(report.var_part) == pytest.approx(oracle["pv"], rel=1e-12)


def test_the_two_methods_agree_on_the_same_data() -> None:
    # ANOVA and average-and-range are different estimators; on data with a small
    # interaction they should still land within a few points of each other.
    data = np.array(CASES["spc-anova-gage-rr-pooled"]["input"]["data"])
    anova = gage_rr(data)
    rng = gage_rr_range(data)
    assert rng.pct_study_var_gage_rr == pytest.approx(
        anova.pct_study_var_gage_rr, abs=2.0
    )


def test_average_range_clamps_negative_appraiser_variation() -> None:
    # Identical operators (no reproducibility) but noisy trials: the appraiser
    # term is smaller than the repeatability it subtracts, so AV clamps to zero.
    part_base = np.array([10.0, 20.0, 30.0, 40.0])
    trial_noise = np.array([-1.0, 0.0, 1.0])
    data = np.empty((4, 3, 3))
    for i in range(4):
        for j in range(3):
            data[i, j, :] = part_base[i] + trial_noise
    report = gage_rr_range(data)
    assert report.var_operator == 0.0
    assert any("clamped to zero" in w for w in report.warnings)


def test_average_range_rejects_two_dimensional_data() -> None:
    with pytest.raises(ValueError, match="3-D"):
        gage_rr_range(np.zeros((3, 3)))


def test_average_range_rejects_non_positive_tolerance() -> None:
    with pytest.raises(ValueError, match="tolerance must be positive"):
        gage_rr_range(_strong_interaction(), tolerance=-1.0)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_two_dimensional_data_is_rejected() -> None:
    with pytest.raises(ValueError, match="3-D"):
        gage_rr(np.zeros((3, 3)))


def test_non_finite_data_is_rejected() -> None:
    data = _strong_interaction()
    data[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN or infinite"):
        gage_rr(data)


def test_too_few_parts_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 2 parts"):
        gage_rr(np.zeros((1, 3, 3)))


def test_too_few_operators_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 2 operators"):
        gage_rr(np.zeros((3, 1, 3)))


def test_single_trial_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least 2 trials"):
        gage_rr(np.zeros((3, 3, 1)))


def test_non_positive_tolerance_is_rejected() -> None:
    with pytest.raises(ValueError, match="tolerance must be positive"):
        gage_rr(_strong_interaction(), tolerance=0.0)


def test_report_is_immutable() -> None:
    report = gage_rr(_strong_interaction())
    with pytest.raises(AttributeError):
        report.var_part = 1.0  # type: ignore[misc]


def test_report_type() -> None:
    assert isinstance(gage_rr(_strong_interaction()), GageRRReport)


# ---------------------------------------------------------------------------
# The verdict is the core's to state, once (T-0058)
# ---------------------------------------------------------------------------


def test_the_report_states_the_aiag_verdict_itself() -> None:
    """The AIAG bands lived twice: in `_verdict_warnings` and in the web app's
    colouring. A traffic light that disagrees with the printed warning is
    exactly the discrepancy this project exists to avoid, so the band is now a
    property and everything downstream reads it."""
    report = gage_rr(_strong_interaction())
    assert report.verdict in {"good", "marginal", "unacceptable"}
    # The verdict and the warning are the same judgement, not two.
    if report.verdict == "unacceptable":
        assert any("unacceptable" in w for w in report.warnings)
    elif report.verdict == "marginal":
        assert any("marginal" in w for w in report.warnings)
    else:
        assert not any("marginal" in w or "unacceptable" in w for w in report.warnings)


def test_the_verdict_turns_exactly_at_the_published_thresholds() -> None:
    """Pinned against the constants, not against 10 and 30 written again here --
    a test that restates the number cannot catch the number being changed."""
    from capstat_core.gage_rr import (
        GRR_GOOD_AT_OR_BELOW,
        GRR_MARGINAL_AT_OR_BELOW,
    )

    def report_at(pct: float) -> GageRRReport:
        # %Study variation is sqrt(var_grr / var_total), so pick the variances
        # that produce the wanted percentage exactly.
        fraction = (pct / 100.0) ** 2
        return GageRRReport(
            method="anova",
            n_parts=5,
            n_operators=3,
            n_trials=3,
            interaction_included=False,
            interaction_pvalue=None,
            var_repeatability=fraction,
            var_operator=0.0,
            var_interaction=0.0,
            var_part=1.0 - fraction,
            study_var_multiplier=6.0,
            tolerance=None,
            warnings=(),
        )

    assert report_at(GRR_GOOD_AT_OR_BELOW).verdict == "good"
    assert report_at(GRR_GOOD_AT_OR_BELOW + 0.5).verdict == "marginal"
    assert report_at(GRR_MARGINAL_AT_OR_BELOW).verdict == "marginal"
    assert report_at(GRR_MARGINAL_AT_OR_BELOW + 0.5).verdict == "unacceptable"


def test_a_gage_with_no_variation_of_its_own_has_no_verdict_to_give() -> None:
    """A perfect gage divides by zero on the way to a percentage. `None` says
    "not judged", which a colour can render as absent rather than as good."""
    perfect = GageRRReport(
        method="anova",
        n_parts=5,
        n_operators=3,
        n_trials=3,
        interaction_included=False,
        interaction_pvalue=None,
        var_repeatability=0.0,
        var_operator=0.0,
        var_interaction=0.0,
        var_part=1.0,
        study_var_multiplier=6.0,
        tolerance=None,
        warnings=(),
    )
    assert perfect.verdict is None
    assert perfect.ndc is None
    assert perfect.ndc_adequate is None


def test_the_warnings_read_the_reports_own_numbers() -> None:
    """`_verdict_warnings` recomputed %SV and ndc from raw variances instead of
    reading the properties beside them -- two implementations of one number."""
    report = gage_rr(_strong_interaction())
    stated = [w for w in report.warnings if "% of study variation" in w]
    if stated:
        assert f"{report.pct_study_var_gage_rr:.1f}%" in stated[0]
    if report.ndc_adequate is False:
        assert any(
            f"only {report.ndc} distinct categories" in w for w in report.warnings
        )
