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

The public API is populated milestone by milestone. Today the core package
exposes its version; the first statistical methods (descriptive statistics,
normality tests, capability indices) land in Week 1.

```python
import capstat_core

print(capstat_core.__version__)
```

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
