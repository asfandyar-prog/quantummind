"""Phase 1 focused regressions (need Postgres + Redis):
  - end_session is a single, idempotent UPDATE (the old INSERT-dup-PK bug).
  - load_active reconstructs the full active state from Postgres with Redis empty.
"""
import _util
from _util import run_isolated, cleanup_session

from sqlalchemy import text

from app.db import audit_db, database, redis_client
from app.core import exam_state


def test_end_session_single_idempotent_update():
    async def body():
        sid = await audit_db.create_session("Unit End", "grover", "V2")

        # Two calls must not error and must not create a duplicate row (the old
        # end_session did INSERT-then-UPDATE on the same PK).
        await audit_db.end_session(sid, 7.5, 3)
        await audit_db.end_session(sid, 8.0, 4)  # idempotent re-run

        async with database.get_engine().connect() as conn:
            count = (await conn.execute(
                text("SELECT COUNT(*) FROM exam_sessions WHERE session_id=:s"), {"s": sid}
            )).scalar()
        assert count == 1                          # single row — no dup-PK INSERT

        row = await audit_db.get_session_row(sid)
        assert row["status"] == "completed"

        await cleanup_session(sid)

    run_isolated(body)


def test_load_active_reconstructs_with_redis_empty():
    async def body():
        sid = await audit_db.create_session("Unit Reconstruct", "grover", "V2")
        # one completed turn (weak sub-scores) + advance the in-flight question
        await audit_db.advance_exam(
            session_id=sid, turn_number=1, question="Q1", student_answer="A1",
            score_accuracy=4.0, score_reasoning=3.0, score_clarity=2.0,
            ai_justification="j", ideal_answer="i", is_followup=False,
            next_question="Q-current", next_turn_number=2,
            next_is_followup=False, next_followup_count=0,
        )

        # Redis empty for this session → reconstruction must come from Postgres.
        await redis_client.get_redis().delete(f"exam:{sid}")

        state = await exam_state.load_active(sid)
        assert state is not None
        assert state["current_question"] == "Q-current"
        assert state["turn_number"] == 2
        assert len(state["turns"]) == 1
        assert state["turns"][0]["score"] == 3.0           # (4+3+2)/3
        # weak areas re-derived from the turn's sub-scores
        assert set(state["weak_areas"]) == {
            "factual accuracy", "conceptual reasoning", "answer clarity and structure"
        }

        await cleanup_session(sid)

    run_isolated(body)
