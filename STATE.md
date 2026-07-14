# STATE.md — capstat

Date: 2026-07-14

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project; v0.1.0 in 3 weeks.

## Status

- Planning complete (2026-07-13); all decisions final (name, LICENSE holder,
  English, GitHub Xindaan).
- Repo live at github.com/Xindaan/capstat (**private**; flip with
  `gh repo edit --visibility public` when ready). CI green on 3.11/3.12/3.13.
- Week 1 core: T-0002 bootstrap, T-0003 descriptive + robust, T-0004 normality,
  T-0005 capability + constants. **234 tests, 100 % coverage**, mypy strict.
- The capability gate is wired: `capability()` runs `assess_normality()` and
  warns loudly when the normal model is rejected — which is exactly the hand-off
  T-0006 must catch.
- `capstat_core.constants` now holds `d2` and `c4` (pulled forward from T-0007,
  because Cp/Cpk cannot exist without a within-subgroup sigma). T-0007 extends
  it with d3, A2, D3, D4, B3, B4.
- Working method that keeps paying off: **compute from the definition, then
  validate against a source that did not produce the value.** d2 vs NIST's A2
  table; the AD p-value vs Stephens' critical values; scipy vs NIST. Never
  transcribe a constant or coefficient from memory.

## Next actions

1. T-0006 M1d the non-normal path: Box-Cox + the ISO 22514 percentile method.
   `capability()` currently *tells* the user to go there; T-0006 builds the
   destination. Watch for: Box-Cox needs strictly positive data, lambda must be
   reported (not hidden), and the spec limits must be transformed too — the
   classic error is transforming the data but not the limits.
2. T-0007 M2a the remaining control-chart constants + I-MR, X-bar-R, X-bar-S.

## Last done

- 2026-07-14: T-0005 capability indices (Cp/Cpk/Cpm, Pp/Ppk) + d2/c4 constants.
- 2026-07-14: T-0004 normality tests with a caveated verdict.
- 2026-07-14: T-0003 descriptive + robust statistics, NIST StRD validated.
- 2026-07-14: T-0002 repo bootstrap; CI green on GitHub.
