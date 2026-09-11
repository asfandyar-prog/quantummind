"""/status hands a saved-pending answer's result back once it is graded.

This is the contract the exam UI polls: awaiting_grade while the grader is down,
then the graded turn (scores, justification, ideal answer) plus the next
question once the backfill worker has caught up.
"""
import _util
from _util import run_isolated, cleanup_session

import app.core.llm as llm_mod
from app.core import grading_backfill
from app.core.llm_errors import LLMUnavailable
from app.routes.exam import start_exam, submit_answer, session_status, StartRequest, AnswerRequest


def _chat(mode):
    async def chat(messages, *, call_type=None, **kwargs):
        if mode["down"]:
            raise LLMUnavailable("simulated outage")
        if call_type == "exam_grade":
            return ('{"accuracy": 8, "reasoning": 7, "clarity": 9, '
                    '"justification": "clear", "ideal_answer": "ideal"}')
        return "Next question"
    return chat


def test_status_returns_the_pending_answers_result_once_graded(monkeypatch):
    mode = {"down": False}
    monkeypatch.setattr(llm_mod, "chat", _chat(mode))

    async def body():
        sid = (await start_exam(StartRequest(student_name="Polling", topic="grover", version="V2")))["session_id"]
        mode["down"] = True
        saved = await submit_answer(AnswerRequest(session_id=sid, student_answer="an answer"))
        turn_id = saved["turn_id"]

        waiting = await session_status(sid, turn_id=turn_id)
        assert waiting["awaiting_grade"] is True
        assert waiting["turn"] is None

        mode["down"] = False
        await grading_backfill.reconcile_session(sid)
        done = await session_status(sid, turn_id=turn_id)
        assert done["awaiting_grade"] is False
        assert done["current_question"] == "Next question"
        assert done["turn"]["scores"]["total"] == 8.0
        assert done["turn"]["needs_review"] is False
        assert done["turn"]["ideal_answer"] == "ideal"

        await cleanup_session(sid)

    run_isolated(body)
