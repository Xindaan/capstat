# STATE.md — capstat

Date: 2026-07-15

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project; v0.1.0 in 3 weeks.

## Status

- **`capstat-core` is feature-complete for Weeks 1 and 2**, and **the FastAPI
  service (T-0010) now wraps it.** Core: T-0002..T-0009 (descriptive/robust,
  normality, capability incl. non-normal, chart constants, Shewhart charts,
  EWMA/CUSUM, run rules). API: `apps/api` with stateless compute endpoints,
  CSV/XLSX ingestion, and a committed OpenAPI contract.
- **403 core + 34 API tests, 100 % coverage on both packages**, mypy strict,
  ruff clean, OpenAPI drift check green. CI matrix 3.11/3.12/3.13.
- **T-0011 (M4 Next.js app) is complete** (upload -> capability -> control
  charts; vitest + Playwright in CI). **T-0012 (M5a Gage R&R) is in progress**:
  the ANOVA method landed in `capstat-core` (`gage_rr`), average-and-range next.
- **The core stays web-free.** fastapi/pandas/openpyxl live only in `apps/api`;
  `capstat-core` remains numpy+scipy and independently PyPI-publishable.
- **The API is a faithful serialisation layer**, not a reinterpretation: every
  response mirrors a core dataclass (warnings tuples preserved, nullable
  indices kept as `null`, `nan` coerced to `null`, derived properties read by
  attribute). Every endpoint test asserts equality with the core's own output.
- **Gage R&R (T-0012a, ANOVA method) landed in `capstat-core`.** `gage_rr()`
  runs the crossed two-way random-effects model, applies the AIAG
  interaction-drop rule (pool into repeatability when p > 0.25) and clamps
  negative variance components to zero with a warning, and reports
  %Contribution, %Study Variation, and ndc. Validated against the SPC-for-Excel
  AIAG worked example (independently recomputed first) and a constructed
  interaction-kept case. The average-and-range method (T-0012b) is next; it
  needs d2* constants, computed from their definition rather than transcribed.
- The core still exposes nothing web-facing for Gage R&R yet -- no API endpoint
  or UI. That wiring is a later increment; T-0012 is core credibility first.
- Repo live at github.com/Xindaan/capstat (**private**; flip with
  `gh repo edit --visibility public` when ready).
- Only open decision: demo hosting (T-0019, due Week 3).

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

1. T-0012b — Gage R&R **average-and-range method** in `capstat-core`: compute
   the d2* (bias-corrected, finite-subgroup) constants from their definition,
   then EV/AV/PV -> GRR; cross-check it lands near the ANOVA result on the same
   data. Same %/ndc summary as the ANOVA path.
2. T-0013 M5b Bias, linearity, stability.
3. T-0024 web run-rule selection UI (small, low priority).

## Last done

- 2026-07-15: T-0012a — Gage R&R ANOVA method (`gage_rr`) in capstat-core:
  variance components with AIAG interaction-drop + negative-variance clamp;
  %Contribution/%Study Variation/ndc. Validated against an independently
  recomputed AIAG worked example. 403 core tests, 100% coverage.
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
