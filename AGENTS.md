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
- **`apps/web` runs Next.js 16, which diverges from most training data** —
  App Router APIs, conventions and file layout have all moved. Before writing
  frontend code, read the relevant guide under
  `apps/web/node_modules/next/dist/docs/` (it ships inside the package, and is
  not visible from the repo root) and heed the deprecation notices. Next
  itself drops an `AGENTS.md` and a `CLAUDE.md` into `apps/web` whenever it
  detects an agent; those are gitignored (T-0050) and unmaintained — this
  bullet is the version that is kept current.
- **Every claim carries its evidence, where the claim is made.** A statement
  about this repository — what the suite reports, what version is installed,
  what a source says, what an agent changed — is stated together with the
  command and its output, the `file:line`, or the citation that establishes
  it, in the conversation, commit message, TASK.md or STATE.md that carries
  the claim. What was not checked is labelled as unchecked or as an inference
  instead of being asserted; "measured: `uv sync --frozen` succeeds either way"
  is the standard, not "should be fine". A claim later found wrong is
  corrected in the file that made it (see the 0.2.0/0.2.1 correction in
  TASK.md), not quietly dropped.
- **A release is verified against the published artefact, not against the
  green run.** An upload to an index is permanent and a version number can
  never be reused, so before the publish is approved: the tag stamps the
  version in every file that carries it (both `pyproject.toml` files,
  `__version__`, `uv.lock`), a build at that tag produces the expected sdist
  and wheel, and the version is still absent from the index. After it: the
  index's own metadata reports the version, and a clean environment installs
  it and exercises the release's new behaviour — or, when a release adds no
  new symbol, compares the installed files against the tag byte for byte,
  because that comparison is then the only thing that proves which code
  shipped. A green CI run is not that evidence. Done this way for 0.3.0 and
  0.3.1; see TASK.md.
- **The rules in this file are the maintainer's, not the agent's.** Do not
  reword, soften, restructure or relocate "Read this first", "Workflow" or
  "Quality gates", nor the Definition of Done that PLAN.md restates, unless
  the maintainer asks for that change in the task at hand — propose it in the
  conversation instead. These sections mirror conventions shared across the
  maintainer's repositories, so a local rewrite forks them silently. On
  2026-09-13 an agent did exactly that, uncommitted and unasked, in three
  repositories at once: "a commit that changes code but not TASK.md/STATE.md
  is usually wrong" became optional, and documentation work was excused from
  the test suites (T-0085).

## Workflow

- Small increments (1–3 concrete changes). After each increment, state
  the files changed and the verification command run.
- Conventional Commits. A commit that changes code but not
  TASK.md/STATE.md is usually wrong.
- **A commit touching only the project's own steering and rule files is
  `chore`, never `docs`** -- `TASK.md`, `STATE.md`, `PLAN.md`, `AGENTS.md`,
  `CLAUDE.md`, `.claude/`. `release-please-config.json` makes `feat`, `fix`,
  `docs`, `test`, `refactor` and `perf` visible, and a visible type opens a
  release pull request; `chore` and `ci` are hidden and do not. These files are
  how the project runs itself, not something anyone reads to *use* capstat, so
  cutting a version for them does not merely add noise -- it loops: merging a
  release writes STATE.md, that commit opens the next release PR, merging that
  one writes STATE.md again, and it never settles. Measured 2026-09-21: #44 came
  from a commit changing only TASK.md and STATE.md, #45 from one changing only
  STATE.md.

  The test is who the change is for, not where the file sits. `docs` is for
  documentation someone reads to use the project -- README, `docs/`, docstrings,
  CLI help -- and that still earns a release. A commit that changes code *and*
  steering files keeps the code's type, as before.
- Definition of Done per session: TASK.md moves (Doing→Done), STATE.md
  refreshed (date, status, next actions), tests green with the pass
  count reported, README/docs updated on user-visible changes.

## Quality gates (CI must stay green)

- Python: ruff (lint + format), mypy --strict, pytest with coverage
  >= 95 % on capstat-core.
- TypeScript: eslint, prettier, tsc, vitest; Playwright smoke tests.
- OpenAPI contract: regenerate the TS client in CI; fail on
  `git diff --exit-code` (no frontend/backend drift).
