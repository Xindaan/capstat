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

## Phase I and Phase II

By default the limits are estimated from the data being plotted. That is what
you do when establishing a chart, and it has a cost worth stating: a sustained
shift drags the centre line towards itself. On a 25-subgroup series with a
shift over the last five, the centre moves from 9.98 to 11.18 — which does not
merely soften the signal on the shifted subgroups, it flags seven *stable* ones
for sitting too far below a centre the shift invented. The chart misattributes
the fault.

Once a process is known to be stable, pass the centre and within-subgroup sigma
from that period:

```python
baseline = xbar_r_chart(stable_period)
today = xbar_r_chart(new_data,
                     center=baseline.location.limits.center,
                     sigma=baseline.sigma_within)
today.phase   # "II"
```

Now the limits cannot move, and only the genuinely shifted subgroups signal.

!!! note "Both halves or neither"
    A known centre combined with a sigma estimated from the data under test is
    neither phase, so capstat refuses it rather than producing limits that
    belong to no defensible chart.

The arithmetic is the same in both phases — every limit follows from a centre
and a sigma, and the only question is where those came from. Handed exactly
what it would have estimated, a Phase II chart reproduces the Phase I limits;
that identity is asserted for all three chart pairs.

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
