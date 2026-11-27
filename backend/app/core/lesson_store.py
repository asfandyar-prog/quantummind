# ── app/core/lesson_store.py ─────────────────────────────────
# Server-side copy of each generated lesson plan, keyed by a plan id.
#
# The plan holds each step's answer key (check_answer). The browser only ever
# sees public_plan(), which leaves the keys out, and /lesson/grade looks the
# key up here by (plan_id, step), so a student can neither read the answer nor
# send in a different one.
#
# Redis, not Postgres: a plan is shared-ephemeral data (any worker may grade it,
# and losing it only means restarting the lesson), so it gets a TTL instead of a
# table.

import json
import uuid
from typing import Optional

from app.core.config import settings
from app.db.redis_client import get_redis


def _key(plan_id: str) -> str:
    return f"lesson:{plan_id}"


async def save_plan(plan: dict) -> str:
    """Store the full plan, answer keys included. Returns its new plan id."""
    plan_id = uuid.uuid4().hex
    await get_redis().set(_key(plan_id), json.dumps(plan), ex=settings.lesson_plan_ttl_seconds)
    return plan_id


async def load_plan(plan_id: str) -> Optional[dict]:
    """The full stored plan, or None if it never existed or has expired."""
    raw = await get_redis().get(_key(plan_id))
    return json.loads(raw) if raw is not None else None


def public_plan(plan: dict, plan_id: str) -> dict:
    """What the browser may see: the plan without any step's check_answer."""
    steps = [{k: v for k, v in step.items() if k != "check_answer"} for step in plan.get("steps", [])]
    return {**plan, "steps": steps, "plan_id": plan_id}
