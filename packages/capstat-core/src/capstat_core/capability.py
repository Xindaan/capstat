"""Process capability and performance indices.

The single most common way capability software misleads people is by blurring
two different standard deviations:

* **sigma_within** (short-term) is estimated from variation *inside* subgroups.
  It answers: how good could this process be if it held its current settings?
  It drives **Cp, Cpk, Cpm** -- the *potential*.
* **sigma_overall** (long-term) is the ordinary standard deviation of every
  observation. It absorbs drift, tool wear, shift changes -- everything that
  moves the process between subgroups. It drives **Pp, Ppk** -- the *actual*
  performance the customer receives.

For a perfectly stable process the two coincide. For a real one, ``Cpk > Ppk``,
and the gap *is* the instability. A tool that reports only Cpk on a drifting
process is quoting a number the customer will never experience. capstat always
reports both, and warns when they diverge.

Cp/Cpk therefore require subgroup structure. Handed a flat list of numbers with
no subgroups, capstat estimates the short-term sigma from the moving range
(the I-MR convention) and says so, rather than quietly substituting the overall
sigma and still calling the result Cpk.

Formulas (NIST/SEMATECH e-Handbook 6.1.6)::

    Cp  = (USL - LSL) / (6 * sigma)
    Cpu = (USL - mu)  / (3 * sigma)
    Cpl = (mu - LSL)  / (3 * sigma)
    Cpk = min(Cpu, Cpl)
    Cpm = (USL - LSL) / (6 * sqrt(sigma^2 + (mu - T)^2))

Pp, Ppu, Ppl, Ppk are the same expressions evaluated with sigma_overall.

References
----------
NIST/SEMATECH e-Handbook of Statistical Methods, section 6.1.6.
Montgomery, D. C. *Introduction to Statistical Quality Control*, ch. 8.
Chan, L. K., Cheng, S. W., & Spiring, F. A. (1988). A new measure of process
    capability: Cpm. *Journal of Quality Technology*, 20(3), 162-175.
AIAG. *Statistical Process Control (SPC)*, 2nd ed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
import numpy.typing as npt

from capstat_core.constants import MAX_SUBGROUP_SIZE, c4, d2
from capstat_core.descriptive import std_dev
from capstat_core.normality import (
    AD_MIN_SAMPLE_SIZE,
    NormalityAssessment,
    assess_normality,
)

__all__ = [
    "STABILITY_RATIO",
    "CapabilityReport",
    "WithinMethod",
    "capability",
]

#: sigma_overall / sigma_within above which the process is called unstable and
#: the potential indices (Cp, Cpk) are flagged as not describing what the
#: customer actually receives.
STABILITY_RATIO = 1.25

WithinMethod = Literal["pooled", "rbar_d2", "sbar_c4", "moving_range"]


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    """Capability (potential, short-term) and performance (actual, long-term).

    Indices are ``None`` when they are not defined for the specification given:
    ``cp``/``pp``/``cpm`` need *both* limits, ``cpm`` additionally needs a
    target, and the one-sided indices need their own limit.

    Read ``cpk`` and ``ppk`` together. ``cpk`` alone is the number a supplier
    would like to quote; ``ppk`` is the one the customer lives with.
    """

    n: int
    subgroup_size: int
    subgroups: int
    mean: float
    sigma_within: float
    sigma_overall: float
    within_method: WithinMethod
    lsl: float | None
    usl: float | None
    target: float | None

    # Potential (short-term, sigma_within)
    cp: float | None
    cpl: float | None
    cpu: float | None
    cpk: float | None
    cpm: float | None

    # Actual (long-term, sigma_overall)
    pp: float | None
    ppl: float | None
    ppu: float | None
    ppk: float | None

    normality: NormalityAssessment | None
    warnings: tuple[str, ...]

    @property
    def stability_ratio(self) -> float:
        """``sigma_overall / sigma_within``. 1.0 for a perfectly stable process."""
        return self.sigma_overall / self.sigma_within


def _as_subgroups(x: npt.ArrayLike) -> npt.NDArray[np.float64]:
    """Coerce input to a 2-D (subgroups x size) array; 1-D becomes k x 1."""
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.ndim != 2:
        raise ValueError(
            f"expected 1-D (individuals) or 2-D (subgroups x size) data, "
            f"got {arr.ndim} dimensions"
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError("data contains NaN or infinite values")
    if arr.shape[0] < 2:
        raise ValueError(f"need at least 2 subgroups, got {arr.shape[0]}")
    return arr


def _sigma_within(groups: npt.NDArray[np.float64], method: WithinMethod) -> float:
    """Estimate the within-subgroup standard deviation."""
    k, n = groups.shape

    if method == "moving_range":
        # Individuals data: the "subgroup" is a consecutive pair.
        flat = groups.ravel()
        moving_ranges = np.abs(np.diff(flat))
        return float(moving_ranges.mean()) / d2(2)

    if n < 2:
        raise ValueError(
            f"within method {method!r} needs subgroups of size >= 2; got size 1. "
            f"For individual measurements use within_method='moving_range'."
        )

    if method == "rbar_d2":
        ranges = groups.max(axis=1) - groups.min(axis=1)
        return float(ranges.mean()) / d2(n)

    if method == "sbar_c4":
        sds = groups.std(axis=1, ddof=1)
        return float(sds.mean()) / c4(n)

    if method == "pooled":
        # Pooled variance is unbiased for sigma^2, but its square root is
        # biased low for sigma. c4 at the pooled degrees of freedom removes
        # that bias -- the same convention Minitab uses.
        degrees = k * (n - 1)
        pooled_variance = float(np.sum((n - 1) * groups.var(axis=1, ddof=1)) / degrees)
        return math.sqrt(pooled_variance) / c4(degrees + 1)

    raise ValueError(f"unknown within_method {method!r}")


def _indices(
    mean: float,
    sigma: float,
    lsl: float | None,
    usl: float | None,
) -> tuple[float | None, float | None, float | None, float | None]:
    """Return ``(two_sided, lower, upper, k)`` for one sigma. Shared by both
    the within (Cp...) and overall (Pp...) families -- they differ only in the
    sigma passed in, so they must not differ in code."""
    two_sided = (
        (usl - lsl) / (6.0 * sigma) if lsl is not None and usl is not None else None
    )
    lower = (mean - lsl) / (3.0 * sigma) if lsl is not None else None
    upper = (usl - mean) / (3.0 * sigma) if usl is not None else None

    candidates = [v for v in (lower, upper) if v is not None]
    k_index = min(candidates) if candidates else None

    return two_sided, lower, upper, k_index


def capability(
    data: npt.ArrayLike,
    *,
    lsl: float | None = None,
    usl: float | None = None,
    target: float | None = None,
    within_method: WithinMethod | None = None,
    alpha: float = 0.05,
) -> CapabilityReport:
    """Compute capability (Cp, Cpk, Cpm) and performance (Pp, Ppk) indices.

    Parameters
    ----------
    data:
        Either a 2-D array of subgroups (``k`` rows of size ``n``), or a 1-D
        sequence of individual measurements. Subgroups are strongly preferred:
        they are what make a short-term sigma meaningful.
    lsl, usl:
        Specification limits. At least one is required. With only one limit the
        two-sided indices (Cp, Pp, Cpm) are ``None`` rather than invented.
    target:
        The target value for Cpm. If omitted, ``cpm`` is ``None``: capstat does
        not silently assume the target is the midpoint of the specification,
        because for an asymmetric tolerance that assumption is wrong and the
        resulting Cpm is meaningless.
    within_method:
        How to estimate the short-term sigma. Defaults to ``"pooled"`` for
        subgroups and ``"moving_range"`` for individuals.
    alpha:
        Significance level for the normality assessment attached to the report.

    Raises
    ------
    ValueError
        If neither limit is given, if ``lsl >= usl``, if the data have fewer
        than two subgroups, or if the estimated sigma is zero.

    Notes
    -----
    Every index here assumes the data are normally distributed -- the indices
    extrapolate into the tails, which is exactly where a wrong distribution
    hurts most. The report therefore carries a
    :class:`~capstat_core.normality.NormalityAssessment` and warns when the
    normal model is rejected. Take that warning seriously; a Cpk computed on
    visibly non-normal data is not a conservative estimate, it is a wrong one.
    """
    if lsl is None and usl is None:
        raise ValueError("at least one specification limit (lsl or usl) is required")
    if lsl is not None and usl is not None and lsl >= usl:
        raise ValueError(f"lsl ({lsl}) must be strictly below usl ({usl})")

    groups = _as_subgroups(data)
    k, n = groups.shape
    flat = groups.ravel()

    if within_method is None:
        within_method = "moving_range" if n == 1 else "pooled"

    if n > MAX_SUBGROUP_SIZE and within_method == "rbar_d2":
        raise ValueError(
            f"subgroup size {n} exceeds {MAX_SUBGROUP_SIZE}; the range is a poor "
            f"scale estimator that large. Use within_method='pooled' or 'sbar_c4'."
        )

    sigma_overall = std_dev(flat)
    if sigma_overall == 0.0:
        raise ValueError("data have zero variance; capability is undefined")

    sigma_within = _sigma_within(groups, within_method)
    if sigma_within == 0.0:
        raise ValueError(
            "the estimated within-subgroup sigma is zero (every subgroup is "
            "constant); capability is undefined"
        )

    mean = float(flat.mean())

    cp, cpl, cpu, cpk = _indices(mean, sigma_within, lsl, usl)
    pp, ppl, ppu, ppk = _indices(mean, sigma_overall, lsl, usl)

    cpm: float | None = None
    if lsl is not None and usl is not None and target is not None:
        deviation = math.sqrt(sigma_within**2 + (mean - target) ** 2)
        cpm = (usl - lsl) / (6.0 * deviation)

    normality: NormalityAssessment | None = None
    if flat.size >= AD_MIN_SAMPLE_SIZE:
        normality = assess_normality(flat, alpha=alpha)

    warnings = _warnings(
        n=n,
        subgroups=k,
        within_method=within_method,
        sigma_within=sigma_within,
        sigma_overall=sigma_overall,
        lsl=lsl,
        usl=usl,
        target=target,
        normality=normality,
    )

    return CapabilityReport(
        n=int(flat.size),
        subgroup_size=n,
        subgroups=k,
        mean=mean,
        sigma_within=sigma_within,
        sigma_overall=sigma_overall,
        within_method=within_method,
        lsl=lsl,
        usl=usl,
        target=target,
        cp=cp,
        cpl=cpl,
        cpu=cpu,
        cpk=cpk,
        cpm=cpm,
        pp=pp,
        ppl=ppl,
        ppu=ppu,
        ppk=ppk,
        normality=normality,
        warnings=warnings,
    )


def _warnings(
    *,
    n: int,
    subgroups: int,
    within_method: WithinMethod,
    sigma_within: float,
    sigma_overall: float,
    lsl: float | None,
    usl: float | None,
    target: float | None,
    normality: NormalityAssessment | None,
) -> tuple[str, ...]:
    messages: list[str] = []

    if normality is not None and not normality.normal:
        messages.append(
            "the normal model was rejected, and every index in this report "
            "assumes normality. These numbers are not conservative, they are "
            "wrong. Use the non-normal path (Box-Cox or the ISO 22514 "
            "percentile method) instead."
        )

    ratio = sigma_overall / sigma_within
    if ratio > STABILITY_RATIO:
        messages.append(
            f"sigma_overall is {ratio:.2f}x sigma_within, so the process is not "
            f"stable: it drifts between subgroups. Cp/Cpk describe a potential "
            f"the process is not currently delivering -- quote Pp/Ppk to the "
            f"customer, and put the process in control before trusting Cpk."
        )

    if n == 1:
        messages.append(
            "no subgroups were supplied, so the short-term sigma comes from the "
            "moving range of consecutive observations. This assumes the data are "
            "in time order; if they are not, sigma_within is meaningless."
        )

    if within_method == "moving_range" and n > 1:
        messages.append(
            "within_method='moving_range' was applied to subgrouped data, which "
            "ignores the subgroup structure."
        )

    if lsl is None or usl is None:
        messages.append(
            "only one specification limit was given, so Cp, Pp and Cpm are "
            "undefined (they measure spread against a two-sided tolerance). "
            "Cpk/Ppk are reported against the single limit."
        )
    elif target is None:
        messages.append(
            "no target was given, so Cpm was not computed. capstat does not "
            "assume the target is the midpoint of the specification."
        )

    if subgroups < 20 and n > 1:
        messages.append(
            f"only {subgroups} subgroups: the sigma estimates, and hence every "
            f"index, carry wide confidence intervals. AIAG recommends at least "
            f"25 subgroups for a capability study."
        )

    return tuple(messages)
