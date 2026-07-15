# capstat-api

Stateless FastAPI service wrapping [`capstat-core`](../../packages/capstat-core).
It exposes every reference-validated statistic as an HTTP endpoint and adds
CSV/XLSX ingestion. The core library stays web-free (numpy + scipy only);
pandas/openpyxl live here.

## Run

```bash
uv run uvicorn capstat_api.main:app --reload
```

Interactive docs at `http://127.0.0.1:8000/docs`.

## Contract

The OpenAPI schema is the single source of truth. `apps/api/openapi.json` is
committed and checked for drift in CI:

```bash
uv run python -m capstat_api.export_openapi --check
```
