"""/chat keeps callers' conversations apart; /history returns what was stored.

Hermetic: fake LLM, in-memory checkpointer, route functions called directly.
"""
import asyncio

from langgraph.checkpoint.memory import MemorySaver

import app.core.llm as llm_mod
from app.agents import theory_agent
from app.core import memory
from app.routes.chat import ChatRequest, chat, get_history


def _setup(monkeypatch):
    prompts = []

    async def fake_chat(messages, *, call_type=None, **kwargs):
        if call_type == "route":
            return '{"agent": "theory", "reason": "test"}'
        prompts.append([m.content for m in messages])
        return "an answer"

    monkeypatch.setattr(llm_mod, "chat", fake_chat)
    monkeypatch.setattr(memory, "_checkpointer", MemorySaver())
    monkeypatch.setattr(theory_agent, "_graph", None)
    return prompts


def test_callers_without_a_thread_id_do_not_share_memory(monkeypatch):
    prompts = _setup(monkeypatch)

    async def body():
        await chat(ChatRequest(message="I am user A, my PIN is 4242", mode="theory"))
        await chat(ChatRequest(message="I am user B", mode="theory"))

    asyncio.run(body())
    assert len(prompts) == 2
    assert not any("4242" in text for text in prompts[1])   # B's prompt carries nothing of A's


def test_history_returns_the_stored_conversation(monkeypatch):
    _setup(monkeypatch)

    async def body():
        await chat(ChatRequest(message="what is superposition?", mode="theory", thread_id="t-hist"))
        return await get_history("t-hist")

    history = asyncio.run(body())
    assert history["messages"] == [
        {"role": "user", "content": "what is superposition?"},
        {"role": "ai", "content": "an answer"},
    ]


def test_theory_graph_replays_only_recent_history(monkeypatch):
    prompts = _setup(monkeypatch)
    for i in range(10):
        asyncio.run(chat(ChatRequest(message=f"turn {i}", mode="theory", thread_id="t-long")))
    last = prompts[-1]
    assert len(last) <= 1 + theory_agent.MAX_HISTORY_MESSAGES
    assert "turn 9" in last and "turn 0" not in last   # old turns stop being replayed
