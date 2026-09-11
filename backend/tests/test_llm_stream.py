"""The streaming path of the LLM seam.

Transient failures retry only before the first token, so no text is ever sent
twice; a failure after tokens have shipped ends the stream as LLMUnavailable;
every stream is accounted with its outcome. Hermetic: fake client, no-op slot.
"""
import asyncio
from contextlib import asynccontextmanager

import httpx
import openai
import pytest
from langchain_core.messages import AIMessageChunk, HumanMessage

from app.core import llm, llm_limiter
from app.core.config import settings


def _rate_limit():
    req = httpx.Request("POST", "https://api.test/v1/chat/completions")
    return openai.RateLimitError("rate limited", response=httpx.Response(429, request=req), body=None)


class FakeClient:
    """Each astream() call plays the next script: some tokens, then maybe an error."""

    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.calls = 0

    async def astream(self, messages):
        tokens, error = self.scripts[self.calls]
        self.calls += 1
        for token in tokens:
            yield AIMessageChunk(content=token)
        if error is not None:
            raise error


@pytest.fixture
def seam(monkeypatch):
    @asynccontextmanager
    async def no_slot():
        yield

    records = []

    async def fake_account(call_type, model, message, latency_ms, outcome):
        records.append({"outcome": outcome, "message": message})

    monkeypatch.setattr(llm_limiter, "slot", no_slot)
    monkeypatch.setattr(llm, "_account", fake_account)
    monkeypatch.setattr(settings, "llm_retry_base_delay", 0.0)
    monkeypatch.setattr(settings, "llm_retry_max_delay", 0.0)
    monkeypatch.setattr(settings, "llm_max_attempts", 3)

    def use(client):
        monkeypatch.setattr(llm, "_build_client", lambda *a, **k: client)

    return use, records


def _consume(tokens):
    async def run():
        try:
            async for token in llm.stream([HumanMessage(content="hi")], call_type="theory"):
                tokens.append(token)
        finally:
            await asyncio.sleep(0)   # let the scheduled accounting task run
    asyncio.run(run())


def test_transient_error_before_first_token_is_retried(seam):
    use, records = seam
    client = FakeClient([([], _rate_limit()), (["Hello", " world"], None)])
    use(client)
    tokens = []
    _consume(tokens)
    assert tokens == ["Hello", " world"]
    assert client.calls == 2
    assert [r["outcome"] for r in records] == ["ok"]


def test_failure_after_first_token_is_not_retried_and_never_double_emits(seam):
    use, records = seam
    client = FakeClient([(["partial"], _rate_limit()), (["partial", " again"], None)])
    use(client)
    tokens = []
    with pytest.raises(llm.LLMUnavailable):
        _consume(tokens)
    assert tokens == ["partial"]          # sent once; the retry that would repeat it never runs
    assert client.calls == 1
    assert [r["outcome"] for r in records] == ["unavailable"]


def test_exhausted_retries_become_llm_unavailable(seam):
    use, records = seam
    client = FakeClient([([], _rate_limit())] * 3)
    use(client)
    tokens = []
    with pytest.raises(llm.LLMUnavailable):
        _consume(tokens)
    assert tokens == [] and client.calls == 3      # llm_max_attempts
    assert [r["outcome"] for r in records] == ["unavailable"]


def test_stream_usage_is_accounted_when_the_provider_sends_it(seam):
    use, records = seam

    class UsageClient(FakeClient):
        async def astream(self, messages):
            yield AIMessageChunk(content="hi")
            yield AIMessageChunk(content="", usage_metadata={
                "input_tokens": 5, "output_tokens": 2, "total_tokens": 7})

    use(UsageClient([]))
    _consume([])
    assert records[0]["outcome"] == "ok"
    assert records[0]["message"].usage_metadata["total_tokens"] == 7
