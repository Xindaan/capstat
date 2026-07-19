# Control charts

## Read the dispersion chart first

An X-bar chart's limits are computed *from* the dispersion estimate. While the
spread is unstable, those limits — and any verdict drawn from them — mean
nothing. capstat returns both charts as a pair and warns when the dispersion
chart is out of control, because a location signal read off unstable limits is
not a signal at all.

## The charts

| Function | Use | Sigma from |
|---|---|---|
| `xbar_r_chart` | Subgroups, n ≤ 10 | `Rbar / d2(n)` |
| `xbar_s_chart` | Subgroups, larger n | `sbar / c4(n)` |
| `i_mr_chart` | Individual measurements | moving range of consecutive points |

```
X-bar:  xbarbar +/- A2 * Rbar        (equivalently +/- 3 sigma / sqrt(n))
R:      D3 * Rbar  ..  D4 * Rbar
```

The range uses only the largest and smallest value of each subgroup, so it
discards information and loses efficiency as n grows. Beyond n = 10, prefer
`xbar_s_chart`.

!!! note "D3 is zero for small subgroups, and that matters"
    The R chart's lower limit is `max(0, 1 - 3*d3/d2)`, which is zero for
    n ≤ 6. That is not a rounding convention: the unclamped value is genuinely
    negative and a range cannot be negative. The practical consequence is worth
    knowing — with small subgroups an R chart **cannot** signal that the spread
    has *improved*, because there is no lower limit to cross.

**Sources.** NIST/SEMATECH §6.3.2 and §6.3.2.1; Montgomery Appendix VI; ASTM
E2587. See [Sources](../validation-sources.md#shewhart-control-charts).

## Time-weighted charts

A Shewhart chart only looks at the current point, so it is slow to notice a
small sustained shift. EWMA and CUSUM accumulate evidence across points and see
those shifts far sooner.

- **`ewma_chart`** — an exponentially weighted moving average, `lambda = 0.2` by
  default, with time-varying limits that widen to their steady state.
- **`cusum_chart`** — accumulates deviations from target, signalling when the
  running sum crosses a decision interval `h`.

Both NIST worked examples are reproduced exactly, including *which* group first
signals — a decision, not a value, so it is asserted with no tolerance at all.

**Sources.** NIST/SEMATECH §6.3.2.3 (CUSUM) and §6.3.2.4 (EWMA). See
[Sources](../validation-sources.md#ewma-and-cusum).

## Run rules

A point outside the limits is the only signal a bare Shewhart chart gives, and
it is rarely the one a real process offers first. Processes drift, trend, and
hug the centre line long before they throw a point past 3σ.

Rules are applied **to** a chart, not baked into it — the zones are derived from
the chart's own limits. So `ControlChart.violations` keeps meaning exactly what
it always meant (points beyond the limits, which *is* Nelson rule 1), and
nothing gets reported twice under two names. Each violation carries the point
that completed the pattern *and* the whole window, so a plot can highlight the
run rather than just its last point.

!!! warning "More rules are not free"
    On a perfectly stable process the 3σ test alone signals about once in 370
    points. All four Western Electric rules: once in 61. All eight Nelson rules:
    **once in 44** — roughly eight times jumpier. Nelson himself advised against
    running all eight at once. Pass a subset and pick the rules that match the
    failure you are hunting.

    These rates are simulated in capstat's own test suite, not quoted from a
    textbook.

**The two standards disagree, and that is useful.** Western Electric rule 4
fires on **eight** consecutive points on one side; Nelson's rule 2 needs
**nine**. A run of exactly eight fires one and not the other — which is exactly
the sequence that would expose an off-by-one in either implementation, and
capstat tests it.

**Sources.** Nelson (1984); Western Electric Statistical Quality Control
Handbook (1956). See [Sources](../validation-sources.md#run-rules).
