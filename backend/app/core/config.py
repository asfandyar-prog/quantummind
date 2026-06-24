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
        extra = "ignore"
        # Ignore unknown keys in .env (e.g. a leftover GROQ_MODEL after the
        # rename to LLM_MODEL) instead of failing to start.
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

