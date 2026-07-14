# TASK.md — capstat

## Doing

<!-- max 3 -->

## Next

- T-0004 M1b Normality tests: Anderson-Darling, Shapiro-Wilk; clear reporting
  on non-normality. Reference values from published examples / R comparison
  values.
- T-0005 M1c Capability indices Cp/Cpk/Pp/Ppk/Cpm; short-term vs long-term
  variation stated explicitly. Validated against Montgomery and AIAG SPC
  examples.
- T-0006 M1d Non-normal path: Box-Cox transformation + ISO 22514 percentile
  method; documented decision path instead of a silent normality assumption.
- T-0007 M2a Control-chart constants (d2, d3, c4, A2, D3, D4, B3, B4; source:
  Montgomery Appendix / ASTM E2587) + I-MR, X-bar-R, X-bar-S.
- T-0008 M2b EWMA + CUSUM, validated against Montgomery / NIST Handbook
  examples.
- T-0009 M2c Nelson rules + Western Electric rules, tested with constructed
  sequences + published example data.
- T-0010 M3 FastAPI service: compute endpoints (descriptive, capability,
  control charts), CSV/XLSX ingestion, OpenAPI schema, TS client generation
  with a drift check in CI.

## Backlog

- T-0011 M4 Next.js app: upload (CSV/XLSX), capability dashboard, histogram
  with spec limits + fitted distribution, control charts with violation
  markers (ECharts).
- T-0012 M5a Gage R&R: ANOVA method + average-and-range method;
  %Contribution, %Study Variation, ndc. Validated against the AIAG MSA-4
  worked examples (core credibility).
- T-0013 M5b Bias, linearity, stability.
- T-0014 M6a PDF report: print-optimized report route with vector charts
  (ECharts SVG renderer); server PDF as roadmap.
- T-0015 M6b docker-compose (api + web) + public demo deployment
  (Vercel + Fly.io/Render).
- T-0016 M6c Docs site: mkdocs-material + mkdocstrings; Getting Started,
  method reference (formula + citation per method), API reference.
- T-0017 M6d v0.1.0 release via release-please, README polish (badges,
  screenshots, quickstart, demo link).
- T-0018 Roadmap (explicitly NOT v0.1): acceptance sampling (AQL/ISO 2859),
  multi-user auth, persistence/database, server PDF.
- T-0020 CI: `actions/checkout@v4` and `astral-sh/setup-uv@v6` still target the
  deprecated Node.js 20 runtime (GitHub forces them onto Node 24 and warns on
  every run). Bump to the Node-24 native majors when released; dependabot
  (github-actions, weekly) will likely raise this PR on its own. Cosmetic
  today, breaking once GitHub drops the shim.
- T-0019 Decide demo hosting (due Week 3, before T-0015): recommendation
  Vercel Hobby (web, free) + Render Free (API container, sleeps when idle);
  alternative Fly.io (a few EUR/month). Needs one account each (GitHub login
  is enough).

## Done

- T-0003 (2026-07-14) M1a Descriptive statistics + robust variants.
  `capstat_core.descriptive` (mean, variance, std_dev, skewness, kurtosis,
  lag1_autocorrelation, `describe` -> immutable `DescriptiveSummary`) and
  `capstat_core.robust` (median, mad, iqr, trimmed_mean, winsorized_mean).
  Validated against all 9 NIST StRD Univariate datasets (archived verbatim
  in-tree with their certified-value headers); robust estimators validated by
  hand-computed values + scipy cross-check. 152 tests, 100 % coverage.
  Findings worth keeping:
  * The one-pass variance returns a *negative* variance (-0.032) on NumAcc4.
    All centered moments therefore use a two-pass algorithm, pinned by a
    regression test plus a shift-stability test across the whole family.
  * The residual 5.6e-09 error on NumAcc4 is a float64 *input representation*
    floor, not an algorithmic one (proven in exact rational arithmetic); the
    loosened tolerance there is justified in the reference YAML.
  * Bug found and fixed in the T-0002 config: `mypy python_version = "3.11"`
    breaks against numpy >= 2.5 stubs (PEP 695) and was masking two real
    strict-mode errors. mypy now infers the version from the interpreter.
- T-0002 (2026-07-14) M0 Repo bootstrap: git init; MIT LICENSE (© André
  Leopold); root README with CI/license/python badges; CONTRIBUTING,
  CODE_OF_CONDUCT, SECURITY; `.github/` (CI workflow, dependabot, issue/PR
  templates); uv workspace with `capstat-core` (numpy+scipy, hatchling,
  py.typed); shared ruff/mypy(strict)/pytest/coverage config; pre-commit
  (local hooks via `uv run`); TASK/STATE converted to English. Green locally:
  ruff, ruff-format, mypy strict, pytest 1/1, coverage 100 %.
- T-0001 (2026-07-13) Kickoff plan confirmed: name capstat ("Capsat" typo
  resolved explicitly), LICENSE name André Leopold, language English, GitHub
  account Xindaan; hosting split out into T-0019.
