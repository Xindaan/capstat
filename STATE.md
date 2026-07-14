# STATE.md — capstat

Date: 2026-07-14

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project; v0.1.0 in 3 weeks.

## Status

- **`capstat-core` is feature-complete for Weeks 1 and 2.** T-0002 bootstrap,
  T-0003 descriptive + robust, T-0004 normality, T-0005 capability + constants,
  T-0006 non-normal path, T-0007 Shewhart charts, T-0008 EWMA/CUSUM, T-0009 run
  rules. **382 tests, 100 % coverage**, mypy strict, CI green on 3.11/3.12/3.13.
- The library now covers: descriptive/robust statistics; normality testing;
  capability (normal, Box-Cox, ISO 22514) with a recorded decision path; all
  control-chart constants; I-MR / X-bar-R / X-bar-S; EWMA / CUSUM; Nelson and
  Western Electric run rules.
- **The next milestone leaves the core.** T-0010 is the FastAPI service — the
  first work that is not pure statistics. Everything after it (web app, PDF,
  deploy) builds on that.
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

1. T-0010 M3 FastAPI service: compute endpoints (descriptive, capability,
   control charts), CSV/XLSX ingestion, OpenAPI schema, TS client generation
   with a drift check in CI. Notes before starting:
   * `capstat-core` must stay web-free (numpy + scipy only) — pandas/openpyxl
     belong in `apps/api` alone. This is a PLAN.md non-negotiable.
   * The core's rich `warnings` tuples and `None`-able indices are the
     interesting part of the API surface: they must survive serialisation, not
     be flattened away. A JSON schema that drops the warnings would undo most of
     what Weeks 1-2 were for.
   * The OpenAPI schema is the single source of truth; the TS client is
     generated in CI with a `git diff --exit-code` drift check.
2. T-0011 M4 Next.js app.

## Last done

- 2026-07-14: T-0009 Nelson + Western Electric run rules.
- 2026-07-14: T-0008 EWMA + CUSUM, both NIST worked examples reproduced.
- 2026-07-14: T-0007 chart constants + Shewhart charts; 75x d3 speedup.
- 2026-07-14: T-0006 non-normal path (Box-Cox, ISO 22514, decision path).
- 2026-07-14: T-0005 capability indices + d2/c4 constants.
- 2026-07-14: T-0004 normality tests with a caveated verdict.
- 2026-07-14: T-0003 descriptive + robust statistics, NIST StRD validated.
- 2026-07-14: T-0002 repo bootstrap; CI green on GitHub.
