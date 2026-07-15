"""Control-chart constants, computed from their definitions.

Textbooks print these as tables, and most software copies the table. capstat
evaluates the defining integral instead. The reason is prosaic: a transcribed
table can carry a typo that no test will catch, because the test was written by
copying the same table. A constant derived from its definition and then checked
against an independently published table cannot fail that way -- and it is
exact for every n, not just the eight rows somebody chose to print.

Two of the values here show why that matters:

* ``D4(3)``. We compute 2.5746. NIST prints 2.575; a widely reproduced
  ASTM-derived table prints 2.574. The published tables disagree with each other
  in the last digit, and our computed value settles it.
* ``E2(2)``. Tables print 2.660. The true value is 2.6587, and the discrepancy
  is not ours: the tables computed ``3 / d2`` from an already-rounded
  ``d2 = 1.128`` and propagated the error. Copying the table would import that
  mistake; deriving from the definition does not.

References
----------
Montgomery, D. C. *Introduction to Statistical Quality Control*, Appendix VI.
ASTM E2587, *Standard Practice for Use of Control Charts in Statistical Process
    Control*.
NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2.
"""

from __future__ import annotations

import math
from functools import cache

import numpy as np
from scipy import integrate, special

__all__ = [
    "A2",
    "A3",
    "B3",
    "B4",
    "D3",
    "D4",
    "E2",
    "MAX_SUBGROUP_SIZE",
    "c4",
    "d2",
    "d2_star",
    "d3",
]

# ---------------------------------------------------------------------------
# A naming hazard, inherited from the literature and kept deliberately.
#
#   d3(n)  (lowercase)  = the standard DEVIATION of the range of n normals.
#   D3(n)  (uppercase)  = the LOWER control-limit factor of the R chart,
#                         D3 = 1 - 3*d3/d2, floored at zero.
#
# They differ only in case, and they are entirely different quantities. Every
# textbook does this, so renaming would make the code harder to check against
# its sources, not easier -- but it is a real trap, so: read the case.
# ---------------------------------------------------------------------------

#: Largest subgroup size ``d2`` is offered for. The range loses efficiency
#: badly as a scale estimator beyond this, and refusing is more useful than
#: obliging. ``c4`` carries no such limit: it is applied at the pooled degrees
#: of freedom, which are routinely in the hundreds.
MAX_SUBGROUP_SIZE = 25

_C4_MAX_N = 100_000


def _check_n(n: int, *, maximum: int, hint: str = "") -> None:
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError(f"subgroup size must be an int, got {type(n).__name__}")
    if n < 2:
        raise ValueError(f"subgroup size must be >= 2, got {n}")
    if n > maximum:
        raise ValueError(f"subgroup size must be <= {maximum}, got {n}{hint}")


_SQRT_2 = math.sqrt(2.0)
_INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)


def _phi(x: float) -> float:
    """Standard normal pdf.

    Hand-rolled rather than ``scipy.stats.norm.pdf``. The quadratures below call
    these hundreds of thousands of times on *scalars*, and a scalar scipy
    distribution call carries ~50 us of dispatch overhead against ~0.1 us here.
    Using scipy made d3(n) take 1.5 seconds -- a control chart is not allowed to
    cost that. The values agree to 1e-15.
    """
    return _INV_SQRT_2PI * math.exp(-0.5 * x * x)


def _Phi(x: float) -> float:
    """Standard normal cdf, via erfc. See :func:`_phi` for why not scipy."""
    return 0.5 * math.erfc(-x / _SQRT_2)


@cache
def _d2_cached(n: int) -> float:
    def integrand(x: float) -> float:
        upper = _Phi(x)
        return 1.0 - upper**n - (1.0 - upper) ** n

    value, _error = integrate.quad(integrand, -np.inf, np.inf, limit=200)
    return float(value)


@cache
def _c4_cached(n: int) -> float:
    log_ratio = special.gammaln(n / 2.0) - special.gammaln((n - 1) / 2.0)
    return math.sqrt(2.0 / (n - 1)) * math.exp(log_ratio)


# The public functions below deliberately wrap the cached ones rather than
# carrying @cache themselves. functools.cache erases the signature -- mypy sees
# an _lru_cache_wrapper whose __call__ takes *args: Hashable -- so a decorated
# d2 would accept d2(5.0), d2("five") and anything else without complaint, for
# us *and* for anyone type-checking against capstat. The wrapper keeps the
# signature checkable and the results cached.


def d2(n: int) -> float:
    """Expected range of ``n`` independent standard normal variates.

    ``d2(n) = E[R] / sigma``, so ``sigma_hat = Rbar / d2(n)`` is an unbiased
    estimator of the within-subgroup standard deviation.

    It is defined by the integral over the range distribution::

        d2(n) = integral over R of [ 1 - Phi(x)^n - (1 - Phi(x))^n ] dx

    which this function evaluates numerically (absolute error ~1e-8, far below
    the three decimals to which the textbook tables are printed).

    Raises
    ------
    ValueError
        If ``n < 2`` (a range needs two observations) or ``n`` exceeds
        :data:`MAX_SUBGROUP_SIZE`.
    """
    _check_n(
        n,
        maximum=MAX_SUBGROUP_SIZE,
        hint="; for larger subgroups use a standard-deviation-based estimator, "
        "not the range",
    )
    return _d2_cached(n)


def c4(n: int) -> float:
    """Bias-correction factor for the sample standard deviation.

    ``E[s] = c4(n) * sigma``, so ``sigma_hat = sbar / c4(n)`` is unbiased. The
    sample standard deviation *underestimates* sigma -- markedly so for small n
    (``c4(2) = 0.7979``) -- which is why the correction exists.

    Closed form::

        c4(n) = sqrt(2 / (n - 1)) * Gamma(n / 2) / Gamma((n - 1) / 2)

    Computed via ``lgamma`` so that the gamma functions do not overflow: the
    pooled estimator applies c4 at the total degrees of freedom, which for a
    realistic study runs into the hundreds and would overflow ``Gamma`` outright.

    Raises
    ------
    ValueError
        If ``n < 2``.
    """
    _check_n(n, maximum=_C4_MAX_N)
    return _c4_cached(n)


@cache
def _d3_cached(n: int) -> float:
    # The joint density of the minimum x and the maximum y of n iid standard
    # normals (x < y) is
    #     f(x, y) = n(n-1) phi(x) phi(y) [Phi(y) - Phi(x)]^(n-2)
    # so E[W^2] for the range W = y - x is the double integral below, and
    #     d3 = sqrt(E[W^2] - d2^2).
    # The same joint density integrated against (y - x) reproduces d2, which the
    # tests use as an internal consistency check on this derivation.
    def integrand(y: float, x: float) -> float:
        gap = _Phi(y) - _Phi(x)
        return (y - x) ** 2 * n * (n - 1) * _phi(x) * _phi(y) * gap ** (n - 2)

    # +/-8 sigma: beyond that the normal density contributes less than 1e-15,
    # far below the accuracy the result is used at.
    second_moment, _error = integrate.dblquad(
        integrand, -8.0, 8.0, lambda x: x, lambda _x: 8.0, epsabs=1e-10
    )
    return math.sqrt(float(second_moment) - _d2_cached(n) ** 2)


def d3(n: int) -> float:
    """Standard deviation of the range of ``n`` standard normal variates.

    Not to be confused with :func:`D3`, the R chart's lower limit factor. See
    the note at the top of this module.

    Computed from the joint density of the sample minimum and maximum; the
    published tables (Montgomery Appendix VI) are reproduced to their full
    printed precision.
    """
    _check_n(
        n,
        maximum=MAX_SUBGROUP_SIZE,
        hint="; the range is a poor scale estimator for subgroups that large",
    )
    return _d3_cached(n)


def d2_star(n: int, g: int) -> float:
    """Bias-corrected ``d2`` for the mean of ``g`` ranges of size ``n``.

    When a scale estimate is built from the *average* of only a few ranges --
    as the average-and-range Gage R&R does, with a single range of the operator
    means or the part means -- the plain ``d2`` under-corrects. The relative
    range ``W = R / sigma`` has mean ``d2(n)`` and standard deviation ``d3(n)``,
    so the average of ``g`` independent ranges satisfies::

        E[Rbar^2] = sigma^2 * (d2(n)^2 + d3(n)^2 / g)

    and the divisor that makes ``Rbar / d2_star`` unbiased in that mean-square
    sense is::

        d2_star(n, g) = sqrt(d2(n)^2 + d3(n)^2 / g)

    As ``g -> infinity`` this collapses to ``d2(n)`` (many ranges, no
    correction). For ``g = 1`` it reproduces Duncan's tabulated d2* -- e.g.
    ``d2_star(2, 1) = 1.4142``, ``d2_star(10, 1) = 3.179`` -- which is exactly
    where the AIAG K2 and K3 constants come from (``K = 1 / d2_star``). Computed
    from ``d2`` and ``d3`` rather than transcribed, for the reason this whole
    module exists.

    Raises
    ------
    ValueError
        If ``n < 2``, ``n`` exceeds :data:`MAX_SUBGROUP_SIZE`, or ``g < 1``.
    """
    if not isinstance(g, int) or isinstance(g, bool):
        raise TypeError(f"number of ranges must be an int, got {type(g).__name__}")
    if g < 1:
        raise ValueError(f"number of ranges must be >= 1, got {g}")
    return math.sqrt(d2(n) ** 2 + d3(n) ** 2 / g)


def A2(n: int) -> float:
    """X-bar chart limit factor for a range-based sigma: ``3 / (d2 * sqrt(n))``.

    The limits are ``xbarbar +/- A2 * Rbar``, which is exactly
    ``xbarbar +/- 3 * sigma_within / sqrt(n)`` with ``sigma_within = Rbar / d2``.
    """
    return 3.0 / (d2(n) * math.sqrt(n))


def A3(n: int) -> float:
    """X-bar chart limit factor for an s-based sigma: ``3 / (c4 * sqrt(n))``.

    The limits are ``xbarbar +/- A3 * sbar``. Prefer this over :func:`A2` for
    larger subgroups: the range discards all but two observations, so it loses
    efficiency as n grows.
    """
    return 3.0 / (c4(n) * math.sqrt(n))


def D3(n: int) -> float:
    """R chart LOWER limit factor: ``max(0, 1 - 3 * d3 / d2)``.

    Zero for ``n <= 6``. That is not a rounding convention: the lower limit is
    genuinely negative there, and a range cannot be negative. The practical
    consequence is worth knowing -- with small subgroups an R chart *cannot*
    signal that the spread has improved, because there is no lower limit to
    cross.
    """
    return max(0.0, 1.0 - 3.0 * d3(n) / d2(n))


def D4(n: int) -> float:
    """R chart UPPER limit factor: ``1 + 3 * d3 / d2``."""
    return 1.0 + 3.0 * d3(n) / d2(n)


def B3(n: int) -> float:
    """s chart LOWER limit factor: ``max(0, 1 - 3 * sqrt(1 - c4^2) / c4)``.

    Zero for ``n <= 5``, for the same reason :func:`D3` is: the unclamped value
    is negative and a standard deviation is not.
    """
    return max(0.0, 1.0 - 3.0 * math.sqrt(1.0 - c4(n) ** 2) / c4(n))


def B4(n: int) -> float:
    """s chart UPPER limit factor: ``1 + 3 * sqrt(1 - c4^2) / c4``.

    NIST states the s chart limits as ``sbar +/- 3 * (sbar / c4) * sqrt(1 - c4^2)``
    (e-Handbook 6.3.2), which is this factor multiplied out.
    """
    return 1.0 + 3.0 * math.sqrt(1.0 - c4(n) ** 2) / c4(n)


def E2(n: int = 2) -> float:
    """Individuals chart limit factor: ``3 / d2(n)``.

    The limits are ``xbar +/- E2 * MRbar``. With the usual moving range of two
    consecutive points, ``E2(2) = 2.6587``.

    Published tables give 2.660. They are slightly wrong: that value comes from
    evaluating ``3 / d2`` with ``d2`` already rounded to 1.128, propagating the
    rounding error. Deriving from the definition avoids importing that mistake.
    """
    return 3.0 / d2(n)
