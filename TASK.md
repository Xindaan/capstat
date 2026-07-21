# TASK.md — capstat

## Doing

<!-- max 3 -->

- (Doing is clear -- M5 is complete end-to-end: Gage R&R and the three MSA
  studies all reach the UI. Next in Backlog: the M6 release path.)

## Backlog
- T-0029 Docs stack risk: mkdocs-material warns that MkDocs 2.0 removes the
  plugin system entirely, with "no migration path" and the theming rewritten --
  which would break mkdocstrings and the Material theme together. We pin
  mkdocs 1.x, so nothing is broken today. Revisit before it becomes urgent:
  either stay pinned deliberately, or evaluate an alternative generator. Do not
  bump mkdocs to 2.x casually.
- T-0024 Web run-rule selection UI: let the user pick which Nelson rules the
  control-chart panel applies (it currently hard-codes rules 1-4). Small
  feature; low priority. Optional companion: add prettier if formatting ever
  drifts (skipped in sub-increment 6 -- eslint + consistent style cover it now).
- ~~T-0015b Public demo deployment~~ -- dropped. T-0026 decided against public
  hosting (local only). The Docker artifacts stay for self-hosting; there is
  just nothing to deploy.
- T-0030 Decide whether capstat-core goes to PyPI. Needs a PyPI account and a
  trusted-publisher (OIDC) config, neither creatable from inside the repo. Until
  then releases are GitHub-only and the docs say so rather than implying a
  `pip install` that would fail. Once decided, add a publish job keyed on the
  release tag.
- T-0031 README screenshots. Deferred from T-0017: the app is worth showing, but
  it means committing binaries and re-shooting them whenever the UI moves. Since
  there is no hosted demo to link (T-0026: local only), a screenshot or two is
  the *only* way a reader sees the UI without running it -- so this matters more
  than it would with a live link. Worth doing once the UI settles.
- T-0018 Roadmap (explicitly NOT v0.1): acceptance sampling (AQL/ISO 2859),
  multi-user auth, persistence/database, server PDF.
- T-0021 scipy deprecation: `scipy.stats.anderson` drops its `critical_values`
  / `significance_level` / `fit_result` attributes in scipy 1.19 (FutureWarning
  since 1.17). capstat's *library* code is unaffected -- it implements the
  Anderson-Darling statistic itself -- but two cross-check tests in
  `test_normality.py` use those attributes and currently suppress the warning
  via `pytestmark`. Before scipy 1.19, pin Stephens' critical values in the
  reference YAML instead of reading them from scipy.
- T-0022 starlette TestClient deprecation: FastAPI's `TestClient` rides on
  `httpx`, and starlette 1.3 warns "install `httpx2` instead"; it also renamed
  the `HTTP_4xx_*` status constants (ENTITY -> CONTENT). capstat's API code
  sidesteps the constant churn by using int literals (422/413/415), but the
  TestClient warning surfaces once per test session. Cosmetic today; revisit
  when starlette settles the httpx2 transition. Same class as T-0020/T-0021
  (a dependency's deprecation, not our bug).
- T-0026 [DECIDED 2026-07-20: no public hosting; local only.] The maintainer
  would sooner run capstat locally than send measurement data to a third party,
  which is the right instinct for a tool people feed real production data into.
  So there is no public demo and no hosted API. `docker compose up` is the
  supported way to run it, and it needs no account, no cloud, and no data ever
  leaving the machine. Left in the docs for anyone who *does* want to host it:
  the measurement (~152 MB deps, ~1 s cold import) and why that points at a
  container host over serverless. But we are not doing it.
  A quieter consequence, worth stating: the web app is fully static (all three
  routes prerender), so if a public demo is ever wanted it needs only a static
  host (GitHub Pages, free) for the app plus a compute host for the API -- the
  `output: "standalone"` Docker setup is for self-hosting, not that.
- T-0023 web `npm audit`: 2 moderate advisories in `postcss` (<8.5.10, XSS in
  the CSS stringify output), pulled in transitively via Next's build tooling --
  not from `echarts`, and a build-time path with no runtime exposure for us.
  `npm audit fix --force` would downgrade `next` to 9.3.3 (a destructive
  breaking change), so leave it. Clears itself when Next ships a patch that
  bumps its postcss floor; dependabot (npm ecosystem is not yet configured --
  only github-actions is) or a routine `next` bump will resolve it.

## Done

- T-0017b (2026-07-21) **v0.1.0 released.** PR #3 squash-merged; release-please
  cut tag `v0.1.0` and the GitHub release. Versions verified at 0.1.0 across all
  six files beforehand; post-merge CI green on all six jobs, including the drift
  check T-0034 had just fixed — the precise failure it was written for.
  Two things learned about release PRs, both worth repeating next time:
  1. Workflows on a GITHUB_TOKEN-created PR are queued as `action_required`,
     awaiting manual approval. `gh pr checks` reports *nothing* while a run is
     held, which is indistinguishable from a repo with no CI. Approve with
     `gh api -X POST repos/Xindaan/capstat/actions/runs/<id>/approve`.
  2. release-please rebuilds the PR whenever `main` moves, so a green run can
     belong to a superseded head. Compare the run's sha against
     `gh pr view <n> --json headRefOid` before trusting it. This happened here:
     the first green tick was for `3fbaa54d`, the head was already `22c2f444`.

- T-0034 (2026-07-21) The OpenAPI drift check no longer fails on formatting it
  does not own. release-please stamps `$.info.version` into `openapi.json` and
  rewrites the file with JavaScript's JSON writer, which cannot tell `5.0` from
  `5` -- so the 0.1.0 release commit differed from a fresh render in exactly
  three whitespace-equivalent numbers and would have turned `main` red on an
  artefact nobody had touched. `--check` now compares the *parsed* documents,
  which is what it was always meant to assert: that the committed contract
  describes the same API as the code. Byte differences are reported, not failed.
  Proven by checking out the release branch into a worktree, running the check
  (exit 1), patching the exporter in, and running it again (exit 0) -- the first
  measurement was confounded by the version field and had to be redone properly.
  Then confirmed on the real thing: the release PR's own CI, once approved, went
  green on all six jobs.
  Guard kept sharp by a test that mutates a value rather than its formatting.
  Isomorphie-Check: `apps/web/package.json` goes through the same JSON updater
  but is under no byte-comparison, so `openapi.json` was the only instance.

- T-0032 (2026-07-21) "Allow GitHub Actions to create and approve pull requests"
  enabled by the maintainer; re-running the workflow opened PR #3 immediately.
  It was a permission decision, not a config bug -- the switch lets *any*
  workflow in the repo open PRs, which is why it was not mine to make.

- T-0033 (2026-07-21) The upload panel no longer auto-selects a row index. It
  landed on `part` = 1..60 in the demo CSV and computed Pp 0.006 -- capability of
  the *part numbers* against a diameter spec. Nothing objected, because
  consecutive integers are perfectly good numeric data; that is precisely the
  failure mode this project exists to prevent.
  * `looksLikeRowIndex()` in `lib/stats.ts`: consecutive integers stepping by one
    from 0 or 1, at least three of them. Deliberately strict -- the two mistakes
    are not symmetric. Missing an index is the status quo; wrongly flagging a
    real measurement would teach people to ignore the warning.
  * Auto-select takes the first column that does *not* look like an index, and
    falls back to the first column when every one of them does.
  * Selecting it manually is still allowed -- but the summary then says so in
    amber, naming the arithmetic ("these values run 1, 2, 3 ...").
  * Isomorphy check: `columns[0]`/`columns.find` appears only in
    `upload-panel.tsx`; `/gage-rr` and `/msa` take typed grids, not column
    picking, so there is no second site to fix.
  * 6 unit tests (31 vitest total) + an e2e test covering both halves: the index
    is not preselected, and picking it raises the warning.

- T-0028 (2026-07-20) An index with no value now says *why*, instead of showing
  a bare dash. Prompted by the maintainer asking "did I enter LSL/USL wrong?"
  within a minute of loading the demo CSV -- he had not; on the percentile path
  Cp and Cpk simply do not exist. Two absences that looked identical are now
  distinguished in the card itself:
  * **"not defined on the percentile path"** -- the percentile method reads
    percentiles off the overall fitted distribution and has no within/between
    split, so Cp/Cpk are not merely unknown, they are undefined.
  * **"needs both spec limits"** -- Cp and Pp need two limits; Cpk and Ppk are
    defined by one. A one-sided spec empties different cards for a different
    reason, and now says so.
  The amber warning below already explained the first case, but three blocks
  below the cards is too far away to answer the question the cards raise.
  Verified in-browser on the real demo CSV (both cases), and pinned by an e2e
  test so the explanations cannot decay back into dashes.
- T-0017a (2026-07-20) M6d release automation. release-please configured for the
  repo, plus the README/docs honesty pass that came with it.
  * **One version for the whole repo.** Core, API and web are built and released
    together; independent version numbers would imply a freedom that does not
    exist. The manifest holds it; `extra-files` writes it into both pyprojects,
    both `__version__` constants, `apps/web/package.json`, and
    `apps/api/openapi.json`.
  * That last one is the non-obvious part: the API's version is *part of its
    published schema*, and the schema is drift-checked against the code. A
    release that bumped the version without rewriting `openapi.json` would fail
    the next CI run. Verified the jsonpath (`$.info.version`) resolves by
    reading the file rather than assuming the usual OpenAPI key order -- the
    exporter sorts keys, so `info` sits near the end.
  * CONTRIBUTING now spells out that the commit type decides the version bump,
    not just the changelog section: a commit typed wrongly releases wrongly.
  * **Found while writing the release docs**: `docs/getting-started.md` told
    readers to `pip install capstat-core`. That package is on no index -- the
    instruction would simply fail. Corrected to install from the checkout, with
    the PyPI question filed as T-0030. The README's status block was also stale
    ("the API and web app follow" -- they were finished days ago).
  * Deliberately *not* done: merging the release PR (T-0017b -- a public
    release is your call) and README screenshots (T-0031).
  * **The first run: I misdiagnosed it, then checked and corrected myself
    (2026-07-20).** I claimed the config left both versions at 0.0.0 and rewrote
    the extra-files updaters to "fix" it. Then I inspected the release branch
    release-please had actually pushed -- and every version *was* bumped
    correctly (both pyprojects, package.json, openapi.json, to 1.0.0, via the
    `x-release-please-version` annotations). The config was never broken. I
    reverted the false-premise change and kept the proven config. Lesson logged:
    the release branch is the ground truth; a "No entries modified" line in the
    log was noise from a redundant updater pass, not a failure. The *real* first-
    run finding is one thing, not two: (b) Actions may not open pull requests by
    default, so the run built the branch and then failed at the PR step. Filed
    as T-0032 -- that switch lets every workflow in the repo open PRs, which is
    the maintainer's call, not mine.
  * Separately real: the default first release is **1.0.0**, but the stated goal
    is **0.1.0**. Pinned with a `Release-As: 0.1.0` footer, verified against the
    rebuilt release branch.
- T-0015a (2026-07-16) M6b deployment artifacts: Dockerfiles for both apps,
  docker-compose, Vercel config, and a deployment page in the docs.
  * **API image**: multi-stage, uv-based, dependencies in their own layer so
    editing a statistic does not re-resolve scipy. Runs as a non-root user --
    it parses untrusted uploads through pandas/openpyxl. Honours `$PORT`, which
    is what container hosts inject. Built from the repo root, because
    capstat-api depends on capstat-core as a workspace member.
  * **Web image**: Next `output: "standalone"`, so the image ships only the
    node_modules the build actually reached. Vercel ignores this and builds its
    own way, so setting it costs nothing there.
  * The health check lives in `apps/api/healthcheck.py` rather than an inline
    `python -c`: the nested quoting that needs is exactly the sort of thing that
    breaks silently and then reports "unhealthy" for the wrong reason.
  * **Could not verify locally -- the Docker daemon was not running.** Rather
    than claim the images build, CI gained an `images` job that builds both on
    every commit (build only, nothing pushed), so a deployment artifact cannot
    rot unnoticed until deploy day. What *was* verifiable locally: the uv flags
    exist, and `next build` really emits `.next/standalone/server.js`, which the
    web Dockerfile depends on.
  * Measurement for T-0026 recorded in docs/deployment.md: ~152 MB of runtime
    dependencies and ~1 s of cold import, hence the recommendation to put the
    API on a container host rather than serverless.
- T-0016 (2026-07-16) M6c docs site: mkdocs-material + mkdocstrings, in a
  separate `docs` dependency group so test CI does not drag mkdocs in.
  * Pages: Home (what makes it different), Getting started (install, first
    study, run the API/app), Methods (capability, control charts, measurement
    systems -- the *reasoning* per method, with formulas and citations),
    Validation (the five rules and the errors they caught), API reference
    (mkdocstrings from the docstrings).
  * **`docs/validation-sources.md` is generated** from the reference YAMLs by
    `scripts/gen_sources_page.py`, with a `--check` drift mode in CI -- the same
    rule the library applies to constants: do not transcribe what you can
    derive. A hand-written source list would drift the first time a reference
    was added and the page forgotten. Drift detection verified by tampering with
    the file and confirming a non-zero exit.
  * CI gained a `docs` job: sources-page drift + `mkdocs build --strict` (strict
    turns broken links and missing nav targets into failures).
  * Verified mkdocstrings actually rendered rather than silently no-op'ing: the
    built page carries real docstring prose and parameter tables, not just nav.
  * Noted for later: mkdocs-material prints a warning that MkDocs 2.0 will
    remove the plugin system with no migration path. Not actionable now (we pin
    1.x), but it makes the docs stack a future liability -- see T-0029.
- T-0027 (2026-07-16) **Bug: a degenerate Box-Cox crashed the capability path.**
  Found by generating a realistic demo CSV (a capable-but-drifting process,
  spec 9.70/10.30) and running it through the app before shipping it: the
  decision path routed to Box-Cox, the fitted lambda came out at -46, and at
  that lambda `x**lambda` underflows across the whole range -- so *both* spec
  limits mapped to the same float (0.0217086) and the inner `capability()` call
  raised `lsl (0.0217...) must be strictly below usl (0.0217...)`. A user who
  typed 9.70 and 10.30 got a 422 about 0.0217. This is the note left open in
  T-0011 sub-increment 5; now with a repro from ordinary data.
  * `box_cox_capability` now detects the collapse and raises an error naming the
    limits the *caller* passed, not their transformed ghosts.
  * `analyze_capability` catches it and routes to the percentile method -- the
    fallback it already had for "Box-Cox didn't work", which simply was never
    reached because Box-Cox raised first. Percentile does not transform the
    limits, so it handles this fine (lognorm, Ppk 0.942).
  * Tests: the collapse (forced lambda, deterministic) and the fallback
    (seeded drift data, with a precondition asserting it really is the new
    branch and not the older "failed to achieve normality" one).
  * Also caught while verifying: `uvicorn --reload` watches `apps/api` only, so
    the running server kept serving the old core. Verify through the live
    server, not just the unit test.
- T-0014 (2026-07-16) M6a printable report. **Scope changed on purpose**: the
  task said "report *route*", but a separate route would mean plumbing each
  page's analysis state somewhere a second route could read it -- for three
  different surfaces (`/`, `/gage-rr`, `/msa`), that is a store refactor bought
  for nothing. Instead the analysis pages print *themselves*: a `@media print`
  stylesheet drops the nav, the buttons and the dropzone, flattens the inputs so
  their values read as text (the study's parameters belong in the report), keeps
  colour (a red limit is meaning, not decoration), and avoids page breaks inside
  charts, tables and cards. A "Print / save as PDF" button on each page hands it
  to the browser. One stylesheet, all three surfaces, no new state.
  * ECharts now renders **SVG instead of canvas** (`lib/echarts.ts`), so charts
    come out vector in the PDF rather than a screen-resolution bitmap. Our
    series are small, so SVG costs nothing.
  * Verified automatically, not by eyeballing a dialog: a Playwright test
    emulates print media and asserts the controls are gone while the headings,
    verdicts and chart SVGs remain.
  * Server-side PDF stays out of scope (it would put a headless browser in the
    API image for what every browser already does). Still a roadmap item.
  * Snag worth remembering: the e2e assertions counted `canvas`; with SVG they
    had to be scoped to the panels, because Next's dev overlay ships SVGs of its
    own and inflated the count.
- T-0019 (2026-07-16) Demo hosting decided: **Vercel** for the Next.js app.
  The API's host is a separate open question -- see T-0026.
- T-0025 (2026-07-16) MSA API + UI: `/compute/{bias,linearity,stability}` with
  faithful serialisation (derived verdicts included; an identical-reading bias
  study's infinite t serialises as null, the interval-based verdict survives;
  stability nests the existing ChartPair schema), and a `/msa` page with the
  three studies, each pre-filled with a worked example. Stability reuses the
  `ControlChart` component built for the control-chart panel. 45 API tests, 25
  vitest, 5 Playwright. Verified in-browser: the linearity panel renders the
  AIAG slope -0.132 / intercept 1.408 and the published per-part biases live.
  **M5 is now complete end-to-end.**
- T-0013 (2026-07-16) M5b measurement-system studies in `capstat-core` -- the
  three that ask whether a gage is *right*, not just consistent.
  * **Bias** (`bias`): one-sample t-test of repeated readings against a known
    reference. Bias, repeatability, t/p, a confidence interval, and a CI-based
    verdict that stays meaningful when every reading is identical (the
    t-statistic is not). Validated against scipy's `ttest_1samp` and both AIAG
    worked examples (hardness = no bias, colorimeter = biased).
  * **Linearity** (`linearity`): least-squares regression of per-reading bias on
    the reference across masters spanning the range; slope/intercept, R^2, the
    slope's t-test, %linearity = |slope| x 100, absolute linearity when a
    process variation is given. Validated against the AIAG example (slope
    -0.132, intercept 1.408, per-part biases) and scipy's `linregress`.
  * **Stability** (`stability`): a deliberately thin MSA-framed wrapper over the
    validated I-MR / Xbar-R charts -- a control chart on a master part, with the
    out-of-control points read as gage drift.
  445 core tests, 100% coverage, mypy strict + ruff clean. Core-only; the API +
  UI wiring is T-0025.
- T-0012 web+API (2026-07-15) Gage R&R wired out of the core: `/compute/gage-rr`
  (both methods, faithful `GageRRReportOut` with the derived %/ndc read via
  from_attributes; a nan-guard so degenerate input serialises as null, not a
  500) and a `/gage-rr` web page -- data-entry grid (parts x operators x trials,
  pre-filled with the AIAG example), method toggle, variance/%/ndc report with
  verdict warnings, nav link. 38 API tests; 2 Playwright smoke tests. Verified
  in-browser on both methods (ANOVA 33% / ndc 4, avg-range 34% / ndc 3).
- T-0012 (2026-07-15) M5a Gage R&R (measurement-system analysis) in
  `capstat-core`, both AIAG methods.
  * **ANOVA** (`gage_rr`): crossed two-way random-effects model; variance
    components with the interaction-drop rule (pool when the F-test's p > 0.25)
    and negative-variance clamping; %Contribution, %Study Variation, ndc
    (1.41 * PV/GRR), optional precision-to-tolerance, AIAG verdict warnings.
  * **Average-and-range** (`gage_rr_range`): EV = Rbar/d2(r),
    AV = sqrt((Xdiff/d2*(o,1))^2 - EV^2/(pr)), PV = Rp/d2*(p,1); shares the same
    `GageRRReport`. New `d2_star(n, g) = sqrt(d2^2 + d3^2/g)` in constants.py,
    computed from the existing d2/d3 (not transcribed) and validated against
    Duncan's published table -- it is exactly what the AIAG K2/K3 constants
    encode.
  * Validation: the ANOVA path against the SPC-for-Excel AIAG worked example
    (independently recomputed in plain numpy first); the average-and-range path
    against the published AIAG 10-part summary and an independent oracle on the
    5-part data; the two methods cross-checked to agree on the same data
    (33% vs 34% GRR). 412 core tests, 100% coverage, mypy strict + ruff clean.
  * Also hardened a pre-existing d3 timing test that flakes under coverage
    instrumentation (sub-second wall-clock assert): the tight bound now applies
    only when no line tracer is active; under coverage a generous ceiling still
    catches the order-of-magnitude scipy regression it guards against.
  * Core-only: no Gage R&R API endpoint or UI yet (a later increment).
- T-0011 (2026-07-15) M4 Next.js app -- all six sub-increments: typed TS client
  (openapi-typescript, drift-checked); Next 16 / React 19 / Tailwind v4 scaffold;
  upload flow (`/ingest` + CORS); capability dashboard (decision-path analyze +
  ECharts histogram); I-MR control charts with a Nelson run-rule overlay (shared
  `useEchart` hook); and a test safety net (vitest for the pure numerics +
  Playwright smoke, both in CI). The app now covers upload -> capability ->
  control charts, typed against the API and tested. Detail in the commits
  (ec3e1ac, 23b40d5, 7c8bdd3, ed2fe9a).
- T-0020 (2026-07-15) CI actions bumped off the deprecated Node.js 20 runtime:
  `actions/checkout@v4->v7`, `astral-sh/setup-uv@v6->v7`,
  `actions/setup-node@v4->v7`. Verified none of the breaking changes touch
  inputs we use (checkout takes none; setup-node's v5 auto-cache is additive to
  our explicit `cache: npm`; setup-uv dropped only `server-url` / the old custom
  manifest). setup-uv stopped at v7 on purpose: v8 removed the moving major tag,
  so `@v8` does not resolve -- only full versions do. CI green, warnings gone.
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
