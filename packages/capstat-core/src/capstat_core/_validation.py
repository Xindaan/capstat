"""Internal input validation shared by the public statistics modules.

Not part of the public API.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

__all__ = ["as_sample"]


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
