"""The limiter fails open: with Redis unreachable, LLM calls proceed unslotted
rather than every call blocking on a protective limit."""
import asyncio

from app.core import llm_limiter


class DownRedis:
    async def eval(self, *args, **kwargs):
        raise ConnectionError("redis down")

    async def zrem(self, *args, **kwargs):
        raise ConnectionError("redis down")


def test_slot_fails_open_when_redis_is_down(monkeypatch):
    monkeypatch.setattr(llm_limiter, "get_redis", lambda: DownRedis())
    entered = []

    async def body():
        async with llm_limiter.slot():
            entered.append(True)

    asyncio.run(body())
    assert entered == [True]
