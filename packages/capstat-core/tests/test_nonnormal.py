"""Non-normal capability: Box-Cox, the ISO 22514 percentile method, and the
decision between them.

Sources, identities and tolerances: ``references/nonnormal.yaml``.

No published worked example pins these end to end, so validation rests on
identities that must hold for *every* dataset rather than on one quoted number:

* the percentile method must reduce to the classic indices on normal data;
* Box-Cox and the percentile method must agree at the just-capable point -- and
  must NOT be expected to agree elsewhere, which these tests are what disproved;
* Box-Cox must recover lambda = 0 on lognormal data.

Plus the failure this module exists to prevent: transforming the data and
forgetting the specification limits.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import yaml
from capstat_core import (
    DistributionFit,
    analyze_capability,
    box_cox_capability,
    capability,
    fit_distribution,
    percentile_capability,
)
from capstat_core.nonnormal import (
    LOWER_PERCENTILE,
    UPPER_PERCENTILE,
    _box_cox,
    _fit_score,
)
from conftest import REFERENCES
from scipy import stats

DOCUMENT = yaml.safe_load((REFERENCES / "nonnormal.yaml").read_text())
CASES = {case["id"]: case for case in DOCUMENT["cases"]}


def _normal(n: int = 400, seed: int = 101) -> np.ndarray:
    return np.random.default_rng(seed).normal(loc=100.0, scale=2.0, size=n)


def _lognormal(n: int = 800, seed: int = 5) -> np.ndarray:
    draws = stats.lognorm(s=0.4, scale=math.exp(3.0)).rvs(n, random_state=seed)
    return np.asarray(draws, dtype=np.float64)


# ---------------------------------------------------------------------------
# Identity 1: the ISO percentiles ARE the three-sigma points
# ---------------------------------------------------------------------------


def test_iso_percentiles_are_the_three_sigma_points() -> None:
    case = CASES["percentile-percentiles-are-the-three-sigma-points"]
    tol = case["tolerance"]["abs"]
    expected = case["expected"]

    assert expected["lower_percentile"] == LOWER_PERCENTILE
    assert expected["upper_percentile"] == UPPER_PERCENTILE
    assert float(stats.norm.cdf(-3.0)) == pytest.approx(
        expected["normal_cdf_at_minus_three"], abs=tol
    )


def test_the_percentile_span_is_almost_but_not_exactly_six_sigma() -> None:
    """ISO rounds the tail to 0.135 %; the true +/-3 sigma tail is 0.13498980 %.

    The span is therefore 5.999954 sigma, not 6. Knowing this is what lets the
    next test use a tight tolerance honestly instead of a loose one blindly.
    """
    span = float(stats.norm.ppf(UPPER_PERCENTILE) - stats.norm.ppf(LOWER_PERCENTILE))
    assert span == pytest.approx(5.999954, abs=1e-6)
    assert span != 6.0


# ---------------------------------------------------------------------------
# Identity 2: on normal data, the percentile method must reproduce the classics
# ---------------------------------------------------------------------------


def test_percentile_method_reduces_to_the_classic_indices_on_normal_data() -> None:
    """The strongest check available for the percentile method.

    Given the *same* normal distribution -- passed in, not refitted -- the ISO
    formulas must collapse onto the classic ones. If the implementation had the
    percentiles the wrong way round, used the mean instead of the median, or
    dropped the asymmetric denominators, this identity would not hold.

    The distribution is built from the sample mean and the ddof=1 sample sd, i.e.
    exactly what `capability` uses, so that this test measures the *identity* and
    not the estimator difference (which the next test measures instead).
    """
    tol = CASES["percentile-reduces-to-classic-on-normal-data"]["tolerance"]["rel"]
    data = _normal(n=4000)

    classic = capability(data, lsl=94.0, usl=107.0)
    exact = DistributionFit(
        name="norm",
        params=(float(data.mean()), float(data.std(ddof=1))),
        fit_score=0.0,
    )
    iso = percentile_capability(data, lsl=94.0, usl=107.0, distribution=exact)

    assert iso.pp == pytest.approx(classic.pp, rel=tol)
    assert iso.ppk == pytest.approx(classic.ppk, rel=tol)
    assert iso.ppl == pytest.approx(classic.ppl, rel=tol)
    assert iso.ppu == pytest.approx(classic.ppu, rel=tol)


def test_fitted_normal_differs_from_classic_by_exactly_two_known_factors() -> None:
    """Even on perfectly normal data the fitted percentile index does not equal
    the classic one, and the whole difference is accounted for by two effects
    that are both understood:

    1. `norm.fit` is maximum likelihood, so its sigma has denominator n, while
       the classic index uses the sample sigma with denominator n-1. Factor:
       sqrt(n / (n - 1)).
    2. ISO's rounded 0.135 % percentile gives a span of 5.999954 sigma, not 6.
       Factor: 6 / 5.999954.

    Predicting the product exactly -- rather than shrugging and widening the
    tolerance -- is what keeps a genuine bug from hiding inside the gap.
    """
    case = CASES["percentile-fitted-normal-differs-by-the-ddof-factor"]
    tol = case["tolerance"]["rel"]
    n = case["input"]["n"]
    data = _normal(n=n)

    classic = capability(data, lsl=94.0, usl=107.0)
    fitted = percentile_capability(data, lsl=94.0, usl=107.0, distribution="norm")

    assert classic.pp is not None and fitted.pp is not None
    observed = fitted.pp / classic.pp

    span = float(stats.norm.ppf(UPPER_PERCENTILE) - stats.norm.ppf(LOWER_PERCENTILE))
    ddof_factor = math.sqrt(n / (n - 1))
    rounding_factor = 6.0 / span
    predicted = ddof_factor * rounding_factor

    assert observed == pytest.approx(predicted, rel=tol), (
        f"fitted/classic = {observed:.9f}, but the two known effects predict "
        f"{predicted:.9f} (ddof {ddof_factor:.9f} x ISO rounding "
        f"{rounding_factor:.9f}). Something else is now contributing."
    )
    # And the whole thing is a 1.3e-04 effect: real, but vanishing in 1/n.
    assert abs(observed - 1.0) < 2e-4


def test_percentile_method_uses_the_median_not_the_mean() -> None:
    """On a skewed distribution mean != median, and ISO specifies the median.

    Using the mean would shift both one-sided indices; on a right-skewed
    process it would flatter the upper one.
    """
    data = _lognormal()
    iso = percentile_capability(data, lsl=5.0, usl=60.0, distribution="lognorm")

    frozen = stats.lognorm(*stats.lognorm.fit(data))
    assert iso.p_median == pytest.approx(float(frozen.ppf(0.5)), rel=1e-12)
    assert iso.p_median != pytest.approx(float(data.mean()), rel=1e-3)


def test_percentile_method_offers_no_cp_or_cpk() -> None:
    """Its absence is deliberate: the method has no within/between split."""
    iso = percentile_capability(_lognormal(), lsl=5.0, usl=60.0)
    assert not hasattr(iso, "cp")
    assert not hasattr(iso, "cpk")
    assert any("no Cp or Cpk exists" in w for w in iso.warnings)


# ---------------------------------------------------------------------------
# Box-Cox
# ---------------------------------------------------------------------------


def test_box_cox_recovers_lambda_zero_on_lognormal_data() -> None:
    """A lognormal variable is exactly normal under a log transform (lambda 0)."""
    tol = CASES["box-cox-recovers-lambda-zero-on-lognormal-data"]["tolerance"]["abs"]
    result = box_cox_capability(_lognormal(n=2000), lsl=5.0, usl=60.0)
    assert result.lmbda == pytest.approx(0.0, abs=tol)
    assert result.transform_successful is True


def test_box_cox_transforms_the_specification_limits() -> None:
    """The mistake this module exists to prevent.

    The limits must be carried onto the transformed scale with the same lambda.
    Leaving them in original units would compare a transformed mean (~3) against
    an untransformed limit (~60) and produce a confident, absurd Cpk.
    """
    data = _lognormal()
    result = box_cox_capability(data, lsl=5.0, usl=60.0, target=20.0)
    lam = result.lmbda

    assert result.lsl_transformed == pytest.approx(_box_cox(5.0, lam), rel=1e-12)
    assert result.usl_transformed == pytest.approx(_box_cox(60.0, lam), rel=1e-12)
    assert result.target_transformed == pytest.approx(_box_cox(20.0, lam), rel=1e-12)

    # The report really was computed against the transformed limits.
    assert result.capability.lsl == result.lsl_transformed
    assert result.capability.usl == result.usl_transformed

    # And those are nowhere near the originals -- which is exactly why forgetting
    # to transform them would be catastrophic rather than merely imprecise.
    assert result.usl_transformed is not None
    assert abs(result.usl_transformed - 60.0) > 50.0


def test_forgetting_to_transform_the_limits_would_change_the_answer_wildly() -> None:
    """Pins the magnitude of the bug being prevented, not just its absence."""
    data = _lognormal()
    correct = box_cox_capability(data, lsl=5.0, usl=60.0)

    # What a careless implementation would do: transformed data, raw limits.
    transformed = stats.boxcox(data, lmbda=correct.lmbda)
    wrong = capability(transformed, lsl=5.0, usl=60.0)

    assert correct.capability.ppk is not None and wrong.ppk is not None
    assert abs(wrong.ppk - correct.capability.ppk) > 1.0, (
        "the untransformed-limits bug must produce a grossly different Ppk; "
        "if it does not, this guard proves nothing"
    )


def test_box_cox_preserves_the_order_of_the_limits_for_every_lambda() -> None:
    """Box-Cox has derivative x**(lambda-1) > 0 for x > 0, so it is strictly
    increasing for *every* lambda -- including negative ones, where intuition
    says the transform should flip. LSL therefore stays the lower limit."""
    for lam in (-2.0, -0.5, 0.0, 0.5, 1.0, 3.0):
        assert _box_cox(5.0, lam) < _box_cox(20.0, lam) < _box_cox(60.0, lam)


def test_box_cox_with_explicit_lambda_zero_is_the_log_transform() -> None:
    result = box_cox_capability(_lognormal(), lsl=5.0, usl=60.0, lmbda=0.0)
    assert result.lmbda == 0.0
    assert result.lsl_transformed == pytest.approx(math.log(5.0), rel=1e-12)


def test_box_cox_reports_lambda_rather_than_hiding_it() -> None:
    result = box_cox_capability(_lognormal(), lsl=5.0, usl=60.0)
    assert math.isfinite(result.lmbda)
    assert any("lambda" in w for w in result.warnings)
    assert any("NOT in the original units" in w for w in result.warnings)


def test_box_cox_flags_a_transformation_that_did_not_work() -> None:
    """Box-Cox cannot normalise everything. When it fails, say so."""
    rng = np.random.default_rng(4)
    bimodal = np.concatenate(
        [rng.normal(10.0, 0.5, size=200), rng.normal(40.0, 0.5, size=200)]
    )
    result = box_cox_capability(bimodal, lsl=1.0, usl=60.0)
    assert result.transform_successful is False
    assert result.normality_after.normal is False
    assert any("did NOT achieve normality" in w for w in result.warnings)


def test_box_cox_refuses_non_positive_data_instead_of_shifting_silently() -> None:
    data = np.concatenate([_lognormal(n=50), np.array([-1.0])])
    with pytest.raises(ValueError, match="strictly positive data"):
        box_cox_capability(data, lsl=1.0, usl=60.0)


def test_box_cox_refuses_non_positive_limits() -> None:
    with pytest.raises(ValueError, match="strictly positive lsl"):
        box_cox_capability(_lognormal(), lsl=-5.0, usl=60.0)
    with pytest.raises(ValueError, match="strictly positive target"):
        box_cox_capability(_lognormal(), lsl=5.0, usl=60.0, target=0.0)


def test_box_cox_transform_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError, match="undefined for non-positive"):
        _box_cox(0.0, 0.5)


def test_box_cox_refuses_a_lambda_that_collapses_the_limits() -> None:
    """A large |lambda| saturates in floating point: x**lambda underflows for the
    whole range, so both limits map to -1/lambda and the spec width vanishes.

    The error must name the limits the caller passed, not their transformed
    ghosts -- being told "lsl 0.0217 must be below usl 0.0217" when you typed
    9.7 and 10.3 is useless.
    """
    data = [10.0 + 0.02 * (i % 5) for i in range(20)]
    with pytest.raises(ValueError, match="degenerate for this specification"):
        box_cox_capability(data, lsl=9.7, usl=10.3, lmbda=-46.0)
    with pytest.raises(ValueError, match=r"lsl=9\.7 and usl=10\.3"):
        box_cox_capability(data, lsl=9.7, usl=10.3, lmbda=-46.0)


def test_analyze_falls_back_to_percentile_when_box_cox_is_degenerate() -> None:
    """Choosing a workable path is analyze_capability's job.

    A tight, drifting process around 10 fits lambda ~= -46, which collapses the
    limits. Box-Cox is then unusable -- but the percentile method does not
    transform the limits, so the analysis must route there rather than raising.
    """
    rng = np.random.default_rng(0)
    data = 10.0 + rng.normal(0.0, 0.05, 40)
    data[-8:] += np.linspace(0.02, 0.16, 8)

    # Precondition: this really is the degenerate branch, not the older
    # "Box-Cox failed to achieve normality" one.
    with pytest.raises(ValueError, match="degenerate"):
        box_cox_capability(data, lsl=9.7, usl=10.3)

    analysis = analyze_capability(data, lsl=9.7, usl=10.3)
    assert analysis.path == "percentile"
    assert analysis.box_cox is None
    assert analysis.percentile is not None
    assert analysis.ppk is not None
    assert "degenerate" in analysis.rationale
    assert "percentile method was used instead" in analysis.rationale


# ---------------------------------------------------------------------------
# Identity 3: two methods, no shared code, must agree where both are valid
# ---------------------------------------------------------------------------


def test_box_cox_and_percentile_agree_at_the_just_capable_point() -> None:
    """The two methods coincide at exactly one place, and this is it.

    Box-Cox Ppu = (ln(USL) - mu) / (3 sigma); percentile Ppu =
    (e**U - 1)/(e**(3 sigma) - 1) with U = ln(USL) - mu. Put U = 3 sigma -- the
    limit exactly on the 99.865 % percentile -- and both equal 1.

    This file originally asserted that they agree in general. They do not, and
    this test is what proved it.
    """
    case = CASES["box-cox-and-percentile-agree-only-when-just-capable"]
    tol = case["tolerance"]["abs"]
    expected = case["expected"]["index_at_the_just_capable_point"]

    data = _lognormal(n=4000)
    frozen = stats.lognorm(*stats.lognorm.fit(data))
    usl = float(frozen.ppf(UPPER_PERCENTILE))  # exactly "just capable"

    transformed = box_cox_capability(data, usl=usl)
    iso = percentile_capability(data, usl=usl, distribution="lognorm")

    assert transformed.capability.ppu == pytest.approx(expected, abs=tol)
    assert iso.ppu == pytest.approx(expected, abs=tol)


def test_box_cox_and_percentile_diverge_away_from_the_just_capable_point() -> None:
    """Pins the divergence, so nobody later 'fixes' one method to match the other.

    They answer different questions -- one linear on the log scale, one nonlinear
    on the original scale -- and forcing them to agree would mean breaking one.
    """
    data = _lognormal(n=4000)
    frozen = stats.lognorm(*stats.lognorm.fit(data))
    usl = float(frozen.ppf(0.999999))  # far out in the tail

    transformed = box_cox_capability(data, usl=usl)
    iso = percentile_capability(data, usl=usl, distribution="lognorm")

    assert transformed.capability.ppu is not None and iso.ppu is not None
    assert iso.ppu > transformed.capability.ppu * 1.3, (
        "the two methods must visibly diverge away from the just-capable point; "
        "if they no longer do, one of them has been quietly changed"
    )


# ---------------------------------------------------------------------------
# Distribution fitting
# ---------------------------------------------------------------------------


def test_fit_distribution_picks_the_true_family() -> None:
    fit = fit_distribution(_lognormal(n=3000))
    assert fit.name == "lognorm"
    assert math.isfinite(fit.fit_score)


def test_fit_score_is_not_dressed_up_as_a_pvalue() -> None:
    """The parameters were estimated from the same data, so any p-value would be
    anticonservative by an unknown amount. We expose a score, and only a score."""
    fit = fit_distribution(_lognormal())
    assert not hasattr(fit, "p_value")
    assert not hasattr(fit, "normal")


def test_lower_fit_score_means_a_better_fit() -> None:
    data = _lognormal(n=2000)
    best = fit_distribution(data, candidates=("lognorm", "expon"))
    worse = percentile_capability(data, lsl=5.0, usl=60.0, distribution="expon")
    assert best.name == "lognorm"
    assert best.fit_score < worse.fit_score


def test_unknown_distribution_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown scipy distribution"):
        percentile_capability(_lognormal(), lsl=5.0, usl=60.0, distribution="wibble")


def test_fit_distribution_raises_when_nothing_fits() -> None:
    with pytest.raises(ValueError, match="could be fitted to the data"):
        fit_distribution(_lognormal(), candidates=("not_a_distribution",))


# ---------------------------------------------------------------------------
# The documented decision path -- the headline deliverable
# ---------------------------------------------------------------------------


def test_normal_data_takes_the_normal_path() -> None:
    analysis = analyze_capability(_normal(), lsl=94.0, usl=107.0)
    assert analysis.path == "normal"
    assert analysis.normal is not None
    assert analysis.box_cox is None and analysis.percentile is None
    assert "not rejected" in analysis.rationale
    assert analysis.ppk == analysis.normal.ppk


def test_lognormal_data_takes_the_box_cox_path() -> None:
    """Box-Cox is preferred when it works: it keeps Cp/Cpk alive."""
    analysis = analyze_capability(_lognormal(), lsl=5.0, usl=60.0)
    assert analysis.path == "box-cox"
    assert analysis.box_cox is not None
    assert analysis.box_cox.transform_successful is True
    assert "lambda" in analysis.rationale
    assert "preserves the within/overall split" in analysis.rationale
    # Cp/Cpk survive the transform, which is the whole reason to prefer it.
    assert analysis.box_cox.capability.cpk is not None


def test_data_box_cox_cannot_fix_falls_through_to_the_percentile_method() -> None:
    rng = np.random.default_rng(4)
    bimodal = np.concatenate(
        [rng.normal(10.0, 0.5, size=200), rng.normal(40.0, 0.5, size=200)]
    )
    analysis = analyze_capability(bimodal, lsl=1.0, usl=60.0)

    assert analysis.path == "percentile"
    assert analysis.percentile is not None
    assert analysis.box_cox is None
    assert "failed to fix it" in analysis.rationale
    assert "ISO 22514" in analysis.rationale


def test_non_positive_data_skips_box_cox_and_says_why() -> None:
    """Box-Cox is undefined for x <= 0. capstat must not shift the data to make
    it applicable -- the offset changes the indices and is the user's decision."""
    rng = np.random.default_rng(8)
    data = rng.exponential(scale=2.0, size=300) - 1.0  # straddles zero
    analysis = analyze_capability(data, lsl=-3.0, usl=8.0)

    assert analysis.path == "percentile"
    assert "not strictly positive" in analysis.rationale
    assert "will not shift the data" in analysis.rationale


def test_the_analysis_always_records_which_path_it_took_and_why() -> None:
    """The record is the deliverable: an unauditable capability figure is the
    thing this library exists to replace."""
    for data, lsl, usl in (
        (_normal(), 94.0, 107.0),
        (_lognormal(), 5.0, 60.0),
    ):
        analysis = analyze_capability(data, lsl=lsl, usl=usl)
        assert analysis.path in ("normal", "box-cox", "percentile")
        assert len(analysis.rationale) > 40
        assert analysis.normality is not None


def test_headline_indices_come_from_the_chosen_branch() -> None:
    analysis = analyze_capability(_lognormal(), lsl=5.0, usl=60.0)
    assert analysis.box_cox is not None
    assert analysis.pp == analysis.box_cox.capability.pp
    assert analysis.ppk == analysis.box_cox.capability.ppk


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "function", [analyze_capability, box_cox_capability, percentile_capability]
)
def test_at_least_one_limit_is_required(function: object) -> None:
    with pytest.raises(ValueError, match="at least one specification limit"):
        function(_lognormal())  # type: ignore[operator]


@pytest.mark.parametrize(
    "function", [analyze_capability, box_cox_capability, percentile_capability]
)
def test_inverted_limits_are_rejected(function: object) -> None:
    with pytest.raises(ValueError, match="must be strictly below"):
        function(_lognormal(), lsl=60.0, usl=5.0)  # type: ignore[operator]


def test_one_sided_limits_are_supported() -> None:
    upper = percentile_capability(_lognormal(), usl=60.0)
    assert upper.pp is None and upper.ppl is None
    assert upper.ppu is not None and upper.ppk == upper.ppu

    lower = percentile_capability(_lognormal(), lsl=5.0)
    assert lower.pp is None and lower.ppu is None
    assert lower.ppl is not None and lower.ppk == lower.ppl


def test_small_samples_are_warned_about() -> None:
    """The indices live on the 0.135 % / 99.865 % percentiles -- far out in the
    tails, where a distribution fitted to 40 points says very little."""
    report = percentile_capability(_lognormal(n=40), lsl=5.0, usl=60.0)
    assert any("far out in the tails" in w for w in report.warnings)


def test_reports_are_immutable() -> None:
    report = percentile_capability(_lognormal(), lsl=5.0, usl=60.0)
    with pytest.raises(AttributeError):
        report.ppk = 9.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Degenerate fits. A distribution that fits badly enough must be discarded, not
# allowed to produce a confident nonsense index.
# ---------------------------------------------------------------------------


class _NanCdf:
    """A distribution whose CDF degenerates to NaN."""

    def cdf(self, data: np.ndarray) -> np.ndarray:
        return np.full(np.shape(data), np.nan)


class _ConstantCdf:
    """A distribution whose CDF is constant, so the transform has no variance."""

    def cdf(self, data: np.ndarray) -> np.ndarray:
        return np.full(np.shape(data), 0.5)


def test_fit_score_is_infinite_for_a_nan_cdf() -> None:
    assert math.isinf(_fit_score(_lognormal(n=50), _NanCdf()))


def test_fit_score_is_infinite_when_the_transform_has_no_variance() -> None:
    """Anderson-Darling is undefined on a zero-variance sample; score it out."""
    assert math.isinf(_fit_score(_lognormal(n=50), _ConstantCdf()))


def test_a_candidate_that_cannot_be_fitted_is_skipped_not_fatal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Failing:
        def fit(self, data: np.ndarray) -> tuple[float, ...]:
            raise RuntimeError("cannot fit")

    monkeypatch.setattr(stats, "failing_dist", Failing(), raising=False)
    fit = fit_distribution(_lognormal(), candidates=("failing_dist", "lognorm"))
    assert fit.name == "lognorm"


def test_a_candidate_scoring_non_finite_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Degenerate:
        def fit(self, data: np.ndarray) -> tuple[float, ...]:
            return (0.0, 1.0)

        def __call__(self, *params: float) -> _NanCdf:
            return _NanCdf()

    monkeypatch.setattr(stats, "degenerate_dist", Degenerate(), raising=False)
    fit = fit_distribution(_lognormal(), candidates=("degenerate_dist", "lognorm"))
    assert fit.name == "lognorm"


def test_a_fit_with_non_finite_percentiles_is_rejected() -> None:
    """A degenerate lognormal (s = 0) yields NaN percentiles. Refuse it rather
    than return an index computed from NaN."""
    degenerate = DistributionFit(name="lognorm", params=(0.0, 0.0, 1.0), fit_score=0.0)
    with pytest.raises(ValueError, match="non-finite percentiles"):
        percentile_capability(_lognormal(), lsl=5.0, usl=60.0, distribution=degenerate)
