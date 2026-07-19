# STATE.md — capstat

Date: 2026-07-15

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
- **445 core + 38 API tests, 100 % coverage on both packages**, mypy strict,
  ruff clean, OpenAPI drift check green. CI matrix 3.11/3.12/3.13.
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
- **Hosting decided (2026-07-16): Vercel** for the Next.js app. Still open: where
  the FastAPI service lives — Vercel Python functions would keep it on one
  platform but numpy+scipy+pandas is a real size risk against the serverless
  bundle limit; a container host (Render/Fly) is the safe pairing. Decide before
  T-0015.

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

1. **T-0026 needs your call**: where the API is hosted. Measured — 152 MB of
   deps, ~1 s cold import — so serverless fits but is tight and slow to wake.
   Recommendation: a container host (Render free / Fly.io). Needs an account.
2. T-0017 M6d v0.1.0 release via release-please; README badges + demo link.
3. T-0028 Cp/Cpk cards read as "missing" on the percentile path (small, real).

## Last done

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
