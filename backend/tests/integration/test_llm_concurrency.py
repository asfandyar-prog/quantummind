"""Phase 2 commit 3: the Redis-backed concurrency limiter (real Upstash ZSET).

A burst of concurrent slot-holders never exceeds the limit (peak ≤ limit, excess
waits then proceeds); under sustained saturation, contenders surface LLMBusy
cleanly rather than piling on.
"""
import asyncio

import _util
from _util import run_isolated

from app.core import llm_limiter
from app.core.llm_errors import LLMBusy
from app.core.config import settings
from app.db import redis_client


async def _clear():
    await redis_client.get_redis().delete("llm:inflight")


def test_burst_stays_bounded(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_concurrency", 5)
    monkeypatch.setattr(settings, "llm_acquire_timeout_seconds", 10.0)

    async def body():
        await _clear()
        st = {"cur": 0, "peak": 0, "done": 0}

        async def worker():
            async with llm_limiter.slot():
                st["cur"] += 1
                st["peak"] = max(st["peak"], st["cur"])
                await asyncio.sleep(0.2)   # hold the slot
                st["cur"] -= 1
                st["done"] += 1

        await asyncio.gather(*[worker() for _ in range(20)])
        assert st["peak"] <= 5, f"peak {st['peak']} exceeded limit 5"
        assert st["done"] == 20            # excess waited then proceeded — nothing dropped
        await _clear()

    run_isolated(body)


def test_saturation_surfaces_llm_busy(monkeypatch):
    monkeypatch.setattr(settings, "llm_max_concurrency", 2)
    monkeypatch.setattr(settings, "llm_acquire_timeout_seconds", 0.3)

    async def body():
        await _clear()
        result = {"busy": 0, "ok": 0}
        hold = asyncio.Event()

        async def hog():
            async with llm_limiter.slot():
                await hold.wait()           # occupy a slot until released

        async def contender():
            try:
                async with llm_limiter.slot():
                    result["ok"] += 1
            except LLMBusy:
                result["busy"] += 1

        hogs = [asyncio.create_task(hog()) for _ in range(2)]   # fill both slots
        await asyncio.sleep(0.3)                                # let the hogs win them
        await asyncio.gather(*[contender() for _ in range(4)])  # cannot acquire in 0.3s

        assert result["busy"] == 4, result   # all contenders degrade cleanly
        assert result["ok"] == 0

        hold.set()
        await asyncio.gather(*hogs)
        await _clear()

    run_isolated(body)
