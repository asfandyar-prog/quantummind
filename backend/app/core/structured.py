# ── app/core/structured.py ───────────────────────────────────
# Structured LLM output: ask, validate against a Pydantic model, re-ask once,
# then give up and let the caller fail closed.
#
# Used by the three places whose JSON reply drives a decision: the router's
# label, the lesson grader's pass/fail, and the exam grader's scores. Each one
# decides for itself what "fail closed" means (fall back to Theory, don't pass,
# store no score); this module only guarantees that whatever it returns has
# been validated.

import json
import logging
import math
import re
from typing import Literal, Optional, Type, TypeVar

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, StrictBool, ValidationError, field_validator

from app.core import llm

logger = logging.getLogger("quantummind.structured")

M = TypeVar("M", bound=BaseModel)


# ── The three reply shapes ────────────────────────────────────

class RouteDecision(BaseModel):
    """The router's reply."""
    agent: Literal["theory", "code", "rag", "review"]
    reason: str = ""


class LessonGrade(BaseModel):
    """The lesson grader's reply. StrictBool: only JSON true/false, never the
    string "true" or the number 1."""
    passed: StrictBool
    feedback: str = ""


class ExamGrade(BaseModel):
    """The exam grader's reply. Each score must be a real, finite number; it is
    clamped to 0-10. A missing score is a validation error, never a default."""
    accuracy: float
    reasoning: float
    clarity: float
    justification: str = ""
    ideal_answer: str = ""

    @field_validator("accuracy", "reasoning", "clarity", mode="before")
    @classmethod
    def _no_bools(cls, v):
        if isinstance(v, bool):          # pydantic would read True as 1.0
            raise ValueError("a score must be a number, not a boolean")
        return v

    @field_validator("accuracy", "reasoning", "clarity")
    @classmethod
    def _finite_and_clamped(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("a score must be finite")
        return min(10.0, max(0.0, v))

    @field_validator("justification", "ideal_answer", mode="before")
    @classmethod
    def _text(cls, v):
        return "" if v is None else str(v)


# ── Parsing ───────────────────────────────────────────────────

def extract_json_object(reply: str) -> Optional[dict]:
    """The first {...} object in a reply, tolerating code fences and prose
    around it. None if there is no JSON object."""
    raw = re.sub(r"```(?:json)?", "", reply or "")
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end < start:
        return None
    try:
        data = json.loads(raw[start:end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def parse_model(model: Type[M], reply: str) -> Optional[M]:
    """reply validated as `model`, or None."""
    data = extract_json_object(reply)
    if data is None:
        return None
    try:
        return model.model_validate(data)
    except ValidationError:
        return None


def retry_prompt(model: Type[BaseModel]) -> str:
    fields = ", ".join(model.model_fields)
    return (
        "That reply was not the JSON object requested. Return ONLY one JSON object "
        f"with the fields {fields}, using the types asked for. No prose, no code fences."
    )


async def ask_validated(
    messages: list[BaseMessage],
    schema: Type[M],
    *,
    call_type: str,
    correction: Optional[str] = None,
    **chat_kwargs,
) -> Optional[M]:
    """Ask once; if the reply doesn't validate, show the model its reply and ask
    once more. Returns the validated object, or None so the caller can fail
    closed. LLM errors (LLMUnavailable, LLMBusy) propagate unchanged.

    `schema` is the Pydantic class; chat_kwargs (e.g. model=...) go to llm.chat."""
    reply = await llm.chat(messages, call_type=call_type, **chat_kwargs)
    parsed = parse_model(schema, reply)
    if parsed is not None:
        return parsed

    logger.warning(f"{call_type}: reply failed {schema.__name__} validation — one corrective retry")
    reply = await llm.chat(
        [*messages, AIMessage(content=reply), HumanMessage(content=correction or retry_prompt(schema))],
        call_type=call_type, **chat_kwargs,
    )
    parsed = parse_model(schema, reply)
    if parsed is None:
        logger.warning(f"{call_type}: reply still invalid after the retry — failing closed")
    return parsed
