# ── app/db/audit_db.py ───────────────────────────────────────
# Async Postgres repository for the AI Examiner audit trail.
#
# Rewritten in Phase 1 (commit 3): the old synchronous sqlite3 + per-request
# connections are gone. This now uses SQLAlchemy 2.0 async sessions over the
# shared pooled engine in db/database.py. Function names/shapes are unchanged so
# routes only needed to `await` them. The schema lives in db/models.py and is
# created by Alembic migrations — there is no init_db() here anymore.
#
# Scores are stored as Numeric (Decimal); the read helpers convert to float so
# the JSON API shape is unchanged.

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, text, update

from app.db.database import get_engine, get_sessionmaker
from app.db.models import ExamSession, ExamTurn, TeacherReview


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _f(v) -> Optional[float]:
    """Decimal/None → float/None for JSON responses."""
    return float(v) if v is not None else None


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


# ════════════════════════════════════════════════════════════════
# SESSION OPERATIONS
# ════════════════════════════════════════════════════════════════

async def create_session(student_name: str, topic: str, version: str) -> str:
    """Create a new exam session. Returns session_id."""
    session_id = str(uuid.uuid4())
    async with get_sessionmaker()() as session:
        session.add(ExamSession(
            session_id=session_id,
            student_name=student_name,
            topic=topic,
            version=version,
            started_at=_now(),
        ))
        await session.commit()
    print(f"[AuditDB] Session created: {session_id} | {student_name} | {topic} | {version}")
    return session_id


async def end_session(session_id: str, avg_score: float, total_turns: int) -> None:
    """Mark a session completed. Single UPDATE — fixes the old INSERT+UPDATE bug."""
    async with get_sessionmaker()() as session:
        await session.execute(
            update(ExamSession)
            .where(ExamSession.session_id == session_id)
            .values(
                ended_at=_now(),
                total_turns=total_turns,
                avg_score=avg_score,
                status="completed",
            )
        )
        await session.commit()
    print(f"[AuditDB] Session ended: {session_id} | avg={avg_score} | turns={total_turns}")


# ════════════════════════════════════════════════════════════════
# TURN OPERATIONS — one transaction: completed turn + in-flight/completion
# ════════════════════════════════════════════════════════════════

def _make_turn(
    session_id:       str,
    turn_number:      int,
    question:         str,
    student_answer:   str,
    score_accuracy:   float,
    score_reasoning:  float,
    score_clarity:    float,
    ai_justification: str,
    ideal_answer:     str,
    is_followup:      bool,
) -> ExamTurn:
    score_total = round((score_accuracy + score_reasoning + score_clarity) / 3, 2)
    return ExamTurn(
        turn_id=str(uuid.uuid4()),
        session_id=session_id,
        turn_number=turn_number,
        question=question,
        student_answer=student_answer,
        score_accuracy=score_accuracy,
        score_reasoning=score_reasoning,
        score_clarity=score_clarity,
        score_total=score_total,
        ai_justification=ai_justification,
        ideal_answer=ideal_answer,
        is_followup=bool(is_followup),
        graded=True,
        answered_at=_now(),
    )


def _turn_to_dict(t: ExamTurn) -> dict:
    return {
        "turn_id":          t.turn_id,
        "session_id":       t.session_id,
        "turn_number":      t.turn_number,
        "question":         t.question,
        "student_answer":   t.student_answer,
        "score_accuracy":   _f(t.score_accuracy),
        "score_reasoning":  _f(t.score_reasoning),
        "score_clarity":    _f(t.score_clarity),
        "score_total":      _f(t.score_total),
        "ai_justification": t.ai_justification,
        "ideal_answer":     t.ideal_answer,
        "is_followup":      int(t.is_followup),
        "graded":           bool(t.graded),
    }


# ════════════════════════════════════════════════════════════════
# GRACEFUL DEGRADATION — pending turns + idempotent reconciliation
# ════════════════════════════════════════════════════════════════

async def create_pending_turn(
    session_id:     str,
    turn_number:    int,
    question:       str,
    student_answer: str,
    is_followup:    bool,
) -> str:
    """Persist a student's answer durably with graded=false (no scores yet, the
    session is NOT advanced). This is the 'answer saved, grade owed' record."""
    turn_id = str(uuid.uuid4())
    async with get_sessionmaker()() as session:
        session.add(ExamTurn(
            turn_id=turn_id,
            session_id=session_id,
            turn_number=turn_number,
            question=question,
            student_answer=student_answer,
            is_followup=bool(is_followup),
            graded=False,
            answered_at=_now(),
        ))
        await session.commit()
    print(f"[AuditDB] Pending turn saved: {turn_id} | session={session_id} turn={turn_number}")
    return turn_id


async def finalize_grade(
    turn_id:          str,
    score_accuracy:   float,
    score_reasoning:  float,
    score_clarity:    float,
    ai_justification: str,
    ideal_answer:     str,
) -> bool:
    """Backfill a pending turn's grade. Idempotent: the conditional UPDATE only
    affects a row that is still graded=false, so exactly one worker can claim it.
    Returns True iff this call claimed (graded) the turn."""
    score_total = round((score_accuracy + score_reasoning + score_clarity) / 3, 2)
    async with get_sessionmaker()() as session:
        result = await session.execute(
            update(ExamTurn)
            .where(ExamTurn.turn_id == turn_id, ExamTurn.graded.is_(False))
            .values(
                score_accuracy=score_accuracy,
                score_reasoning=score_reasoning,
                score_clarity=score_clarity,
                score_total=score_total,
                ai_justification=ai_justification,
                ideal_answer=ideal_answer,
                graded=True,
            )
        )
        await session.commit()
    claimed = result.rowcount == 1
    print(f"[AuditDB] finalize_grade {turn_id}: {'claimed' if claimed else 'already graded'}")
    return claimed


async def advance_in_flight_if(
    session_id:          str,
    expected_turn_number: int,
    next_question:       str,
    next_turn_number:    int,
    next_is_followup:    bool,
    next_followup_count: int,
) -> bool:
    """Advance the in-flight question ONLY if the session is still parked at
    expected_turn_number (and active). Idempotent guard against double-advance."""
    async with get_sessionmaker()() as session:
        result = await session.execute(
            update(ExamSession)
            .where(
                ExamSession.session_id == session_id,
                ExamSession.current_turn_number == expected_turn_number,
                ExamSession.status == "active",
            )
            .values(
                current_question=next_question,
                current_turn_number=next_turn_number,
                current_is_followup=bool(next_is_followup),
                followup_count=next_followup_count,
            )
        )
        await session.commit()
    return result.rowcount == 1


async def complete_if(
    session_id:          str,
    expected_turn_number: int,
    avg_score:           float,
    total_turns:         int,
) -> bool:
    """Mark the session completed ONLY if still parked at expected_turn_number
    (and active). Idempotent guard against double-complete."""
    async with get_sessionmaker()() as session:
        result = await session.execute(
            update(ExamSession)
            .where(
                ExamSession.session_id == session_id,
                ExamSession.current_turn_number == expected_turn_number,
                ExamSession.status == "active",
            )
            .values(
                ended_at=_now(),
                total_turns=total_turns,
                avg_score=avg_score,
                status="completed",
                current_question=None,
            )
        )
        await session.commit()
    return result.rowcount == 1


async def get_pending_turn(session_id: str) -> Optional[dict]:
    """The 'stuck' turn for one session: an answered turn the session hasn't moved
    past (turn_number == current_turn_number, session active). It may be ungraded
    or graded-but-not-yet-advanced. None if the session has no answer in flight."""
    async with get_sessionmaker()() as session:
        t = (await session.execute(
            select(ExamTurn)
            .join(ExamSession, ExamSession.session_id == ExamTurn.session_id)
            .where(
                ExamSession.session_id == session_id,
                ExamSession.status == "active",
                ExamTurn.turn_number == ExamSession.current_turn_number,
            )
        )).scalars().first()
    return _turn_to_dict(t) if t is not None else None


async def get_pending_turns(limit: int = 50) -> list[dict]:
    """All stuck turns across active sessions (ungraded OR graded-but-not-advanced)
    — the backfill worker's reconciliation set."""
    async with get_sessionmaker()() as session:
        rows = (await session.execute(
            select(ExamTurn)
            .join(ExamSession, ExamSession.session_id == ExamTurn.session_id)
            .where(
                ExamSession.status == "active",
                ExamTurn.turn_number == ExamSession.current_turn_number,
            )
            .limit(limit)
        )).scalars().all()
    return [_turn_to_dict(t) for t in rows]


async def set_in_flight(
    session_id:          str,
    current_question:    str,
    current_turn_number: int,
    current_is_followup: bool,
    followup_count:      int,
) -> None:
    """Persist the in-flight question on the session (durable; survives restart)."""
    async with get_sessionmaker()() as session:
        await session.execute(
            update(ExamSession)
            .where(ExamSession.session_id == session_id)
            .values(
                current_question=current_question,
                current_turn_number=current_turn_number,
                current_is_followup=bool(current_is_followup),
                followup_count=followup_count,
            )
        )
        await session.commit()
    print(f"[AuditDB] In-flight set: {session_id} | turn={current_turn_number}")


async def advance_exam(
    *,
    session_id:          str,
    turn_number:         int,
    question:            str,
    student_answer:      str,
    score_accuracy:      float,
    score_reasoning:     float,
    score_clarity:       float,
    ai_justification:    str,
    ideal_answer:        str,
    is_followup:         bool,
    next_question:       str,
    next_turn_number:    int,
    next_is_followup:    bool,
    next_followup_count: int,
) -> str:
    """ONE transaction: persist the completed turn AND set the next in-flight question."""
    turn = _make_turn(
        session_id, turn_number, question, student_answer,
        score_accuracy, score_reasoning, score_clarity,
        ai_justification, ideal_answer, is_followup,
    )
    async with get_sessionmaker()() as session:
        session.add(turn)
        await session.execute(
            update(ExamSession)
            .where(ExamSession.session_id == session_id)
            .values(
                current_question=next_question,
                current_turn_number=next_turn_number,
                current_is_followup=bool(next_is_followup),
                followup_count=next_followup_count,
            )
        )
        await session.commit()
    print(f"[AuditDB] Turn logged + advanced: {turn.turn_id} | next turn={next_turn_number}")
    return turn.turn_id


async def complete_exam(
    *,
    session_id:       str,
    turn_number:      int,
    question:         str,
    student_answer:   str,
    score_accuracy:   float,
    score_reasoning:  float,
    score_clarity:    float,
    ai_justification: str,
    ideal_answer:     str,
    is_followup:      bool,
    avg_score:        float,
    total_turns:      int,
) -> str:
    """ONE transaction: persist the final turn AND mark the session completed."""
    turn = _make_turn(
        session_id, turn_number, question, student_answer,
        score_accuracy, score_reasoning, score_clarity,
        ai_justification, ideal_answer, is_followup,
    )
    async with get_sessionmaker()() as session:
        session.add(turn)
        await session.execute(
            update(ExamSession)
            .where(ExamSession.session_id == session_id)
            .values(
                ended_at=_now(),
                total_turns=total_turns,
                avg_score=avg_score,
                status="completed",
                current_question=None,
            )
        )
        await session.commit()
    print(f"[AuditDB] Turn logged + completed: {turn.turn_id} | avg={avg_score}")
    return turn.turn_id


# ════════════════════════════════════════════════════════════════
# TEACHER REVIEW OPERATIONS
# ════════════════════════════════════════════════════════════════

async def log_teacher_review(
    session_id:        str,
    turn_id:           str,
    ai_accuracy:       float,
    ai_reasoning:      float,
    ai_clarity:        float,
    teacher_accuracy:  Optional[float],
    teacher_reasoning: Optional[float],
    teacher_clarity:   Optional[float],
    teacher_feedback:  str,
    teacher_notes:     str,
    action:            str,  # 'accepted' or 'modified'
) -> str:
    """Log a teacher review. Always appends — never updates."""
    review_id = str(uuid.uuid4())
    ai_total = round((ai_accuracy + ai_reasoning + ai_clarity) / 3, 2)

    if action == "modified" and teacher_accuracy is not None:
        t_total         = round((teacher_accuracy + teacher_reasoning + teacher_clarity) / 3, 2)
        delta_accuracy  = round(teacher_accuracy  - ai_accuracy,  2)
        delta_reasoning = round(teacher_reasoning - ai_reasoning, 2)
        delta_clarity   = round(teacher_clarity   - ai_clarity,   2)
    else:
        t_total = ai_total
        teacher_accuracy = teacher_reasoning = teacher_clarity = None
        delta_accuracy = delta_reasoning = delta_clarity = 0.0

    async with get_sessionmaker()() as session:
        session.add(TeacherReview(
            review_id=review_id,
            session_id=session_id,
            turn_id=turn_id,
            ai_accuracy=ai_accuracy,
            ai_reasoning=ai_reasoning,
            ai_clarity=ai_clarity,
            ai_total=ai_total,
            teacher_accuracy=teacher_accuracy,
            teacher_reasoning=teacher_reasoning,
            teacher_clarity=teacher_clarity,
            teacher_total=t_total,
            delta_accuracy=delta_accuracy,
            delta_reasoning=delta_reasoning,
            delta_clarity=delta_clarity,
            teacher_feedback=teacher_feedback,
            teacher_notes=teacher_notes,
            reviewed_at=_now(),
            action=action,
        ))
        await session.commit()
    print(f"[AuditDB] Teacher review: {action} | delta_acc={delta_accuracy}")
    return review_id


# ════════════════════════════════════════════════════════════════
# QUERY OPERATIONS — for teacher dashboard and research
# ════════════════════════════════════════════════════════════════

async def get_session_row(session_id: str) -> Optional[dict]:
    """The session row incl. in-flight columns — used to reconstruct active state."""
    async with get_sessionmaker()() as session:
        s = (await session.execute(
            select(ExamSession).where(ExamSession.session_id == session_id)
        )).scalar_one_or_none()
    if s is None:
        return None
    return {
        "session_id":          s.session_id,
        "student_name":        s.student_name,
        "topic":               s.topic,
        "version":             s.version,
        "status":              s.status,
        "current_question":    s.current_question,
        "current_turn_number": s.current_turn_number,
        "current_is_followup": s.current_is_followup,
        "followup_count":      s.followup_count,
    }


async def get_all_sessions(limit: int = 50) -> list[dict]:
    """Get recent exam sessions for the teacher dashboard."""
    async with get_sessionmaker()() as session:
        rows = (await session.execute(
            select(ExamSession).order_by(ExamSession.started_at.desc()).limit(limit)
        )).scalars().all()
    return [
        {
            "session_id":   s.session_id,
            "student_name": s.student_name,
            "topic":        s.topic,
            "version":      s.version,
            "started_at":   _iso(s.started_at),
            "ended_at":     _iso(s.ended_at),
            "total_turns":  s.total_turns,
            "avg_score":    _f(s.avg_score),
            "status":       s.status,
        }
        for s in rows
    ]


async def get_session_turns(session_id: str) -> list[dict]:
    """Get all turns for a session (with any teacher review) — for transcript review."""
    stmt = (
        select(
            ExamTurn,
            TeacherReview.teacher_accuracy,
            TeacherReview.teacher_reasoning,
            TeacherReview.teacher_clarity,
            TeacherReview.teacher_feedback,
            TeacherReview.action.label("review_action"),
        )
        .outerjoin(TeacherReview, TeacherReview.turn_id == ExamTurn.turn_id)
        .where(ExamTurn.session_id == session_id)
        .order_by(ExamTurn.turn_number.asc())
    )
    async with get_sessionmaker()() as session:
        rows = (await session.execute(stmt)).all()

    result = []
    for turn, t_acc, t_reas, t_clar, t_fb, r_action in rows:
        result.append({
            "turn_id":          turn.turn_id,
            "session_id":       turn.session_id,
            "turn_number":      turn.turn_number,
            "question":         turn.question,
            "student_answer":   turn.student_answer,
            "score_accuracy":   _f(turn.score_accuracy),
            "score_reasoning":  _f(turn.score_reasoning),
            "score_clarity":    _f(turn.score_clarity),
            "score_total":      _f(turn.score_total),
            "ai_justification": turn.ai_justification,
            "ideal_answer":     turn.ideal_answer,
            "is_followup":      int(turn.is_followup),
            "graded":           bool(turn.graded),
            "answered_at":      _iso(turn.answered_at),
            "teacher_accuracy":  _f(t_acc),
            "teacher_reasoning": _f(t_reas),
            "teacher_clarity":   _f(t_clar),
            "teacher_feedback":  t_fb,
            "review_action":     r_action,
        })
    return result


def _conv(mapping) -> dict:
    """Row mapping → plain dict, converting Decimal aggregates to float."""
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in dict(mapping).items()}


async def get_research_stats() -> dict:
    """Aggregate stats for the research layer (3 experiments)."""
    async with get_engine().connect() as conn:
        version_counts = (await conn.execute(text(
            "SELECT version, COUNT(*) AS count, AVG(avg_score) AS avg_score "
            "FROM exam_sessions GROUP BY version"
        ))).mappings().all()

        agreement = (await conn.execute(text(
            "SELECT AVG(ABS(delta_accuracy))  AS mean_delta_accuracy, "
            "       AVG(ABS(delta_reasoning)) AS mean_delta_reasoning, "
            "       AVG(ABS(delta_clarity))   AS mean_delta_clarity, "
            "       COUNT(*) AS total_reviews, "
            "       SUM(CASE WHEN action='accepted' THEN 1 ELSE 0 END) AS accepted, "
            "       SUM(CASE WHEN action='modified' THEN 1 ELSE 0 END) AS modified "
            "FROM teacher_reviews"
        ))).mappings().first()

        weak_answers = (await conn.execute(text(
            "SELECT COUNT(*) AS weak_count, AVG(score_total) AS avg_weak_score "
            "FROM exam_turns WHERE score_total < 5"
        ))).mappings().first()

    return {
        "sessions_by_version":   [_conv(r) for r in version_counts],
        "grading_agreement":     _conv(agreement) if agreement else {},
        "weak_answer_detection": _conv(weak_answers) if weak_answers else {},
    }
