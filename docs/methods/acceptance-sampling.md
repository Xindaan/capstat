# Acceptance sampling

Every other method in capstat asks what a process is doing. This one asks a
narrower question with a harder edge: given a sample from a delivered lot,
**accept it or send it back**.

A single sampling plan by attributes is two numbers — draw `n` items, accept if
at most `Ac` of them are defective — and everything else follows from them.
capstat computes that "everything else" from the definition; it does not read
plans out of a table.

!!! warning "What a sampling plan does not tell you"
    A plan bounds risk over a **stream** of lots. It says almost nothing about
    the single lot in front of you, and accepting a lot is not evidence that the
    lot is good. Acceptance sampling also does not improve quality — it sorts
    what has already been made. Every report capstat produces carries these
    caveats rather than leaving them to be inferred.

## The OC curve

The operating characteristic curve is the plan's whole personality: the
probability `Pa` of accepting a lot, against how defective that lot really is.

| Model | When it applies | Distribution |
|---|---|---|
| `binomial` (Type B) | Sampling a process, or a lot large enough that removing the sample does not change it | `X ~ Binomial(n, p)` |
| `hypergeometric` (Type A) | Sampling one finite lot of known size `N` | `X ~ Hypergeometric(N, D, n)` |
| `poisson` | The classical approximation the published unity-value tables are built on | `X ~ Poisson(np)` |

```
Pa = P(X <= Ac)
```

The choice is not stylistic. The binomial treats the lot as inexhaustible; when
the sample is more than about a tenth of the lot, that is simply the wrong
model, and capstat says so instead of quietly carrying on.

!!! note "A finite lot cannot be any fraction defective"
    A lot of 50 items cannot be 1 % defective — the nearest whole number of
    defectives is zero. On the Type A path capstat reports the quality level it
    actually evaluated, and refuses to *design* a plan against a level the lot
    cannot express, because the producer's risk condition would then be met by a
    perfect lot and constrain nothing.

## Rectifying inspection: AOQ, AOQL, ATI

If rejected lots are screened 100 % and their defectives replaced, two more
quantities follow:

```
AOQ = Pa(p) * p * (N - n) / N        ATI = n + (1 - Pa(p)) * (N - n)
```

The AOQ curve starts at zero (perfect incoming quality), returns to zero (every
lot rejected and screened), and peaks in between. That peak is the **AOQL** —
the worst long-run outgoing quality the scheme can produce. capstat finds it by
searching the curve rather than reading it off a grid, which is why its AOQL
generally sits between the tabulated points of published examples.

!!! warning "The AOQL is an average"
    It bounds the mean outgoing quality over a stream of rectified lots.
    Individual outgoing lots can be worse. It is not a guarantee about anything
    you can hold.

## Designing a plan

Given two points — an AQL you want accepted with probability `1 - alpha` and an
LTPD you want rejected with probability `1 - beta` — `design_single_sampling_plan`
returns the **smallest** `(n, Ac)` whose OC curve passes both. It searches the
same OC function the rest of the module uses; there is no table involved, and no
standard's master plan is consulted.

```python
from capstat_core import design_single_sampling_plan, evaluate_plan

plan = design_single_sampling_plan(aql=0.01, ltpd=0.05,
                                   producer_risk=0.02, consumer_risk=0.15)
plan.sample_size, plan.acceptance_number   # (144, 4)

report = evaluate_plan(plan, aql=0.01, ltpd=0.05)
report.producer_risk, report.consumer_risk # (0.01534843..., 0.1487162...)
```

!!! note "Ac = 0 plans are not simply 'tighter'"
    With `Ac = 0` the curve is `Pa = (1 - p)^n`: it has no shoulder and falls
    from the first defective onward, so it rejects genuinely good lots far more
    often than the sample size suggests. That is a deliberate trade, and capstat
    names it.

## What it is validated against

The NIST/SEMATECH handbook's worked `(n=52, c=3)` plan supplies the OC, AOQ,
AOQL and ATI tables; three independent implementations (the R packages
*AcceptanceSampling* and *AccSamplingDesign*, and Minitab's documented worked
example) supply values to eight significant digits, which is far tighter than
any printed table. Plans — being decisions, not estimates — are asserted
exactly.

Validating against those sources turned up four inconsistencies **in the
published tables**, which capstat reproduces and explains rather than tolerating:
the handbook's AOQ column is computed with an approximation its own page
contradicts, one of its entries is off by a factor of ten, its ATI column is
truncated rather than rounded, and its AOQL is quoted with a digit missing. See
[Sources](../validation-sources.md).

The one gap, stated plainly: no published worked example with an acceptance
number above zero was found for the Type A (hypergeometric) curve, so that path
is validated against `scipy.stats.hypergeom` and a hand-written enumeration of
the definition instead of against a citation.

## In the app

The `/acceptance-sampling` page designs a plan from your two risk points, draws
the OC curve with both levels marked, and decides a lot from an observed defect
count. Over HTTP it is
`/compute/acceptance-sampling/{evaluate,design,oc-curve,inspect}` — one route
per core entry point, as everywhere else in the API.

## If your specification names a standard

capstat does **not** implement the AQL master tables and sample-size code
letters of ISO 2859-1 / ANSI-ASQ Z1.4 / MIL-STD-105E. That is a position, not a
gap waiting to be filled.

Those tables are committee conventions rather than values derived from a
definition — the sample sizes follow the R5 preferred-number series and the
acceptance numbers were chosen so that `Pa` lands near 0.95 at the AQL, but no
formula generates a given cell. Reproducing ISO's tables in an MIT-licensed
project is also a licensing question before it is a statistical one: ISO
standards may not be reproduced without permission. MIL-STD-105E, the
public-domain ancestor, is **not** a substitute — its tables were adopted into
ISO 2859 *"with minor changes"*, so a plan taken from it may differ from the ISO
cell your specification actually names. A plan that looks conformant without
being conformant is worse than no plan at all.

What to do instead, which loses you nothing: anyone claiming conformity to
ISO 2859-1 needs a licensed copy of it in any case. Read `n` and `Ac` out of it,
enter them on the `/acceptance-sampling` page or pass them to `evaluate_plan`,
and capstat reports what the table itself does not — the producer's and
consumer's risk the plan really carries at your two quality levels, the quality
at which it is a coin flip, the AOQL, and the inspection it costs. The standard
tells you *which* plan to use; capstat tells you *what that plan buys*.

Two things worth knowing if you work to ISO 2859-1, neither of which a lookup
table would have given you:

- It is a **scheme, not a plan**. Its protection comes from the switching rules
  between normal, tightened and reduced inspection. Looking up the
  normal-inspection row and never switching does not deliver what the standard
  promises.
- Where a cell carries an **arrow**, you follow it to the next usable row — which
  changes the sample size, and with it everything on this page.
