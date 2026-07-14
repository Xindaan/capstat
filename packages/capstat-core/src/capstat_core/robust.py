"""Robust (outlier-resistant) location and scale estimators.

The classical mean and standard deviation have a breakdown point of 0: a
single grossly wrong observation can move them arbitrarily far. That matters
in process data, where a mis-keyed measurement or a transient fault is common.
The estimators here trade a little efficiency under exact normality for
resistance to such contamination.

References
----------
Rousseeuw, P. J., & Croux, C. (1993). Alternatives to the median absolute
    deviation. *Journal of the American Statistical Association*, 88(424),
    1273-1283.
Huber, P. J., & Ronchetti, E. M. (2009). *Robust Statistics* (2nd ed.). Wiley.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from capstat_core._validation import as_sample as _as_sample

__all__ = [
    "MAD_NORMAL_CONSISTENCY",
    "iqr",
    "mad",
    "median",
    "trimmed_mean",
    "winsorized_mean",
]

#: Scale factor making the MAD a consistent estimator of sigma for normal data.
#:
#: For Y ~ N(mu, sigma^2), median(|Y - median(Y)|) converges to
#: sigma * Phi^-1(0.75), so dividing by Phi^-1(0.75) = 0.674489750196081...
#: recovers sigma. The reciprocal is the constant below.
MAD_NORMAL_CONSISTENCY = 1.482602218505602


def median(x: npt.ArrayLike) -> float:
    """Sample median: the 50 % quantile, and a location estimator with the
    highest possible breakdown point (50 %)."""
    return float(np.median(_as_sample(x)))


def iqr(x: npt.ArrayLike) -> float:
    """Interquartile range ``Q3 - Q1``.

    Quartiles use linear interpolation between order statistics
    (``numpy.percentile`` default, equivalent to R's type 7).
    """
    arr = _as_sample(x)
    q1, q3 = np.percentile(arr, [25.0, 75.0])
    return float(q3 - q1)


def mad(x: npt.ArrayLike, *, normal_consistent: bool = True) -> float:
    """Median absolute deviation about the median.

    ``MAD = median(|y_i - median(y)|)``

    Parameters
    ----------
    normal_consistent:
        If ``True`` (default), scale by :data:`MAD_NORMAL_CONSISTENCY` so the
        result estimates sigma for normally distributed data and is directly
        comparable to a standard deviation. If ``False``, return the raw MAD.

    Notes
    -----
    The MAD has a 50 % breakdown point, versus 0 % for the standard deviation.
    It returns 0 when more than half the sample takes a single value, which is
    a property of the estimator, not an error.
    """
    arr = _as_sample(x)
    raw = float(np.median(np.abs(arr - np.median(arr))))
    return raw * MAD_NORMAL_CONSISTENCY if normal_consistent else raw


def _trim_count(n: int, proportion: float) -> int:
    """Number of observations trimmed from *each* tail."""
    if not 0.0 <= proportion < 0.5:
        raise ValueError(f"proportion must be in [0.0, 0.5), got {proportion}")
    return int(n * proportion)


def trimmed_mean(x: npt.ArrayLike, proportion: float = 0.1) -> float:
    """Symmetrically trimmed mean.

    Discards ``floor(n * proportion)`` observations from each tail of the
    sorted sample and averages the rest.

    Parameters
    ----------
    proportion:
        Fraction removed from each tail, in ``[0.0, 0.5)``. ``0.0`` reproduces
        the arithmetic mean.

    Raises
    ------
    ValueError
        If ``proportion`` is outside ``[0.0, 0.5)``.

    Notes
    -----
    Because ``proportion < 0.5`` forces ``g = floor(n * proportion) < n / 2``,
    at least one observation always survives the trim; no empty-sample case
    can arise here.
    """
    arr = _as_sample(x)
    g = _trim_count(arr.size, proportion)
    kept = np.sort(arr)[g : arr.size - g]
    return float(kept.mean())


def winsorized_mean(x: npt.ArrayLike, proportion: float = 0.1) -> float:
    """Winsorized mean.

    Like :func:`trimmed_mean`, but instead of discarding the ``g = floor(n *
    proportion)`` most extreme observations in each tail, it *replaces* them
    with the nearest retained value. Extremes are pulled in rather than
    dropped, so every observation still carries weight.

    Parameters
    ----------
    proportion:
        Fraction winsorized in each tail, in ``[0.0, 0.5)``. ``0.0``
        reproduces the arithmetic mean.
    """
    arr = _as_sample(x)
    n = arr.size
    g = _trim_count(n, proportion)
    if g == 0:
        return float(arr.mean())
    ordered = np.sort(arr)
    ordered[:g] = ordered[g]
    ordered[n - g :] = ordered[n - g - 1]
    return float(ordered.mean())
