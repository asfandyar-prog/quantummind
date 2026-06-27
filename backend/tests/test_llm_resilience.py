"""Phase 2 commit 1: retry + timeout + typed errors in the LLM seam.

Hermetic — exercises _is_transient and _run_resilient directly with fake
coroutines and real openai exception instances. No network, no DB.
"""
import asyncio

import httpx
import openai
import pytest

from app.core.config import settings
from app.core.llm import LLMUnavailable, _is_transient, _run_resilient


# ── openai exception builders ─────────────────────────────────
def _req():
    return httpx.Request("POST", "https://api.test/v1/chat/completions")


def _rate_limit():
    return openai.RateLimitError("rate limited", response=httpx.Response(429, request=_req()), body=None)


def _api_timeout():
    return openai.APITimeoutError(request=_req())


def _server_error():
    return openai.InternalServerError("boom", response=httpx.Response(503, request=_req()), body=None)


def _bad_request():
    return openai.BadRequestError("bad input", response=httpx.Response(400, request=_req()), body=None)


# ── _is_transient classification ──────────────────────────────
def test_is_transient_true_for_retryable():
    assert _is_transient(_rate_limit())
    assert _is_transient(_api_timeout())
    assert _is_transient(_server_error())
    assert _is_transient(asyncio.TimeoutError())


def test_is_transient_false_for_others():
    assert not _is_transient(_bad_request())     # 400 — not retried
    assert not _is_transient(ValueError("nope"))


# ── retry behaviour ───────────────────────────────────────────
def _fast(monkeypatch, attempts):
    # zero backoff so tests are quick and deterministic
    monkeypatch.setattr(settings, "llm_retry_base_delay", 0.0)
    monkeypatch.setattr(settings, "llm_retry_max_delay", 0.0)
    monkeypatch.setattr(settings, "llm_max_attempts", attempts)


def test_retries_then_succeeds(monkeypatch):
    _fast(monkeypatch, attempts=4)
    calls = {"n": 0}

    async def make():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _rate_limit()
        return "ok"

    assert asyncio.run(_run_resilient(make, timeout=5)) == "ok"
    assert calls["n"] == 3


def test_exhausts_to_llm_unavailable(monkeypatch):
    _fast(monkeypatch, attempts=3)
    calls = {"n": 0}

    async def make():
        calls["n"] += 1
        raise _api_timeout()

    with pytest.raises(LLMUnavailable):
        asyncio.run(_run_resilient(make, timeout=5))
    assert calls["n"] == 3                        # hit the ceiling, no more


def test_non_transient_not_retried(monkeypatch):
    _fast(monkeypatch, attempts=4)
    calls = {"n": 0}

    async def make():
        calls["n"] += 1
        raise _bad_request()

    with pytest.raises(openai.BadRequestError):    # propagates unchanged
        asyncio.run(_run_resilient(make, timeout=5))
    assert calls["n"] == 1                          # tried exactly once


def test_timeout_becomes_llm_unavailable(monkeypatch):
    _fast(monkeypatch, attempts=2)
    calls = {"n": 0}

    async def make():
        calls["n"] += 1
        await asyncio.sleep(1.0)                    # exceeds the timeout
        return "never"

    with pytest.raises(LLMUnavailable):
        asyncio.run(_run_resilient(make, timeout=0.05))
    assert calls["n"] == 2                          # each attempt timed out
