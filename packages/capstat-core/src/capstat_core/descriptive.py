"""Descriptive summary statistics.

Numerical accuracy is a design constraint here, not an afterthought. The
textbook one-pass variance ``(sum(x^2) - n * mean^2) / (n - 1)`` suffers
catastrophic cancellation when the data have a large mean relative to their
spread. On the NIST StRD ``NumAcc4`` dataset it does not merely lose precision:
it returns a *negative* variance (about -0.032, where the true value is 0.01),
which is mathematically impossible.

Every routine in this module therefore centers the data first and works from
the deviations (a two-pass algorithm), which reproduces the NIST certified
values to the limit of double precision. That limit is set by the input itself,
not by the algorithm: on NumAcc4 the float64 representation of the data already
perturbs the standard deviation by 5.6e-09 relative, and our result sits exactly
there.

References
----------
NIST/ITL Statistical Reference Datasets (StRD), Univariate Summary Statistics.
    https://www.itl.nist.gov/div898/strd/univ/homepage.html
Chan, T. F., Golub, G. H., & LeVeque, R. J. (1983). Algorithms for computing
    the sample variance: analysis and recommendations. *The American
    Statistician*, 37(3), 242-247.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from capstat_core._validation import as_sample as _as_sample

__all__ = [
    "DescriptiveSummary",
    "describe",
    "kurtosis",
    "lag1_autocorrelation",
    "mean",
    "skewness",
    "std_dev",
    "variance",
]


def _deviations(arr: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    """Deviations from the sample mean (the centering step of the two-pass)."""
    # Annotated rather than returned directly: numpy < 2.5 types `ndarray.__sub__`
    # as Any, which --strict rejects as an implicit Any return.
    deviations: npt.NDArray[np.float64] = arr - arr.mean()
    return deviations


def mean(x: npt.ArrayLike) -> float:
    """Arithmetic sample mean ``ybar = (1/n) * sum(y_i)``."""
    return float(_as_sample(x).mean())


def variance(x: npt.ArrayLike, *, ddof: int = 1) -> float:
    """Sample variance, two-pass.

    ``s^2 = sum((y_i - ybar)^2) / (n - ddof)``

    Parameters
    ----------
    ddof:
        Delta degrees of freedom. The default ``1`` gives the unbiased sample
        variance (denominator ``n - 1``), which is what NIST certifies and
        what SPC uses. Pass ``0`` for the population variance.
    """
    arr = _as_sample(x, minimum=ddof + 1)
    dev = _deviations(arr)
    return float(dev @ dev) / (arr.size - ddof)


def std_dev(x: npt.ArrayLike, *, ddof: int = 1) -> float:
    """Sample standard deviation, the square root of :func:`variance`."""
    return float(np.sqrt(variance(x, ddof=ddof)))


def lag1_autocorrelation(x: npt.ArrayLike) -> float:
    """Lag-1 autocorrelation coefficient, in the NIST StRD definition.

    ``r(1) = sum_{i=1}^{n-1} (y_i - ybar)(y_{i+1} - ybar)
             / sum_{i=1}^{n} (y_i - ybar)^2``

    Note that the denominator runs over *all* n observations while the
    numerator runs over the n-1 adjacent pairs; both use the overall mean.

    Returns
    -------
    float
        ``nan`` for a zero-variance sample, where the coefficient is
        undefined (0/0).
    """
    arr = _as_sample(x, minimum=2)
    dev = _deviations(arr)
    denominator = float(dev @ dev)
    if denominator == 0.0:
        return float("nan")
    return float(dev[:-1] @ dev[1:]) / denominator


def skewness(x: npt.ArrayLike, *, bias: bool = True) -> float:
    """Sample skewness.

    With ``bias=True`` (default, matching ``scipy.stats.skew``) this is the
    moment ratio ``g1 = m3 / m2**1.5`` with ``m_k = (1/n) * sum((y_i - ybar)^k)``.

    With ``bias=False`` the bias-corrected estimator is returned::

        G1 = g1 * sqrt(n * (n - 1)) / (n - 2)

    which is the convention used by most quality-engineering software. It
    requires at least three observations.

    Returns
    -------
    float
        ``nan`` for a zero-variance sample, where skewness is undefined.
    """
    arr = _as_sample(x, minimum=3 if not bias else 2)
    n = arr.size
    dev = _deviations(arr)
    m2 = float(dev @ dev) / n
    if m2 == 0.0:
        return float("nan")
    m3 = float((dev**3).sum()) / n
    # m2 > 0 here, so m2**1.5 == sqrt(m2)**3; spelling it this way keeps the
    # expression float-typed (typeshed gives `float ** float` the type Any,
    # since a negative base may produce a complex result).
    g1 = m3 / math.sqrt(m2) ** 3
    if bias:
        return g1
    return g1 * math.sqrt(n * (n - 1)) / (n - 2)


def kurtosis(x: npt.ArrayLike, *, bias: bool = True, fisher: bool = True) -> float:
    """Sample kurtosis.

    With ``bias=True`` and ``fisher=True`` (defaults, matching
    ``scipy.stats.kurtosis``) this is the excess kurtosis
    ``g2 = m4 / m2**2 - 3``, so a normal distribution has kurtosis 0.

    Parameters
    ----------
    bias:
        If ``False``, apply the bias correction::

            G2 = ((n + 1) * g2 + 6) * (n - 1) / ((n - 2) * (n - 3))

        which requires at least four observations.
    fisher:
        If ``False``, return Pearson's kurtosis (excess kurtosis + 3), so a
        normal distribution has kurtosis 3.

    Returns
    -------
    float
        ``nan`` for a zero-variance sample, where kurtosis is undefined.
    """
    arr = _as_sample(x, minimum=4 if not bias else 2)
    n = arr.size
    dev = _deviations(arr)
    m2 = float(dev @ dev) / n
    if m2 == 0.0:
        return float("nan")
    m4 = float((dev**4).sum()) / n
    g2 = m4 / m2**2 - 3.0
    if not bias:
        g2 = ((n + 1) * g2 + 6.0) * (n - 1) / ((n - 2) * (n - 3))
    return g2 if fisher else g2 + 3.0


@dataclass(frozen=True, slots=True)
class DescriptiveSummary:
    """A complete descriptive summary of one sample.

    ``std_dev`` and ``variance`` use the ``n - 1`` denominator; ``skewness``
    and ``kurtosis`` use the moment-ratio (biased) definitions, and kurtosis is
    the *excess* kurtosis (0 for a normal distribution).
    """

    n: int
    mean: float
    variance: float
    std_dev: float
    minimum: float
    maximum: float
    range: float
    median: float
    q1: float
    q3: float
    iqr: float
    skewness: float
    kurtosis: float
    lag1_autocorrelation: float


def describe(x: npt.ArrayLike) -> DescriptiveSummary:
    """Compute a full :class:`DescriptiveSummary` for ``x``.

    Requires at least two observations (the sample standard deviation is
    undefined for one). Quartiles use linear interpolation between order
    statistics (``numpy.percentile`` default, equivalent to R's type 7).
    """
    arr = _as_sample(x, minimum=2)
    q1, median, q3 = (float(q) for q in np.percentile(arr, [25.0, 50.0, 75.0]))
    minimum, maximum = float(arr.min()), float(arr.max())
    var = variance(arr)
    return DescriptiveSummary(
        n=int(arr.size),
        mean=float(arr.mean()),
        variance=var,
        std_dev=float(np.sqrt(var)),
        minimum=minimum,
        maximum=maximum,
        range=maximum - minimum,
        median=median,
        q1=q1,
        q3=q3,
        iqr=q3 - q1,
        skewness=skewness(arr),
        kurtosis=kurtosis(arr),
        lag1_autocorrelation=lag1_autocorrelation(arr),
    )
