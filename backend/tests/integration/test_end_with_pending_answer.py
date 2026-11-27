"""Ending an exam while an answer is pending doesn't strand that answer.

LLM down → the answer is saved ungraded → the student ends the exam → the LLM
recovers → the backfill grades the answer and the session's average includes it.
"""
import itertools

from _util import run_isolated, cleanup_session

import app.core.llm as llm_mod
from app.core.llm_errors import LLMUnavailable
from app.core import grading_backfill
from app.db import audit_db
from app.routes.exam import start_exam, submit_answer, end_exam_early, StartRequest, AnswerRequest


def test_pending_answer_is_graded_after_the_exam_ends(monkeypatch):
    state = {"down": False, "q": itertools.count(1)}

    async def chat(messages, *, call_type=None, **kwargs):
        if state["down"]:
            raise LLMUnavailable("simulated outage")
        if call_type == "exam_grade":
            return '{"accuracy": 8, "reasoning": 6, "clarity": 7, "justification": "ok", "ideal_answer": "i"}'
        return f"Generated question #{next(state['q'])}"

    monkeypatch.setattr(llm_mod, "chat", chat)

    async def body():
        sid = (await start_exam(StartRequest(student_name="End Pending", topic="grover", version="V2")))["session_id"]
        state["down"] = True
        resp = await submit_answer(AnswerRequest(session_id=sid, student_answer="late answer"))
        assert resp["status"] == "saved_pending_grading"

        await end_exam_early({"session_id": sid})
        assert (await audit_db.get_session_row(sid))["status"] == "completed"

        state["down"] = False
        await grading_backfill.sweep()

        turns = await audit_db.get_session_turns(sid)
        assert len(turns) == 1 and turns[0]["graded"] is True
        assert turns[0]["score_total"] == 7.0
        sessions = {s["session_id"]: s for s in await audit_db.get_all_sessions(100)}
        assert sessions[sid]["avg_score"] == 7.0

        await grading_backfill.sweep()        # a second sweep finds nothing to redo
        assert len(await audit_db.get_session_turns(sid)) == 1
        await cleanup_session(sid)

    run_isolated(body)
