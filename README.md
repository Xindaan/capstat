# capstat

[![CI](https://github.com/Xindaan/capstat/actions/workflows/ci.yml/badge.svg)](https://github.com/Xindaan/capstat/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

**Reference-validated statistical process control, process capability, and
measurement system analysis — correctness you can audit.**

capstat is a trustworthy, MIT-licensed alternative to expensive
quality-engineering software. Its differentiator is verifiable correctness:
every statistical result is validated against published reference values
(NIST StRD, Montgomery, AIAG manuals, ISO 22514).

> **Status:** early development (v0.1 in progress). The core statistics
> library is being built method by method; the API and web app follow. See
> [PLAN.md](PLAN.md) for the roadmap and [TASK.md](TASK.md) for the backlog.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) (Python 3.11+ is fetched
automatically).

```bash
git clone https://github.com/Xindaan/capstat.git
cd capstat
uv sync                 # create the environment and install all workspace members
uv run pytest           # run the test suite
```

Install the standalone core library from source:

```bash
uv pip install ./packages/capstat-core
```

## Usage

The public API is populated milestone by milestone. Available today:
descriptive statistics and robust (outlier-resistant) estimators.

```python
from capstat_core import describe, mad, median, trimmed_mean

measurements = [10.1, 10.3, 9.8, 10.0, 10.2, 9.9, 10.4, 25.0]  # one bad reading

summary = describe(measurements)
summary.mean        # 11.9625   -- dragged up by the one bad reading
summary.std_dev     # 5.2717    -- and so is the spread
summary.skewness    # skewness / kurtosis for a normality gut-check
summary.lag1_autocorrelation  # serial correlation: are the data independent?

# Robust alternatives, which the outlier barely moves:
median(measurements)              # ~10.15
trimmed_mean(measurements, 0.125) # 10.15
mad(measurements)                 # ~0.2965 -- a sigma estimate, scaled for
                                  # normal data, vs. std_dev's 5.2717
```

`describe` returns an immutable `DescriptiveSummary` with `n`, `mean`,
`variance`, `std_dev`, `minimum`, `maximum`, `range`, `median`, `q1`, `q3`,
`iqr`, `skewness`, `kurtosis`, and `lag1_autocorrelation`.

### Normality — with the caveats attached

Capability indices assume a normal process. `assess_normality` runs both the
Anderson-Darling and Shapiro-Wilk tests and returns a verdict you can act on,
together with every reason that verdict might mislead you:

```python
from capstat_core import assess_normality

report = assess_normality(measurements)

report.normal            # False -- True only if BOTH tests fail to reject
report.recommendation    # what to do next, in words
report.warnings          # why the verdict might be wrong; () means "take it at face value"
```

On the NIST `Mavro` dataset (50 filter-transmittance readings) it reports
non-normality (Anderson-Darling p = 2.4e-04, Shapiro-Wilk p = 5.1e-04) — and
also warns that the lag-1 autocorrelation is **0.938**, which violates the
independence assumption *both tests are built on*. A tool that printed only the
p-value would be confidently reporting a number it had no right to compute.
`assess_normality` also flags samples too small to have power, samples so large
that trivial deviations turn "significant", and cases where the two tests
disagree (which fail closed, as non-normal).

### Capability — Cpk and Ppk, never one without the other

```python
from capstat_core import capability

report = capability(subgroups, lsl=90.0, usl=110.0, target=100.0)
```

On a process whose mean drifts between subgroups, capstat reports:

| | potential (short-term) | actual (long-term) |
|---|---|---|
| spread | Cp = 3.61 | Pp = 1.26 |
| centred | **Cpk = 3.25** | **Ppk = 1.13** |

Same data. `Cpk = 3.25` looks world-class; `Ppk = 1.13` is what the customer
actually receives. The gap *is* the instability — `sigma_overall` is 2.87× the
within-subgroup sigma — and capstat says so in `report.warnings` rather than
letting you quote the flattering number.

Cp/Cpk need subgroup structure to mean anything. Given a flat list of
measurements, capstat estimates the short-term sigma from the moving range and
tells you it did, instead of quietly substituting the overall sigma and still
calling the result Cpk. Given no `target`, it returns `cpm = None` rather than
assuming your target is the midpoint of the tolerance — for an asymmetric
tolerance, that assumption is simply wrong.

### Non-normal processes — a decision path, not a silent assumption

Plenty of real processes are legitimately skewed (anything bounded at zero:
flatness, roundness, contamination). On those, the standard indices are not
merely imprecise — they are wrong, and usually optimistic. `analyze_capability`
picks a method and **records why**:

```python
from capstat_core import analyze_capability

analysis = analyze_capability(measurements, lsl=5.0, usl=60.0)

analysis.path       # "normal" | "box-cox" | "percentile"
analysis.rationale  # the reasoning, in words
analysis.ppk
```

On a lognormal process it reports:

> path: `box-cox` — *"the normal model was rejected, but a Box-Cox
> transformation with lambda = 0.0525 achieved normality, so the standard
> indices were computed on the transformed scale against the transformed
> specification limits. Box-Cox is preferred over the percentile method because
> it preserves the within/overall split, and hence Cp and Cpk."*

Note **"against the transformed specification limits"**. Transforming the data
and leaving the limits in their original units is the classic way to produce a
confidently wrong Cpk; capstat carries the limits through the same λ (here
LSL 5.0 → 1.6794, USL 60.0 → 4.5677). Box-Cox is skipped, with an explanation,
when the data are not strictly positive — capstat will not shift your data to
make the maths work, because the offset changes the indices and must be your
recorded decision.

If Box-Cox cannot achieve normality either, the path falls through to the
**ISO 22514 percentile method**, which replaces the 6σ span with the span
between the 0.135 % and 99.865 % percentiles of a fitted distribution. That
method yields long-term indices only — it has no within/between split, so no Cp
or Cpk exists for it, and capstat does not invent one.

> **The two non-normal methods are not interchangeable.** They agree only where
> a process is exactly "just capable" (index = 1); elsewhere they legitimately
> differ — we measure Box-Cox Ppu = 1.61 against percentile Ppu = 2.44 on
> identical data. Don't compare an index from one against a threshold
> calibrated on the other.

### Control charts — read the dispersion chart first

```python
from capstat_core import xbar_r_chart, xbar_s_chart, i_mr_chart

pair = xbar_r_chart(subgroups)

pair.location.violations     # X-bar chart: []      — every average in limits
pair.dispersion.violations   # R chart:     [9]     — the spread is not
pair.in_control              # False
```

The X-bar chart above looks perfectly healthy. It isn't. Its limits are computed
*from* R̄ — so when the R chart is out of control, R̄ is an average of
incomparable things and the X-bar limits derived from it mean nothing. capstat
judges the dispersion chart first and says so:

> *"the R chart is out of control at [9]. Judge this first: the X-bar limits are
> computed from the dispersion estimate, so while the spread is unstable those
> limits — and any verdict drawn from them — mean nothing. Fix the spread, then
> re-chart."*

`in_control` is the AND of both charts, never just the location chart.

Other things capstat tells you rather than leaving you to know:

- **The R/s chart has no lower limit for small subgroups** (D₃ = 0 for n ≤ 6).
  That is not a rounding convention — the unclamped limit is negative, and a
  range cannot be. The consequence is that the chart *cannot detect an
  improvement* in spread, and capstat says so.
- **`i_mr_chart` assumes your data are in time order.** Shuffle them and the
  limits still look perfectly reasonable. capstat cannot detect that, so it
  warns every time.
- **These are Phase I (trial) limits**, estimated from the data being plotted.
  A large excursion inflates the very limits meant to catch it.

Run-based rules (Nelson, Western Electric) that catch drifts never crossing a
limit are not in yet — only points beyond the limits are flagged today.

All chart constants (d₂, d₃, c₄, A₂, A₃, B₃, B₄, D₃, D₄, E₂) are **computed from
their definitions**, not copied from a table. That is not fussiness: the
published tables print `E₂ = 2.660`, which is wrong — they evaluated `3/d₂` using
an already-rounded `d₂ = 1.128` and propagated the error. The true value is
2.6587. (The tables also disagree with each other: NIST prints D₄(3) = 2.575,
the ASTM-derived table 2.574. We compute 2.5746.)

### EWMA and CUSUM — seeing what Shewhart misses

A Shewhart chart looks at one point at a time, which makes it excellent at
catching a big jump and nearly blind to a small sustained drift. Give a process
a **+1σ shift at point 30** and watch:

```python
from capstat_core import i_mr_chart, cusum_chart

i_mr_chart(values).location.violations   # ()  — never notices, across 70 points
cusum_chart(values, target=100, sigma=1).violations[0]   # 46 — found it
```

The Shewhart chart never signals at all. CUSUM finds the shift 16 points in.
That is the whole reason these charts exist: a 3σ Shewhart chart takes ~44
points on average to see a 1σ shift, a CUSUM about 10 — both figures verified by
simulation in the test suite, not quoted on faith.

**The trap capstat defaults around:** both charts need a σ, and the obvious
choice — the standard deviation of all the data — is poison. A sustained shift
*inflates* that σ, which widens the limits, which hides the shift. The chart then
reports that everything is fine. capstat estimates σ from the **moving range**
instead, which only sees consecutive differences and so survives a level change
almost intact (measured over 200 runs: moving-range σ = 1.002 where the overall
standard deviation is inflated to 1.406). It tells you it did that, and tells you
that a σ from a known stable period would be better still.

EWMA limits are **time-varying** by default, because the variance of the EWMA
statistic grows with i. Using the steady-state width everywhere — as the NIST
e-Handbook example does — makes the first limit **40 % too wide**, so a shift
present at the start of the series can slip underneath it. Pass
`time_varying_limits=False` to reproduce published tables.

### Run rules — Nelson and Western Electric

A point outside the limits is the only signal a bare Shewhart chart gives, and
it is rarely the one a real process offers first. Processes drift, trend, and hug
the centre line long before they throw a point past 3σ.

```python
from capstat_core import xbar_r_chart, nelson_rules, western_electric_rules

pair = xbar_r_chart(subgroups)
for v in nelson_rules(pair.location):
    print(v.point, v.rule, v.description)
    # 4  rule 6: four out of five points in a row more than 1 sigma
    #            from the centre line, on the same side
```

Rules are applied **to** a chart, not baked into it — the zones are derived from
the chart's own limits. So `ControlChart.violations` keeps meaning exactly what
it always meant (points beyond the limits, which *is* Nelson rule 1), and nothing
gets reported twice under two names. Each `RuleViolation` carries the point that
completed the pattern *and* the whole window, so a plot can highlight the run and
not just its last point.

**The two standards disagree, and that is useful.** Western Electric rule 4 fires
on **eight** consecutive points on one side; Nelson's rule 2 needs **nine**. A run
of exactly eight fires one and not the other — which is exactly the sequence that
would expose an off-by-one in either implementation, and capstat tests it.

> **Switching on more rules is not free.** On a perfectly stable process the 3σ
> test alone signals about once in 370 points. All four Western Electric rules:
> once in 61. All eight Nelson rules: **once in 44** — roughly *eight times*
> jumpier. Nelson himself advised against running all eight at once. Pass a
> subset (`nelson_rules(chart, [1, 2, 3])`) and pick the rules that match the
> failure you're actually hunting. (These rates are simulated in the test suite,
> not quoted from a textbook.)

**On accuracy.** The variance and every other centered moment use a two-pass
algorithm. This is not pedantry: on the NIST `NumAcc4` dataset the textbook
one-pass formula returns a *negative* variance. capstat reproduces the NIST
certified values to the limit of double precision — see
[the reference suite](packages/capstat-core/tests/references/) for the sources,
the certified numbers, and a written justification for every tolerance.

### Gage R&R — how much of the spread is the gage, not the parts

Before you trust a measurement, find out how much of the variation you are
seeing is the measurement system itself. `gage_rr` runs the crossed ANOVA
method (parts × operators × trials) and partitions the variance into
repeatability, reproducibility, and the real part-to-part spread.

```python
import numpy as np
from capstat_core import gage_rr

# data[part, operator, trial]
report = gage_rr(measurements)
print(report.pct_study_var_gage_rr)   # 33.1  -> unacceptable (> 30%)
print(report.ndc)                     # 4     -> < 5, can't tell parts apart
for w in report.warnings:
    print(w)
```

Two things that quietly bias other tools are handled explicitly. When the
part-by-operator **interaction is not significant** (AIAG's generous
`p > 0.25`), it is dropped and pooled back into repeatability before the
components are re-estimated — keeping a phantom interaction inflates
reproducibility and hides a good gage. And when a variance estimate comes out
**negative** (mean-square differences can, for a component near zero), it is
clamped to zero and reported honestly as "indistinguishable from zero", with a
warning, rather than printed as a negative variance. %Contribution, %Study
Variation, and the number of distinct categories all fall out of the same
components.

## HTTP API

`apps/api` is a stateless FastAPI service that exposes every core statistic
over HTTP and adds CSV/XLSX ingestion. The core stays web-free (numpy + scipy);
pandas/openpyxl live only in the API package.

```bash
uv run uvicorn capstat_api.main:app --reload   # http://127.0.0.1:8000/docs
```

```bash
curl -s http://127.0.0.1:8000/compute/capability \
  -H 'content-type: application/json' \
  -d '{"data": [10.1, 9.9, 10.0, 10.2, 9.8, 10.05], "lsl": 9.5, "usl": 10.5}'
```

Every response mirrors a core dataclass faithfully — the `warnings` arrays and
the nullable capability indices survive serialisation rather than being
flattened away. Endpoints: `/compute/descriptive`, `/compute/capability`,
`/compute/capability/analyze`, `/compute/control-chart/{i-mr,xbar-r,xbar-s,ewma,cusum}`,
`/compute/rules/{nelson,western-electric}`, and `/ingest` for files.

The OpenAPI schema at `apps/api/openapi.json` is the single source of truth for
the generated TypeScript client (added with the web app) and is checked for
drift in CI:

```bash
uv run python -m capstat_api.export_openapi           # regenerate
uv run python -m capstat_api.export_openapi --check    # fail on drift
```

## Web app

`apps/web` is a Next.js (App Router) front end that talks to the API through a
typed client generated from the same OpenAPI schema. Upload a CSV/XLSX, pick a
numeric column, and get a capability report (with the normal / Box-Cox /
percentile decision path and a spec-limit histogram) plus I-MR control charts
with Nelson run-rule flags.

Run it against a local API:

```bash
uv run uvicorn capstat_api.main:app          # terminal 1: the API on :8000
cd apps/web && npm install && npm run dev     # terminal 2: the app on :3000
```

Then open <http://localhost:3000>. The client's API base URL defaults to
`http://127.0.0.1:8000`; override it at build time with `NEXT_PUBLIC_API_URL`.

```bash
npm run test        # vitest unit tests (pure binning / stats)
npm run test:e2e    # Playwright smoke test (API mocked, no backend needed)
npm run build       # production build + type-check
```

## Configuration

capstat-core is configuration-free. The API is stateless and needs no
configuration to run. One optional knob exists for the browser client:

- **`CAPSTAT_CORS_ORIGINS`** — comma-separated list of allowed browser origins
  (default `http://localhost:3000,http://127.0.0.1:3000`, the Next.js dev
  server). Set it to your web app's origin when deploying elsewhere.

The client's API base URL is set at build time via `NEXT_PUBLIC_API_URL`
(default `http://127.0.0.1:8000`).

## Troubleshooting

- **`uv: command not found`** — install uv per the
  [official instructions](https://docs.astral.sh/uv/getting-started/installation/).
- **Wrong Python version** — uv manages an isolated interpreter; you do not
  need a system Python 3.11+. Run everything through `uv run`.

## Development

```bash
uv sync                       # install dev toolchain
uv run pre-commit install     # enable pre-commit hooks
uv run ruff check .           # lint
uv run ruff format .          # format
uv run mypy                   # type-check (strict)
uv run pytest --cov=capstat_core --cov=capstat_api   # tests with coverage
```

Quality gates (enforced in CI): ruff (lint + format), mypy `--strict`, an
OpenAPI drift check, and pytest with ≥ 95 % coverage (currently 100 % on both
capstat-core and capstat-api). See [AGENTS.md](AGENTS.md) for
the full contributor workflow and [CONTRIBUTING.md](CONTRIBUTING.md) to get
started.

## Architecture

capstat is a uv-managed monorepo:

```
packages/capstat-core/   # pure numpy+scipy stats library, PyPI-publishable
apps/api/                # FastAPI compute service (wraps the core)
apps/web/                # Next.js dashboard                          [later]
docs/                    # mkdocs-material site                       [later]
```

The core carries no web dependencies and can be used on its own. The API
exposes it over HTTP; its OpenAPI schema is the single source of truth for the
generated TypeScript client. Details and the rationale for every toolchain
choice are in [PLAN.md](PLAN.md).

## License

[MIT](LICENSE) © André Leopold
