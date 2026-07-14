# STATE.md — capstat

Date: 2026-07-14

## Goal

Reference-validated SPC / capability / MSA library (Python) + FastAPI +
Next.js frontend as a professional MIT open-source project; v0.1.0 in 3 weeks.

## Status

- Planning phase complete (2026-07-13). All decisions final: name capstat,
  LICENSE © André Leopold, language English, GitHub Xindaan.
- PLAN.md = handoff-ready master plan; AGENTS.md + CLAUDE.md exist.
- T-0002 repo bootstrap done: uv workspace with `capstat-core`, shared
  ruff/mypy(strict)/pytest/coverage config, pre-commit, `.github/` CI
  workflow (matrix 3.11–3.13), community files. Green locally (ruff,
  ruff-format, mypy, pytest 1/1, coverage 100 %). Not yet pushed to GitHub,
  so the CI badge is pending its first run.
- Only open decision: demo hosting (T-0019, due Week 3).

## Next actions

1. T-0003 M1a descriptive + robust statistics in capstat-core, validated
   against NIST StRD "Univariate Summary Statistics".
2. Push to github.com/Xindaan/capstat and confirm the CI workflow goes green
   on the remote (turns the README badge green).

## Last done

- 2026-07-14: T-0002 repo bootstrap (see TASK.md Done for the full list).
- 2026-07-13: T-0001 kickoff plan confirmed (name, LICENSE name, language,
  GitHub account); AGENTS.md + project CLAUDE.md created.
- 2026-07-13: PLAN.md (master plan) created; PyPI/GitHub name checks;
  milestone plan + toolchain decided.
