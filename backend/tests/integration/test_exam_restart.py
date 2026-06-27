"""Phase 1 proof-of-done: a process death mid-exam loses nothing.

Start an exam, answer one question, then simulate a real restart — Redis loses
the hot copy and every data-layer singleton is disposed — and prove the exam is
fully reconstructable from Postgres alone: the in-flight question and the scored
turn survive, and the exam continues correctly.
"""
import _util
from _util import run_isolated, cleanup_session, grading_chat_factory

import app.core.llm as llm_mod
from app.core import exam_state
from app.db import audit_db, redis_client
from app.routes.exam import start_exam, submit_answer, StartRequest, AnswerRequest


def test_exam_restart(monkeypatch):
    monkeypatch.setattr(llm_mod, "chat", grading_chat_factory())

    async def body():
        # ── boot #1: start an exam and answer one question ──────────────────
        started = await start_exam(StartRequest(
            student_name="Restart Test", topic="superposition", version="V2"))
        sid = started["session_id"]
        q1 = started["question"]

        a1 = await submit_answer(AnswerRequest(session_id=sid, student_answer="my first answer"))
        q2 = a1["next_question"]
        score1 = a1["scores"]["total"]
        assert q2 and q2 != q1            # advanced to a new in-flight question
        assert not a1["exam_complete"]

        # ── simulate a REAL restart ─────────────────────────────────────────
        # 1) Redis loses this session's hot copy (eviction/flush).
        await redis_client.get_redis().delete(f"exam:{sid}")
        # 2) the process dies: dispose engine + redis + checkpointer, clear graph caches.
        await _util.dispose_all()
        # 3) fresh data-layer instances are created lazily on the next call.

        # ── reconstruct from Postgres ALONE ─────────────────────────────────
        rebuilt = await exam_state.load_active(sid)
        assert rebuilt is not None, "active exam must be recoverable from Postgres after Redis loss"
        assert rebuilt["current_question"] == q2, "the in-flight question must survive the restart"
        assert len(rebuilt["turns"]) == 1, "the answered turn must be present"
        assert rebuilt["turns"][0]["score"] == score1, "the scored answer must be preserved"
        assert rebuilt["turn_number"] == 2

        # the durable turn row itself is intact, with its scores
        turns = await audit_db.get_session_turns(sid)
        assert len(turns) == 1
        assert turns[0]["turn_number"] == 1
        assert turns[0]["score_total"] == score1

        # ── resume: the next answer continues correctly ─────────────────────
        a2 = await submit_answer(AnswerRequest(session_id=sid, student_answer="my second answer"))
        assert a2["next_question"] and a2["next_question"] != q2
        turns_after = await audit_db.get_session_turns(sid)
        assert len(turns_after) == 2
        assert [t["turn_number"] for t in turns_after] == [1, 2]

        await cleanup_session(sid)

    run_isolated(body)
