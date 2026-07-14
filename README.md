# capstat

[![CI](https://github.com/Xindaan/capstat/actions/workflows/ci.yml/badge.svg)](https://github.com/Xindaan/capstat/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

**Reference-validated statistical process control, process capability, and
measurement system analysis — correctness you can audit.**

capstat is a trustworthy, MIT-licensed alternative to expensive
quality-engineering software. Its differentiator is verifiable correctness:
every statistical result is validated against published reference values
(NIST StRD, Montgomery, AIAG manuals, ISO 22514).

> **Status:** early development (v0.1 in progress). The core statistics
> library is being built method by method; the API and web app follow. See
> [PLAN.md](PLAN.md) for the roadmap and [TASK.md](TASK.md) for the backlog.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) (Python 3.11+ is fetched
automatically).

```bash
git clone https://github.com/Xindaan/capstat.git
cd capstat
uv sync                 # create the environment and install all workspace members
uv run pytest           # run the test suite
```

Install the standalone core library from source:

```bash
uv pip install ./packages/capstat-core
```

## Usage

The public API is populated milestone by milestone. Available today:
descriptive statistics and robust (outlier-resistant) estimators.

```python
from capstat_core import describe, mad, median, trimmed_mean

measurements = [10.1, 10.3, 9.8, 10.0, 10.2, 9.9, 10.4, 25.0]  # one bad reading

summary = describe(measurements)
summary.mean        # 11.9625   -- dragged up by the one bad reading
summary.std_dev     # 5.2717    -- and so is the spread
summary.skewness    # skewness / kurtosis for a normality gut-check
summary.lag1_autocorrelation  # serial correlation: are the data independent?

# Robust alternatives, which the outlier barely moves:
median(measurements)              # ~10.15
trimmed_mean(measurements, 0.125) # 10.15
mad(measurements)                 # ~0.2965 -- a sigma estimate, scaled for
                                  # normal data, vs. std_dev's 5.2717
```

`describe` returns an immutable `DescriptiveSummary` with `n`, `mean`,
`variance`, `std_dev`, `minimum`, `maximum`, `range`, `median`, `q1`, `q3`,
`iqr`, `skewness`, `kurtosis`, and `lag1_autocorrelation`.

**On accuracy.** The variance and every other centered moment use a two-pass
algorithm. This is not pedantry: on the NIST `NumAcc4` dataset the textbook
one-pass formula returns a *negative* variance. capstat reproduces the NIST
certified values to the limit of double precision — see
[the reference suite](packages/capstat-core/tests/references/) for the sources,
the certified numbers, and a written justification for every tolerance.

## Configuration

capstat-core is configuration-free. The API server and web app (later
milestones) are configured via environment variables, documented when they
land.

## Troubleshooting

- **`uv: command not found`** — install uv per the
  [official instructions](https://docs.astral.sh/uv/getting-started/installation/).
- **Wrong Python version** — uv manages an isolated interpreter; you do not
  need a system Python 3.11+. Run everything through `uv run`.

## Development

```bash
uv sync                       # install dev toolchain
uv run pre-commit install     # enable pre-commit hooks
uv run ruff check .           # lint
uv run ruff format .          # format
uv run mypy                   # type-check (strict)
uv run pytest --cov=capstat_core   # tests with coverage
```

Quality gates (enforced in CI): ruff (lint + format), mypy `--strict`, and
pytest with ≥ 95 % coverage on capstat-core. See [AGENTS.md](AGENTS.md) for
the full contributor workflow and [CONTRIBUTING.md](CONTRIBUTING.md) to get
started.

## Architecture

capstat is a uv-managed monorepo:

```
packages/capstat-core/   # pure numpy+scipy stats library, PyPI-publishable
apps/api/                # FastAPI compute service (wraps the core)   [later]
apps/web/                # Next.js dashboard                          [later]
docs/                    # mkdocs-material site                       [later]
```

The core carries no web dependencies and can be used on its own. The API
exposes it over HTTP; its OpenAPI schema is the single source of truth for the
generated TypeScript client. Details and the rationale for every toolchain
choice are in [PLAN.md](PLAN.md).

## License

[MIT](LICENSE) © André Leopold
