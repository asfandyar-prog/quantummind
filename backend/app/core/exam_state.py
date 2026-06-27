# ── app/core/exam_state.py ───────────────────────────────────
# Active-exam state: Redis hot copy + Postgres-only reconstruction.
#
# Replaces the in-memory _exam_state dict. The authoritative durable record is
# Postgres (exam_sessions in-flight columns + exam_turns); Redis holds a fast
# shared copy under exam:{session_id}. If Redis is flushed, an active exam is
# fully reconstructable from Postgres alone.
#
# The state dict shape is unchanged from the old _exam_state entry:
#   { topic, version, student_name, turns[ {question, answer, score, turn_id} ],
#     turn_number, followup_count, weak_areas[], current_question, total_score }

import json
from typing import Optional

from app.core.config import settings
from app.db import audit_db
from app.db.redis_client import get_redis
from app.agents.exam_agent import identify_weak_areas


def _key(session_id: str) -> str:
    return f"exam:{session_id}"


async def save_active(session_id: str, state: dict) -> None:
    """Write the hot copy to Redis with a safety TTL (Postgres stays the source of truth)."""
    await get_redis().set(
        _key(session_id), json.dumps(state), ex=settings.exam_state_ttl_seconds
    )


async def clear_active(session_id: str) -> None:
    """Drop the Redis hot copy (e.g. on completion / early end)."""
    await get_redis().delete(_key(session_id))


async def load_active(session_id: str) -> Optional[dict]:
    """Return the active-exam state.

    Reconstruction order:
      1. Redis hit → return it (fast path).
      2. Redis miss → rebuild from Postgres alone (session row + turns),
         repopulate Redis, and return.
    Returns None if the session does not exist or is no longer active.
    """
    cached = await get_redis().get(_key(session_id))
    if cached is not None:
        return json.loads(cached)

    # Redis miss — rebuild from Postgres alone.
    row = await audit_db.get_session_row(session_id)
    if row is None or row["status"] != "active":
        return None

    turns_raw = await audit_db.get_session_turns(session_id)
    turns: list[dict] = []
    total_score = 0.0
    weak_areas: list[str] = []
    for t in turns_raw:
        score = t["score_total"] or 0.0
        turns.append({
            "question": t["question"],
            "answer":   t["student_answer"],
            "score":    score,
            "turn_id":  t["turn_id"],
        })
        total_score += score
        for area in identify_weak_areas(
            t["score_accuracy"] or 0.0,
            t["score_reasoning"] or 0.0,
            t["score_clarity"] or 0.0,
        ):
            if area not in weak_areas:
                weak_areas.append(area)

    state = {
        "topic":            row["topic"],
        "version":          row["version"],
        "student_name":     row["student_name"],
        "turns":            turns,
        "turn_number":      row["current_turn_number"],
        "followup_count":   row["followup_count"],
        "weak_areas":       weak_areas,
        "current_question": row["current_question"],
        "total_score":      total_score,
    }
    await save_active(session_id, state)  # repopulate the hot copy
    return state
