# ── app/routes/exam.py ───────────────────────────────────────
import os
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional

from app.agents.exam_agent import generate_question, grade_answer, decide_followup
from app.db.audit_db import (
    create_session, end_session, set_in_flight, advance_exam, complete_exam,
    create_pending_turn, get_pending_turn, get_session_row,
    log_teacher_review, get_all_sessions, get_session_turns, get_research_stats,
)
from app.core.exam_state import save_active, load_active, clear_active
from app.core.llm_errors import LLMUnavailable, LLMBusy

router = APIRouter()


def verify_teacher(password: Optional[str]) -> bool:
    expected = os.environ.get("TEACHER_PASSWORD", "quantum2025")
    return password == expected


# ════════════════════════════════════════════════════════════════
# STUDENT ENDPOINTS
# ════════════════════════════════════════════════════════════════

class StartRequest(BaseModel):
    student_name: str = Field(..., min_length=1)
    topic:        str = Field(..., min_length=2)
    version:      str = Field(default="V2")


@router.post("/exam/start")
async def start_exam(req: StartRequest):
    if req.version not in ("V1", "V2", "V3"):
        raise HTTPException(400, "version must be V1, V2, or V3")

    session_id = await create_session(req.student_name, req.topic, req.version)

    question = await generate_question(
        topic=req.topic, version=req.version,
        turn_number=1, previous_qa=[], is_followup=False,
    )

    # Postgres FIRST: the in-flight question is durable before we respond, so a
    # restart immediately after start still knows the current question.
    await set_in_flight(
        session_id,
        current_question=question,
        current_turn_number=1,
        current_is_followup=False,
        followup_count=0,
    )

    # THEN the Redis hot copy.
    state = {
        "topic": req.topic, "version": req.version,
        "student_name": req.student_name,
        "turns": [], "turn_number": 1,
        "followup_count": 0, "weak_areas": [],
        "current_question": question, "total_score": 0.0,
    }
    await save_active(session_id, state)

    print(f"[ExamRoute] Started: {session_id} | {req.student_name} | {req.topic} | {req.version}")
    return {"session_id": session_id, "question": question, "turn_number": 1, "version": req.version}


class AnswerRequest(BaseModel):
    session_id:     str
    student_answer: str = Field(..., min_length=1)


def _pending_response(turn_id: str) -> dict:
    return {
        "status": "saved_pending_grading",
        "turn_id": turn_id,
        "awaiting_grade": True,
        "exam_complete": False,
        "message": "Your answer is saved. Grading is catching up — check back shortly.",
    }


@router.post("/exam/answer")
async def submit_answer(req: AnswerRequest):
    state = await load_active(req.session_id)
    if state is None:
        raise HTTPException(404, "Session not found. Please start a new exam.")

    # Idempotency: if this session already has an answered turn awaiting
    # grading/advance, the answer is already safe — return the pending state
    # instead of grading the same answer again.
    existing = await get_pending_turn(req.session_id)
    if existing is not None:
        return _pending_response(existing["turn_id"])

    topic    = state["topic"]
    version  = state["version"]
    question = state["current_question"]
    turn_num = state["turn_number"]

    # Whether the question just answered was a follow-up (mirrors the old logic).
    is_followup_for_turn = state["followup_count"] > 0

    try:
        # Grade — 1 LLM call
        grading = await grade_answer(topic, question, req.student_answer)

        # Update the working state. The turn is appended now so it feeds the next
        # question's context (previous_qa uses question/answer/score, not turn_id).
        new_turn = {"question": question, "answer": req.student_answer, "score": grading["total"], "turn_id": None}
        state["turns"].append(new_turn)
        state["total_score"] += grading["total"]
        for area in grading["weak_areas"]:
            if area not in state["weak_areas"]:
                state["weak_areas"].append(area)

        # Deterministic follow-up decision — 0 LLM calls
        followup = decide_followup(
            score_total=grading["total"], version=version,
            followup_count=state["followup_count"],
            turn_number=turn_num, weak_areas=grading["weak_areas"],
        )

        # Feedback
        t = grading["total"]
        feedback = "Excellent answer!" if t >= 8 else "Good answer, some areas could be more precise." if t >= 6 else "Partial understanding. Let's explore further." if t >= 4 else "This needs more work. Let's try a follow-up."

        next_question = None
        is_followup   = False
        exam_complete = False
        max_q = 5 if version == "V1" else 10

        if followup["should_followup"]:
            is_followup = True
            next_turn_number    = turn_num + 1
            next_followup_count = state["followup_count"] + 1
            next_question = await generate_question(
                topic=topic, version=version, turn_number=next_turn_number,
                previous_qa=state["turns"], weak_areas=grading["weak_areas"], is_followup=True,
            )
            # Postgres FIRST: completed turn + next in-flight question, one transaction.
            turn_id = await advance_exam(
                session_id=req.session_id, turn_number=turn_num,
                question=question, student_answer=req.student_answer,
                score_accuracy=grading["accuracy"], score_reasoning=grading["reasoning"],
                score_clarity=grading["clarity"], ai_justification=grading["justification"],
                ideal_answer=grading["ideal_answer"], is_followup=is_followup_for_turn,
                next_question=next_question, next_turn_number=next_turn_number,
                next_is_followup=True, next_followup_count=next_followup_count,
            )
            new_turn["turn_id"]       = turn_id
            state["followup_count"]   = next_followup_count
            state["turn_number"]      = next_turn_number
            state["current_question"] = next_question
            await save_active(req.session_id, state)  # THEN the Redis hot copy

        elif len(state["turns"]) < max_q:
            next_turn_number    = turn_num + 1
            next_followup_count = 0
            next_question = await generate_question(
                topic=topic, version=version, turn_number=next_turn_number,
                previous_qa=state["turns"], weak_areas=state["weak_areas"], is_followup=False,
            )
            turn_id = await advance_exam(
                session_id=req.session_id, turn_number=turn_num,
                question=question, student_answer=req.student_answer,
                score_accuracy=grading["accuracy"], score_reasoning=grading["reasoning"],
                score_clarity=grading["clarity"], ai_justification=grading["justification"],
                ideal_answer=grading["ideal_answer"], is_followup=is_followup_for_turn,
                next_question=next_question, next_turn_number=next_turn_number,
                next_is_followup=False, next_followup_count=0,
            )
            new_turn["turn_id"]       = turn_id
            state["followup_count"]   = next_followup_count
            state["turn_number"]      = next_turn_number
            state["current_question"] = next_question
            await save_active(req.session_id, state)

        else:
            exam_complete = True
            avg = round(state["total_score"] / len(state["turns"]), 2)
            turn_id = await complete_exam(
                session_id=req.session_id, turn_number=turn_num,
                question=question, student_answer=req.student_answer,
                score_accuracy=grading["accuracy"], score_reasoning=grading["reasoning"],
                score_clarity=grading["clarity"], ai_justification=grading["justification"],
                ideal_answer=grading["ideal_answer"], is_followup=is_followup_for_turn,
                avg_score=avg, total_turns=len(state["turns"]),
            )
            new_turn["turn_id"] = turn_id
            await clear_active(req.session_id)

        return {
            "status": "graded",
            "awaiting_grade": False,
            "turn_id": turn_id,
            "scores": {"accuracy": grading["accuracy"], "reasoning": grading["reasoning"], "clarity": grading["clarity"], "total": grading["total"]},
            "justification": grading["justification"],
            "ideal_answer": grading["ideal_answer"],
            "feedback": feedback,
            "next_question": next_question,
            "is_followup": is_followup,
            "exam_complete": exam_complete,
            "turn_number": turn_num + 1 if not exam_complete else turn_num,
        }

    except (LLMUnavailable, LLMBusy):
        # LLM down/saturated: persist the answer durably (graded=false) BEFORE
        # responding. The backfill worker grades it and advances the exam later.
        turn_id = await create_pending_turn(
            session_id=req.session_id, turn_number=turn_num,
            question=question, student_answer=req.student_answer,
            is_followup=is_followup_for_turn,
        )
        await clear_active(req.session_id)  # Redis copy is stale; rebuild from PG next
        return _pending_response(turn_id)


@router.post("/exam/end")
async def end_exam_early(req: dict):
    session_id = req.get("session_id")
    state = await load_active(session_id)
    if state is None:
        raise HTTPException(404, "Session not found.")
    total = len(state["turns"])
    avg   = round(state["total_score"] / total, 2) if total > 0 else 0.0
    await end_session(session_id, avg, total)   # Postgres FIRST
    await clear_active(session_id)               # THEN drop Redis
    return {"status": "ended", "avg_score": avg, "total_turns": total}


@router.get("/exam/session/{session_id}")
async def get_session(session_id: str):
    turns = await get_session_turns(session_id)
    return {"session_id": session_id, "turns": turns}


@router.get("/exam/session/{session_id}/status")
async def session_status(session_id: str):
    """Poll point for the 'answer saved, grading catching up' UX (Phase 5 consumes
    this). awaiting_grade flips false once the backfill worker has graded and
    advanced; then current_question is the next question (or exam_complete)."""
    row = await get_session_row(session_id)
    if row is None:
        raise HTTPException(404, "Session not found.")
    if row["status"] != "active":
        return {"status": "completed", "awaiting_grade": False, "exam_complete": True}

    pending = await get_pending_turn(session_id)
    if pending is None:
        # A question is in flight, not yet answered — ready for the next answer.
        return {
            "status": "active",
            "awaiting_grade": False,
            "exam_complete": False,
            "current_question": row["current_question"],
            "turn_number": row["current_turn_number"],
        }

    # An answer is mid-processing (grading and/or next-question generation).
    resp = {
        "status": "awaiting_grade",
        "awaiting_grade": True,
        "exam_complete": False,
        "turn_id": pending["turn_id"],
        "graded": bool(pending["graded"]),
    }
    if pending["graded"]:
        resp["scores"] = {
            "accuracy":  pending["score_accuracy"],
            "reasoning": pending["score_reasoning"],
            "clarity":   pending["score_clarity"],
            "total":     pending["score_total"],
        }
    return resp


# ════════════════════════════════════════════════════════════════
# TEACHER ENDPOINTS
# ════════════════════════════════════════════════════════════════

@router.get("/teacher/sessions")
async def teacher_sessions(x_teacher_password: Optional[str] = Header(None)):
    if not verify_teacher(x_teacher_password):
        raise HTTPException(401, "Invalid teacher password.")
    return {"sessions": await get_all_sessions(100)}


@router.get("/teacher/session/{session_id}")
async def teacher_session(session_id: str, x_teacher_password: Optional[str] = Header(None)):
    if not verify_teacher(x_teacher_password):
        raise HTTPException(401, "Invalid teacher password.")
    return {"session_id": session_id, "turns": await get_session_turns(session_id)}


class ReviewRequest(BaseModel):
    session_id: str
    turn_id:    str
    action:     str   # 'accepted' or 'modified'
    teacher_accuracy:  Optional[float] = None
    teacher_reasoning: Optional[float] = None
    teacher_clarity:   Optional[float] = None
    teacher_feedback:  str = ""
    teacher_notes:     str = ""
    ai_accuracy:       float = 5.0
    ai_reasoning:      float = 5.0
    ai_clarity:        float = 5.0


@router.post("/teacher/review")
async def teacher_review(req: ReviewRequest, x_teacher_password: Optional[str] = Header(None)):
    if not verify_teacher(x_teacher_password):
        raise HTTPException(401, "Invalid teacher password.")
    review_id = await log_teacher_review(
        session_id=req.session_id, turn_id=req.turn_id,
        ai_accuracy=req.ai_accuracy, ai_reasoning=req.ai_reasoning, ai_clarity=req.ai_clarity,
        teacher_accuracy=req.teacher_accuracy, teacher_reasoning=req.teacher_reasoning, teacher_clarity=req.teacher_clarity,
        teacher_feedback=req.teacher_feedback, teacher_notes=req.teacher_notes, action=req.action,
    )
    return {"review_id": review_id, "status": "logged"}


@router.get("/research/stats")
async def research_stats(x_teacher_password: Optional[str] = Header(None)):
    if not verify_teacher(x_teacher_password):
        raise HTTPException(401, "Invalid teacher password.")
    return await get_research_stats()
