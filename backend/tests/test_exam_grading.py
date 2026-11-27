"""Grading never invents a score.

The grader's JSON is parsed tolerantly (fences, prose around it) and clamped to
0-10. A reply with missing or non-numeric scores gets one corrective retry; if
that fails too, grading raises GradingFailed instead of defaulting to 5.0.
"""
import asyncio

import pytest

import app.core.llm as llm_mod
from app.agents import exam_agent

GOOD = '{"accuracy": 8, "reasoning": 7, "clarity": 9, "justification": "ok", "ideal_answer": "ideal"}'


def test_parse_accepts_fenced_and_wrapped_json():
    fenced = "```json\n" + GOOD + "\n```"
    wrapped = "Here is the grading:\n" + GOOD + "\nHope that helps."
    for reply in (GOOD, fenced, wrapped):
        parsed = exam_agent.parse_grade(reply)
        assert (parsed["accuracy"], parsed["reasoning"], parsed["clarity"]) == (8.0, 7.0, 9.0)


def test_parse_clamps_out_of_range_scores():
    parsed = exam_agent.parse_grade('{"accuracy": 14, "reasoning": -2, "clarity": "7.5"}')
    assert (parsed["accuracy"], parsed["reasoning"], parsed["clarity"]) == (10.0, 0.0, 7.5)


@pytest.mark.parametrize("reply", [
    "not json at all",
    '{"accuracy": 8, "reasoning": 7}',                    # a dimension missing
    '{"accuracy": "high", "reasoning": 7, "clarity": 9}',  # not a number
    '{"accuracy": null, "reasoning": 7, "clarity": 9}',
    '{"accuracy": true, "reasoning": 7, "clarity": 9}',
    "[8, 7, 9]",
])
def test_parse_rejects_unusable_replies(reply):
    assert exam_agent.parse_grade(reply) is None


def _fake_chat(replies, calls):
    async def chat(messages, **kwargs):
        calls.append(messages)
        return replies[min(len(calls), len(replies)) - 1]
    return chat


def test_unusable_reply_gets_one_corrective_retry(monkeypatch):
    calls = []
    monkeypatch.setattr(llm_mod, "chat", _fake_chat(["Sure! I'd say about an 8.", GOOD], calls))
    res = asyncio.run(exam_agent.grade_answer("entanglement", "What is a Bell state?", "an answer"))
    assert len(calls) == 2
    assert res["total"] == pytest.approx(8.0)
    assert type(calls[1][-2]).__name__ == "AIMessage"  # the bad reply is shown back to the model


def test_grading_fails_instead_of_inventing_scores(monkeypatch):
    calls = []
    monkeypatch.setattr(llm_mod, "chat", _fake_chat(["nope", "still nope"], calls))
    with pytest.raises(exam_agent.GradingFailed):
        asyncio.run(exam_agent.grade_answer("entanglement", "What is a Bell state?", "an answer"))
    assert len(calls) == 2                               # one retry, not a loop


def test_ungraded_answers_are_left_out_of_decisions_and_averages():
    assert exam_agent.decide_followup(None, "V3", 0, 1, [])["should_followup"] is False
    assert exam_agent.average_score([8.0, None, 6.0]) == 7.0
    assert exam_agent.average_score([None]) == 0.0
