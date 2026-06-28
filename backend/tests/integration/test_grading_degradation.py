"""Phase 2 commit 4: graceful exam-grading degradation (Neon + Upstash).

The LLM is simulated as down at answer time: the answer must be persisted durably
(graded=false) and the response is saved_pending_grading — never a 500, never lost.
When the LLM recovers, the backfill worker grades the pending turn and advances
the exam. The /status endpoint reflects awaiting_grade throughout.
"""
import itertools

import _util
from _util import run_isolated, cleanup_session

import app.core.llm as llm_mod
from app.core.llm_errors import LLMUnavailable
from app.core import grading_backfill
from app.db import audit_db
from app.routes.exam import (
    start_exam, submit_answer, session_status, StartRequest, AnswerRequest,
)


def _make_chat():
    """A switchable fake llm.chat: raise when 'down', else canned grade/question."""
    state = {"mode": "up", "q": itertools.count(1)}

    async def chat(messages, *, call_type=None, **kwargs):
        if state["mode"] == "down":
            raise LLMUnavailable("simulated outage")
        if call_type == "exam_grade":
            return ('{"accuracy": 8, "reasoning": 7, "clarity": 9, '
                    '"justification": "ok", "ideal_answer": "ideal"}')
        if call_type == "exam_question":
            return f"Generated question #{next(state['q'])}"
        return "generic"

    return state, chat


def test_answer_never_lost_on_llm_outage(monkeypatch):
    ctl, chat = _make_chat()
    monkeypatch.setattr(llm_mod, "chat", chat)

    async def body():
        ctl["mode"] = "up"
        started = await start_exam(StartRequest(
            student_name="Degrade Test", topic="superposition", version="V2"))
        sid = started["session_id"]

        ctl["mode"] = "down"  # LLM goes down before grading
        resp = await submit_answer(AnswerRequest(session_id=sid, student_answer="my answer"))

        # safe failure mode — no exception, a clear pending response
        assert resp["status"] == "saved_pending_grading"
        assert resp["awaiting_grade"] is True
        assert resp["exam_complete"] is False

        # the answer is durable in Postgres, graded=false
        pending = await audit_db.get_pending_turn(sid)
        assert pending is not None
        assert pending["graded"] is False
        assert pending["student_answer"] == "my answer"

        # idempotency: re-submitting while pending returns pending, no new turn
        resp2 = await submit_answer(AnswerRequest(session_id=sid, student_answer="my answer"))
        assert resp2["status"] == "saved_pending_grading"
        turns = await audit_db.get_session_turns(sid)
        assert len(turns) == 1

        await cleanup_session(sid)

    run_isolated(body)


def test_backfill_grades_and_advances(monkeypatch):
    ctl, chat = _make_chat()
    monkeypatch.setattr(llm_mod, "chat", chat)

    async def body():
        ctl["mode"] = "up"
        started = await start_exam(StartRequest(
            student_name="Backfill Test", topic="entanglement", version="V2"))
        sid = started["session_id"]

        ctl["mode"] = "down"
        await submit_answer(AnswerRequest(session_id=sid, student_answer="answer one"))
        assert (await audit_db.get_pending_turn(sid))["graded"] is False

        # LLM recovers; one reconciliation grades + advances
        ctl["mode"] = "up"
        await grading_backfill.reconcile_session(sid)

        turns = await audit_db.get_session_turns(sid)
        assert len(turns) == 1
        assert turns[0]["graded"] is True
        assert turns[0]["score_total"] == 8.0          # (8+7+9)/3

        row = await audit_db.get_session_row(sid)
        assert row["status"] == "active"
        assert row["current_turn_number"] == 2          # advanced past the graded turn
        assert row["current_question"]                  # a next question was generated
        assert await audit_db.get_pending_turn(sid) is None   # no longer stuck

        # reconciling again is a no-op (idempotent — no double-advance)
        await grading_backfill.reconcile_session(sid)
        row2 = await audit_db.get_session_row(sid)
        assert row2["current_turn_number"] == 2
        assert len(await audit_db.get_session_turns(sid)) == 1

        await cleanup_session(sid)

    run_isolated(body)


def test_status_endpoint_contract(monkeypatch):
    ctl, chat = _make_chat()
    monkeypatch.setattr(llm_mod, "chat", chat)

    async def body():
        ctl["mode"] = "up"
        started = await start_exam(StartRequest(
            student_name="Status Test", topic="grover", version="V2"))
        sid = started["session_id"]

        ctl["mode"] = "down"
        await submit_answer(AnswerRequest(session_id=sid, student_answer="answer"))

        # while pending: awaiting_grade true
        s1 = await session_status(sid)
        assert s1["awaiting_grade"] is True
        assert s1["exam_complete"] is False
        assert s1["graded"] is False

        # after backfill: awaiting_grade false, next question available
        ctl["mode"] = "up"
        await grading_backfill.reconcile_session(sid)
        s2 = await session_status(sid)
        assert s2["awaiting_grade"] is False
        assert s2["exam_complete"] is False
        assert s2["current_question"]
        assert s2["turn_number"] == 2

        await cleanup_session(sid)

    run_isolated(body)
