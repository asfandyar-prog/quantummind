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
import json
import logging
import random
import time
from datetime import datetime, timezone
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
from app.core import llm_limiter
from app.core.llm_errors import LLMError, LLMUnavailable, LLMBusy  # re-exported

logger = logging.getLogger("quantummind.llm")

# Strong refs to fire-and-forget accounting tasks so they aren't GC'd mid-flight.
_accounting_tasks: set = set()


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


# ── Token / cost accounting (best-effort, off the response path) ──────────────

async def _bump_counters(total_tokens: int) -> None:
    """Increment shared daily token + call counters in Redis; warn over soft budget."""
    from app.db.redis_client import get_redis

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    r = get_redis()
    daily = await r.incrby(f"llm:tokens:total:{day}", total_tokens)
    await r.incr(f"llm:calls:{day}")

    budget = settings.llm_token_budget_per_day
    if budget and daily > budget:
        # Soft budget: warn only — never refuse a call (a live exam must not break
        # on a counter).
        logger.warning(json.dumps({
            "event": "llm_budget_exceeded", "date": day,
            "daily_tokens": daily, "budget": budget,
        }))


async def _account(call_type, model, message, latency_ms: int, outcome: str) -> None:
    """Log one structured per-request record + bump counters. Never raises —
    accounting must not break (or slow) an LLM call."""
    try:
        usage = (getattr(message, "usage_metadata", None) or {}) if message is not None else {}
        in_tok = int(usage.get("input_tokens", 0) or 0)
        out_tok = int(usage.get("output_tokens", 0) or 0)
        total = int(usage.get("total_tokens", in_tok + out_tok) or 0)
        logger.info(json.dumps({
            "event": "llm_call",
            "call_type": call_type,
            "model": model,
            "provider": settings.llm_provider,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "total_tokens": total,
            "latency_ms": latency_ms,
            "outcome": outcome,
        }))
        await _bump_counters(total)
    except Exception as exc:  # accounting is best-effort
        logger.warning("llm accounting failed: %s", exc)


def _schedule_accounting(coro) -> None:
    """Run accounting as a tracked background task so it never blocks the response."""
    task = asyncio.create_task(coro)
    _accounting_tasks.add(task)
    task.add_done_callback(_accounting_tasks.discard)


async def chat(
    messages: list[BaseMessage],
    *,
    call_type: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
) -> str:
    """Run one completion and return the response text (timed out + retried).

    Usage is captured from the returned AIMessage and accounted off the response
    path; the return type stays `str`, so agents are untouched.
    """
    model_name, temp = _resolve_params(call_type, temperature, model)
    timeout = _resolve_timeout(call_type)
    client = _build_client(model_name, temp, max_tokens, timeout=timeout)

    start = time.monotonic()
    try:
        async with llm_limiter.slot():  # global bounded concurrency (shared via Redis)
            message = await _run_resilient(lambda: client.ainvoke(messages), timeout=timeout)
    except LLMBusy:
        _schedule_accounting(_account(call_type, model_name, None,
                                      int((time.monotonic() - start) * 1000), "busy"))
        raise
    except LLMUnavailable:
        _schedule_accounting(_account(call_type, model_name, None,
                                      int((time.monotonic() - start) * 1000), "unavailable"))
        raise
    _schedule_accounting(_account(call_type, model_name, message,
                                  int((time.monotonic() - start) * 1000), "ok"))
    return StrOutputParser().invoke(message)


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
    # Hold a global concurrency slot for the whole stream (released on completion
    # or when the consumer closes the generator). LLMBusy on acquire propagates.
    async with llm_limiter.slot():
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
