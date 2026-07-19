# capstat-api. Built from the repository root:
#     docker build -f apps/api/Dockerfile -t capstat-api .
#
# The build context is the root because the API depends on capstat-core as a uv
# workspace member -- a context of apps/api alone could not see it.

# --- build ------------------------------------------------------------------
FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, in their own layer: they change far less often than the
# source, so editing a statistic does not re-resolve scipy.
COPY pyproject.toml uv.lock ./
COPY packages/capstat-core/pyproject.toml packages/capstat-core/
COPY apps/api/pyproject.toml apps/api/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --package capstat-api --no-dev

# Then the workspace members themselves.
COPY packages/capstat-core packages/capstat-core
COPY apps/api apps/api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package capstat-api --no-dev

# --- runtime ----------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Run as a non-root user: this image serves untrusted uploads (CSV/XLSX parsed
# by pandas/openpyxl), so it should not be root if that parsing ever misbehaves.
RUN useradd --create-home --uid 10001 capstat

WORKDIR /app
COPY --from=build --chown=capstat:capstat /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER capstat
EXPOSE 8000

# Container hosts (Render, Fly) inject the port they want; default to 8000 for
# local compose.
ENV PORT=8000

# Kept in a script rather than inline: the nested quoting an inline python -c
# needs here is the sort of thing that breaks silently and reports "unhealthy"
# for the wrong reason.
COPY --chown=capstat:capstat apps/api/healthcheck.py /app/healthcheck.py
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
    CMD ["python", "/app/healthcheck.py"]

CMD ["sh", "-c", "uvicorn capstat_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
