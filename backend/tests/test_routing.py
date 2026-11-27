"""/chat and /stream route every label to the same workflow.

Before, "review" went to Code on /chat and to Theory on /stream, and "rag"
went to Theory on both. Hermetic:
the router call and both workflows are faked.
"""
import asyncio

import pytest

from app.agents import orchestrator


def _setup(monkeypatch, label):
    async def fake_route(message):
        return label

    async def run_theory(*a, **k):  return "theory"
    async def run_code(*a, **k):    return "code"
    async def stream_theory(*a, **k):
        yield "theory"
    async def stream_code(*a, **k):
        yield "code"
    async def run_rag(*a, **k):     return f"rag-week-{a[3]}"
    async def stream_rag(*a, **k):
        yield f"rag-week-{a[3]}"

    monkeypatch.setattr(orchestrator, "route", fake_route)
    monkeypatch.setattr(orchestrator, "run_theory_agent", run_theory)
    monkeypatch.setattr(orchestrator, "run_code_agent", run_code)
    monkeypatch.setattr(orchestrator, "stream_theory_agent", stream_theory)
    monkeypatch.setattr(orchestrator, "stream_code_agent", stream_code)
    monkeypatch.setattr(orchestrator, "run_rag_agent", run_rag)
    monkeypatch.setattr(orchestrator, "stream_rag_agent", stream_rag)


async def _streamed(mode, week=0):
    return "".join([t async for t in orchestrator.stream_agent("msg", mode=mode, week=week)])


@pytest.mark.parametrize("label,expected", [
    ("theory", "theory"), ("code", "code"), ("review", "code"), ("rag", "rag-week-0"),
])
def test_chat_and_stream_agree(monkeypatch, label, expected):
    _setup(monkeypatch, label)
    assert asyncio.run(orchestrator.run_agent("msg", mode="guided")) == expected
    assert asyncio.run(_streamed("guided")) == expected


def test_practice_mode_always_uses_code(monkeypatch):
    _setup(monkeypatch, "theory")
    assert asyncio.run(orchestrator.run_agent("msg", mode="practice")) == "code"
    assert asyncio.run(_streamed("practice")) == "code"


def test_week_reaches_the_rag_workflow_on_both_paths(monkeypatch):
    _setup(monkeypatch, "rag")
    assert asyncio.run(orchestrator.run_agent("msg", mode="course", week=3)) == "rag-week-3"
    assert asyncio.run(_streamed("course", week=3)) == "rag-week-3"
