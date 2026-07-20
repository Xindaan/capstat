# Contributing to capstat

Thanks for your interest in capstat. This project's promise is **auditable
correctness**, so the contribution rules center on validation.

## Ground rules

- Everything in this repository is **English**: code, comments, identifiers,
  commit messages, and docs.
- **Correctness is the product.** A statistical method without a
  reference-validated test does not ship. For every method, follow this
  strict order:
  1. Transcribe the reference values into
     `packages/capstat-core/tests/references/*.yaml` with a full citation
     (title, edition, section/page) and double-check them against the source.
  2. Implement the method with the formula and citation in the docstring.
  3. Make the reference test green.
  4. Only then expose the method via the API or UI.
- `capstat-core` stays free of web dependencies (numpy + scipy only).
- Do not build anything [PLAN.md](PLAN.md) marks out of scope for v0.1.

See [AGENTS.md](AGENTS.md) for the full working model (it applies to human and
AI contributors alike).

## Development setup

```bash
uv sync
uv run pre-commit install
```

## Before you push

Run the same gates CI runs:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=capstat_core
```

All must pass; coverage on capstat-core must stay ≥ 95 %.

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, …). Releases are automated from
  the commit history by [release-please](https://github.com/googleapis/release-please),
  so the type prefix decides both the changelog section and the version bump:
  `fix:` gives a patch, `feat:` a minor, and a `!` or a `BREAKING CHANGE:`
  footer a major. A commit typed wrongly releases wrongly.
- Keep changes small and focused. Each increment should state the files it
  changed and the command used to verify it.
- A commit that changes code but not `TASK.md` / `STATE.md` is usually wrong.

## Reporting bugs and requesting features

Open an issue using the templates under `.github/ISSUE_TEMPLATE/`. For
suspected incorrect statistical results, include the input data, the expected
value, and the authoritative source you are comparing against.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
