# ── app/core/cache.py ─────────────────────────────────────────
# In-memory LRU cache for LLM responses.
# Caches: lesson plans (expensive, deterministic per topic)
#         theory responses to common questions
# Does NOT cache: code execution (always different), grading (personalized)

import hashlib
import time
from collections import OrderedDict
from typing import Optional


class LRUCache:
    """
    Thread-safe LRU cache with TTL expiry.
    Uses OrderedDict for O(1) access + eviction.

    Why not Redis? No infrastructure needed. For a single-server
    deployment this is perfectly sufficient and zero cost.
    Upgrade to Redis when you have multiple Railway instances.
    """

    def __init__(self, max_size: int = 200, ttl_seconds: int = 3600):
        self._cache: OrderedDict = OrderedDict()
        self._max_size   = max_size
        self._ttl        = ttl_seconds
        self._hits       = 0
        self._misses     = 0

    def _make_key(self, namespace: str, content: str) -> str:
        # Normalize: lowercase, strip whitespace for better hit rate
        normalized = content.lower().strip()
        h = hashlib.md5(normalized.encode()).hexdigest()[:16]
        return f"{namespace}:{h}"

    def get(self, namespace: str, content: str) -> Optional[str]:
        key = self._make_key(namespace, content)
        if key not in self._cache:
            self._misses += 1
            return None
        value, expires_at = self._cache[key]
        if time.time() > expires_at:
            del self._cache[key]
            self._misses += 1
            return None
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        print(f"[Cache] HIT {namespace} — total hits: {self._hits}")
        return value

    def set(self, namespace: str, content: str, value: str) -> None:
        key = self._make_key(namespace, content)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (value, time.time() + self._ttl)
        if len(self._cache) > self._max_size:
            # Evict least recently used
            self._cache.popitem(last=False)

    def stats(self) -> dict:
        total = self._hits + self._misses
        rate  = round(self._hits / total * 100, 1) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{rate}%",
            "cached_items": len(self._cache),
        }


# Global cache instance
cache = LRUCache(max_size=200, ttl_seconds=3600)

# What gets cached:
# "plan:{topic_hash}"    → JSON lesson plan (1hr TTL — same topic = same plan)
# "theory:{question_hash}" → theory responses for common questions (1hr TTL)
# What does NOT get cached:
# Code generation — always personalized
# Grading — always personalized to student answer
# Step teaching — varies by context