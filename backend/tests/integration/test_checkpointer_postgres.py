"""Code-agent memory lives in Postgres and survives a restart.

The practice assistant's conversation is checkpointed by AsyncPostgresSaver.
After the checkpointer's pool is closed and the compiled graph is dropped (a
simulated process restart), a new turn on the same thread still replays the
earlier one. The unit tests use MemorySaver, so this is the only test of the
Postgres checkpointer itself.
"""
import uuid

from sqlalchemy import text

import _util
from _util import run_isolated

import app.core.llm as llm_mod
from app.agents import code_agent
from app.core import executor, memory
from app.db import database

REPLY = "EXPLANATION: ok\n```python\nprint(1)\n```\nEXPECTED OUTPUT: 1"


def test_code_agent_memory_survives_a_restart(monkeypatch):
    prompts = []

    async def fake_chat(messages, **kwargs):
        prompts.append([m.content for m in messages])
        return REPLY

    async def fake_run_code(code, **kwargs):
        return executor.ExecResult(True, "1", "", "", 0.1)

    monkeypatch.setattr(llm_mod, "chat", fake_chat)
    monkeypatch.setattr(executor, "run_code", fake_run_code)
    thread = f"checkpoint-restart-{uuid.uuid4().hex}"

    async def body():
        await memory.init_checkpointer()
        code_agent._graph = None                     # build bound to the Postgres saver
        await code_agent.run_code_agent("make a Bell state", thread_id=thread)

        # Simulated restart: the pool closes and the compiled graph is forgotten.
        await memory.close_checkpointer()
        code_agent._graph = None

        await memory.init_checkpointer()
        await code_agent.run_code_agent("now add a third qubit", thread_id=thread)

        async with database.get_engine().begin() as conn:
            for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                await conn.execute(text(f"DELETE FROM {table} WHERE thread_id = :t"), {"t": thread})

    run_isolated(body)

    last_prompt = prompts[-1]
    assert "make a Bell state" in last_prompt          # replayed from Postgres after the restart
    assert last_prompt[-1] == "now add a third qubit"
