"""Phase 2 commit 2: token/cost accounting in the seam.

Hermetic — _account is driven directly with a fake AIMessage and a fake Redis;
no network, no real Redis. Verifies usage capture, the structured log line, the
shared counters, the soft/warn-only budget, and best-effort behaviour on failure.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from langchain_core.messages import AIMessage

from app.core import llm
from app.core.config import settings


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def incrby(self, key, amount):
        self.store[key] = self.store.get(key, 0) + amount
        return self.store[key]

    async def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]


def _day():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def test_token_capture_logs_and_counts(monkeypatch, caplog):
    fake = FakeRedis()
    monkeypatch.setattr("app.db.redis_client.get_redis", lambda: fake)
    msg = AIMessage(
        content="hello world",
        usage_metadata={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )
    with caplog.at_level(logging.INFO, logger="quantummind.llm"):
        asyncio.run(llm._account("exam_grade", "llama-3.1-8b-instant", msg, 123, "ok"))

    # shared counters bumped by the captured usage
    assert fake.store[f"llm:tokens:total:{_day()}"] == 15
    assert fake.store[f"llm:calls:{_day()}"] == 1

    # one structured per-request log line with the token breakdown
    records = [r for r in caplog.records if '"event": "llm_call"' in r.getMessage()]
    assert records, "expected a structured llm_call log line"
    logged = json.loads(records[0].getMessage())
    assert (logged["input_tokens"], logged["output_tokens"], logged["total_tokens"]) == (10, 5, 15)
    assert logged["call_type"] == "exam_grade"
    assert logged["outcome"] == "ok"


def test_soft_budget_warns_but_does_not_raise(monkeypatch, caplog):
    fake = FakeRedis()
    monkeypatch.setattr("app.db.redis_client.get_redis", lambda: fake)
    monkeypatch.setattr(settings, "llm_token_budget_per_day", 10)
    msg = AIMessage(
        content="x",
        usage_metadata={"input_tokens": 8, "output_tokens": 7, "total_tokens": 15},
    )
    with caplog.at_level(logging.WARNING, logger="quantummind.llm"):
        asyncio.run(llm._account("theory", "m", msg, 50, "ok"))  # 15 > budget 10
    assert [r for r in caplog.records if '"event": "llm_budget_exceeded"' in r.getMessage()]
    # returned normally — soft budget never raises


def test_accounting_never_raises_on_redis_failure(monkeypatch):
    class BrokenRedis:
        async def incrby(self, *a, **k):
            raise RuntimeError("redis down")

        async def incr(self, *a, **k):
            raise RuntimeError("redis down")

    monkeypatch.setattr("app.db.redis_client.get_redis", lambda: BrokenRedis())
    msg = AIMessage(content="x", usage_metadata={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2})
    # best-effort: a broken Redis must not raise out of accounting
    asyncio.run(llm._account("route", "m", msg, 10, "ok"))
