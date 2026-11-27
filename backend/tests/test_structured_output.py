"""Router, lesson-grade and exam-grade replies are validated with Pydantic.

An invalid reply gets exactly one corrective retry that shows the model its
own reply; if that is invalid too, each caller fails closed. Hermetic: fake LLM.
"""
import asyncio

import pytest

import app.core.llm as llm_mod
from app.agents import exam_agent, lesson_agent, orchestrator
from app.core.structured import ExamGrade, LessonGrade, RouteDecision, parse_model


def _replies(monkeypatch, replies):
    calls = []
    it = iter(replies)

    async def fake_chat(messages, **kwargs):
        calls.append(messages)
        return next(it)

    monkeypatch.setattr(llm_mod, "chat", fake_chat)
    return calls


# ── schemas ──

def test_route_schema_accepts_only_known_labels():
    assert parse_model(RouteDecision, '{"agent": "code", "reason": "r"}').agent == "code"
    assert parse_model(RouteDecision, '{"agent": "review_bot"}') is None
    assert parse_model(RouteDecision, '{"reason": "no agent"}') is None


@pytest.mark.parametrize("value", ['"true"', "1", "null"])
def test_lesson_schema_needs_a_real_boolean(value):
    assert parse_model(LessonGrade, '{"passed": %s}' % value) is None


@pytest.mark.parametrize("reply", [
    '{"accuracy": true, "reasoning": 5, "clarity": 5}',
    '{"accuracy": NaN, "reasoning": 5, "clarity": 5}',
    '{"accuracy": "high", "reasoning": 5, "clarity": 5}',
    '{"reasoning": 5, "clarity": 5}',
])
def test_exam_schema_rejects_bad_scores(reply):
    assert parse_model(ExamGrade, reply) is None


def test_exam_schema_clamps():
    g = parse_model(ExamGrade, '{"accuracy": 14, "reasoning": -1, "clarity": "7.5"}')
    assert (g.accuracy, g.reasoning, g.clarity) == (10.0, 0.0, 7.5)


# ── re-ask once, then fail closed ──

def test_router_reasks_once_then_uses_the_valid_reply(monkeypatch):
    calls = _replies(monkeypatch, ['{"agent": "review_bot"}', '{"agent": "code", "reason": "r"}'])
    assert asyncio.run(orchestrator.route("fix my circuit")) == "code"
    assert len(calls) == 2
    assert type(calls[1][-2]).__name__ == "AIMessage"      # its bad reply shown back


def test_router_fails_closed_to_theory(monkeypatch):
    calls = _replies(monkeypatch, ["not json", '{"agent": "nope"}'])
    assert asyncio.run(orchestrator.route("hi")) == "theory"
    assert len(calls) == 2


def test_lesson_grade_reasks_then_accepts(monkeypatch):
    calls = _replies(monkeypatch, ['{"passed": "true"}', '{"passed": true, "feedback": "ok"}'])
    result = asyncio.run(lesson_agent.grade_answer("q", "a", "a"))
    assert result == {"passed": True, "feedback": "ok"} and len(calls) == 2


def test_lesson_grade_fails_closed(monkeypatch):
    calls = _replies(monkeypatch, ['{"passed": "yes"}', "Sure, it passes!"])
    result = asyncio.run(lesson_agent.grade_answer("q", "a", "a"))
    assert result["passed"] is False and len(calls) == 2


def test_exam_grade_fails_closed(monkeypatch):
    calls = _replies(monkeypatch, ['{"accuracy": 9}', '{"accuracy": 9, "reasoning": true, "clarity": 9}'])
    with pytest.raises(exam_agent.GradingFailed):
        asyncio.run(exam_agent.grade_answer("t", "q", "a"))
    assert len(calls) == 2
