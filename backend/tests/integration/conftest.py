"""Integration-test setup: dedicated test DB (alembic upgrade head) + test Redis.

Resource URLs come from DATABASE_URL_TEST / REDIS_URL_TEST, falling back to the
app's DATABASE_URL / REDIS_URL. If the resources are unreachable, every
integration test is skipped with a clear message — they never run against an
imaginary database, and the unit suite stays independent of any cloud service.
"""
import os
import sys
import asyncio

import pytest

# psycopg 3 async needs a SelectorEventLoop (Windows defaults to Proactor).
# Safe for the whole session — SelectorEventLoop runs all our async fine.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Make `import _util` work for sibling test modules.
sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings


def _libpq(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


DATABASE_URL_TEST = os.environ.get("DATABASE_URL_TEST", settings.database_url)
REDIS_URL_TEST = os.environ.get("REDIS_URL_TEST", settings.redis_url)
# Only blanket-flush Redis when a DEDICATED test instance is given (distinct from
# the app's Redis). Otherwise we never flush a shared db (e.g. Upstash db 0).
_DEDICATED_REDIS = "REDIS_URL_TEST" in os.environ and REDIS_URL_TEST != settings.redis_url


def _check_reachable():
    import psycopg
    import redis
    try:
        with psycopg.connect(_libpq(DATABASE_URL_TEST), connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        r = redis.from_url(REDIS_URL_TEST, socket_connect_timeout=10)
        try:
            r.ping()
            if _DEDICATED_REDIS:
                r.flushdb()  # safe: dedicated test Redis
        finally:
            r.close()
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


INTEGRATION_OK, SKIP_REASON = _check_reachable()
_MIGRATED = False


@pytest.fixture(autouse=True)
def integration_env():
    if not INTEGRATION_OK:
        pytest.skip(
            "integration resources unreachable — set DATABASE_URL_TEST / REDIS_URL_TEST "
            f"(or DATABASE_URL / REDIS_URL): {SKIP_REASON}"
        )

    orig_db, orig_redis = settings.database_url, settings.redis_url
    settings.database_url = DATABASE_URL_TEST
    settings.redis_url = REDIS_URL_TEST

    global _MIGRATED
    if not _MIGRATED:
        from alembic.config import Config
        from alembic import command
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", DATABASE_URL_TEST)
        command.upgrade(cfg, "head")
        _MIGRATED = True

    yield
    settings.database_url, settings.redis_url = orig_db, orig_redis
