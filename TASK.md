# TASK.md — capstat

## Doing

<!-- max 3 -->

- T-0011 M4 Next.js app: upload (CSV/XLSX), capability dashboard, histogram
  with spec limits + fitted distribution, control charts with violation
  markers (ECharts). Sub-increments:
  1. **[done 2026-07-15]** TS client: `apps/web` with `openapi-typescript`
     generating `lib/api-client/schema.d.ts` from `apps/api/openapi.json`,
     committed + drift-checked in CI (`npm run check:api`). Closes the Node
     half of the M3 contract deferred from T-0010.
  2. **[done 2026-07-15]** Next.js scaffold: Next 16 App Router + React 19 +
     Tailwind v4 + ESLint 9 (flat), typed `api` client wired via
     `openapi-fetch`. `npm run build` green (lint + typecheck + static /).
     Web CI job added (npm ci -> drift -> lint -> build).
  3. **[done 2026-07-15]** Upload flow: `UploadPanel` client component
     (drag-drop + browse) POSTs to `/ingest` via a typed `ingestFile` helper
     (the one place that reconciles the binary-body / FormData mismatch),
     surfaces ignored columns + dropped cells as ingestion notes, offers a
     numeric-column picker with an n/min/max/mean preview. `CORSMiddleware`
     added to the API (origins from `CAPSTAT_CORS_ORIGINS`, default
     localhost/127.0.0.1:3000) -- browser-only, so the OpenAPI contract and its
     drift check are untouched; 4 CORS tests added. Verified end-to-end in the
     browser (real cross-origin upload, 200 OK, warnings + stats correct).
     Also fixed: the `apps/*` uv-workspace glob claimed the new Node `apps/web`
     as a Python member and broke `uv run`; excluded it in the root pyproject.
  4. **[next]** Capability dashboard: `/compute/capability` + `/analyze`;
     histogram with spec limits + fitted distribution (ECharts).
  5. Control charts: I-MR/Xbar via ECharts `markLine`/`markArea` for limits +
     zones; violation markers; run-rule overlay.
  6. eslint/prettier/vitest + a Playwright smoke test; polish.

## Backlog
- T-0012 M5a Gage R&R: ANOVA method + average-and-range method;
  %Contribution, %Study Variation, ndc. Validated against the AIAG MSA-4
  worked examples (core credibility).
- T-0013 M5b Bias, linearity, stability.
- T-0014 M6a PDF report: print-optimized report route with vector charts
  (ECharts SVG renderer); server PDF as roadmap.
- T-0015 M6b docker-compose (api + web) + public demo deployment
  (Vercel + Fly.io/Render).
- T-0016 M6c Docs site: mkdocs-material + mkdocstrings; Getting Started,
  method reference (formula + citation per method), API reference.
- T-0017 M6d v0.1.0 release via release-please, README polish (badges,
  screenshots, quickstart, demo link).
- T-0018 Roadmap (explicitly NOT v0.1): acceptance sampling (AQL/ISO 2859),
  multi-user auth, persistence/database, server PDF.
- T-0021 scipy deprecation: `scipy.stats.anderson` drops its `critical_values`
  / `significance_level` / `fit_result` attributes in scipy 1.19 (FutureWarning
  since 1.17). capstat's *library* code is unaffected -- it implements the
  Anderson-Darling statistic itself -- but two cross-check tests in
  `test_normality.py` use those attributes and currently suppress the warning
  via `pytestmark`. Before scipy 1.19, pin Stephens' critical values in the
  reference YAML instead of reading them from scipy.
- T-0020 CI: `actions/checkout@v4` and `astral-sh/setup-uv@v6` still target the
  deprecated Node.js 20 runtime (GitHub forces them onto Node 24 and warns on
  every run). Bump to the Node-24 native majors when released; dependabot
  (github-actions, weekly) will likely raise this PR on its own. Cosmetic
  today, breaking once GitHub drops the shim.
- T-0022 starlette TestClient deprecation: FastAPI's `TestClient` rides on
  `httpx`, and starlette 1.3 warns "install `httpx2` instead"; it also renamed
  the `HTTP_4xx_*` status constants (ENTITY -> CONTENT). capstat's API code
  sidesteps the constant churn by using int literals (422/413/415), but the
  TestClient warning surfaces once per test session. Cosmetic today; revisit
  when starlette settles the httpx2 transition. Same class as T-0020/T-0021
  (a dependency's deprecation, not our bug).
- T-0019 Decide demo hosting (due Week 3, before T-0015): recommendation
  Vercel Hobby (web, free) + Render Free (API container, sleeps when idle);
  alternative Fly.io (a few EUR/month). Needs one account each (GitHub login
  is enough).

## Done

- T-0010 (2026-07-15) M3 FastAPI service. New workspace member `apps/api`
  (`capstat_api`): stateless compute endpoints over every core entry point,
  `/ingest` for CSV/XLSX, `/health`, `/rules/catalogue`. OpenAPI schema
  committed at `apps/api/openapi.json` with a drift check in CI + pre-commit.
  412 tests, 100 % coverage on both packages, mypy strict clean.
  * **The core stays web-free.** fastapi/pandas/openpyxl live only in
    `apps/api`; `capstat-core` is still numpy+scipy (PLAN.md non-negotiable).
    Enforced by construction -- the api package depends on the core, never the
    reverse.
  * **Faithful serialisation was the whole job.** Response models are Pydantic
    mirrors built with `model_validate(core_obj)` under `from_attributes=True`,
    so the core's `warnings` tuples survive as JSON arrays AND the derived
    `@property` values (`in_control`, `stability_ratio`) are read by attribute
    -- `dataclasses.asdict` would have silently dropped them. Every compute
    test asserts equality with the core's own output, not just a 200.
  * **`None` is preserved, never coerced to 0.** A one-sided spec leaves
    `cp`/`cpl` undefined; the schema carries `null`. Pinned by a test.
  * **Non-finite floats become `null`.** A zero-variance sample yields `nan`
    skewness; JSON has no `NaN`, so a `SafeFloat` validator maps non-finite to
    `null` on the (few) fields that can be non-finite. Pinned by a test.
  * **The 8-vs-9 rule discriminant carries through HTTP.** The rules endpoints
    rebuild a minimal `ControlChart` (points + limits); a run of exactly eight
    fires Western Electric rule 4 and not Nelson rule 2 -- the same off-by-one
    guard as T-0009, now at the API boundary.
  * **Ingestion says what it dropped.** Non-numeric columns are named as
    ignored; missing cells are dropped per column and counted. A silent drop
    would misstate the sample size.
  * `capability` accepts 1D (individuals) or 2D (subgroups) so within-subgroup
    Cp is reachable over HTTP, not just Ppk.
  * **TS client split out by decision (2026-07-15):** M3 ships the committed
    `openapi.json` + a Python drift check; the `openapi-typescript` generation
    moves to T-0011 where the Node toolchain arrives anyway. Recorded so the
    acceptance criterion is not silently dropped.
  * **My own test was wrong, not the code (again).** A dropped-missing test
    used a wholly blank CSV line; pandas skips blank lines by default, so no
    missing value ever existed. The gap had to sit beside a populated column.
- T-0009 (2026-07-14) M2c Nelson + Western Electric run rules.
  `capstat_core.rules`: `nelson_rules`, `western_electric_rules` ->
  `tuple[RuleViolation, ...]`; `NELSON_RULES` / `WESTERN_ELECTRIC_RULES`
  catalogues. 382 tests, 100 % coverage. **Week 2's chart work is complete.**
  * **No breaking change after all.** STATE.md had flagged this task as needing
    `ControlChart.violations` to grow into a rule-aware type. The better design
    avoids it: rules are a *lens applied to* a chart, deriving their sigma zones
    from the chart's own limits. So `violations` keeps meaning "beyond the
    limits" (which IS Nelson rule 1), nothing is double-reported, and the
    published dataclass is untouched.
  * **The discriminating test:** Western Electric rule 4 needs EIGHT consecutive
    points on one side, Nelson rule 2 needs NINE. The standards genuinely
    disagree, and a run of exactly eight must fire one and not the other. Every
    rule is a count, so an off-by-one would produce a chart that looks entirely
    plausible and is permanently wrong -- this asymmetry is what catches it.
    Each rule is additionally tested twice: with its pattern, and one point short.
  * A web-search summary consulted while writing this stated Nelson rule 2 as
    "nine consecutive points on the same side WITHIN one standard error" -- it had
    fused rule 2 with rule 7. Definitions were taken from the rule tables instead.
  * **My own docstring claim was wrong and the simulation caught it.** I wrote
    that all eight Nelson rules make a chart "roughly four times as jumpy, about
    1 in 90". Measured: 1 in 44 -- **eight times** as jumpy as the limit test
    alone (1 in 351; theory 1 in 370). Western Electric: 1 in 61. Corrected in
    the docstring, README and reference YAML, and pinned by a test.
  * Zone rules need a symmetric chart. An R/s/moving-range chart's limits are
    D3*Rbar and D4*Rbar -- not equidistant from Rbar -- so the functions refuse
    it with an explanation rather than computing arithmetic without meaning.
  * A rule fires on the point that *completes* its pattern, and the k-of-m rules
    require that final point to qualify. Without that, a window like
    [3.1, 2.5, 0.2] would flag the harmless last point long after the pattern
    passed.
- T-0008 (2026-07-14) M2b EWMA + CUSUM. `capstat_core.time_weighted`:
  `ewma_chart` -> `EwmaChart`, `cusum_chart` -> `CusumChart`.
  355 tests, 100 % coverage. Both NIST worked examples reproduced.
  * **Real published reference values at last** (NIST 6.3.2.3 CUSUM, 6.3.2.4
    EWMA), so this milestone rests on quoted numbers, not only identities.
  * EWMA reproduces NIST to 4.8e-3 (inside their 2-decimal printing); limits to
    1e-4. CUSUM only to 2.8e-2 -- and that is *explained, not tolerated*: NIST
    prints its inputs to 2 decimals and a CUSUM is a CUMULATIVE sum, so input
    rounding accumulates rather than averaging out. A systematic +0.005 on every
    input moves the final S_hi by 0.040, so our 0.0275 sits comfortably inside
    what their rounding can produce. A dedicated test proves the tolerance is
    explained by rounding and has no room to hide a defect.
  * **The values carry a tolerance; the DECISION carries none.** NIST's first
    signal is group 14, and ours must be group 14 exactly -- asserted separately
    with no tolerance at all.
  * **Design: sigma defaults to the moving range, not the overall sd.** A
    sustained shift inflates the overall sd, which widens the limits, which hides
    the shift -- the chart then reports all is well. Measured over 200 runs with
    a 2-sigma shift: moving-range sigma = 1.002 (true 1.0) while the overall sd
    is inflated to 1.406.
  * **EWMA limits are time-varying by default.** NIST (and many textbooks) apply
    the steady-state width to every point, which makes the first limit 40 % too
    wide -- a shift present at the start can slip under it. `time_varying_limits
    =False` reproduces the published example.
  * Claims verified rather than quoted: Shewhart ARL1 = 43.9 for a 1-sigma shift
    (analytic), CUSUM ARL1 = 10.5 and ARL0 = 457 (simulated). lambda=1 reduces
    EWMA exactly to a Shewhart individuals chart -- the sanity check on the
    recursion.
  * Three of my own tests were wrong, not the library: (a) I asserted a stable
    EWMA series is always in control -- but with ARL0 ~500, **34.7 %** of
    200-point series contain a false alarm, so the *rate* is what must be tested;
    (b) I bounded the CUSUM detection delay at 15 when its p95 is 16; (c) I used
    random symmetric jitter to justify the CUSUM tolerance, but random errors
    partially cancel in a cumulative sum -- the systematic worst case is the
    correct (and looser) argument.
- T-0007 (2026-07-14) M2a Control-chart constants + Shewhart charts.
  `capstat_core.constants` extended with d3, A2, A3, B3, B4, D3, D4, E2 (all
  computed from definitions, none transcribed). `capstat_core.control_charts`:
  `xbar_r_chart`, `xbar_s_chart`, `i_mr_chart` -> `ChartPair`.
  317 tests, 100 % coverage.
  * d3 (sd of the range) needs the joint density of the sample minimum and
    maximum: f(x,y) = n(n-1) phi(x) phi(y) [Phi(y)-Phi(x)]^(n-2), integrated as
    a double integral for E[W^2], then d3 = sqrt(E[W^2] - d2^2). Internal check:
    the SAME joint density integrated against (y-x) reproduces d2, which comes
    from a completely different single integral.
  * **The published tables are wrong about E2.** They print 2.660; the exact
    value is 2.6587. They evaluated 3/d2 with d2 already rounded to 1.128 and
    propagated the error. Computing from the definition avoids importing it.
    Pinned by a test that asserts the gap exceeds the table's own rounding.
  * The published tables also disagree with each other: NIST prints D4(3)=2.575,
    the ASTM-derived table 2.574. We compute 2.5746, which rounds to NIST's.
    Tolerance is 1e-3 absolute -- set by the sources' precision, not ours (~1e-8).
  * Naming hazard kept deliberately: d3 (sd of the range) vs D3 (R chart lower
    limit factor) differ only in case. Every textbook does this; renaming would
    make the code harder to check against its sources. Flagged loudly instead.
  * **Design: the dispersion chart is judged first.** The X-bar limits are
    computed FROM Rbar/sbar, so an out-of-control dispersion chart makes them
    meaningless. `ChartPair.in_control` is the AND of both charts, and the pair
    warns explicitly when dispersion is the one signalling. A location chart can
    read "all in control" on a process that plainly is not.
  * D3/B3 are zero for small n because the unclamped value is negative -- so the
    chart cannot detect an *improvement* in spread. Warned about, not hidden.
  * Isomorphy check on the E2 error class ("a rounded published value used as an
    input to a computation"): the only hardcoded float in the whole library is
    MAD_NORMAL_CONSISTENCY, and it is validated against scipy at full precision.
    Every chart factor derives from the exact d2/d3/c4. No propagation anywhere.
- T-0006 (2026-07-14) M1d Non-normal path. `capstat_core.nonnormal`:
  `box_cox_capability`, `percentile_capability` (ISO 22514), `fit_distribution`,
  and `analyze_capability` -> `CapabilityAnalysis`, which runs the documented
  decision path (normal -> Box-Cox -> percentile) and records *why*.
  277 tests, 100 % coverage. Week 1 (Tier-1 statistics) is complete.
  * The limits are transformed with the same lambda as the data. A test pins the
    magnitude of the bug being prevented (forgetting them shifts Ppk by > 1.0),
    not merely its absence.
  * Box-Cox is strictly increasing for **every** lambda (derivative
    x**(lambda-1) > 0 for x > 0), so LSL stays the lower limit. Verified for
    lambda in {-2, -0.5, 0, 0.5, 1, 3} -- the negative cases are the ones where
    intuition says it should flip.
  * capstat refuses to shift non-positive data to make Box-Cox applicable: the
    offset changes the indices and must be the user's recorded decision.
  * **A reference claim of mine was wrong and the tests caught it.** I asserted
    that Box-Cox and the percentile method must agree on lognormal data. They
    must not: Box-Cox is linear on the log scale, ISO is nonlinear on the
    original scale ((e^U - 1)/(e^3s - 1)). They coincide ONLY at the just-capable
    point (U = 3s, both = 1) and diverge sharply elsewhere -- measured Ppu 1.61
    vs 2.44 on identical data. The YAML, the module docstring and the README now
    say so; the tests pin both the agreement and the divergence.
  * The fitted-normal percentile index differs from the classic one by exactly
    sqrt(n/(n-1)) * (6/5.999954): the MLE sigma (denominator n) times ISO's
    rounded percentile span. Predicted exactly and pinned at rel=1e-12, because
    it is exact algebra -- a loose tolerance there would be an admission we did
    not understand the gap, and could hide a real bug.
  * `DistributionFit.fit_score` is an AD statistic via the probability integral
    transform. It carries NO p-value: the parameters were estimated from the same
    data, so any p-value would be anticonservative by an unknown amount. It ranks
    candidates; it does not certify one.
  * Isomorphy: the `float ** float -> Any` typeshed wrinkle (first hit in T-0003
    at `m2**1.5`) recurred here at `x**lmbda`. Fixed the same way (`math.pow`).
- T-0005 (2026-07-14) M1c Capability indices. `capstat_core.capability`
  (`capability` -> `CapabilityReport` with Cp/Cpl/Cpu/Cpk/Cpm and
  Pp/Ppl/Ppu/Ppk) and `capstat_core.constants` (`d2`, `c4`). 234 tests,
  100 % coverage.
  * **Plan delta:** d2/c4 were pulled forward from T-0007. Cp/Cpk require a
    within-subgroup sigma (Rbar/d2 or sbar/c4); without them there is no
    short-term sigma, only a number mislabelled Cpk. T-0007's scope shrinks
    accordingly (see Next).
  * Constants are **computed from their definitions**, not transcribed:
    d2 = E[range of n standard normals] by quadrature, c4 = the closed-form
    gamma ratio via lgamma. A copied table can hide a typo that the test never
    catches, because the test was written by copying the same table. Validated
    three ways: the published d2 table; NIST's A2 table via A2 = 3/(d2*sqrt(n))
    (a source that never states d2); and Monte-Carlo E[range].
  * The within/overall split is enforced, not documented-and-ignored. On a
    drifting process the tests confirm Cpk > Ppk, and the report warns when
    sigma_overall/sigma_within > 1.25.
  * `cpm` is `None` without an explicit target -- no silent midpoint assumption,
    which is wrong for an asymmetric tolerance.
  * The NIST worked example estimates sigma with the sample s, so it maps onto
    capstat's **Pp/Ppk**, not Cp/Cpk. That mapping is pinned by a test.
  * Bug found: `@cache` on a public function erases its type signature (mypy
    sees `_lru_cache_wrapper.__call__(*args: Hashable)`), so `d2(5.0)` type-
    checked clean -- for us and for any user. Fixed by wrapping a private
    cached impl behind a typed public function; a load-bearing `type: ignore`
    in the tests now guards the regression. Isomorphy check: these were the only
    two cache decorators in the package.
  * Measured, not assumed: the `assess_normality` fail-closed AND-rule rejects
    7.6 % of genuinely normal samples (vs 5.8 % / 4.8 % for the individual tests
    at alpha=0.05). Documented in the docstring and pinned by a calibration test.
- T-0004 (2026-07-14) M1b Normality tests. `capstat_core.normality`:
  `anderson_darling` (own implementation, with the p-value scipy does not
  provide), `shapiro_wilk` (delegates to scipy's AS R94), and
  `assess_normality` -> `NormalityAssessment` with an explicit verdict,
  recommendation, and warnings. 193 tests, 100 % coverage.
  Validation rests on four independent legs, because the AD p-value is the one
  piece capstat owns outright and a mis-transcribed coefficient there would be
  invisible:
  * AD statistic cross-checked against `scipy.stats.anderson` on 8 NIST
    datasets (rel 1e-10; Mavro's tiny sd of 4.3e-04 amplifies rounding to
    ~2e-12, hence not machine epsilon).
  * AD p-value formula transcribed verbatim from CRAN `nortest` 1.0-4
    (D'Agostino & Stephens 1986), NOT from memory.
  * Round-trip: feeding Stephens' *independently published* critical values
    into that formula returns the nominal alphas to within 2 %. Two sources
    that never touched each other agree.
  * Shapiro-Wilk validated against a published R `shapiro.test` result
    (W = 0.7888, p = 0.006704) -- testing scipy against scipy would be circular.
  Design decisions worth keeping:
  * `assess_normality` fails closed: `normal` is the AND of both tests, and a
    disagreement is surfaced as a warning rather than silently resolved.
  * It warns on material autocorrelation (|r1| > 0.2). Both tests assume
    independence; NIST Mavro has r1 = 0.94, so its p-values are meaningless.
    A tool reporting only the p-value there would be actively misleading.
  * It warns on low power (n < 20) and on large n, where a practically
    irrelevant deviation becomes "significant".
  * AD requires n >= 8 (the p-value approximation is undefined below), matching
    R's `nortest::ad.test` guard.
  * The branches of the p-value approximation are genuinely discontinuous (up
    to 3.3e-03 at A*^2 = 0.34); that is the published fit, not our error, and
    is pinned by a test at 5e-3.
- T-0003 (2026-07-14) M1a Descriptive statistics + robust variants.
  `capstat_core.descriptive` (mean, variance, std_dev, skewness, kurtosis,
  lag1_autocorrelation, `describe` -> immutable `DescriptiveSummary`) and
  `capstat_core.robust` (median, mad, iqr, trimmed_mean, winsorized_mean).
  Validated against all 9 NIST StRD Univariate datasets (archived verbatim
  in-tree with their certified-value headers); robust estimators validated by
  hand-computed values + scipy cross-check. 152 tests, 100 % coverage.
  Findings worth keeping:
  * The one-pass variance returns a *negative* variance (-0.032) on NumAcc4.
    All centered moments therefore use a two-pass algorithm, pinned by a
    regression test plus a shift-stability test across the whole family.
  * The residual 5.6e-09 error on NumAcc4 is a float64 *input representation*
    floor, not an algorithmic one (proven in exact rational arithmetic); the
    loosened tolerance there is justified in the reference YAML.
  * Bug found and fixed in the T-0002 config: `mypy python_version = "3.11"`
    breaks against numpy >= 2.5 stubs (PEP 695) and was masking two real
    strict-mode errors. mypy now infers the version from the interpreter.
- T-0002 (2026-07-14) M0 Repo bootstrap: git init; MIT LICENSE (© André
  Leopold); root README with CI/license/python badges; CONTRIBUTING,
  CODE_OF_CONDUCT, SECURITY; `.github/` (CI workflow, dependabot, issue/PR
  templates); uv workspace with `capstat-core` (numpy+scipy, hatchling,
  py.typed); shared ruff/mypy(strict)/pytest/coverage config; pre-commit
  (local hooks via `uv run`); TASK/STATE converted to English. Green locally:
  ruff, ruff-format, mypy strict, pytest 1/1, coverage 100 %.
- T-0001 (2026-07-13) Kickoff plan confirmed: name capstat ("Capsat" typo
  resolved explicitly), LICENSE name André Leopold, language English, GitHub
  account Xindaan; hosting split out into T-0019.
