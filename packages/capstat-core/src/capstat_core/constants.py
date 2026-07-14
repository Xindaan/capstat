"""Control-chart constants, computed from their definitions.

Textbooks print these as tables, and most software copies the table. capstat
evaluates the defining integral instead. The reason is prosaic: a transcribed
table can carry a typo that no test will catch, because the test was written by
copying the same table. A constant derived from its definition and then checked
against an independently published table cannot fail that way -- and it is
exact for every n, not just the eight rows somebody chose to print.

Currently provided: ``d2`` and ``c4``, the two needed to estimate a
within-subgroup standard deviation for capability analysis. The remaining
constants (d3, A2, D3, D4, B3, B4) arrive with the control charts (T-0007).

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
from scipy import integrate, special, stats

__all__ = ["MAX_SUBGROUP_SIZE", "c4", "d2"]

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


@cache
def _d2_cached(n: int) -> float:
    def integrand(x: float) -> float:
        return 1.0 - float(stats.norm.cdf(x)) ** n - float(stats.norm.sf(x)) ** n

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
