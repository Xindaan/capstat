"""Gage R&R: how much of the variation you see is the gage, not the parts.

A measurement system adds its own noise on top of the true part-to-part
variation. Gage R&R (Repeatability & Reproducibility) partitions the total
observed variance into:

* **Repeatability** (equipment variation, EV) -- the same operator measuring the
  same part twice and not getting the same number. This is the pure replicate
  variance ``sigma_e^2``.
* **Reproducibility** (appraiser variation, AV) -- different operators getting
  systematically different numbers. In the AIAG model this is the operator
  variance *plus* the part-by-operator interaction (operators who disagree more
  on some parts than others).
* **Part variation** (PV) -- the real spread of the parts, which is what you
  actually wanted to measure.

``GRR = Repeatability + Reproducibility``. A gage is trustworthy when GRR is
small next to the part variation.

This module uses the **ANOVA method** (the one AIAG prefers over average-and-
range, because it is the only one that recovers the interaction term). The
crossed two-way random-effects model with replication is::

    y_ijk = mu + Part_i + Operator_j + (Part*Operator)_ij + e_ijk

and the balanced expected mean squares give the AIAG variance-component
estimators::

    sigma_e^2          = MS_error                              (repeatability)
    sigma_interaction^2 = (MS_interaction - MS_error) / r
    sigma_operator^2    = (MS_operator - MS_interaction) / (p * r)
    sigma_part^2        = (MS_part - MS_interaction) / (o * r)

with ``p`` parts, ``o`` operators, ``r`` trials.

Two things routinely go wrong, and both are handled here:

* **The interaction is not real.** If the part*operator F-test is not significant
  (AIAG's threshold is a generous ``alpha = 0.25``), the interaction term is
  dropped and its sum of squares is *pooled back into* the repeatability error
  before the components are re-estimated. Keeping a spurious interaction inflates
  reproducibility and hides a good gage.
* **A variance estimate comes out negative.** Mean-square differences can be
  negative for a component that is genuinely near zero. A variance cannot be
  negative, so it is clamped to zero and a warning is emitted -- the estimate is
  reported honestly as "indistinguishable from zero", not as a negative number.

Summary metrics (AIAG MSA-4):

* **%Contribution** = 100 * (component variance / total variance). Variances are
  additive, so these sum to 100%.
* **%Study Variation** = 100 * (component sigma / total sigma). Standard
  deviations are *not* additive, so these do not sum to 100% -- and %SV is always
  the larger, less flattering number.
* **ndc** (number of distinct categories) = ``1.41 * sigma_part / sigma_GRR``,
  truncated. It is how many non-overlapping groups the gage can actually tell
  apart; AIAG wants at least 5.

References
----------
AIAG. *Measurement Systems Analysis (MSA)*, 4th ed., 2010, ch. III sec. B
    (ANOVA method), and the average-and-range worked example.
Montgomery, D. C. *Introduction to Statistical Quality Control*, ch. 8
    (gauge capability, the two-way random-effects model).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy import stats

__all__ = [
    "NDC_MULTIPLIER",
    "GageRRReport",
    "gage_rr",
]

#: AIAG MSA-4 defines ndc = 1.41 * (PV / GRR); 1.41 is its rounding of sqrt(2),
#: which is the signal-to-noise factor behind the number of distinct categories.
NDC_MULTIPLIER = 1.41

#: Default significance level for retaining the part*operator interaction. AIAG
#: uses a deliberately generous 0.25 so a real interaction is not discarded.
DEFAULT_INTERACTION_ALPHA = 0.25

#: Default study-variation multiplier: 6 sigma spans 99.73% of a normal (MSA-4).
DEFAULT_STUDY_VAR_MULTIPLIER = 6.0


@dataclass(frozen=True, slots=True)
class GageRRReport:
    """Variance-component breakdown of a crossed ANOVA Gage R&R study.

    The four stored components are the independent ones -- reproducibility, GRR
    and total are their sums and are exposed as properties. Every component is a
    variance (sigma^2); take a square root for a standard deviation.

    Read ``pct_study_var_gage_rr`` for the AIAG verdict (< 10% good, 10-30%
    marginal, > 30% unacceptable) and ``ndc`` for whether the gage can tell the
    parts apart at all (>= 5 wanted).
    """

    n_parts: int
    n_operators: int
    n_trials: int

    interaction_included: bool
    interaction_pvalue: float

    # Independent variance components; the rest derive from these.
    var_repeatability: float
    var_operator: float
    var_interaction: float
    var_part: float

    study_var_multiplier: float
    tolerance: float | None
    warnings: tuple[str, ...]

    @property
    def var_reproducibility(self) -> float:
        """Operator + interaction variance (AIAG counts the interaction here)."""
        return self.var_operator + self.var_interaction

    @property
    def var_gage_rr(self) -> float:
        return self.var_repeatability + self.var_reproducibility

    @property
    def var_total(self) -> float:
        return self.var_gage_rr + self.var_part

    # -- %Contribution (of variance; sums to 100) -------------------------------
    @property
    def pct_contribution_gage_rr(self) -> float:
        return 100.0 * self.var_gage_rr / self.var_total

    @property
    def pct_contribution_repeatability(self) -> float:
        return 100.0 * self.var_repeatability / self.var_total

    @property
    def pct_contribution_reproducibility(self) -> float:
        return 100.0 * self.var_reproducibility / self.var_total

    @property
    def pct_contribution_part(self) -> float:
        return 100.0 * self.var_part / self.var_total

    # -- %Study Variation (of sigma; does not sum to 100) -----------------------
    @property
    def pct_study_var_gage_rr(self) -> float:
        return 100.0 * math.sqrt(self.var_gage_rr / self.var_total)

    @property
    def pct_study_var_repeatability(self) -> float:
        return 100.0 * math.sqrt(self.var_repeatability / self.var_total)

    @property
    def pct_study_var_reproducibility(self) -> float:
        return 100.0 * math.sqrt(self.var_reproducibility / self.var_total)

    @property
    def pct_study_var_part(self) -> float:
        return 100.0 * math.sqrt(self.var_part / self.var_total)

    @property
    def pct_tolerance_gage_rr(self) -> float | None:
        """GRR study variation as a fraction of the tolerance, if one was given."""
        if self.tolerance is None:
            return None
        study_var = self.study_var_multiplier * math.sqrt(self.var_gage_rr)
        return 100.0 * study_var / self.tolerance

    @property
    def ndc(self) -> int | None:
        """Number of distinct categories, truncated. ``None`` for a perfect gage."""
        if self.var_gage_rr <= 0.0:
            return None
        ratio = math.sqrt(self.var_part) / math.sqrt(self.var_gage_rr)
        return int(NDC_MULTIPLIER * ratio)


def _as_layout(x: npt.ArrayLike) -> npt.NDArray[np.float64]:
    """Coerce input to a 3-D (parts x operators x trials) array and validate it."""
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError(
            f"expected 3-D data (parts x operators x trials), got {arr.ndim} dimensions"
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError("data contains NaN or infinite values")
    p, o, r = arr.shape
    if p < 2:
        raise ValueError(f"need at least 2 parts, got {p}")
    if o < 2:
        raise ValueError(f"need at least 2 operators, got {o}")
    if r < 2:
        raise ValueError(
            f"need at least 2 trials to separate repeatability from the "
            f"interaction, got {r}"
        )
    return arr


def gage_rr(
    data: npt.ArrayLike,
    *,
    tolerance: float | None = None,
    study_var_multiplier: float = DEFAULT_STUDY_VAR_MULTIPLIER,
    interaction_alpha: float = DEFAULT_INTERACTION_ALPHA,
) -> GageRRReport:
    """Crossed ANOVA Gage R&R.

    Parameters
    ----------
    data
        A 3-D array shaped ``(parts, operators, trials)``. Balanced only: every
        part must be measured the same number of times by every operator.
    tolerance
        The specification width (USL - LSL). If given, ``pct_tolerance_gage_rr``
        reports GRR against it (the precision-to-tolerance ratio).
    study_var_multiplier
        Sigma multiplier for the study-variation span; 6.0 (99.73%) per MSA-4.
        Percentages of study variation do not depend on it, only the absolute
        precision-to-tolerance ratio does.
    interaction_alpha
        Significance level for keeping the part*operator interaction. Above this
        p-value the interaction is dropped and pooled into repeatability. AIAG
        uses 0.25.

    Returns
    -------
    GageRRReport

    Raises
    ------
    ValueError
        If the data is not 3-D, is non-finite, or has fewer than 2 parts,
        2 operators, or 2 trials.
    """
    if tolerance is not None and tolerance <= 0.0:
        raise ValueError(f"tolerance must be positive, got {tolerance}")

    arr = _as_layout(data)
    p, o, r = arr.shape

    grand = float(arr.mean())
    cell_means = arr.mean(axis=2)  # (parts x operators)
    part_means = arr.mean(axis=(1, 2))  # (parts,)
    operator_means = arr.mean(axis=(0, 2))  # (operators,)

    ss_part = o * r * float(((part_means - grand) ** 2).sum())
    ss_operator = p * r * float(((operator_means - grand) ** 2).sum())
    ss_interaction = r * float(
        (
            (cell_means - part_means[:, None] - operator_means[None, :] + grand) ** 2
        ).sum()
    )
    ss_error = float(((arr - cell_means[:, :, None]) ** 2).sum())

    df_part = p - 1
    df_operator = o - 1
    df_interaction = (p - 1) * (o - 1)
    df_error = p * o * (r - 1)

    ms_part = ss_part / df_part
    ms_operator = ss_operator / df_operator
    ms_interaction = ss_interaction / df_interaction
    ms_error = ss_error / df_error

    warnings: list[str] = []

    # Interaction F-test: MS_interaction against MS_error. A zero error mean
    # square (perfect repeatability) leaves the test undefined -- keep the
    # interaction in that case and say so.
    if ms_error > 0.0:
        f_interaction = ms_interaction / ms_error
        p_interaction = float(stats.f.sf(f_interaction, df_interaction, df_error))
    else:
        p_interaction = 0.0
        warnings.append(
            "repeatability is exactly zero (identical replicates); the "
            "interaction test is undefined and the interaction was kept"
        )

    interaction_included = p_interaction <= interaction_alpha

    if interaction_included:
        var_repeatability = ms_error
        var_interaction = (ms_interaction - ms_error) / r
        var_operator = (ms_operator - ms_interaction) / (p * r)
        var_part = (ms_part - ms_interaction) / (o * r)
    else:
        # Drop the interaction: pool its sum of squares into the error, then
        # re-estimate the remaining components against the pooled repeatability.
        pooled_ss_error = ss_interaction + ss_error
        pooled_df_error = df_interaction + df_error
        pooled_ms_error = pooled_ss_error / pooled_df_error
        var_repeatability = pooled_ms_error
        var_interaction = 0.0
        var_operator = (ms_operator - pooled_ms_error) / (p * r)
        var_part = (ms_part - pooled_ms_error) / (o * r)
        warnings.append(
            f"part-operator interaction was not significant "
            f"(p = {p_interaction:.3f} > {interaction_alpha}); it was pooled "
            "into repeatability"
        )

    var_repeatability, w = _clamp(var_repeatability, "repeatability")
    warnings += w
    var_operator, w = _clamp(var_operator, "operator (reproducibility)")
    warnings += w
    var_interaction, w = _clamp(var_interaction, "part-operator interaction")
    warnings += w
    var_part, w = _clamp(var_part, "part")
    warnings += w

    warnings += _verdict_warnings(
        var_repeatability + var_operator + var_interaction, var_part
    )

    return GageRRReport(
        n_parts=p,
        n_operators=o,
        n_trials=r,
        interaction_included=interaction_included,
        interaction_pvalue=p_interaction,
        var_repeatability=var_repeatability,
        var_operator=var_operator,
        var_interaction=var_interaction,
        var_part=var_part,
        study_var_multiplier=study_var_multiplier,
        tolerance=tolerance,
        warnings=tuple(warnings),
    )


def _clamp(value: float, name: str) -> tuple[float, list[str]]:
    """A variance cannot be negative; clamp to zero and report it."""
    if value < 0.0:
        return 0.0, [
            f"{name} variance estimate was negative ({value:.4g}); clamped to "
            "zero (the component is indistinguishable from zero)"
        ]
    return value, []


def _verdict_warnings(var_gage_rr: float, var_part: float) -> list[str]:
    """AIAG acceptance guidance -- said out loud, not left for the reader to infer."""
    out: list[str] = []
    var_total = var_gage_rr + var_part
    if var_gage_rr <= 0.0 or var_total <= 0.0:
        return out
    pct = 100.0 * math.sqrt(var_gage_rr / var_total)
    if pct > 30.0:
        out.append(
            f"gage R&R is {pct:.1f}% of study variation (> 30%): the "
            "measurement system is unacceptable"
        )
    elif pct > 10.0:
        out.append(
            f"gage R&R is {pct:.1f}% of study variation (10-30%): the "
            "measurement system is marginal"
        )
    ndc = int(NDC_MULTIPLIER * math.sqrt(var_part) / math.sqrt(var_gage_rr))
    if ndc < 5:
        out.append(
            f"only {ndc} distinct categories (< 5): the gage cannot reliably "
            "tell the parts apart"
        )
    return out
