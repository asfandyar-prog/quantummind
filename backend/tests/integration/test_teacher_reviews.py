"""Append-only teacher reviews never duplicate the turn they review.

A turn reviewed twice must still appear once — in the teacher transcript and in
the active-exam state rebuilt from Postgres — carrying the latest review.
"""
import _util
from _util import run_isolated, cleanup_session

from app.core import exam_state
from app.db import audit_db, redis_client


def test_turn_reviewed_twice_is_listed_once():
    async def body():
        sid = await audit_db.create_session("Two Reviews", "grover", "V2")
        await audit_db.set_in_flight(sid, "Q1", 1, False, 0)
        turn_id = await audit_db.advance_exam(
            session_id=sid, turn_number=1, question="Q1", student_answer="A1",
            score_accuracy=6.0, score_reasoning=6.0, score_clarity=6.0,
            ai_justification="j", ideal_answer="i", is_followup=False,
            next_question="Q2", next_turn_number=2,
            next_is_followup=False, next_followup_count=0,
        )

        await _review(sid, turn_id, "accepted")
        await _review(sid, turn_id, "modified", teacher=(9.0, 8.0, 7.0))

        turns = await audit_db.get_session_turns(sid)
        assert len(turns) == 1                           # not one row per review
        assert turns[0]["review_action"] == "modified"   # the latest review wins
        assert turns[0]["teacher_accuracy"] == 9.0

        await redis_client.get_redis().delete(f"exam:{sid}")
        state = await exam_state.load_active(sid)
        assert len(state["turns"]) == 1
        assert state["total_score"] == 6.0               # counted once

        await cleanup_session(sid)

    run_isolated(body)


async def _review(session_id, turn_id, action, teacher=(None, None, None)):
    await audit_db.log_teacher_review(
        session_id=session_id, turn_id=turn_id,
        ai_accuracy=6.0, ai_reasoning=6.0, ai_clarity=6.0,
        teacher_accuracy=teacher[0], teacher_reasoning=teacher[1], teacher_clarity=teacher[2],
        teacher_feedback="", teacher_notes="", action=action,
    )
