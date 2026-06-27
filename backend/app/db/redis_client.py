# ── app/db/redis_client.py ───────────────────────────────────
# Shared async Redis client (one connection pool per process).
#
# Holds the hot copy of active-exam state, shared across workers. Created lazily
# so importing this module never opens a connection; warmed/closed by the app
# lifespan. TLS is handled automatically by the rediss:// scheme (e.g. Upstash).

from typing import Optional

import redis.asyncio as redis

from app.core.config import settings

_redis: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """The process-wide async Redis client. Created on first use."""
    global _redis
    if _redis is None:
        # decode_responses=True → str in/out, so JSON round-trips cleanly.
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    """Close the client on shutdown (wired into the lifespan)."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
    _redis = None
