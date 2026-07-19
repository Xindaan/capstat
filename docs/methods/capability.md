# Capability

## The two sigmas

The single most common way capability software misleads people is by blurring
two different standard deviations.

**`sigma_within`** (short-term) is estimated from variation *inside* subgroups.
It answers: how good could this process be if it held its current settings? It
drives **Cp, Cpk, Cpm** — the *potential*.

**`sigma_overall`** (long-term) is the ordinary standard deviation of every
observation. It absorbs drift, tool wear, shift changes — everything that moves
the process between subgroups. It drives **Pp, Ppk** — the *actual* performance
the customer receives.

For a perfectly stable process the two coincide. For a real one, `Cpk > Ppk`,
and the gap *is* the instability. A tool that reports only Cpk on a drifting
process is quoting a number the customer will never experience. capstat always
reports both, and warns when they diverge by more than 25 %.

## Formulas

```
Cp  = (USL - LSL) / (6 * sigma)
Cpu = (USL - mu)  / (3 * sigma)
Cpl = (mu - LSL)  / (3 * sigma)
Cpk = min(Cpu, Cpl)
Cpm = (USL - LSL) / (6 * sqrt(sigma^2 + (mu - T)^2))
```

Pp, Ppu, Ppl and Ppk are the same expressions evaluated with `sigma_overall`.

An index is `None` when it is not defined for the specification given: `Cp`,
`Pp` and `Cpm` need *both* limits, `Cpm` additionally needs a target, and the
one-sided indices need their own limit. `None` means "undefined here", which is
not the same as `0.0`.

!!! note "No target is invented"
    `Cpm` is only computed when you supply a target. capstat does not assume the
    target is the midpoint of the specification — that is a real engineering
    decision, and often wrong.

**Sources.** NIST/SEMATECH e-Handbook §6.1.6 for the indices; Chan, Cheng &
Spiring (1988) for Cpm. Both listed under
[Sources](../validation-sources.md#capability-indices-and-chart-constants).

## Subgroups, and what happens without them

Cp/Cpk need subgroup structure to estimate a within-subgroup sigma. Handed a
flat list of numbers, capstat estimates the short-term sigma from the moving
range (the I-MR convention) **and says so** in a warning, rather than quietly
substituting the overall sigma and still calling the result Cpk.

That fallback assumes the data are in time order. If they are not, `sigma_within`
is meaningless — and this is exactly the failure that leaves no trace.

## When the data are not normal

Capability indices read tail probabilities off a fitted normal. On skewed data
those tails are wrong. `analyze_capability()` tests normality first and then
picks a path:

1. **Normal** — the model was not rejected; the standard indices apply.
2. **Box-Cox** — the model was rejected, but a power transformation achieved
   normality. Indices are computed on the transformed scale against transformed
   limits. Preferred over the percentile method because it preserves the
   within/overall split, and hence Cp and Cpk.
3. **Percentile (ISO 22514)** — used when Box-Cox cannot help. Reads the 0.135 %,
   50 % and 99.865 % percentiles off the best-fitting distribution.

The result carries `path` and a `rationale` sentence explaining the choice.

!!! warning "The percentile path has no Cp or Cpk"
    The percentile method reads percentiles off the *overall* fitted
    distribution. It has no within/between subgroup split, so Cp and Cpk do not
    exist for it — capstat returns `None` rather than inventing a number. Only
    Pp and Ppk are meaningful there.

!!! note "Box-Cox is not applied silently"
    Box-Cox needs strictly positive data. capstat will **not** shift your data to
    make it applicable: the offset changes the indices and must be a recorded
    decision, not a silent one. It also refuses when an extreme fitted lambda
    collapses both specification limits onto the same floating-point value —
    which really happens — and routes to the percentile method instead.

**Sources.** Box & Cox (1964); ISO 22514-4. See
[Sources](../validation-sources.md#non-normal-capability).

## Reference values

The NIST worked example pins the index formulas themselves: with `USL = 20`,
`LSL = 8`, `mu = 16`, `sigma = 2`, capstat reproduces `Cp = 1.0` and
`Cpk = 0.6667`. That gap is the entire reason Cpk exists — the spread would fit
the tolerance, but the process is off-centre and producing scrap.
