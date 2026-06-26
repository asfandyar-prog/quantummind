# ── app/db/models.py ─────────────────────────────────────────
# SQLAlchemy 2.0 ORM models for the exam audit schema (Postgres).
#
# These replace the hand-written CREATE TABLE SQL in audit_db.py. They are the
# source of truth for the schema; Alembic migrations are written to match them.
#
# Modernized types vs the old SQLite schema:
#   - timestamps  → DateTime(timezone=True)  (timestamptz)
#   - is_followup → Boolean                  (was INTEGER 0/1)
#   - scores      → Numeric(5, 2)            (exact 2-decimal; graded data is sacred)
#                   NOTE: Numeric maps to Python Decimal — the repository (commit 3)
#                   converts to float when building JSON responses.
#   - proper foreign keys + indexes on FK columns (Postgres does not auto-index FKs)
#
# New in-flight columns on exam_sessions make an exam fully reconstructable from
# Postgres alone (the current question + counters that used to live only in the
# in-memory _exam_state dict).

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    student_name: Mapped[str] = mapped_column(String, nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)  # V1 | V2 | V3
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    total_turns: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    avg_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'active'"))  # active | completed | abandoned

    # ── In-flight question (durable; reconstructable from Postgres alone) ──
    current_question: Mapped[Optional[str]] = mapped_column(Text)
    current_turn_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    current_is_followup: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    followup_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    turns: Mapped[list["ExamTurn"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["TeacherReview"]] = relationship(back_populates="session")


class ExamTurn(Base):
    __tablename__ = "exam_turns"

    turn_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("exam_sessions.session_id"), nullable=False, index=True
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    student_answer: Mapped[str] = mapped_column(Text, nullable=False)

    score_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    score_reasoning: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    score_clarity: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    score_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    ai_justification: Mapped[Optional[str]] = mapped_column(Text)
    ideal_answer: Mapped[Optional[str]] = mapped_column(Text)

    is_followup: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session: Mapped["ExamSession"] = relationship(back_populates="turns")
    reviews: Mapped[list["TeacherReview"]] = relationship(back_populates="turn")


class TeacherReview(Base):
    __tablename__ = "teacher_reviews"

    review_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("exam_sessions.session_id"), nullable=False, index=True
    )
    turn_id: Mapped[str] = mapped_column(
        String, ForeignKey("exam_turns.turn_id"), nullable=False, index=True
    )

    # What the AI gave
    ai_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    ai_reasoning: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    ai_clarity: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    ai_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # What the teacher changed it to (NULL = accepted AI score)
    teacher_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    teacher_reasoning: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    teacher_clarity: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    teacher_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Delta (teacher - AI) for research analysis
    delta_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    delta_reasoning: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    delta_clarity: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    teacher_feedback: Mapped[Optional[str]] = mapped_column(Text)
    teacher_notes: Mapped[Optional[str]] = mapped_column(Text)  # private; not shown to student

    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # accepted | modified

    session: Mapped["ExamSession"] = relationship(back_populates="reviews")
    turn: Mapped["ExamTurn"] = relationship(back_populates="reviews")


class ResearchMetric(Base):
    __tablename__ = "research_metrics"

    metric_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("exam_sessions.session_id"), nullable=False, index=True
    )
    metric_name: Mapped[str] = mapped_column(String, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)  # generic metric (unbounded)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
