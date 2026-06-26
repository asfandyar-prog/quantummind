# ── app/db/database.py ───────────────────────────────────────
# Async SQLAlchemy engine + pooled sessions (Postgres via psycopg 3).
#
# Replaces the per-request sqlite3.connect() in audit_db.py with one pooled
# async engine created at startup. DORMANT in this commit — nothing imports it
# yet; the repository + lifespan wiring land in commit 3. The engine is created
# lazily, so importing this module never opens a connection.

from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """The process-wide async engine (one pool). Created on first use."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async session. Final transaction handling lands in commit 3."""
    async with get_sessionmaker()() as session:
        yield session


async def dispose_engine() -> None:
    """Dispose the pool on shutdown (wired into the lifespan in commit 3)."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
