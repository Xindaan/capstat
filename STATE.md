# STATE.md — capstat

Date: 2026-07-22

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project, released as v0.1.0.

Milestones, not calendar weeks: M1-M2 core statistics, M3 API, M4 web app,
M5 MSA, M6 release (report, deployment, docs, release).

## Status

- **`capstat-core` covers all of M1/M2**, and **the FastAPI service (T-0010)
  wraps it.** Core: T-0002..T-0009 (descriptive/robust,
  normality, capability incl. non-normal, chart constants, Shewhart charts,
  EWMA/CUSUM, run rules). API: `apps/api` with stateless compute endpoints,
  CSV/XLSX ingestion, and a committed OpenAPI contract.
- **517 core + 61 API tests, 100 % coverage on both packages**, mypy strict,
  ruff clean, OpenAPI drift check green. CI matrix 3.11/3.12/3.13.
- **Acceptance sampling (T-0035 + T-0036 + T-0037) landed after v0.1.0 and is
  end-to-end**, ISO 2859-1's switching scheme included. Single sampling plans by
  attributes: OC curve (binomial / hypergeometric / Poisson), AOQ, AOQL, ATI,
  producer's and consumer's risk, the limiting quality, the lot decision, and
  two-point plan design -- all from the definition, no standard's table
  anywhere -- plus the switching scheme over a series of lots. Reachable through
  `/compute/acceptance-sampling/{evaluate,design,oc-curve,inspect,switching-rules}`
  and the `/acceptance-sampling` page.
- **M4 (app) and M5 (MSA) are complete end-to-end.** The web app covers
  upload -> capability -> control charts (`/`), a Gage R&R study (`/gage-rr`),
  and bias / linearity / stability (`/msa`) -- every one of them typed against
  the API and reaching the validated core. What remains is the M6 release path
  (PDF report, deployment, docs, release).
- **The core stays web-free.** fastapi/pandas/openpyxl live only in `apps/api`;
  `capstat-core` remains numpy+scipy and independently PyPI-publishable.
- **The API is a faithful serialisation layer**, not a reinterpretation: every
  response mirrors a core dataclass (warnings tuples preserved, nullable
  indices kept as `null`, `nan` coerced to `null`, derived properties read by
  attribute). Every endpoint test asserts equality with the core's own output.
- **Gage R&R (T-0012) is complete in `capstat-core`, both AIAG methods.**
  `gage_rr()` (ANOVA: crossed random-effects model, interaction-drop rule,
  negative-variance clamp) and `gage_rr_range()` (average-and-range: EV/AV/PV
  from ranges and the new `d2_star(n,g)=sqrt(d2^2+d3^2/g)` constant) share one
  `GageRRReport` and report %Contribution, %Study Variation, and ndc. Validated
  against AIAG worked examples (independently recomputed) and cross-checked
  method-to-method. d2_star is computed from the core's own d2/d3, not
  transcribed, and matches Duncan's published table.
- **Gage R&R is wired end-to-end**: core (`gage_rr`/`gage_rr_range`) ->
  `/compute/gage-rr` (both methods, faithful serialisation) -> a `/gage-rr` web
  page with a data-entry grid and a variance/%/ndc report. Verified in-browser.
- Repo live at github.com/Xindaan/capstat (**private**; flip with
  `gh repo edit --visibility public` when ready).
- **Hosting decided (2026-07-20): local only, no public demo.** The maintainer
  trusts running it locally over sending measurement data to a third party --
  the right call for a tool fed real production data. `docker compose up` is the
  supported way to run it; nothing is hosted. The Docker artifacts and the
  measurement notes stay in the docs for anyone who wants to self-host.

## Working method (keeps paying off — do not abandon it under time pressure)

1. **Compute from the definition; never transcribe a constant.** This caught a
   real error *in the published tables* (E2 = 2.660 is wrong; it is 2.6587).
2. **Validate against a source that did not produce the value.**
3. **Prefer identities to quoted numbers.** They hold for every dataset, and
   they disproved a false claim of mine in T-0006.
4. **Explain a discrepancy exactly rather than widening a tolerance.** A loose
   tolerance is where a real bug hides. **Values may carry a tolerance;
   decisions must not** (T-0008: NIST's first CUSUM signal is group 14, and ours
   is asserted to be group 14 exactly).
5. **Suspect your own test, and your own docstring, before the library.** Three
   tests in T-0008 were wrong, not the code. In T-0009 a *docstring claim* was
   wrong — I asserted the full Nelson set is "four times as jumpy"; simulation
   said eight times. Simulate the claim rather than repeating it.
6. **Find the sequence where two sources disagree.** WE rule 4 needs 8 points,
   Nelson rule 2 needs 9. A run of exactly 8 discriminates them — and that is
   what catches an off-by-one, which nothing downstream would reveal.
7. **Say what the numbers cannot say.** Every report carries warnings.

## Next actions

**T-0018 was split** on 2026-07-21 into T-0035..T-0041, because one ID was
carrying four unrelated things. **T-0035 (core) and T-0037 (API + web page) are
both done -- acceptance sampling is end-to-end.** What is left:

- **T-0036 -- decided: yes, and the standard is ISO 2859-1** (2026-07-21). AQL
  sampling is used in the maintainer's own work, so the value is reproducing
  what a customer specifies, not computing a better plan.
  **But ISO changes the shape, and rules out the obvious route.** ISO's tables
  may not be reproduced here, and MIL-STD-105E is not a stand-in: it was adopted
  into ISO 2859 "with minor changes", so a 105E cell may differ from the ISO
  cell a specification names while looking conformant. The buildable shape
  therefore contains no master table: (1) ISO vocabulary plus the
  bring-your-own-plan path that T-0037 already ships, (2) the switching rules
  normal/tightened/reduced -- where 2859-1's protection actually lives, and
  which needs an explicit go because its thresholds are read from the standard,
  (3) a code-letter lookup only if 1 and 2 leave a gap, and only from a source
  we may reproduce.
  **Increments 1 and 2 are done, end-to-end.** Limiting quality; the full
  switching scheme -- normal/tightened/reduced/discontinued, the switching
  score, and the two inputs capstat refuses to guess (the tighter-AQL question,
  and authorisation for reduced inspection) -- in the core, over
  `/compute/acceptance-sampling/switching-rules`, and on the page. Only
  increment 3 remains, a code-letter lookup, and it is only worth revisiting if
  something real turns out to need it.
- **T-0039 / T-0040 are closed unbuilt** (2026-07-21, by decision): auth and
  persistence would both reverse T-0026. What survived is **T-0041** -- saving a
  study as a JSON file the user owns, which is a file format, not persistence,
  and reverses nothing. **Partly done 2026-07-22:** the format and the
  acceptance-sampling page are shipped; `/`, `/gage-rr` and `/msa` are not wired
  yet, and the pattern for doing so is established.
- **T-0038** -- server-side PDF: deferred by decision, not closed. The print
  route already yields a vector PDF; if it is ever wanted, build it as a local
  CLI export rather than a service endpoint.

## Open decisions (unchanged)

**v0.1.0 is released** (tag `v0.1.0`, 2026-07-21). M1–M6 are complete: core,
API, web app, MSA, report, docs, deployment artifacts, release automation.

**Repo visibility** — still private, so the release is visible only to you.
Flipping it is a separate, deliberate step: `gh repo edit --visibility public`.
Decide this *before* T-0030: publishing an sdist puts the source on PyPI, which
is a larger step than making the repo public, not a smaller one.

**T-0030** is half set up: a PyPI account and a pending trusted publisher exist
(`capstat-core` / `Xindaan` / `capstat` / `publish.yml` / env `pypi`), so no API
token will ever be needed. It reserves **nothing** — PyPI has no reserve-without-
upload mechanism, and a name is only yours once a release exists. `publish.yml`
is deliberately absent: with it in the repo, the next release would upload
unasked. Adding it *is* the decision to publish.

Otherwise the backlog is decisions and deliberately-deferred items: **T-0029**
(mkdocs now capped below 2.x; revisit when 2.0 ships), the rest of the
T-0035..T-0041 split of the old T-0018 roadmap (see Next actions), and the
postcss half of T-0023, which cannot move until Next raises its pinned floor.
Nothing is blocked on me.

## Last done

- 2026-07-22: **T-0041 — a study saves to a file and loads back**, on the
  acceptance-sampling page. A file on the user's own disk, written and read by
  the browser: no server, nothing held between requests, so it reverses nothing
  in T-0026. **Only inputs are stored, never results** — a document carrying
  saved numbers could show figures this version would no longer produce with
  nothing on screen to reveal it, so `parseStudyFile` rebuilds the document
  field by field and a stray `results` block is dropped rather than displayed.
  A file from a newer format is refused with a message saying so.
  The design question the task left open answered itself by looking: the panels
  share nothing but strings, so there is no common shape — the document carries
  a version, a page name, and a per-page payload.
  **Two failures worth keeping.** An unscoped `getByRole("alert")` matched
  Next's own route announcer as well as the error card — the same class as the
  dev-overlay SVG trap already recorded here. And adding a client workspace made
  the page slower to hydrate, so *existing* tests began racing it: a fill before
  hydration is overwritten by the component's initial state, and the request
  then carries the example series while the assertion complains about something
  else. Both the spec file (a `ready()` gate) and the Playwright config (a
  global route warm-up) now handle it — the warm-up matters for CI, where the
  dev server is fresh every run and compiles each route inside the first test's
  timeout.

- 2026-07-22: **T-0036 increment 2b — the switching scheme reaches the app.**
  A `/compute/acceptance-sampling/switching-rules` route and a second panel on
  the page: paste the lot outcomes, get the severity each lot was inspected
  under and the switch it caused. The switching score is shown as *absent*
  rather than zero wherever the standard does not maintain it, which is the
  distinction the whole column exists to make.
  Verified against the real API in a browser, which is where the one defect
  turned up: JSX had swallowed a space, rendering "Rfor not" in the panel's
  intro. Prettier kept reformatting the fix away, so the fragile inline `<code>`
  join was removed rather than nursed. 578 tests, both packages at 100 %.

- 2026-07-22: **T-0036 increment 2 — the ISO 2859-1 switching scheme** in the
  core. normal / tightened / reduced / discontinued, the switching score, and
  the two inputs capstat refuses to guess: whether a lot would still have been
  accepted one AQL step tighter (only the master table knows), and whether
  reduced inspection is authorised at all (steady production plus the
  responsible authority — not statistics). Both default to the conservative
  branch, so a scheme left alone never relaxes.
  **Re-running the research that had died at the spend limit paid for itself
  twice.** It found a real bug: the first version counted lots *inspected* under
  tightened where clause 9.4 counts lots *not accepted*, cumulatively — a
  materially different rule for anyone who set the threshold to 5 believing they
  had implemented the standard. And it dissolved the 5-vs-10 disagreement over
  that threshold, which was never a conflict: Z1.4-2003 changed the rule, so
  older material simply states the superseded figure.
  **The validation got much stronger than simulation.** The standard's own
  Annex A works a series of lots all the way through, printing severity *and*
  switching score per lot. capstat reproduces it completely — both transitions,
  every score, and the switch to reduced at the lot where the score reaches 30.
  That also confirmed the two things previously carried as interpretations: a
  switch binds the lot after the one that triggered it, and the window slides.
  The sequence is deliberately not committed: it is a table from a copyrighted
  standard obtained from a copy of uncertain provenance, so what is recorded is
  the outcome of the comparison. The cost is stated where it belongs — this one
  check is not re-run by CI.

- 2026-07-21: **T-0037 — acceptance sampling reaches the API and the app.** Four
  routes, one per core entry point, and an `/acceptance-sampling` page that
  designs a plan from two risk points, draws the OC curve with both levels
  marked, and decides a lot from an observed defect count. **547 Python tests
  (491 core + 56 API) at 100 % coverage on both packages**, 37 vitest, 14
  Playwright specs, both drift gates green.
  Three findings, and only one of them came from a test.
  **The core had an inconsistency I had introduced in T-0035**: `OCCurve` held
  numpy arrays where every other public dataclass holds `tuple[float, ...]`.
  Found by comparing against the neighbours before writing the schema, and fixed
  in the core rather than papered over in the API — a frozen dataclass wrapping
  a mutable array is frozen in name only.
  **The OC chart drew its AQL/LTPD labels rotated 90° and clipped**, because a
  markLine label inherits its line's direction and these lines are vertical,
  unlike every markline in the control chart. Only looking at the page against
  the real API showed it. *Keep verifying in a browser; the mocked e2e suite is
  structurally blind to this class.*
  **The screenshot script skipped its own chart wait.** `shoot()` guarded it
  with `if (await panel.locator("svg").count())` — evaluated once, immediately,
  while ECharts is still being imported lazily, so the count was zero and the
  poll never ran. It photographed an empty chart box. The wait is now explicit
  (`chart: true`); the previous figures were right only by luck of timing.

- 2026-07-21: **T-0035 — acceptance sampling in the core** (first piece of the
  T-0018 split). OC curve in three models, AOQ/AOQL/ATI, risks, the inverse OC,
  the lot decision, and two-point plan design — all computed from the
  definition; no standard's table is consulted anywhere. **491 core + 48 API
  tests, core back at 100 % coverage**, ruff and mypy strict clean.
  Two things worth carrying forward. **First: the published tables were wrong
  four different ways**, and saying so precisely was more work than the
  implementation. NIST's AOQ column uses an approximation its own page
  contradicts, except one row that uses a third formula; one entry has its
  digits transposed (0.0010 for 0.0100); the ATI column truncates where the
  prose rounds. Naming each cause let both columns be asserted with *no*
  tolerance on the published digits at all — `round(Pa*p, 4)` hits ten of
  twelve rows exactly, and every ATI entry must be `floor` or `round` of ours.
  Explaining a discrepancy really does buy a tighter test than tolerating it.
  **Second: three independent implementations print eight significant digits
  where handbooks print three** (R *AcceptanceSampling*, R *AccSamplingDesign*,
  Minitab). Those turned out to be far better references than any table —
  capstat reproduces every digit, including two designed plans asserted
  exactly. Worth reaching for in future methods: a documented software example
  beats a rounded printed table.
  My own two bugs both came from tests failing for the right reason: the design
  search probed plans larger than the lot and died in the constructor, and the
  Type A path accepted quality levels a finite lot cannot represent (a lot of 50
  cannot be 1 % defective) — which quietly made the producer's risk condition
  vacuous. Both fixed and pinned.

- 2026-07-21: **backlog cleared (T-0021, T-0022, T-0023, T-0024).** Run-rule
  selection in the UI (all eight Nelson rules, default 1-4, wording fetched from
  the API, and the report always names the set it applied); scipy-1.19 readiness
  *without* the circular fix the task itself proposed — a NIST-handbook check
  now guards the critical values from outside, and the scipy cross-check skips
  honestly when the API goes; `httpx2` adopted, leaving the suite **warning-free
  at 496 tests**; and the two high npm advisories fixed by a semver-compatible
  js-yaml override, with the postcss pair left alone on purpose because Next
  pins it exactly.
  Also made the screenshot capture **deterministic** — focus rings and an
  in-flight opacity transition were making unrelated figures churn on every run.
  Three consecutive captures are now byte-identical, so a diff in `docs/images/`
  means the UI actually changed.

- 2026-07-21: T-0031 — **README screenshots**, captured by a script rather than
  by hand (`cd apps/web && npm run screenshots`). It drives the *real* API with
  `examples/shaft-diameter.csv`, so the figures show numbers the validated core
  actually computed — illustrating a reference-validated project with mocked
  values would undercut the only thing it claims. Re-run after any UI change.
  The camera found a real bug on its first pass: the histogram's y-axis name
  was clipped by the top of the canvas. Nothing else had ever looked at it.

- 2026-07-21: **T-0017b — v0.1.0 released.** PR #3 squash-merged, release-please
  cut the tag and the GitHub release. Post-merge CI green on all six jobs, and
  the drift check that T-0034 fixed passed on the release commit — the exact
  failure it was written for. Caught one more instance of the held-run trap on
  the way in: the PR's green CI belonged to an *older* head (I had pushed twice
  since), so the tick was real but stale. Re-approved on the current sha before
  merging. **Match the run's sha to the PR head; a green check is not
  necessarily a green check of what you are merging.**

- 2026-07-21: T-0034 — **the OpenAPI drift check stopped failing on formatting
  it does not own.** release-please rewrites `openapi.json` to stamp the version
  and, being JavaScript, renders `5.0` as `5`; the byte-for-byte check called
  that drift and would have reddened `main` on the release commit. `--check` now
  compares parsed documents — which is the guarantee it always meant to give.
  Caught by checking the release branch out locally, because the PR showed no
  checks at all. The reason turned out to be worth knowing: workflows on a
  GITHUB_TOKEN-created PR are queued as `action_required` and sit there awaiting
  manual approval, which `gh pr checks` renders as *nothing reported* -- looking
  exactly like a repo with no CI. Approving the run (`gh api -X POST
  .../actions/runs/<id>/approve`) turned all six jobs green on the release
  commit. **An unapproved release PR is untested and looks the same as a passing
  one; approve it before merging.**

- 2026-07-21: T-0032 — the maintainer enabled Actions-may-open-PRs; re-running
  release-please opened PR #3 ("chore(main): release 0.1.0") on the spot.

- 2026-07-21: T-0033 — **the upload panel no longer analyses the row index.**
  It auto-selected the first numeric column, which on the demo CSV is `part`
  (1..60): Pp 0.006, capability of the part *numbers* against a diameter spec,
  with nothing to warn you, because consecutive integers are valid data.
  Auto-select now skips index-looking columns; picking one manually still works
  but says what it is. Both halves pinned by an e2e test.

- 2026-07-20: T-0028 — an index with no value now **says why** rather than
  showing a dash: "not defined on the percentile path" (Cp/Cpk have no
  within/between split there) vs "needs both spec limits" (one-sided spec).
  Two absences that looked identical are now distinguishable. Pinned by an
  e2e test.

- 2026-07-20: T-0017a — **release automation** via release-please (one version
  for the whole repo). **Caught myself misdiagnosing the first run**: I claimed
  the config left versions at 0.0.0 and "fixed" it; then inspected the release
  branch release-please had actually pushed and found every version bumped
  correctly. Reverted the false-premise change. The real blocker is a repo
  switch (T-0032); the default 1.0.0 was pinned to 0.1.0 to match the goal.

- 2026-07-16: T-0015a — **deployment artifacts**: Dockerfiles (API + web, both
  non-root), docker-compose, Vercel config, docs/deployment.md. Could not build
  locally (no Docker daemon), so CI gained an `images` job that builds both on
  every commit rather than trusting an unverified artifact.

- 2026-07-16: T-0016 — **docs site** (mkdocs-material + mkdocstrings): home,
  getting started, method reference, validation, API reference. The sources page
  is *generated* from the reference YAMLs with a CI drift check, so documented
  sources cannot drift from what the suite asserts. New `docs` CI job.

- 2026-07-16: T-0027 — **fixed a real crash in the capability decision path**: a
  fitted Box-Cox lambda of -46 collapses both spec limits onto the same float,
  and the resulting 422 quoted the transformed limits (0.0217) at a user who
  typed 9.70/10.30. Box-Cox now reports the collapse against the caller's own
  limits, and `analyze_capability` routes to the percentile fallback it already
  had. Found by running a realistic demo CSV through the app before shipping it.
  `examples/shaft-diameter.csv` is that dataset.
- 2026-07-16: T-0014 — **printable report**: every analysis page prints itself
  (print stylesheet drops controls, keeps results), charts switched to ECharts
  **SVG** so the PDF is vector. Verified by a Playwright print-media test.
- 2026-07-16: T-0025 — **MSA API + UI**: `/compute/{bias,linearity,stability}`
  + a `/msa` page with all three studies, each pre-filled with a worked example
  (stability reuses the ControlChart component). **M5 is complete end-to-end.**
- 2026-07-16: **T-0013 (M5b) complete in the core** — bias (t-test vs a
  reference), linearity (bias-vs-reference regression), stability (control chart
  on a master). Validated against both AIAG examples, scipy's ttest_1samp and
  linregress. 445 core tests, 100% coverage.
- 2026-07-15: Gage R&R **web UI** -- a `/gage-rr` route with a data-entry grid
  (parts x operators x trials, pre-filled with the AIAG example), method toggle
  (ANOVA / average-and-range), and a report (variance table, %/ndc cards,
  verdict warnings). Nav added. Verified in-browser on both methods; 2 Playwright
  smoke tests. Gage R&R is now end-to-end: core -> API -> UI.
- 2026-07-15: Gage R&R API — `/compute/gage-rr` in apps/api (both methods,
  faithful `GageRRReportOut` incl. derived %/ndc; degenerate input -> null, not
  500, via a core nan-guard fix); typed TS client regenerated. 38 API tests.
- 2026-07-15: T-0012 — Gage R&R complete in capstat-core, both AIAG methods:
  `gage_rr` (ANOVA) + `gage_rr_range` (average-and-range) sharing one report;
  new `d2_star` constant from d2/d3, validated against Duncan's table; methods
  cross-checked to agree. Hardened a coverage-flaky d3 timing test. 412 core
  tests, 100% coverage.
- 2026-07-15: T-0011 sub-increment 6 — test safety net: pure numerics extracted
  to `lib/stats.ts` + vitest (21 tests); Playwright smoke test (API mocked);
  both wired into CI; README "Web app" section. **T-0011 M4 complete.**
- 2026-07-15: T-0011 sub-increment 5 — I-MR control charts (Individuals + MR,
  limits/zones/violations + Nelson run-rule overlay); shared `useEchart` hook,
  histogram refactored onto it. Verified in-browser (spike + run dataset).
- 2026-07-15: T-0011 sub-increment 4 — capability dashboard: decision-path
  analyze call, Pp/Ppk + Cp/Cpk, ECharts histogram with spec limits + normal
  fit; verified in-browser on normal + Box-Cox data. Fixed two chart bugs
  (empty canvas from an async-init race; spec limit clipped off the x-axis).
- 2026-07-15: T-0020 — CI actions bumped off Node.js 20 (checkout v7, setup-uv
  v7, setup-node v7); no input breakage, warnings gone.
- 2026-07-15: T-0011 sub-increment 3 — upload flow: `UploadPanel` POSTs to
  `/ingest`, ingestion warnings + column picker surfaced, verified in-browser;
  API `CORSMiddleware` (env-configurable), 4 CORS tests; uv-workspace excludes
  `apps/web`. 34 API tests pass, web lint/build/drift green.
- 2026-07-15: T-0011 (in progress) TS client + Next.js scaffold; typed
  `openapi-fetch` client wired, `npm run build` green, web CI job added.
- 2026-07-15: T-0010 FastAPI service (`apps/api`): faithful serialisation,
  CSV/XLSX ingestion, committed OpenAPI + drift check. 412 tests, 100 % cov.
- 2026-07-14: T-0009 Nelson + Western Electric run rules.
- 2026-07-14: T-0008 EWMA + CUSUM, both NIST worked examples reproduced.
- 2026-07-14: T-0007 chart constants + Shewhart charts; 75x d3 speedup.
- 2026-07-14: T-0006 non-normal path (Box-Cox, ISO 22514, decision path).
- 2026-07-14: T-0005 capability indices + d2/c4 constants.
- 2026-07-14: T-0004 normality tests with a caveated verdict.
- 2026-07-14: T-0003 descriptive + robust statistics, NIST StRD validated.
- 2026-07-14: T-0002 repo bootstrap; CI green on GitHub.
