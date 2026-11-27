# ── app/core/auth.py ─────────────────────────────────────────
# Teacher authentication: one shared password, checked in constant time. It
# guards every endpoint that exposes students' answers or changes course data.
# There are no user accounts yet, so a request can't say which teacher it is.

import secrets
from typing import Optional

from fastapi import Header, HTTPException

from app.core.config import settings


def verify_teacher(password: Optional[str]) -> bool:
    """Check the teacher password against the configured value, in constant time.

    Reads settings.teacher_password rather than os.environ. pydantic-settings
    parses .env into the settings object WITHOUT exporting to os.environ, so the
    previous os.environ.get("TEACHER_PASSWORD", "quantum2025") ignored the
    configured password entirely whenever it came from .env — and silently
    accepted a hardcoded fallback that appears in no documentation.

    compare_digest avoids leaking the password's length or its matching prefix
    through response timing. Comparing bytes means a non-ASCII password can't
    raise instead of failing.
    """
    if not password:
        return False
    return secrets.compare_digest(password.encode(), settings.teacher_password.encode())


def require_teacher(x_teacher_password: Optional[str] = Header(None)) -> None:
    """FastAPI dependency: 401 unless the X-Teacher-Password header is correct."""
    if not verify_teacher(x_teacher_password):
        raise HTTPException(401, "Invalid teacher password.")
