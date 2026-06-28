from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional
# pydantic_settings is an extension of Pydantic specifically for config.
# It reads environment variables and validates their types automatically.
# If a required variable is missing, it raises an error BEFORE your app
# starts — not when a request comes in. Fail fast is always better.

from functools import lru_cache
# lru_cache = "Least Recently Used" cache.
# We use it here to ensure config is only loaded ONCE.
# Without it, every function that calls get_settings() would re-read
# the .env file from disk — wasteful and slow.


class Settings(BaseSettings):
    """
    All configuration for QuantumMind backend.

    Pydantic reads these values from environment variables automatically.
    The variable name in .env must match the field name here exactly.
    Example: GROQ_API_KEY in .env → groq_api_key field here.
    Pydantic handles the uppercase → lowercase conversion for you.
    """

    # ── Groq ─────────────────────────────────────────────────
    groq_api_key: Optional[str] = None
    # Optional now: required only when LLM_PROVIDER=groq (enforced by the
    # validator below). Prod (vLLM) starts without a Groq key.
    # Pydantic looks for GROQ_API_KEY in your .env file.

    # ── LLM seam ──────────────────────────────────────────────
    # One client (ChatOpenAI) serves all providers; the provider only
    # selects a base URL + how the API key is resolved. See app/core/llm.py.
    llm_provider: str = "groq"                       # groq | openai | vllm
    llm_model: str = "llama-3.1-8b-instant"          # single source of truth for the model
    llm_router_model: str = "llama-3.1-8b-instant"   # cheap model pinned for routing
    llm_base_url: Optional[str] = None               # overrides per-provider default; required for vllm
    llm_api_key: Optional[str] = None                # key for openai/vllm; groq falls back to groq_api_key

    # ── LLM resilience (Phase 2) ──────────────────────────────
    llm_timeout_seconds: float = 30.0   # per-call timeout (client + asyncio backstop)
    llm_max_attempts: int = 4           # retry ceiling, including the first attempt
    llm_retry_base_delay: float = 0.5   # exponential backoff base (seconds)
    llm_retry_max_delay: float = 8.0    # backoff cap (seconds)
    llm_token_budget_per_day: int = 0   # soft daily token budget (0 = unlimited; warn-only)
    llm_max_concurrency: int = 8             # global in-flight LLM calls (shared via Redis)
    llm_acquire_timeout_seconds: float = 20.0  # max wait for a slot before LLMBusy
    llm_limiter_stale_seconds: float = 180.0   # prune window: a dead worker's slot self-expires
    grading_backfill_interval_seconds: float = 15.0  # backfill worker sweep cadence
    grading_backfill_batch: int = 50                 # max stuck turns reconciled per sweep

    # ── App ───────────────────────────────────────────────────
    app_env: str = "development"
    # "development" enables detailed error messages and auto-reload.
    # "production" disables these for security.

    frontend_url: str = "http://localhost:5173"
    # Your React app's URL. Used to configure CORS.
    # CORS = Cross-Origin Resource Sharing.
    # Without this, browsers block frontend → backend requests
    # because they're on different ports (5173 vs 8000).

    # ── ChromaDB ──────────────────────────────────────────────
    chroma_path: str = "./data/chroma"
    # Where ChromaDB stores its vector files on disk.
    # This folder is created automatically when you first upload a doc.

    teacher_password: str = "quantum2026"
    # Password for teacher mode. Change this in production!

    # ── Database & cache (Phase 1) ────────────────────────────
    # Single connection string — only this changes for managed vs self-hosted.
    # Uses psycopg 3 (postgresql+psycopg://) as the one Postgres driver everywhere.
    database_url: str = "postgresql+psycopg://quantummind:quantummind@localhost:5432/quantummind"
    redis_url: str = "redis://localhost:6379/0"   # shared active-exam state
    db_pool_size: int = 10                          # async engine pool size
    db_max_overflow: int = 5                        # pool overflow ceiling
    exam_state_ttl_seconds: int = 86400             # Redis safety TTL (Postgres is source of truth)

    @model_validator(mode="after")
    def _validate_provider(self):
        """Fail fast at startup if the selected provider is misconfigured."""
        provider = self.llm_provider
        if provider == "groq":
            if not (self.llm_api_key or self.groq_api_key):
                raise ValueError("LLM_PROVIDER=groq requires GROQ_API_KEY (or LLM_API_KEY)")
        elif provider == "openai":
            if not self.llm_api_key:
                raise ValueError("LLM_PROVIDER=openai requires LLM_API_KEY")
        elif provider == "vllm":
            if not self.llm_base_url:
                raise ValueError("LLM_PROVIDER=vllm requires LLM_BASE_URL")
        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (use groq|openai|vllm)")
        return self

    class Config:
        # Tell Pydantic where to find the .env file.
        # It looks for this file relative to where you RUN the app from.
        # Since you run `uvicorn` from the backend/ folder, it finds
        # backend/.env correctly.
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "forbid"
        # Strict: an unknown/misspelled key in .env crashes at startup rather
        # than silently falling back to a default. Keep .env keys in sync with
        # the fields above (e.g. use LLM_MODEL, not the old GROQ_MODEL).
        # Always specify encoding — prevents issues on Windows
        # where the default encoding can vary.


@lru_cache()
def get_settings() -> Settings:
    """
    Returns the Settings instance. Cached after first call.

    Why a function instead of just Settings() directly?
    Because lru_cache only works on functions, not class instantiation.
    Also makes it easy to override in tests:
        app.dependency_overrides[get_settings] = lambda: test_settings

    Usage in any other file:
        from app.core.config import get_settings
        settings = get_settings()
        print(settings.groq_api_key)
    """
    return Settings()


# ── One convenience instance ──────────────────────────────────
# This lets other files do:
#   from app.core.config import settings
# instead of:
#   from app.core.config import get_settings; settings = get_settings()
# Both work — the shorthand is just cleaner for most uses.
settings = get_settings()

