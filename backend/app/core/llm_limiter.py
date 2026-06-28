# ── app/core/llm_limiter.py ──────────────────────────────────
# Shared, bounded concurrency in front of the LLM — one honest global limit
# across all workers (not per-process), so a burst of simultaneous calls doesn't
# all fire at once.
#
# Design: a self-healing sorted-set semaphore in Redis (ZSET `llm:inflight`).
#   - Each in-flight call adds a unique token scored by acquisition time.
#   - Admission is by COUNT (ZCARD): claim a slot, and keep it iff the live
#     holder count is within `llm_max_concurrency`. (Counting by ZCARD rather
#     than ZRANK avoids a tie bug — many concurrent calls can share the same
#     wall-clock score, and ZRANK breaks ties lexicographically, which would
#     over-admit.)
#   - Prune + claim + count + conditional-release run in ONE atomic Lua script,
#     so concurrent acquirers can't interleave and over-admit.
#   - The token's score is acquisition time, used only for the stale prune: a
#     token from a worker that died mid-call is pruned after
#     `llm_limiter_stale_seconds`, so capacity self-heals with no reconciliation.
#   - If no slot frees within `llm_acquire_timeout_seconds`, raise LLMBusy.
#   - If Redis itself is unavailable, fail OPEN (proceed without a slot) rather
#     than block all LLM traffic — the limit is protective, not a correctness
#     invariant.

import asyncio
import logging
import random
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from app.core.config import settings
from app.core.llm_errors import LLMBusy
from app.db.redis_client import get_redis

logger = logging.getLogger("quantummind.llm")

_KEY = "llm:inflight"

# Atomic acquire: prune stale, claim, admit iff live count is within the limit.
# KEYS[1]=zset; ARGV[1]=now ARGV[2]=stale_cutoff ARGV[3]=limit ARGV[4]=token
_ACQUIRE_LUA = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[2])
redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
if redis.call('ZCARD', KEYS[1]) <= tonumber(ARGV[3]) then
  return 1
end
redis.call('ZREM', KEYS[1], ARGV[4])
return 0
"""


async def _acquire() -> Optional[str]:
    """Acquire a concurrency slot.

    Returns a token to release later, or None (a no-op slot) if Redis is
    unavailable (fail-open). Raises LLMBusy if no slot frees within the timeout.
    """
    limit = settings.llm_max_concurrency
    stale = settings.llm_limiter_stale_seconds
    deadline = time.monotonic() + settings.llm_acquire_timeout_seconds
    token = uuid.uuid4().hex
    r = get_redis()

    while True:
        now = time.time()
        try:
            admitted = await r.eval(_ACQUIRE_LUA, 1, _KEY, now, now - stale, limit, token)
        except Exception as exc:
            logger.warning("llm limiter unavailable, proceeding without a slot: %s", exc)
            return None

        if admitted == 1:
            return token

        if time.monotonic() >= deadline:
            raise LLMBusy(
                f"no LLM slot within {settings.llm_acquire_timeout_seconds}s "
                f"(limit {limit})"
            )
        await asyncio.sleep(0.05 + random.uniform(0, 0.05))  # small jittered poll


async def _release(token: Optional[str]) -> None:
    if token is None:
        return
    try:
        await get_redis().zrem(_KEY, token)
    except Exception:
        pass  # self-heals via the prune window


@asynccontextmanager
async def slot():
    """Hold a global LLM concurrency slot for the duration of the block."""
    token = await _acquire()
    try:
        yield
    finally:
        await _release(token)
