"""Code agent graph behaviour.

One LLM call when the sandbox is off (retrying can't fix an outage), exactly one
retry on a real code error, the student's message sent once, and a bounded
history replayed from the checkpointer. Hermetic: fake LLM, fake executor,
in-memory checkpointer.
"""
import asyncio

from langgraph.checkpoint.memory import MemorySaver

import app.core.llm as llm_mod
from app.agents import code_agent
from app.core import executor, memory

REPLY = "EXPLANATION: a Bell state\n```python\nprint(1)\n```\nEXPECTED OUTPUT: 1"


def _setup(monkeypatch, exec_result):
    calls = []

    async def fake_chat(messages, **kwargs):
        calls.append(messages)
        return REPLY

    async def fake_run_code(code, **kwargs):
        return exec_result

    monkeypatch.setattr(llm_mod, "chat", fake_chat)
    monkeypatch.setattr(executor, "run_code", fake_run_code)
    monkeypatch.setattr(memory, "_checkpointer", MemorySaver())
    monkeypatch.setattr(code_agent, "_graph", None)   # rebuild bound to the in-memory saver
    return calls


def test_sandbox_off_means_one_call_and_an_honest_note(monkeypatch):
    off = executor.ExecResult(False, "", executor.DISABLED_MESSAGE, "", 0.0, unavailable=True)
    calls = _setup(monkeypatch, off)
    out = asyncio.run(code_agent.run_code_agent("make a Bell state", thread_id="t-off"))
    assert len(calls) == 1                        # no retry against an outage
    assert executor.DISABLED_MESSAGE in out


def test_code_error_is_retried_once(monkeypatch):
    calls = _setup(monkeypatch, executor.ExecResult(False, "", "NameError: name 'qc' is not defined", "", 0.1))
    asyncio.run(code_agent.run_code_agent("make a Bell state", thread_id="t-err"))
    assert len(calls) == 2
    assert "Fix this error" in calls[1][-1].content


def test_message_sent_once_and_history_bounded(monkeypatch):
    calls = _setup(monkeypatch, executor.ExecResult(True, "{'00': 512}", "", "", 0.1))
    for i in range(10):
        asyncio.run(code_agent.run_code_agent(f"request {i}", thread_id="t-long"))
    last_prompt = calls[-1]
    human = [m.content for m in last_prompt if type(m).__name__ == "HumanMessage"]
    assert human.count("request 9") == 1          # not duplicated
    assert "request 0" not in human               # old turns stop being replayed
    assert len(last_prompt) <= 1 + code_agent.MAX_HISTORY_MESSAGES
