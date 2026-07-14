# AGENTS.md — capstat

Instructions for coding agents (Claude Code, Codex, and others) working
on this repository.

## Read this first

1. `STATE.md` — current state and the next 1–3 actions.
2. `TASK.md` — task backlog with stable IDs (T-####); single source of
   truth for what to do.
3. `PLAN.md` — master plan: architecture, toolchain decisions with
   rationale, validation sources per statistical method, decisions log.

## Hard rules

- Everything in this repo is **English**: code, comments, identifiers,
  commit messages, docs, steering files.
- **Correctness is the product.** For every statistical method, strict
  order: (1) transcribe the reference values into
  `packages/capstat-core/tests/references/*.yaml` with full citation
  (title, edition, section/page) and double-check them against the
  source — never delegate this transcription to subagents; (2) implement
  with the formula and citation in the docstring; (3) reference test
  green; (4) only then expose via API/UI. A method without a
  reference-validated test does not ship.
- `capstat-core` stays free of web dependencies (numpy + scipy only).
- Do not build anything PLAN.md marks out of scope for v0.1.

## Workflow

- Small increments (1–3 concrete changes). After each increment, state
  the files changed and the verification command run.
- Conventional Commits. A commit that changes code but not
  TASK.md/STATE.md is usually wrong.
- Definition of Done per session: TASK.md moves (Doing→Done), STATE.md
  refreshed (date, status, next actions), tests green with the pass
  count reported, README/docs updated on user-visible changes.

## Quality gates (CI must stay green)

- Python: ruff (lint + format), mypy --strict, pytest with coverage
  >= 95 % on capstat-core.
- TypeScript: eslint, prettier, tsc, vitest; Playwright smoke tests.
- OpenAPI contract: regenerate the TS client in CI; fail on
  `git diff --exit-code` (no frontend/backend drift).
