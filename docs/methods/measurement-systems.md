# Measurement systems

Before trusting a capability study, find out how much of the variation you are
seeing is the *measurement system* rather than the parts.

The four studies answer different questions, and they are not
interchangeable:

| Study | Question | Needs |
|---|---|---|
| Gage R&R | Is the gage **consistent**? | Parts × operators × trials |
| Bias | Is it **right**? | A part with a known value |
| Linearity | Is it right **everywhere**? | Several masters across the range |
| Stability | Does it **stay** right? | One master, measured over time |

Gage R&R needs no reference value — it only compares readings to each other. The
other three need a part whose true value you already know.

## Gage R&R

A crossed study: every part is measured by every operator, several times. The
variance splits into

```
GRR = Repeatability + Reproducibility
```

**Repeatability** (equipment variation) is the same operator measuring the same
part twice and not getting the same number — the pure replicate variance.
**Reproducibility** (appraiser variation) is different operators getting
systematically different numbers; in the AIAG model this includes the
part-by-operator interaction, where operators disagree more on some parts than
others.

capstat implements both AIAG methods:

- **`gage_rr`** — the crossed two-way random-effects ANOVA. Preferred, because
  it is the only method that recovers the interaction term.
- **`gage_rr_range`** — the classic average-and-range method, for comparison or
  hand-calculation parity.

Two things routinely go wrong, and both are handled explicitly:

!!! note "A spurious interaction is dropped"
    If the part×operator F-test is not significant (AIAG's deliberately generous
    `p > 0.25`), the interaction is pooled back into repeatability before the
    components are re-estimated. Keeping a phantom interaction inflates
    reproducibility and hides a good gage.

!!! note "A negative variance is reported as zero, with a warning"
    Mean-square differences can come out negative for a component that is
    genuinely near zero. A variance cannot be negative, so it is clamped to zero
    and reported honestly as "indistinguishable from zero" — not printed as a
    negative number, and not silently dropped.

### Reading the result

**%Contribution** is variance-based, so the components sum to 100 %.
**%Study Variation** is standard-deviation-based, so they do *not* — and %SV is
always the larger, less flattering number. AIAG's acceptance bars are on %SV:
under 10 % good, 10–30 % marginal, over 30 % unacceptable.

**ndc** (number of distinct categories) is `1.41 × PV/GRR`, truncated: how many
non-overlapping groups the gage can actually tell apart. AIAG wants at least 5.

!!! note "d2* is computed, not copied"
    The average-and-range method needs `d2*`, the bias-corrected d2 for the mean
    of a finite number of ranges — which is what the AIAG K2/K3 constants
    encode. capstat derives it from its own `d2` and `d3` as
    `sqrt(d2² + d3²/g)` rather than transcribing the table, and checks the
    result against Duncan's published values.

**Sources.** AIAG MSA 4th ed.; Duncan, *Quality Control and Industrial
Statistics*, Table D3. See [Sources](../validation-sources.md#gage-rr).

## Bias

Measure a part whose true value is known, several times, and ask whether the
average lands on it:

```
bias = mean(readings) - reference
t    = bias / (s / sqrt(n))          df = n - 1
```

A non-zero bias is expected from noise alone, so the question is whether it is
*significantly* non-zero. capstat reports both the t-test and a confidence
interval for the bias, and takes its verdict from the interval — "does it
straddle zero". The two always agree, but the interval stays meaningful in the
degenerate case where every reading is identical and the t-statistic is not
defined.

**Sources.** AIAG MSA 4th ed. (Bias); validated additionally against scipy's
`ttest_1samp`. See [Sources](../validation-sources.md#bias).

## Linearity

Bias answers "is the gage right *here*?". Linearity asks whether it is right
*everywhere*: measure several masters spanning the range and see whether the
bias drifts.

```
bias_ij = a * reference_i + b + error
%linearity = |a| * 100
```

A significant slope `a` means the bias changes with the measured value — the
gage stretches or compresses the scale, and a single bias correction will not
fix it. The regression is fitted from the individual readings rather than the
per-part averages, so the residual scatter sizes the standard errors correctly;
on a balanced study the slope and intercept are identical either way, but the
degrees of freedom are not.

**Sources.** AIAG MSA 4th ed. (Linearity); validated additionally against
scipy's `linregress`. See [Sources](../validation-sources.md#linearity).

## Stability

Bias and linearity are snapshots. Stability is the movie: measure the same
master again and again over days or weeks and watch whether the readings stay
put.

This is not new statistics — it is a control chart on a master, and capstat says
so rather than dressing it up. `stability()` runs the readings through the
validated I-MR (individuals) or X-bar/R (subgroups) chart. What it adds is the
framing: an out-of-control point means the *gage* drifted, because the part's
true value never moved.
