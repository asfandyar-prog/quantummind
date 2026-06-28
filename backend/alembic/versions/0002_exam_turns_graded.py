"""add exam_turns.graded for graceful grading degradation

Revision ID: 0002_exam_turns_graded
Revises: 0001_initial
Create Date: 2026-06-28

Additive + reversible. Existing turns default to graded=true; pending turns
(answer saved, grade owed) are inserted with graded=false and flipped true by
the backfill worker.
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_exam_turns_graded"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exam_turns",
        sa.Column("graded", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("exam_turns", "graded")
