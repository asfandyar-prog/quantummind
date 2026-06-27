"""Phase 1 proof-of-done: two workers share one session.

Worker A starts and seeds an exam; worker B — a separate data-layer instance
against the same Neon + Upstash — sees the identical state (via the shared Redis
hot copy, no flush) and continues the exam correctly.
"""
import _util
from _util import run_isolated, cleanup_session, grading_chat_factory

import app.core.llm as llm_mod
from app.core import exam_state
from app.db import audit_db
from app.routes.exam import start_exam, submit_answer, StartRequest, AnswerRequest


def test_two_workers_share_session(monkeypatch):
    monkeypatch.setattr(llm_mod, "chat", grading_chat_factory())

    async def body():
        # ── worker A: start + answer one question ───────────────────────────
        started = await start_exam(StartRequest(
            student_name="Two Workers", topic="entanglement", version="V2"))
        sid = started["session_id"]
        a1 = await submit_answer(AnswerRequest(session_id=sid, student_answer="answer from A"))
        q2 = a1["next_question"]
        assert q2

        # ── worker B: a different instance, same Neon + Upstash ─────────────
        # Dispose A's singletons; B creates its own lazily. We do NOT flush
        # Redis — B must see the shared hot copy A wrote.
        await _util.dispose_all()

        view = await exam_state.load_active(sid)
        assert view is not None
        assert view["current_question"] == q2     # identical view across workers
        assert len(view["turns"]) == 1

        # B submits the next answer; it continues correctly
        a2 = await submit_answer(AnswerRequest(session_id=sid, student_answer="answer from B"))
        assert a2["next_question"] and a2["next_question"] != q2

        # both turns are in the shared Postgres
        turns = await audit_db.get_session_turns(sid)
        assert len(turns) == 2
        assert [t["turn_number"] for t in turns] == [1, 2]

        await cleanup_session(sid)

    run_isolated(body)
