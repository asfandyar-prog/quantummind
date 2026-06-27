"""Proof: agents still function through the seam. The seam is monkeypatched to
return canned output (no network), and we drive representative agents end to end.
"""
import asyncio

import pytest

from langgraph.checkpoint.memory import MemorySaver
import app.core.llm as llm_mod
from app.core import memory
from app.agents import orchestrator, theory_agent, exam_agent


def _patch_chat(monkeypatch, returns):
    async def fake_chat(messages, **kwargs):
        return returns
    monkeypatch.setattr(llm_mod, "chat", fake_chat)


def test_orchestrator_route_parses_json(monkeypatch):
    _patch_chat(monkeypatch, '{"agent": "code", "reason": "writes a circuit"}')
    assert asyncio.run(orchestrator.route("write a Bell state")) == "code"


def test_orchestrator_route_falls_back_on_bad_json(monkeypatch):
    _patch_chat(monkeypatch, "this is not json")
    assert asyncio.run(orchestrator.route("hello")) == "theory"


def test_theory_agent_returns_string(monkeypatch):
    _patch_chat(monkeypatch, "**Superposition** is a core quantum idea.")
    # Use an in-memory checkpointer so the test stays hermetic (no Postgres).
    monkeypatch.setattr(memory, "_checkpointer", MemorySaver())
    monkeypatch.setattr(theory_agent, "_graph", None)  # rebuild bound to it
    out = asyncio.run(theory_agent.run_theory_agent("what is superposition?", thread_id="t-smoke"))
    assert isinstance(out, str)
    assert "Superposition" in out


def test_exam_grade_returns_score_dict(monkeypatch):
    _patch_chat(
        monkeypatch,
        '{"accuracy": 8, "reasoning": 7, "clarity": 9, '
        '"justification": "solid", "ideal_answer": "..."}',
    )
    res = asyncio.run(exam_agent.grade_answer("entanglement", "What is a Bell state?", "answer"))
    expected_total = round((8 + 7 + 9) / 3, 2)
    assert res["total"] == pytest.approx(expected_total)
    for key in ("accuracy", "reasoning", "clarity", "total", "justification",
                "ideal_answer", "is_weak", "weak_areas"):
        assert key in res
