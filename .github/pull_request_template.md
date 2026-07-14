## Summary

<!-- What does this change do and why? -->

## Changes

<!-- Bullet the concrete changes: files/modules touched. -->

## Verification

<!-- The exact command(s) you ran and their result (e.g. pass count). -->

```
uv run pytest --cov=capstat_core
```

## Checklist

- [ ] Follows Conventional Commits
- [ ] For any statistical method: reference YAML added/updated with full
      citation, formula + citation in the docstring, reference test green
- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] `uv run mypy` passes (strict)
- [ ] `uv run pytest` passes; coverage on capstat-core ≥ 95 %
- [ ] `TASK.md` / `STATE.md` updated
- [ ] Docs updated for user-visible changes
