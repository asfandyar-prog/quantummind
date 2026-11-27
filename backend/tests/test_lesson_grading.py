"""The lesson grader fails closed.

An unreadable reply, or a "passed" value that isn't JSON true, never unlocks the
next step. Hermetic: fake LLM.
"""
import asyncio

import pytest

import app.core.llm as llm_mod
from app.agents import lesson_agent


def _grade(monkeypatch, reply):
    async def fake_chat(messages, **kwargs):
        return reply

    monkeypatch.setattr(llm_mod, "chat", fake_chat)
    return asyncio.run(lesson_agent.grade_answer("What is a qubit?", "A two-level system.", "a bit"))


@pytest.mark.parametrize("reply", [
    "Sure! The student did well.",          # prose, no JSON
    '{"passed": true, "feedback": ',        # truncated
    "[true]",                               # JSON, but not an object
    "",
])
def test_unreadable_reply_is_not_a_pass(monkeypatch, reply):
    result = _grade(monkeypatch, reply)
    assert result["passed"] is False
    assert result["feedback"] == lesson_agent.UNGRADED_FEEDBACK


@pytest.mark.parametrize("value", ['"true"', '"false"', '"yes"', "1"])
def test_only_json_true_passes(monkeypatch, value):
    result = _grade(monkeypatch, '{"passed": %s, "feedback": "x"}' % value)
    assert result["passed"] is False


def test_a_real_pass_passes(monkeypatch):
    result = _grade(monkeypatch, '```json\n{"passed": true, "feedback": "Right."}\n```')
    assert result == {"passed": True, "feedback": "Right."}
