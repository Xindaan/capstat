# PLAN.md — capstat

Status: confirmed 2026-07-13. Name: **capstat** (final).
This file is the handoff-ready master plan: any agent
(Claude Code, Codex, human) should be able to continue the project from
TASK.md + STATE.md + this file alone.

## Vision

A rigorously validated statistical process control (SPC), process
capability, and measurement system analysis (MSA) toolkit — a trustworthy,
MIT-licensed open-source alternative to expensive quality-engineering
software. Differentiator: **correctness you can audit** — every statistical
result validated against published reference values.

## Non-negotiable principles

1. **Correctness is the product.** A method without a reference-validated
   test does not ship.
2. **The core is a standalone library.** `capstat-core` has zero web
   dependencies and is independently PyPI-publishable. The API server
   merely wraps it.
3. **Small, verifiable increments.** Each change: files changed + how
   verified (command/test).
4. **Plan before scaffold.** Structure and milestones reviewed before
   building.

## Architecture

```
capstat/
├── packages/capstat-core/          # pure stats library, PyPI-ready
│   ├── src/capstat_core/
│   │   ├── capability/             # Cp, Cpk, Pp, Ppk, Cpm, non-normal path
│   │   ├── control_charts/         # I-MR, XbarR, XbarS, EWMA, CUSUM, rules, constants
│   │   ├── msa/                    # Gage R&R (ANOVA + avg-range), bias, linearity, stability
│   │   └── distributions/          # normality tests, Box-Cox, percentile method
│   ├── tests/references/           # reference values as YAML (see below)
│   └── pyproject.toml
├── apps/
│   ├── api/                        # FastAPI, CSV/XLSX ingestion, stateless compute
│   └── web/                        # Next.js App Router; generated TS client in lib/api-client/
├── docs/                           # mkdocs-material site
├── .github/workflows/              # ci.yml, release.yml
├── docker-compose.yml              # local stack: api + web
└── LICENSE, README, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY,
    AGENTS.md, CLAUDE.md, TASK.md, STATE.md, PLAN.md
```

Contract: the FastAPI OpenAPI schema is the single source of truth; the TS
client is generated from it in CI with a drift check (`git diff
--exit-code` after regeneration).

## Toolchain decisions (with rationale)

Python:
- **uv workspace** — native monorepo support (core + api, one lockfile),
  much faster than Poetry.
- **ruff** (lint + format) — replaces black/isort/flake8 with one tool.
- **mypy --strict** on core and api.
- **pytest + pytest-cov**, coverage gate >= 95 % on capstat-core.
- **Core deps: numpy + scipy only.** statsmodels deliberately dropped
  (deviation from kickoff brief): the balanced two-way ANOVA for Gage R&R
  is closed-form; fewer deps keep the PyPI asset light. pandas/openpyxl
  live only in apps/api (ingestion).
- Python floor **3.11**, CI matrix 3.11–3.13.

TypeScript:
- **Next.js App Router + TypeScript strict + Tailwind.**
- **ECharts** for charting — `markLine`/`markArea` natively model control
  limits and zones, canvas performance for large series, Apache-2.0, and
  the SVG renderer yields vector charts for the PDF report (decisive
  over visx/Recharts).
- **openapi-typescript + openapi-fetch** — zero-runtime typed client.
- eslint (flat config), prettier, vitest, Playwright smoke tests.

Repo-wide:
- **release-please** — monorepo-aware, Conventional Commits -> changelog
  PRs -> tags; simpler than semantic-release for mixed Python/JS.
- **pre-commit** framework: ruff, ruff-format, mypy, prettier, eslint.
- **mkdocs-material + mkdocstrings** — Python-native docs, API reference
  from docstrings, LaTeX for the methods reference.
- **PDF report v0.1:** print-optimized report route with vector SVG charts
  + browser print-to-PDF. Server-side PDF endpoint is roadmap (WeasyPrint
  cannot run JS; Playwright-in-container is heavy). Deliberate trim of
  the kickoff brief.

## Statistical scope and validation sources

Reference tests live in `packages/capstat-core/tests/references/*.yaml`:
`{id, method, source: {title, edition, section/page}, input (inline or
dataset file), expected: {name: value}, tolerance (abs/rel), notes}`.
Transcription of expected values from sources is a critical-accuracy task:
never delegate to subagents; double-check against the source.

Tier 1 — Process capability (Week 1):
- Descriptive + robust statistics — NIST StRD "Univariate Summary
  Statistics" (certified to 15 digits).
- Anderson-Darling — D'Agostino & Stephens (1986) tables; scipy cross-check.
- Shapiro-Wilk — Royston AS R94; validate against published R
  `shapiro.test` values.
- Cp/Cpk/Pp/Ppk — Montgomery, *Introduction to Statistical Quality
  Control*, worked examples; AIAG SPC manual examples. Short-term vs
  long-term variation stated explicitly in the API.
- Cpm — Chan/Cheng/Spiring (1988) formulation, textbook example.
- Non-normal path — Box-Cox (NIST/SEMATECH e-Handbook; scipy cross-check)
  + ISO 22514-4 percentile method. Documented decision path, never a
  silent normality assumption.

Tier 2 — Control charts (Week 1–2):
- Constants d2, d3, c4, A2, D3, D4, B3, B4 — Montgomery Appendix VI /
  ASTM E2587 tables.
- I-MR, X-bar-R, X-bar-S — Montgomery worked examples; NIST/SEMATECH
  e-Handbook 6.3.
- EWMA — Montgomery example (lambda 0.1, L 2.7); NIST 6.3.2.4.
- CUSUM (tabular) — Montgomery example; NIST 6.3.2.3.
- Nelson rules (Nelson 1984, JQT) + Western Electric rules (WE Handbook
  1956) — constructed sequences + published example data.

Tier 3 — MSA / Gage R&R (Week 2–3, credibility centerpiece):
- Gage R&R via ANOVA method AND average-and-range method — AIAG MSA-4
  worked examples (10 parts x 3 appraisers x 3 trials); exact match on
  %Contribution, %Study Variation, ndc. Handle negative variance
  components explicitly (clamp-to-zero, reported).
- Bias, linearity, stability — AIAG MSA-4 worked examples.

Out of scope for v0.1 (roadmap only): acceptance sampling (AQL/ISO 2859),
multi-user auth, persistence/database, server-side PDF endpoint.

## Milestones

- **Week 1 — Trustworthy core** (T-0002..T-0009): bootstrap + green CI,
  capability + control charts, all reference-validated. Citable library
  on its own.
- **Week 2 — Product surface** (T-0010..T-0011): FastAPI + OpenAPI +
  typed TS client; Next.js upload + capability dashboard + charts.
- **Week 3 — MSA + ship** (T-0012..T-0017): Gage R&R, PDF report, deploy
  demo, docs complete, v0.1.0 via release-please.

Task backlog with acceptance criteria: TASK.md. Current state: STATE.md.

## Working model (agents)

- **AGENTS.md** at repo root is the agent-agnostic instruction file
  (Codex convention); CLAUDE.md references it. Both exist since
  2026-07-13.
- Every task in TASK.md is self-contained: acceptance criteria + the
  verification command an agent must run.
- Per statistical method, strict order: (1) reference YAML transcribed
  and double-checked, (2) implementation with formula + citation in the
  docstring, (3) test green, (4) only then API/UI exposure.
- Conventional Commits; small focused increments; each increment reports
  files changed + verification command.
- Orchestration: expensive model plans/reviews/synthesizes; volume and
  boilerplate work goes to cheap subagents or Codex. Exception: reference
  value transcription and statistical formula review stay with the
  orchestrator.
- Definition of Done per session: TASK.md moves, STATE.md refreshed,
  README/docs updated on user-visible changes, tests green with pass
  count reported.

## Decisions log

- 2026-07-13 **Language: English** for code, comments, identifiers, docs,
  commits, and steering files (overrides the private ~/src convention;
  to be documented in project CLAUDE.md/AGENTS.md at bootstrap).
- 2026-07-13 statsmodels dropped from core deps (closed-form ANOVA).
- 2026-07-13 ECharts over visx/Recharts (control-chart overlays + SVG
  export for PDF).
- 2026-07-13 PDF v0.1 = print route, server-side PDF deferred to roadmap.
- 2026-07-13 uv / ruff / mypy strict / release-please / mkdocs-material
  (rationale above).
- 2026-07-13 PyPI names checked: capstat, procapy, openspc, capstat-core
  all free. GitHub: no meaningful collision for capstat; procapy has an
  existing repo of that exact name; openspc collides with the SNES SPC
  audio ecosystem.
- 2026-07-13 GitHub account: Xindaan (repo will live under
  github.com/Xindaan/capstat unless decided otherwise).
- 2026-07-13 **Name: capstat** confirmed by the maintainer ("Capsat" in
  chat was a typo, resolved explicitly; capsat would collide with
  CubeSat projects on GitHub).
- 2026-07-13 **Copyright holder for the MIT LICENSE: André Leopold**
  (authoritative spelling, including the accent).
- 2026-07-13 AGENTS.md and project CLAUDE.md created ahead of bootstrap
  (handover from the planning session to the implementing model).

## Open decisions

1. Demo hosting (Week 3, T-0019) — recommendation Vercel Hobby (web,
   free) + Render free tier (API container; sleeps when idle, cold start
   up to ~1 min — acceptable for a demo). Fly.io alternative costs a few
   EUR/month. Decision can wait until Week 3.
