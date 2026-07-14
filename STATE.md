# STATE.md — capstat

Date: 2026-07-14

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project; v0.1.0 in 3 weeks.

## Status

- Week 1 complete; Week 2's chart work nearly done. T-0002 bootstrap, T-0003
  descriptive + robust, T-0004 normality, T-0005 capability + d2/c4, T-0006
  non-normal path, T-0007 chart constants + Shewhart charts, T-0008 EWMA/CUSUM.
  **355 tests, 100 % coverage**, mypy strict, CI green on 3.11/3.12/3.13.
- `capstat_core` covers: descriptive/robust statistics, normality testing,
  capability (normal, Box-Cox, ISO 22514) with a recorded decision path, all
  control-chart constants, I-MR / X-bar-R / X-bar-S, and EWMA / CUSUM.
- Repo live at github.com/Xindaan/capstat (**private**; flip with
  `gh repo edit --visibility public` when ready).
- Only open decision: demo hosting (T-0019, due Week 3).

## Working method (keeps paying off — do not abandon it under time pressure)

1. **Compute from the definition; never transcribe a constant.** This caught a
   real error *in the published tables*: they print E2 = 2.660, the true value
   is 2.6587 (they evaluated 3/d2 from an already-rounded d2 = 1.128).
2. **Validate against a source that did not produce the value.**
3. **Prefer identities to quoted numbers** — they hold for every dataset. This
   disproved a false claim of mine in T-0006.
4. **Explain a discrepancy exactly rather than widening a tolerance.** T-0008's
   CUSUM tolerance (3e-2) is justified by a test showing a systematic +0.005
   input rounding moves S_hi by 0.040 — so the tolerance has no room to hide a
   defect. **Values may carry a tolerance; decisions must not** (NIST's first
   CUSUM signal is group 14, and ours is asserted to be group 14 exactly).
5. **Suspect your own test before the library.** Three tests in T-0008 were
   wrong, not the code — most instructively, "a stable EWMA series is in
   control", which is false: with ARL0 ~500, 34.7 % of 200-point series contain
   a false alarm. Test the *rate*, not one series.
6. **Say what the numbers cannot say.** Every report carries warnings.

## Next actions

1. T-0009 M2c Nelson + Western Electric run rules. **Structural delta to plan
   for:** `ControlChart.violations` is currently a flat tuple of "beyond limits"
   indices. Run rules need "which rule fired at which point", so that field has
   to grow into something like `tuple[RuleViolation, ...]`. That is a breaking
   change to a published dataclass — decide the shape before writing the rules,
   and update `xbar_r_chart` / `xbar_s_chart` / `i_mr_chart` together.
   Nelson rule 1 is the beyond-limits test already implemented, so it must not
   end up double-reported.
2. T-0010 M3 FastAPI service — the first non-core milestone.

## Last done

- 2026-07-14: T-0008 EWMA + CUSUM, both NIST worked examples reproduced.
- 2026-07-14: T-0007 chart constants (d3 via the joint min/max density) +
  I-MR, X-bar-R, X-bar-S charts; 75x d3 speedup.
- 2026-07-14: T-0006 non-normal path (Box-Cox, ISO 22514, decision path).
- 2026-07-14: T-0005 capability indices + d2/c4 constants.
- 2026-07-14: T-0004 normality tests with a caveated verdict.
- 2026-07-14: T-0003 descriptive + robust statistics, NIST StRD validated.
- 2026-07-14: T-0002 repo bootstrap; CI green on GitHub.
