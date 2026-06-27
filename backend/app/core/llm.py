# ── app/core/llm.py ───────────────────────────────────────────
# The single seam for all model access. No module outside this file may
# import an LLM SDK — every agent calls chat()/stream() here.
#
# One client class (ChatOpenAI) serves every provider; the provider only
# selects a base URL and how the API key is resolved. Because Groq, OpenAI,
# and self-hosted vLLM all speak the OpenAI chat-completions protocol, the
# dev path (Groq) and the prod path (vLLM) are the *same* client path —
# only base URL + model + key differ by config.

import asyncio
import random
from typing import AsyncIterator, Optional

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.core.config import settings


# ── Typed seam errors ─────────────────────────────────────────
class LLMError(Exception):
    """Base class for LLM seam errors."""


class LLMUnavailable(LLMError):
    """A transient failure that persisted past the retry ceiling (429/timeout/5xx).

    The exam answer path catches this to persist the answer and degrade gracefully
    (Phase 2 §5); other callers surface it as their normal error path.
    """


# Per-call-type default temperatures. These reproduce the exact values that
# were previously hardcoded in each agent's get_llm(), so behavior does not
# drift after the refactor.
CALL_TEMPERATURES: dict[str, float] = {
    "route":         0.0,
    "theory":        0.7,
    "code":          0.1,
    "rag_generate":  0.3,
    "rag_grade":     0.0,
    "lesson_plan":   0.2,
    "lesson_step":   0.5,
    "lesson_grade":  0.0,
    "exam_question": 0.4,
    "exam_grade":    0.0,
}
DEFAULT_TEMPERATURE = 0.3

# Per-provider base URL defaults. settings.llm_base_url overrides these.
_PROVIDER_BASE_URLS: dict[str, Optional[str]] = {
    "groq":   "https://api.groq.com/openai/v1",  # Groq's OpenAI-compatible endpoint
    "openai": None,                              # openai SDK default (api.openai.com)
    "vllm":   None,                              # must be set via LLM_BASE_URL
}


def _resolve_base_url() -> Optional[str]:
    if settings.llm_base_url:
        return settings.llm_base_url
    return _PROVIDER_BASE_URLS.get(settings.llm_provider)


def _resolve_api_key() -> str:
    if settings.llm_provider == "groq":
        return settings.llm_api_key or settings.groq_api_key or ""
    if settings.llm_provider == "vllm":
        # vLLM usually ignores the key but the OpenAI client requires a value.
        return settings.llm_api_key or "EMPTY"
    return settings.llm_api_key or ""


def _resolve_params(
    call_type: Optional[str],
    temperature: Optional[float],
    model: Optional[str],
) -> tuple[str, float]:
    if temperature is not None:
        temp = temperature
    else:
        temp = CALL_TEMPERATURES.get(call_type, DEFAULT_TEMPERATURE)
    return (model or settings.llm_model), temp


def _build_client(model: str, temperature: float, max_tokens: Optional[int],
                  timeout: Optional[float] = None):
    # Lazy import keeps the LLM SDK out of import time and contained to this module.
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        api_key=_resolve_api_key(),
        base_url=_resolve_base_url(),
    )


def _resolve_timeout(call_type: Optional[str]) -> float:
    # Global per-call timeout for now; per-call-type overrides can be added later.
    return settings.llm_timeout_seconds


def _is_transient(exc: BaseException) -> bool:
    """True for errors worth retrying: timeouts, dropped connections, 429, 5xx."""
    if isinstance(exc, asyncio.TimeoutError):
        return True
    import openai
    if isinstance(exc, (
        openai.APITimeoutError,
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.InternalServerError,
    )):
        return True
    if isinstance(exc, openai.APIStatusError):
        return getattr(exc, "status_code", 0) >= 500
    return False


def _backoff_delay(failed_attempt: int) -> float:
    """Exponential backoff + jitter for the manual stream retry (1-based attempt)."""
    base = settings.llm_retry_base_delay
    delay = min(base * (2 ** (failed_attempt - 1)), settings.llm_retry_max_delay)
    return delay + random.uniform(0, base)


async def _run_resilient(make_coro, *, timeout: float):
    """Run make_coro() under a timeout, retrying transient failures with backoff+jitter.

    make_coro is a zero-arg factory returning a fresh awaitable each attempt.
    Raises LLMUnavailable when transient failures persist past the attempt ceiling;
    non-transient errors propagate unchanged (and are not retried).
    """
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.llm_max_attempts),
            wait=wait_exponential_jitter(
                initial=settings.llm_retry_base_delay,
                max=settings.llm_retry_max_delay,
                jitter=settings.llm_retry_base_delay,
            ),
            retry=retry_if_exception(_is_transient),
            reraise=True,
        ):
            with attempt:
                return await asyncio.wait_for(make_coro(), timeout)
    except Exception as exc:
        if _is_transient(exc):
            raise LLMUnavailable(
                f"LLM unavailable after {settings.llm_max_attempts} attempts: {exc}"
            ) from exc
        raise


async def chat(
    messages: list[BaseMessage],
    *,
    call_type: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
) -> str:
    """Run one completion and return the response text (timed out + retried)."""
    model_name, temp = _resolve_params(call_type, temperature, model)
    timeout = _resolve_timeout(call_type)
    client = _build_client(model_name, temp, max_tokens, timeout=timeout)
    chain = client | StrOutputParser()
    return await _run_resilient(lambda: chain.ainvoke(messages), timeout=timeout)


async def stream(
    messages: list[BaseMessage],
    *,
    call_type: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
) -> AsyncIterator[str]:
    """Stream a completion, yielding content tokens as they arrive.

    Transient failures retry only BEFORE the first token (retrying after tokens
    have shipped would double-emit); once streaming, a failure ends the stream
    with LLMUnavailable. The client-level timeout bounds hangs.
    """
    model_name, temp = _resolve_params(call_type, temperature, model)
    timeout = _resolve_timeout(call_type)
    client = _build_client(model_name, temp, max_tokens, timeout=timeout)
    attempt = 0
    while True:
        attempt += 1
        yielded = False
        try:
            async for chunk in client.astream(messages):
                if chunk.content:
                    yielded = True
                    yield chunk.content
            return
        except Exception as exc:
            if not yielded and _is_transient(exc) and attempt < settings.llm_max_attempts:
                await asyncio.sleep(_backoff_delay(attempt))
                continue
            if _is_transient(exc):
                raise LLMUnavailable(f"LLM unavailable during stream: {exc}") from exc
            raise
