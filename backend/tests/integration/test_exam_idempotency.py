"""An answer is recorded once, never twice.

Two concurrent submits for the same turn both get through grading; the guarded
advance lets exactly one write the turn and the other gets a 409 carrying the
real current question. A stale Redis hot copy (a Redis write that failed after
the Postgres commit) is caught the same way instead of inserting a duplicate.
"""
import asyncio
import json

import pytest

import _util
from _util import run_isolated, cleanup_session

import app.core.llm as llm_mod
from app.core import exam_state
from app.db import audit_db, redis_client
from app.routes.exam import start_exam, submit_answer, StartRequest, AnswerRequest


def _slow_chat():
    """Fake llm.chat that yields long enough for two submits to interleave."""
    counter = {"q": 0}

    async def chat(messages, *, call_type=None, **kwargs):
        await asyncio.sleep(0.2)
        if call_type == "exam_grade":
            return ('{"accuracy": 8, "reasoning": 7, "clarity": 9, '
                    '"justification": "solid", "ideal_answer": "ideal"}')
        if call_type == "exam_question":
            counter["q"] += 1
            return f"Generated question #{counter['q']}"
        return "generic"

    return chat


def _status(resp):
    return getattr(resp, "status_code", 200)


def test_concurrent_submits_record_one_turn(monkeypatch):
    monkeypatch.setattr(llm_mod, "chat", _slow_chat())

    async def body():
        started = await start_exam(StartRequest(
            student_name="Double Submit", topic="superposition", version="V2"))
        sid = started["session_id"]

        a, b = await asyncio.gather(
            submit_answer(AnswerRequest(session_id=sid, student_answer="first click")),
            submit_answer(AnswerRequest(session_id=sid, student_answer="second click")),
        )

        assert sorted([_status(a), _status(b)]) == [200, 409]
        turns = await audit_db.get_session_turns(sid)
        assert [t["turn_number"] for t in turns] == [1]      # recorded exactly once
        row = await audit_db.get_session_row(sid)
        assert row["current_turn_number"] == 2

        stale = json.loads((a if _status(a) == 409 else b).body)
        assert stale["status"] == "stale"
        assert stale["turn_number"] == 2
        assert stale["current_question"] == row["current_question"]

        await cleanup_session(sid)

    run_isolated(body)


def test_stale_hot_copy_does_not_duplicate_turn(monkeypatch):
    monkeypatch.setattr(llm_mod, "chat", _slow_chat())

    async def body():
        started = await start_exam(StartRequest(
            student_name="Stale Cache", topic="entanglement", version="V2"))
        sid = started["session_id"]
        turn_one_state = await exam_state.load_active(sid)

        first = await submit_answer(AnswerRequest(session_id=sid, student_answer="answer one"))
        assert first["status"] == "graded"

        # A Redis write that failed after the Postgres commit leaves turn 1 cached.
        await exam_state.save_active(sid, turn_one_state)

        replay = await submit_answer(AnswerRequest(session_id=sid, student_answer="answer one again"))
        assert _status(replay) == 409
        assert len(await audit_db.get_session_turns(sid)) == 1
        assert await redis_client.get_redis().get(f"exam:{sid}") is None   # stale copy dropped
        assert (await exam_state.load_active(sid))["turn_number"] == 2

        await cleanup_session(sid)

    run_isolated(body)


def test_duplicate_turn_insert_is_rejected():
    async def body():
        sid = await audit_db.create_session("Unique Turn", "grover", "V2")
        await audit_db.set_in_flight(sid, "Q1", 1, False, 0)
        await audit_db.create_pending_turn(sid, 1, "Q1", "an answer", False)

        with pytest.raises(audit_db.StaleTurn):
            await audit_db.create_pending_turn(sid, 1, "Q1", "the same answer again", False)
        assert len(await audit_db.get_session_turns(sid)) == 1

        await cleanup_session(sid)

    run_isolated(body)
