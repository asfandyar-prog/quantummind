# QuantumMind backend — production image.
#
# Base is python:3.12-slim: inside pyproject's requires-python (>=3.10,<3.14)
# and the same minor the CI runner and the local .venv use.

FROM python:3.12-slim

# uv, pinned and copied from its official image — no installer script, no curl,
# and the version is reproducible instead of "whatever latest was that day".
COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /uvx /bin/

# Runtime system libraries:
#   libgomp1 — OpenMP, required by qiskit-aer's simulator and by torch/scipy.
# Everything else in the dependency set ships manylinux wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependency layer first: editing app code must not invalidate the (slow,
# multi-GB) dependency sync. --no-install-project defers the project itself.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Application code. alembic.ini + alembic/ are included so `alembic upgrade head`
# can run as a release command against this same image.
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN uv sync --frozen --no-dev

# Put the venv first on PATH so `uvicorn` / `alembic` resolve without `uv run`.
ENV PATH="/app/.venv/bin:$PATH"

# Non-root. Fixed high UID so the sandbox's --user mapping stays predictable.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# ─────────────────────────────────────────────────────────────────────────────
# SINGLE WORKER — DO NOT ADD --workers OR SWITCH TO GUNICORN WITHOUT READING THIS
#
# Two pieces of shared state are per-process, so a second worker silently
# breaks them:
#
#   1. app/core/cache.py — the LRU response cache is a module-level dict. With
#      N workers you get N independent caches: inconsistent hits and a
#      /api/cache/stats that reports only the worker that answered.
#
#   2. app/core/executor.py — executor_max_concurrency is an asyncio.Semaphore
#      held per process. With N workers the real cap on concurrent sandbox
#      containers becomes N x EXECUTOR_MAX_CONCURRENCY, so the host memory
#      bound is N times looser than configured.
#
# The Redis-backed pieces (LLM concurrency limiter, active-exam state) DO share
# correctly across workers. Only the two above block horizontal scaling.
#
# To scale: move the cache to Redis and make the executor limiter Redis-backed,
# then raise this.
# ─────────────────────────────────────────────────────────────────────────────
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
