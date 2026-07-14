# STATE.md — capstat

Date: 2026-07-14

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project; v0.1.0 in 3 weeks.

## Status

- **Week 1 (Tier-1 statistics) is complete.** T-0002 bootstrap, T-0003
  descriptive + robust, T-0004 normality, T-0005 capability + constants,
  T-0006 non-normal path. **277 tests, 100 % coverage**, mypy strict, CI green
  on 3.11/3.12/3.13.
- `capstat_core` now exposes a coherent capability story end to end:
  `analyze_capability()` tests normality, and routes to the normal indices,
  Box-Cox, or the ISO 22514 percentile method — recording which and why. The
  decision is auditable, which was the whole point of the milestone.
- Repo live at github.com/Xindaan/capstat (**private**; flip with
  `gh repo edit --visibility public` when ready).
- Only open decision: demo hosting (T-0019, due Week 3).

## Working method (keeps paying off — do not abandon it under time pressure)

1. **Compute from the definition, then validate against a source that did not
   produce the value.** d2 vs NIST's A2 table; the AD p-value vs Stephens'
   critical values; scipy vs NIST; published R output vs scipy.
2. **Never transcribe a coefficient from memory.** Fetch the source.
3. **Prefer identities to quoted numbers.** They hold for every dataset, not
   one. This is what caught a false claim in T-0006: Box-Cox and the percentile
   method do *not* agree in general, only at the just-capable point.
4. **Predict the size of a discrepancy exactly rather than widening a
   tolerance.** A loose tolerance is where a real bug hides.

## Next actions

1. T-0007 M2a: extend `capstat_core.constants` with d3, A2, D3, D4, B3, B4 —
   all derivable from d2/d3/c4, so compute them, do not transcribe (d2/c4 are
   already there from T-0005). Then the I-MR, X-bar-R and X-bar-S charts.
   Note the existing cross-check works in reverse here: NIST publishes A2/D3/D4,
   so those tables become the validation source for the computed values.
2. T-0008 M2b EWMA + CUSUM.

## Last done

- 2026-07-14: T-0006 non-normal path (Box-Cox, ISO 22514, decision path).
- 2026-07-14: T-0005 capability indices + d2/c4 constants.
- 2026-07-14: T-0004 normality tests with a caveated verdict.
- 2026-07-14: T-0003 descriptive + robust statistics, NIST StRD validated.
- 2026-07-14: T-0002 repo bootstrap; CI green on GitHub.
