# ── app/core/llm.py ───────────────────────────────────────────
# The single seam for all model access. No module outside this file may
# import an LLM SDK — every agent calls chat()/stream() here.
#
# One client class (ChatOpenAI) serves every provider; the provider only
# selects a base URL and how the API key is resolved. Because Groq, OpenAI,
# and self-hosted vLLM all speak the OpenAI chat-completions protocol, the
# dev path (Groq) and the prod path (vLLM) are the *same* client path —
# only base URL + model + key differ by config.

from typing import AsyncIterator, Optional

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings


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


def _build_client(model: str, temperature: float, max_tokens: Optional[int]):
    # Lazy import keeps the LLM SDK out of import time and contained to this
    # module. Constructed per call (matching the pre-seam code); connection
    # reuse/pooling is a Phase 2 concern.
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=_resolve_api_key(),
        base_url=_resolve_base_url(),
    )


async def chat(
    messages: list[BaseMessage],
    *,
    call_type: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
) -> str:
    """Run one completion and return the response text."""
    model_name, temp = _resolve_params(call_type, temperature, model)
    client = _build_client(model_name, temp, max_tokens)
    return await (client | StrOutputParser()).ainvoke(messages)


async def stream(
    messages: list[BaseMessage],
    *,
    call_type: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model: Optional[str] = None,
) -> AsyncIterator[str]:
    """Stream a completion, yielding content tokens as they arrive."""
    model_name, temp = _resolve_params(call_type, temperature, model)
    client = _build_client(model_name, temp, max_tokens)
    async for chunk in client.astream(messages):
        if chunk.content:
            yield chunk.content
