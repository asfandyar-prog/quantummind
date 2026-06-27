# ── app/core/memory.py ───────────────────────────────────────
# Persistent LangGraph checkpointer (Postgres via AsyncPostgresSaver).
#
# Replaces MemorySaver (RAM): conversation memory for the theory/code/rag graphs
# now survives restarts and is shared across workers via the same Postgres.
#
# Created ONCE at app startup (init_checkpointer) BEFORE any graph is built, with
# a one-time setup() that ensures the checkpoint tables. A long-lived async
# psycopg connection pool backs it for the app's lifetime.
#
# Exam/lesson graphs intentionally stay checkpointer-less: they are single-node,
# stateless-per-call graphs with no cross-call memory — the exam loop state lives
# in Redis+Postgres (core/exam_state), and lesson plan/step/grade are pure
# functions — so a checkpointer there would persist nothing useful.

from typing import Optional

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings

_pool: Optional[AsyncConnectionPool] = None
_checkpointer: Optional[AsyncPostgresSaver] = None


def _conninfo() -> str:
    # AsyncPostgresSaver/psycopg need a libpq conn string, not the SQLAlchemy
    # "+psycopg" form the app engine uses.
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


async def init_checkpointer() -> AsyncPostgresSaver:
    """Create the persistent checkpointer and run its one-time setup().

    Must be called at startup BEFORE any graph is built so the graphs capture it.
    """
    global _pool, _checkpointer
    if _checkpointer is not None:
        return _checkpointer
    _pool = AsyncConnectionPool(
        conninfo=_conninfo(),
        open=False,
        # langgraph's required connection settings for the Postgres saver.
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    await _pool.open()
    _checkpointer = AsyncPostgresSaver(_pool)
    await _checkpointer.setup()  # idempotent: ensures checkpoint tables exist
    print("[Memory] AsyncPostgresSaver checkpointer ready")
    return _checkpointer


def get_checkpointer() -> Optional[AsyncPostgresSaver]:
    return _checkpointer


async def close_checkpointer() -> None:
    """Close the checkpointer's connection pool on shutdown."""
    global _pool, _checkpointer
    if _pool is not None:
        await _pool.close()
    _pool = None
    _checkpointer = None
