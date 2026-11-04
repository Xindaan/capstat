"""The zero-spread guard holds at every magnitude a float can carry.

T-0096 routed every "is this spread zero?" decision through one helper that
takes a mean square. Callers holding a root -- a sigma, a bias, a slope term --
squared it first, and a Python float above ~1e154 does not square to inf, it
raises ``OverflowError``. A Box-Cox transform with a large lambda produces such
values from ordinary readings, so ``capstat capability`` crashed on a column of
30 rounded diameters instead of reporting.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pytest
from capstat_core import (
    bias,
    capability,
    cusum_chart,
    ewma_chart,
    i_mr_chart,
    linearity,
)

BIG = 1e160
RNG = np.random.default_rng(7)
SERIES = BIG * (1.0 + 0.01 * RNG.standard_normal(30))

CASES: dict[str, Callable[[], object]] = {
    # Individuals: the moving-range sigma is a Python float, as on the CLI.
    "capability": lambda: capability(SERIES, lsl=0.9 * BIG, usl=1.1 * BIG),
    "i_mr_chart": lambda: i_mr_chart(SERIES),
    "ewma_chart": lambda: ewma_chart(SERIES),
    "cusum_chart": lambda: cusum_chart(SERIES),
    # Identical readings far from the reference: the bias itself is ~2e160.
    "bias": lambda: bias([3 * BIG] * 7, BIG),
    # Small references, huge readings: the slope itself is ~1e160.
    "linearity": lambda: linearity(
        [1.0, 2.0, 3.0],
        [SERIES[:5] * k for k in (1.0, 2.0, 3.0)],
    ),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_a_huge_scale_is_computed_not_crashed(name: str) -> None:
    with np.errstate(all="ignore"):
        CASES[name]()
