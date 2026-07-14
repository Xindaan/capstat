# STATE.md — capstat

Date: 2026-07-14

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project; v0.1.0 in 3 weeks.

## Status

- Planning phase complete (2026-07-13). All decisions final: name capstat,
  LICENSE © André Leopold, language English, GitHub Xindaan.
- Repo live at github.com/Xindaan/capstat (**private** for now; flip with
  `gh repo edit --visibility public` when ready). CI green on 3.11/3.12/3.13.
- Week 1 core is half done: T-0002 bootstrap, T-0003 descriptive + robust
  statistics, T-0004 normality tests. **193 tests, 100 % coverage**, mypy
  strict clean.
- The reference-test pattern is established and should be reused, not
  reinvented: `tests/references/*.yaml` (sources, certified values,
  per-statistic tolerances with a written justification) + the `conftest.py`
  loader. Two YAMLs exist: `nist_strd_univariate.yaml`, `normality.yaml`.
- Recurring lesson from both statistics tasks: the *validation design* is the
  hard part, not the formula. Cross-check against a source that did not produce
  the value being checked (scipy vs NIST vs CRAN nortest vs published R
  output), and never transcribe a coefficient from memory.
- Only open decision: demo hosting (T-0019, due Week 3).

## Next actions

1. T-0005 M1c capability indices Cp/Cpk/Pp/Ppk/Cpm, validated against
   Montgomery and AIAG SPC worked examples. Short-term vs long-term variation
   must be explicit in the API — this is the single most common way capability
   software misleads people. `assess_normality` (T-0004) is the gate that
   decides whether these indices may be used at all.
2. T-0006 M1d the non-normal path (Box-Cox + ISO 22514 percentile method),
   which is what T-0005 must hand off to when normality is rejected.

## Last done

- 2026-07-14: T-0004 normality tests (Anderson-Darling incl. the p-value scipy
  lacks, Shapiro-Wilk, and a caveated `assess_normality` verdict).
- 2026-07-14: T-0003 descriptive + robust statistics, NIST StRD validated.
- 2026-07-14: T-0002 repo bootstrap; CI green on GitHub.
- 2026-07-13: T-0001 kickoff plan confirmed; PLAN.md master plan.
