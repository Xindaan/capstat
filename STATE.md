# STATE.md — capstat

Date: 2026-07-14

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project; v0.1.0 in 3 weeks.

## Status

- **Week 1 complete, and Week 2's chart work has started.** T-0002 bootstrap,
  T-0003 descriptive + robust, T-0004 normality, T-0005 capability + d2/c4,
  T-0006 non-normal path, T-0007 chart constants + Shewhart charts.
  **317 tests, 100 % coverage**, mypy strict, CI green on 3.11/3.12/3.13.
- `capstat_core` now covers: descriptive/robust statistics, normality testing,
  capability (normal, Box-Cox, ISO 22514 percentile) with a recorded decision
  path, all control-chart constants, and I-MR / X-bar-R / X-bar-S charts.
- Repo live at github.com/Xindaan/capstat (**private**; flip with
  `gh repo edit --visibility public` when ready).
- Only open decision: demo hosting (T-0019, due Week 3).

## Working method (keeps paying off — do not abandon it under time pressure)

1. **Compute from the definition; never transcribe a constant.** This has now
   caught a real error *in the published tables*: they print E2 = 2.660, but the
   true value is 2.6587 — they evaluated 3/d2 from an already-rounded d2 = 1.128.
   The tables also disagree with each other (NIST D4(3) = 2.575, ASTM 2.574).
2. **Validate against a source that did not produce the value.** d2 vs NIST's A2
   table; the AD p-value vs Stephens' critical values; published R output vs scipy.
3. **Prefer identities to quoted numbers.** They hold for every dataset. This is
   what disproved a false claim of mine in T-0006 (Box-Cox and the percentile
   method do *not* agree in general, only at the just-capable point).
4. **Predict the size of a discrepancy exactly rather than widening a tolerance.**
   A loose tolerance is where a real bug hides.
5. **Say what the numbers cannot say.** Every report carries warnings: the R
   chart must be read before the X-bar chart; an I-MR chart assumes time order;
   Cpk without Ppk flatters a drifting process.

## Next actions

1. T-0008 M2b EWMA + CUSUM, validated against Montgomery / NIST e-Handbook
   worked examples (NIST 6.3.2.3 CUSUM, 6.3.2.4 EWMA — both give numbers).
   These detect the small sustained shifts Shewhart charts miss, which is the
   natural complement to what T-0007 built.
2. T-0009 M2c Nelson + Western Electric run rules. T-0007 flags only points
   beyond the limits; the run rules catch drifts that never cross one. The
   `ControlChart.violations` field will need to grow from "beyond limits" into
   "which rule fired".

## Last done

- 2026-07-14: T-0007 chart constants (d3 via the joint min/max density) +
  I-MR, X-bar-R, X-bar-S charts.
- 2026-07-14: T-0006 non-normal path (Box-Cox, ISO 22514, decision path).
- 2026-07-14: T-0005 capability indices + d2/c4 constants.
- 2026-07-14: T-0004 normality tests with a caveated verdict.
- 2026-07-14: T-0003 descriptive + robust statistics, NIST StRD validated.
- 2026-07-14: T-0002 repo bootstrap; CI green on GitHub.
