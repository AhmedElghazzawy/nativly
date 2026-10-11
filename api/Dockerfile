# syntax=docker/dockerfile:1

# Build context: the repo root (so curriculum content in content/ can be baked in).
# ---- build: resolve deps into a venv with uv, using the lockfile ----
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Deps first, in their own layer, so code changes don't reinstall everything.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=api/uv.lock,target=uv.lock \
    --mount=type=bind,source=api/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

COPY api/ .
COPY content/ ./content/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---- runtime: no uv, no build cache, non-root ----
FROM python:3.12-slim

RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER app

# Hosts like Render inject PORT; 8000 is the local default.
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')"]
CMD ["./scripts/start.sh"]
