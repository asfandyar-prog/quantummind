"""An answer saved during an outage is still graded after the exam ends early.

Hermetic: the repository functions and the grader are replaced with fakes, so
this checks the backfill's decisions, not SQL (the integration tier does that).
"""
import asyncio

from app.core import grading_backfill
from app.core.llm_errors import LLMUnavailable
from app.db import audit_db

TURN = {"turn_id": "t1", "session_id": "s1", "turn_number": 3,
        "question": "Q3", "student_answer": "late answer", "graded": False}


def _setup(monkeypatch, grade):
    calls = []

    async def pending(limit):        return []
    async def ended(limit):          return [TURN]
    async def session_row(sid):      return {"topic": "grover", "status": "completed"}
    async def finalize(turn_id, *scores):
        calls.append(("finalize", turn_id, scores[:3])); return True
    async def refresh(sid):          calls.append(("refresh_avg", sid))

    monkeypatch.setattr(audit_db, "get_pending_turns", pending)
    monkeypatch.setattr(audit_db, "get_ungraded_turns_of_ended_sessions", ended)
    monkeypatch.setattr(audit_db, "get_session_row", session_row)
    monkeypatch.setattr(audit_db, "finalize_grade", finalize)
    monkeypatch.setattr(audit_db, "refresh_session_average", refresh)
    monkeypatch.setattr(grading_backfill, "grade_answer", grade)
    return calls


def test_ended_session_answer_is_graded_and_averaged(monkeypatch):
    async def grade(topic, question, answer):
        return {"accuracy": 8.0, "reasoning": 6.0, "clarity": 7.0,
                "justification": "ok", "ideal_answer": "ideal"}

    calls = _setup(monkeypatch, grade)
    asyncio.run(grading_backfill.sweep())
    assert calls == [("finalize", "t1", (8.0, 6.0, 7.0)), ("refresh_avg", "s1")]


def test_still_down_leaves_it_for_the_next_sweep(monkeypatch):
    async def grade(topic, question, answer):
        raise LLMUnavailable("still down")

    calls = _setup(monkeypatch, grade)
    asyncio.run(grading_backfill.sweep())
    assert calls == []            # not finalized, so it is picked up again
