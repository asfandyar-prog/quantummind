"""unique (session_id, turn_number) on exam_turns

Revision ID: 0003_exam_turns_unique_turn
Revises: 0002_exam_turns_graded
Create Date: 2026-09-11

Closes the double-submit race: two concurrent answers to the same turn could
both insert a row. The conditional advance in audit_db now serializes those
writes; this constraint is the database-level backstop for every path that
inserts a turn (graded, pending, backfill).

Refuses to run if duplicates already exist, rather than deleting graded answers.
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_exam_turns_unique_turn"
down_revision = "0002_exam_turns_graded"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dupes = op.get_bind().execute(sa.text(
        "SELECT session_id, turn_number, COUNT(*) AS n FROM exam_turns "
        "GROUP BY session_id, turn_number HAVING COUNT(*) > 1"
    )).fetchall()
    if dupes:
        sample = ", ".join(f"{d.session_id}#{d.turn_number} x{d.n}" for d in dupes[:5])
        raise RuntimeError(
            f"{len(dupes)} (session_id, turn_number) pair(s) already have duplicate "
            f"exam_turns rows ({sample}). Resolve them by hand first; this migration "
            "will not delete graded answers."
        )
    op.create_unique_constraint(
        "uq_exam_turns_session_turn", "exam_turns", ["session_id", "turn_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_exam_turns_session_turn", "exam_turns", type_="unique")
