"""Teacher reviews: append-only, never duplicate a turn, never trust client AI scores.

A turn reviewed twice must still appear once, in the teacher transcript and in
the active-exam state rebuilt from Postgres, carrying the latest review. The
"AI said" half of each review is read from the stored turn, not the request.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import text

import _util
from _util import run_isolated, cleanup_session

from app.core import exam_state
from app.core.config import settings
from app.db import audit_db, database, redis_client
from app.routes.exam import teacher_review, ReviewRequest


async def _session_with_scored_turn(name):
    sid = await audit_db.create_session(name, "grover", "V2")
    await audit_db.set_in_flight(sid, "Q1", 1, False, 0)
    turn_id = await audit_db.advance_exam(
        session_id=sid, turn_number=1, question="Q1", student_answer="A1",
        score_accuracy=6.0, score_reasoning=6.0, score_clarity=6.0,
        ai_justification="j", ideal_answer="i", is_followup=False,
        next_question="Q2", next_turn_number=2,
        next_is_followup=False, next_followup_count=0,
    )
    return sid, turn_id


def test_turn_reviewed_twice_is_listed_once():
    async def body():
        sid, turn_id = await _session_with_scored_turn("Two Reviews")
        await audit_db.log_teacher_review(sid, turn_id, None, None, None, "", "", "accepted")
        await audit_db.log_teacher_review(sid, turn_id, 9.0, 8.0, 7.0, "", "", "modified")

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


def test_review_stores_the_turns_ai_scores_not_the_clients(monkeypatch):
    monkeypatch.setattr(settings, "teacher_password", "pw")

    async def body():
        sid, turn_id = await _session_with_scored_turn("Forged Review")
        forged = ReviewRequest(
            session_id=sid, turn_id=turn_id, action="modified",
            teacher_accuracy=9, teacher_reasoning=9, teacher_clarity=9,
            ai_accuracy=0, ai_reasoning=0, ai_clarity=0,   # an old client's fields: ignored
        )
        await teacher_review(forged, x_teacher_password="pw")

        async with database.get_engine().connect() as conn:
            row = (await conn.execute(text(
                "SELECT ai_accuracy, delta_accuracy FROM teacher_reviews WHERE turn_id=:t"
            ), {"t": turn_id})).one()
        assert float(row.ai_accuracy) == 6.0
        assert float(row.delta_accuracy) == 3.0

        with pytest.raises(HTTPException) as missing:
            await teacher_review(
                ReviewRequest(session_id=sid, turn_id="no-such-turn", action="accepted"),
                x_teacher_password="pw",
            )
        assert missing.value.status_code == 404

        await cleanup_session(sid)

    run_isolated(body)
