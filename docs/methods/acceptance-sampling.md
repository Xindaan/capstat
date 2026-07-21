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

## Not implemented

The AQL master tables and sample-size code letters of ISO 2859-1 / ANSI-ASQ
Z1.4 / MIL-STD-105E. Those are committee conventions rather than values derived
from a definition, and reproducing ISO's tables in an MIT-licensed project is a
licensing question before it is a statistical one. capstat designs plans from
your risks instead.
