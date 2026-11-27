# ── app/routes/lesson.py ─────────────────────────────────────
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.agents.lesson_agent import generate_lesson_plan, teach_step, grade_answer
from app.core import lesson_store

router = APIRouter()


class LessonPlanRequest(BaseModel):
    topic: str = Field(..., min_length=2, description="Topic to generate a lesson for")


class TeachStepRequest(BaseModel):
    topic: str
    step: dict
    step_num: int


class GradeRequest(BaseModel):
    """Which step of which stored plan, and the student's answer. Nothing else:
    the question and its answer key come from the server-side plan, and a
    request that still sends correct_answer (or anything extra) is a 422."""
    model_config = ConfigDict(extra="forbid")

    plan_id:        str = Field(..., min_length=1)
    step_num:       int = Field(..., ge=1, description="1-based, as in /lesson/teach")
    student_answer: str = Field(..., min_length=1)


@router.post("/lesson/plan")
async def get_lesson_plan(request: LessonPlanRequest):
    """Generate a lesson plan. The full plan, answer keys included, is stored
    server-side; the response leaves the keys out and carries the plan_id that
    /lesson/grade needs."""
    try:
        plan = await generate_lesson_plan(request.topic)
        plan_id = await lesson_store.save_plan(plan)
        return lesson_store.public_plan(plan, plan_id)
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
    """Grade a student's answer against the stored plan's answer key."""
    plan = await lesson_store.load_plan(request.plan_id)
    if plan is None:
        raise HTTPException(404, "This lesson has expired. Please start it again.")
    steps = plan.get("steps", [])
    if request.step_num > len(steps):
        raise HTTPException(400, f"This lesson has {len(steps)} steps.")
    step = steps[request.step_num - 1]
    try:
        return await grade_answer(
            step.get("check_question", ""),
            step.get("check_answer", ""),
            request.student_answer,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))