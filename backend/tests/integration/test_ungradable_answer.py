"""An answer the grader can't score is recorded without scores and flagged.

The exam moves on, no follow-up is triggered off a missing score, and nothing
in the audit trail looks like a real grade. The backfill finalizes such an
answer once instead of retrying it on every sweep.
"""
import _util
from _util import run_isolated, cleanup_session

import app.core.llm as llm_mod
from app.core import grading_backfill
from app.core.llm_errors import LLMUnavailable
from app.db import audit_db
from app.routes.exam import start_exam, submit_answer, StartRequest, AnswerRequest


def _chat(mode):
    async def chat(messages, *, call_type=None, **kwargs):
        if mode["down"]:
            raise LLMUnavailable("simulated outage")
        if call_type == "exam_grade":
            return "I would rate this answer quite highly overall."   # never JSON
        return "Next question"
    return chat


def test_ungradable_answer_is_recorded_without_scores(monkeypatch):
    mode = {"down": False}
    monkeypatch.setattr(llm_mod, "chat", _chat(mode))

    async def body():
        started = await start_exam(StartRequest(student_name="Ungradable", topic="grover", version="V3"))
        sid = started["session_id"]
        resp = await submit_answer(AnswerRequest(session_id=sid, student_answer="an answer"))

        assert resp["status"] == "graded"
        assert resp["scores"] is None and resp["needs_review"] is True
        assert resp["is_followup"] is False               # no follow-up off a missing score
        turn = (await audit_db.get_session_turns(sid))[0]
        assert turn["graded"] is True and turn["score_total"] is None
        assert (await audit_db.get_session_row(sid))["current_turn_number"] == 2
        assert (await audit_db.get_research_stats())["ungradable_answers"] >= 1

        await cleanup_session(sid)

    run_isolated(body)


def test_backfill_finalizes_an_ungradable_pending_answer(monkeypatch):
    mode = {"down": False}
    monkeypatch.setattr(llm_mod, "chat", _chat(mode))

    async def body():
        started = await start_exam(StartRequest(student_name="Ungradable Later", topic="grover", version="V2"))
        sid = started["session_id"]
        mode["down"] = True
        pending = await submit_answer(AnswerRequest(session_id=sid, student_answer="an answer"))
        assert pending["status"] == "saved_pending_grading"

        mode["down"] = False
        await grading_backfill.reconcile_session(sid)
        turn = (await audit_db.get_session_turns(sid))[0]
        assert turn["graded"] is True and turn["score_total"] is None   # finalized, not retried forever
        assert await audit_db.get_pending_turn(sid) is None

        await cleanup_session(sid)

    run_isolated(body)
