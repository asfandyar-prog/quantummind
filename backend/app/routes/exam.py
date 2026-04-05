# ── app/routes/exam.py ───────────────────────────────────────
import os
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional

from app.agents.exam_agent import generate_question, grade_answer, decide_followup, identify_weak_areas
from app.db.audit_db import create_session, end_session, log_turn, log_teacher_review, get_all_sessions, get_session_turns, get_research_stats

router = APIRouter()

# In-memory exam state per session
_exam_state: dict = {}


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

    session_id = create_session(req.student_name, req.topic, req.version)

    question = await generate_question(
        topic=req.topic, version=req.version,
        turn_number=1, previous_qa=[], is_followup=False,
    )

    _exam_state[session_id] = {
        "topic": req.topic, "version": req.version,
        "student_name": req.student_name,
        "turns": [], "turn_number": 1,
        "followup_count": 0, "weak_areas": [],
        "current_question": question, "total_score": 0.0,
    }

    print(f"[ExamRoute] Started: {session_id} | {req.student_name} | {req.topic} | {req.version}")
    return {"session_id": session_id, "question": question, "turn_number": 1, "version": req.version}


class AnswerRequest(BaseModel):
    session_id:     str
    student_answer: str = Field(..., min_length=1)


@router.post("/exam/answer")
async def submit_answer(req: AnswerRequest):
    state = _exam_state.get(req.session_id)
    if not state:
        raise HTTPException(404, "Session not found. Please start a new exam.")

    topic    = state["topic"]
    version  = state["version"]
    question = state["current_question"]
    turn_num = state["turn_number"]

    # Grade — 1 LLM call
    grading = await grade_answer(topic, question, req.student_answer)

    # Log to audit DB
    turn_id = log_turn(
        session_id=req.session_id, turn_number=turn_num,
        question=question, student_answer=req.student_answer,
        score_accuracy=grading["accuracy"], score_reasoning=grading["reasoning"],
        score_clarity=grading["clarity"], ai_justification=grading["justification"],
        ideal_answer=grading["ideal_answer"], is_followup=state["followup_count"] > 0,
    )

    state["turns"].append({"question": question, "answer": req.student_answer, "score": grading["total"], "turn_id": turn_id})
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
        next_question = await generate_question(
            topic=topic, version=version, turn_number=turn_num + 1,
            previous_qa=state["turns"], weak_areas=grading["weak_areas"], is_followup=True,
        )
        state["followup_count"] += 1
        is_followup = True
        state["turn_number"] += 1
        state["current_question"] = next_question

    elif len(state["turns"]) < max_q:
        state["followup_count"] = 0
        next_question = await generate_question(
            topic=topic, version=version, turn_number=turn_num + 1,
            previous_qa=state["turns"], weak_areas=state["weak_areas"], is_followup=False,
        )
        state["turn_number"] += 1
        state["current_question"] = next_question

    else:
        exam_complete = True
        avg = round(state["total_score"] / len(state["turns"]), 2)
        end_session(req.session_id, avg, len(state["turns"]))
        del _exam_state[req.session_id]

    return {
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


@router.post("/exam/end")
async def end_exam_early(req: dict):
    session_id = req.get("session_id")
    state = _exam_state.get(session_id)
    if not state:
        raise HTTPException(404, "Session not found.")
    total = len(state["turns"])
    avg   = round(state["total_score"] / total, 2) if total > 0 else 0.0
    end_session(session_id, avg, total)
    del _exam_state[session_id]
    return {"status": "ended", "avg_score": avg, "total_turns": total}


@router.get("/exam/session/{session_id}")
async def get_session(session_id: str):
    turns = get_session_turns(session_id)
    return {"session_id": session_id, "turns": turns}


# ════════════════════════════════════════════════════════════════
# TEACHER ENDPOINTS
# ════════════════════════════════════════════════════════════════

@router.get("/teacher/sessions")
async def teacher_sessions(x_teacher_password: Optional[str] = Header(None)):
    if not verify_teacher(x_teacher_password):
        raise HTTPException(401, "Invalid teacher password.")
    return {"sessions": get_all_sessions(100)}


@router.get("/teacher/session/{session_id}")
async def teacher_session(session_id: str, x_teacher_password: Optional[str] = Header(None)):
    if not verify_teacher(x_teacher_password):
        raise HTTPException(401, "Invalid teacher password.")
    return {"session_id": session_id, "turns": get_session_turns(session_id)}


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
    review_id = log_teacher_review(
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
    return get_research_stats()