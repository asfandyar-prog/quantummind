"""Shared helpers for the Phase 1 integration tests (not collected by pytest)."""
import asyncio
import itertools

from sqlalchemy import text

from app.db import database, redis_client
from app.core import memory
import app.agents.theory_agent as theory
import app.agents.code_agent as code
import app.agents.exam_agent as exam_agent


def libpq(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


async def dispose_all() -> None:
    """Dispose every data-layer singleton and clear cached graphs — simulate a fresh process."""
    await redis_client.close_redis()
    await database.dispose_engine()
    await memory.close_checkpointer()
    theory._graph = None
    code._graph = None
    exam_agent._q_graph = None
    exam_agent._grade_graph = None


def run_isolated(coro_func):
    """Run an async test body, then dispose all singletons in the SAME loop.

    Each test runs in its own asyncio loop; disposing in-loop avoids the
    "future attached to a different loop" trap on the next test.
    """
    async def _wrap():
        try:
            return await coro_func()
        finally:
            await dispose_all()

    return asyncio.run(_wrap())


async def cleanup_session(session_id: str) -> None:
    """Remove a test session's Postgres rows + Redis key."""
    async with database.get_engine().begin() as conn:
        await conn.execute(text("DELETE FROM exam_turns WHERE session_id=:s"), {"s": session_id})
        await conn.execute(text("DELETE FROM exam_sessions WHERE session_id=:s"), {"s": session_id})
    await redis_client.get_redis().delete(f"exam:{session_id}")


def grading_chat_factory():
    """Fake llm.chat: deterministic exam questions + a fixed high grade (no follow-up)."""
    counter = itertools.count(1)

    async def fake_chat(messages, *, call_type=None, **kwargs):
        if call_type == "exam_grade":
            return ('{"accuracy": 8, "reasoning": 7, "clarity": 9, '
                    '"justification": "solid", "ideal_answer": "ideal"}')
        if call_type == "exam_question":
            return f"Generated question #{next(counter)}"
        return "generic"

    return fake_chat
