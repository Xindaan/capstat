# STATE.md — capstat

Date: 2026-07-14

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project; v0.1.0 in 3 weeks.

## Status

- Planning phase complete (2026-07-13). All decisions final: name capstat,
  LICENSE © André Leopold, language English, GitHub Xindaan.
- T-0002 repo bootstrap done: uv workspace, ruff/mypy(strict)/pytest with a
  95 % coverage gate, pre-commit, CI matrix 3.11-3.13, community files.
  Repo is live at github.com/Xindaan/capstat (**private** for now; flip to
  public with `gh repo edit --visibility public` when ready).
- T-0003 done: first real statistics shipped. `capstat_core.descriptive` +
  `capstat_core.robust`, validated against all 9 NIST StRD Univariate
  datasets. **152 tests, 100 % coverage**, mypy strict clean on 3.11-3.13.
- The reference-test harness now exists (`tests/references/*.yaml` +
  `conftest.py` loader with per-statistic tolerances). T-0004 onward should
  reuse it rather than invent a second pattern.
- Only open decision: demo hosting (T-0019, due Week 3).

## Next actions

1. T-0004 M1b normality tests: Anderson-Darling + Shapiro-Wilk, with explicit
   reporting when normality is rejected (feeds the non-normal capability path
   in T-0006). Reference values from published examples / R `shapiro.test`.
2. T-0005 M1c capability indices Cp/Cpk/Pp/Ppk/Cpm.

## Last done

- 2026-07-14: T-0003 descriptive + robust statistics, NIST StRD validated.
- 2026-07-14: T-0002 repo bootstrap; CI green on GitHub (3.11, 3.12, 3.13).
- 2026-07-13: T-0001 kickoff plan confirmed; AGENTS.md + project CLAUDE.md.
- 2026-07-13: PLAN.md (master plan) created; toolchain decided.
