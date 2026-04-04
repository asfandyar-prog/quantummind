# ── app/routes/lesson.py ─────────────────────────────────────
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.agents.lesson_agent import generate_lesson_plan, teach_step, grade_answer

router = APIRouter()


class LessonPlanRequest(BaseModel):
    topic: str = Field(..., min_length=2, description="Topic to generate a lesson for")


class TeachStepRequest(BaseModel):
    topic: str
    step: dict
    step_num: int


class GradeRequest(BaseModel):
    question: str
    correct_answer: str
    student_answer: str = Field(..., min_length=1)


@router.post("/lesson/plan")
async def get_lesson_plan(request: LessonPlanRequest):
    """Generate a structured lesson plan for a topic."""
    try:
        plan = await generate_lesson_plan(request.topic)
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lesson/teach")
async def teach_lesson_step(request: TeachStepRequest):
    """Get teaching content for a specific step."""
    try:
        content = await teach_step(request.topic, request.step, request.step_num)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lesson/grade")
async def grade_student_answer(request: GradeRequest):
    """Grade a student's answer to a check question."""
    try:
        result = await grade_answer(
            request.question,
            request.correct_answer,
            request.student_answer,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))