"""Internal input validation shared by the public statistics modules.

Not part of the public API.
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

__all__ = ["ZERO_SPREAD_RELATIVE", "as_sample", "is_zero_spread"]

#: A spread counts as zero when its root mean square is at most this fraction of
#: the largest magnitude in the data: 2**-43 ~= 1.1e-13, i.e. 1024 units in the
#: last place. See :func:`is_zero_spread` for the derivation.
ZERO_SPREAD_RELATIVE = 2.0**-43


def is_zero_spread(mean_square: float, data: npt.NDArray[np.float64]) -> bool:
    """Whether a mean square is zero at the resolution of ``data``.

    Every "zero variance" decision in capstat goes through here, because an
    exact ``== 0.0`` test decides it by how the data happen to round. Twenty
    readings of 3.3 have no spread, but their float mean is one ulp below 3.3
    for most n, so every computed deviation is ~4e-16 and the variance ~1e-31;
    twenty readings of 5.0 give exactly 0. The same holds for Gage R&R cell
    means, subgroup standard deviations and regression residuals.

    ``mean_square`` is a sum of squared deviations divided by the number of
    observations it runs over (a variance, ``sigma**2``, or an ANOVA sum of
    squares divided by the total count). It is zero here when::

        sqrt(mean_square) <= ZERO_SPREAD_RELATIVE * max|x_i|

    Derivation of the threshold. With ``u = 2**-53`` the unit roundoff, each
    deviation computed from identical values is a rounding residue. Summing n
    values pairwise (what numpy does along the contiguous axis; see the Notes
    of ``numpy.sum``) is accurate to about ``log2(n) * u`` relative, plus a
    small constant for its leaf blocks and one rounding each for the division
    and the subtraction: a few tens of u for any realistic n. Along other axes
    numpy sums naively, bounded by ``n * u`` for n terms -- the Gage R&R
    operator means, over parts x trials, which is a few hundred at most.
    Measured (600 random values from 1e-12 to 1e12, n from 2 to 1e6, numpy
    row variances and five crossed Gage R&R layouts up to 30 x 10 x 10): the
    largest root mean square of the residue was 9.1 u. The threshold,
    ``1024 u``, sits two orders of magnitude above that, so no float residue
    of genuinely identical readings passes for spread.

    On the other side it calls zero only a spread below 1.1e-13 of the data's
    own magnitude -- thirteen significant digits, beyond the resolution of any
    measuring instrument. Real small spreads stay real: sd 1e-9 around 1e-6 is
    1e-3 relative, and sd 1e-3 around 1e9 is 1e-12 relative, nine times the
    threshold.

    References
    ----------
    Higham, N. J. *Accuracy and Stability of Numerical Algorithms*, 2nd ed.,
        SIAM, 2002, ch. 4 (error bounds of recursive and pairwise summation).
    """
    scale = float(np.max(np.abs(data)))
    # Compared as root mean squares rather than squares: squaring the scale
    # overflows for data near 1e154 and underflows for data near 1e-162.
    return math.sqrt(mean_square) <= ZERO_SPREAD_RELATIVE * scale


def as_sample(x: npt.ArrayLike, *, minimum: int = 1) -> npt.NDArray[np.float64]:
    """Validate and coerce ``x`` into a one-dimensional float64 sample.

    Rejecting non-finite input here (rather than silently propagating ``nan``)
    keeps every downstream statistic total: if a call returns a number, that
    number is meaningful.

    Raises
    ------
    ValueError
        If the sample is not one-dimensional, holds fewer than ``minimum``
        observations, or contains NaN or infinite values.
    """
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(
            f"expected a one-dimensional sample, got {arr.ndim} dimension(s)"
        )
    if arr.size < minimum:
        raise ValueError(
            f"sample must contain at least {minimum} observation(s), got {arr.size}"
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError("sample contains NaN or infinite values")
    return arr
