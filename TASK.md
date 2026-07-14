# TASK.md — capstat

## Doing

<!-- max 3 -->

## Next

- T-0008 M2b EWMA + CUSUM, validated against Montgomery / NIST Handbook
  examples.
- T-0009 M2c Nelson rules + Western Electric rules, tested with constructed
  sequences + published example data.
- T-0010 M3 FastAPI service: compute endpoints (descriptive, capability,
  control charts), CSV/XLSX ingestion, OpenAPI schema, TS client generation
  with a drift check in CI.

## Backlog

- T-0011 M4 Next.js app: upload (CSV/XLSX), capability dashboard, histogram
  with spec limits + fitted distribution, control charts with violation
  markers (ECharts).
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
- T-0019 Decide demo hosting (due Week 3, before T-0015): recommendation
  Vercel Hobby (web, free) + Render Free (API container, sleeps when idle);
  alternative Fly.io (a few EUR/month). Needs one account each (GitHub login
  is enough).

## Done

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
