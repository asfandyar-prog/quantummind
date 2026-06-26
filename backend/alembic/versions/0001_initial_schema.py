"""initial schema: exam audit tables (Postgres)

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-26

Hand-written to match app/db/models.py. Modernized types vs the old SQLite
schema: timestamptz, boolean (was INTEGER 0/1), Numeric(5,2) for scores, plus
proper foreign keys and indexes on FK columns. Includes the new in-flight
columns on exam_sessions.

UNVERIFIED: this migration has NOT been run against a real Postgres yet (no DB
available at authoring time). Review before applying; run `alembic upgrade head`
against Postgres to verify.
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_sessions",
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("student_name", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_turns", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("avg_score", sa.Numeric(5, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("current_question", sa.Text(), nullable=True),
        sa.Column("current_turn_number", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("current_is_followup", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("followup_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("session_id"),
    )

    op.create_table(
        "exam_turns",
        sa.Column("turn_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("student_answer", sa.Text(), nullable=False),
        sa.Column("score_accuracy", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_reasoning", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_clarity", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_total", sa.Numeric(5, 2), nullable=True),
        sa.Column("ai_justification", sa.Text(), nullable=True),
        sa.Column("ideal_answer", sa.Text(), nullable=True),
        sa.Column("is_followup", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.session_id"]),
        sa.PrimaryKeyConstraint("turn_id"),
    )
    op.create_index("ix_exam_turns_session_id", "exam_turns", ["session_id"])

    op.create_table(
        "teacher_reviews",
        sa.Column("review_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("turn_id", sa.String(), nullable=False),
        sa.Column("ai_accuracy", sa.Numeric(5, 2), nullable=True),
        sa.Column("ai_reasoning", sa.Numeric(5, 2), nullable=True),
        sa.Column("ai_clarity", sa.Numeric(5, 2), nullable=True),
        sa.Column("ai_total", sa.Numeric(5, 2), nullable=True),
        sa.Column("teacher_accuracy", sa.Numeric(5, 2), nullable=True),
        sa.Column("teacher_reasoning", sa.Numeric(5, 2), nullable=True),
        sa.Column("teacher_clarity", sa.Numeric(5, 2), nullable=True),
        sa.Column("teacher_total", sa.Numeric(5, 2), nullable=True),
        sa.Column("delta_accuracy", sa.Numeric(5, 2), nullable=True),
        sa.Column("delta_reasoning", sa.Numeric(5, 2), nullable=True),
        sa.Column("delta_clarity", sa.Numeric(5, 2), nullable=True),
        sa.Column("teacher_feedback", sa.Text(), nullable=True),
        sa.Column("teacher_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.session_id"]),
        sa.ForeignKeyConstraint(["turn_id"], ["exam_turns.turn_id"]),
        sa.PrimaryKeyConstraint("review_id"),
    )
    op.create_index("ix_teacher_reviews_session_id", "teacher_reviews", ["session_id"])
    op.create_index("ix_teacher_reviews_turn_id", "teacher_reviews", ["turn_id"])

    op.create_table(
        "research_metrics",
        sa.Column("metric_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("metric_name", sa.String(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.session_id"]),
        sa.PrimaryKeyConstraint("metric_id"),
    )
    op.create_index("ix_research_metrics_session_id", "research_metrics", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_research_metrics_session_id", table_name="research_metrics")
    op.drop_table("research_metrics")
    op.drop_index("ix_teacher_reviews_turn_id", table_name="teacher_reviews")
    op.drop_index("ix_teacher_reviews_session_id", table_name="teacher_reviews")
    op.drop_table("teacher_reviews")
    op.drop_index("ix_exam_turns_session_id", table_name="exam_turns")
    op.drop_table("exam_turns")
    op.drop_table("exam_sessions")
