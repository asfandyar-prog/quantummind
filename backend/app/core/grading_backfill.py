# ── app/core/grading_backfill.py ─────────────────────────────
# Asynchronous grading backfill — the other half of graceful degradation.
#
# When the LLM is unavailable at answer time, submit_answer persists the answer
# durably as a pending turn (graded=false) and returns "saved_pending_grading".
# This worker reconciles such turns from Postgres (the source of truth):
#   - ungraded                  → grade it, then advance
#   - graded but not advanced   → advance it (generate next question / complete)
#
# Idempotency (so it never double-grades or double-advances across workers):
#   - finalize_grade flips graded false→true with a conditional UPDATE — only one
#     worker can claim a given turn.
#   - advance_in_flight_if / complete_if only mutate while the session is still
#     parked at the expected turn — a second worker's advance is a no-op.
#
# Runs as one lifespan task per process: a startup sweep then a periodic sweep.
# Multiple processes are safe (the conditional UPDATEs serialize the outcome).

import asyncio
import logging

from app.core.config import settings
from app.core.llm_errors import LLMUnavailable, LLMBusy
from app.agents.exam_agent import (
    grade_answer, generate_question, decide_followup, identify_weak_areas,
)
from app.db import audit_db
from app.core import exam_state

logger = logging.getLogger("quantummind.backfill")

_task: asyncio.Task | None = None


async def reconcile_session(session_id: str) -> None:
    """Bring one session's stuck turn to completion (grade and/or advance)."""
    row = await audit_db.get_session_row(session_id)
    if row is None or row["status"] != "active":
        return
    cur = row["current_turn_number"]
    turns = await audit_db.get_session_turns(session_id)
    stuck = next((t for t in turns if t["turn_number"] == cur), None)
    if stuck is None:
        return  # nothing answered at the current position — not stuck

    topic, version = row["topic"], row["version"]

    # ── Step 1: grade if ungraded (idempotent claim) ────────────────────────
    if not stuck["graded"]:
        try:
            grading = await grade_answer(topic, stuck["question"], stuck["student_answer"])
        except (LLMUnavailable, LLMBusy):
            return  # still down — try again next sweep
        claimed = await audit_db.finalize_grade(
            stuck["turn_id"], grading["accuracy"], grading["reasoning"],
            grading["clarity"], grading["justification"], grading["ideal_answer"],
        )
        if not claimed:
            return  # another worker graded it; a later sweep will advance
        turns = await audit_db.get_session_turns(session_id)
        stuck = next(t for t in turns if t["turn_number"] == cur)

    # ── Step 2: advance (graded, but session not advanced) ──────────────────
    weak_areas: list[str] = []
    total_score = 0.0
    prev_qa: list[dict] = []
    for t in turns:
        total_score += t["score_total"] or 0.0
        prev_qa.append({"question": t["question"], "answer": t["student_answer"], "score": t["score_total"]})
        for a in identify_weak_areas(
            t["score_accuracy"] or 0.0, t["score_reasoning"] or 0.0, t["score_clarity"] or 0.0
        ):
            if a not in weak_areas:
                weak_areas.append(a)

    stuck_weak = identify_weak_areas(
        stuck["score_accuracy"] or 0.0, stuck["score_reasoning"] or 0.0, stuck["score_clarity"] or 0.0
    )
    decision = decide_followup(
        score_total=stuck["score_total"] or 0.0, version=version,
        followup_count=row["followup_count"], turn_number=cur, weak_areas=stuck_weak,
    )
    max_q = 5 if version == "V1" else 10

    try:
        if decision["should_followup"]:
            nq = await generate_question(
                topic=topic, version=version, turn_number=cur + 1,
                previous_qa=prev_qa, weak_areas=stuck_weak, is_followup=True,
            )
            advanced = await audit_db.advance_in_flight_if(
                session_id, cur, nq, cur + 1, True, row["followup_count"] + 1
            )
        elif len(turns) < max_q:
            nq = await generate_question(
                topic=topic, version=version, turn_number=cur + 1,
                previous_qa=prev_qa, weak_areas=weak_areas, is_followup=False,
            )
            advanced = await audit_db.advance_in_flight_if(
                session_id, cur, nq, cur + 1, False, 0
            )
        else:
            avg = round(total_score / len(turns), 2) if turns else 0.0
            advanced = await audit_db.complete_if(session_id, cur, avg, len(turns))
    except (LLMUnavailable, LLMBusy):
        return  # graded but couldn't advance — next sweep advances

    if advanced:
        await exam_state.clear_active(session_id)  # next access rebuilds from Postgres
        logger.info("backfill reconciled session=%s turn=%s", session_id, cur)


async def sweep() -> None:
    try:
        pending = await audit_db.get_pending_turns(settings.grading_backfill_batch)
    except Exception as exc:
        logger.warning("backfill sweep query failed: %s", exc)
        return
    for t in pending:
        try:
            await reconcile_session(t["session_id"])
        except Exception as exc:
            logger.warning("backfill reconcile failed for %s: %s", t["session_id"], exc)


async def _loop() -> None:
    await sweep()  # startup sweep
    while True:
        await asyncio.sleep(settings.grading_backfill_interval_seconds)
        await sweep()


def start() -> None:
    global _task
    if _task is None:
        _task = asyncio.create_task(_loop())
        logger.info("grading backfill worker started")


async def stop() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
