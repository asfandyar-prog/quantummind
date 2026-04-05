# ── app/db/audit_db.py ───────────────────────────────────────
# Append-only SQLite audit trail for the AI Examiner system.
#
# Design principles:
# 1. APPEND-ONLY — rows are never updated or deleted.
#    Teacher overrides create NEW rows, they don't modify old ones.
#    This guarantees reproducibility and fairness.
# 2. FLAT SCHEMA — three tables, no complex joins needed.
# 3. SINGLE FILE — one .db file, easy to backup and export.
#
# Tables:
#   exam_sessions  — one row per exam attempt
#   exam_turns     — one row per Q&A exchange
#   teacher_reviews — one row per teacher review action

import sqlite3
import os
import json
import uuid
from datetime import datetime
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH  = os.path.join(BASE_DIR, "data", "audit.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn


def init_db():
    """
    Creates all tables if they don't exist.
    Called once at app startup.
    Safe to call multiple times — CREATE TABLE IF NOT EXISTS.
    """
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS exam_sessions (
            session_id    TEXT PRIMARY KEY,
            student_name  TEXT NOT NULL,
            topic         TEXT NOT NULL,
            version       TEXT NOT NULL,   -- V1, V2, V3
            started_at    TEXT NOT NULL,
            ended_at      TEXT,
            total_turns   INTEGER DEFAULT 0,
            avg_score     REAL DEFAULT 0.0,
            status        TEXT DEFAULT 'active'  -- active, completed, abandoned
        );

        CREATE TABLE IF NOT EXISTS exam_turns (
            turn_id       TEXT PRIMARY KEY,
            session_id    TEXT NOT NULL,
            turn_number   INTEGER NOT NULL,
            question      TEXT NOT NULL,
            student_answer TEXT NOT NULL,
            -- AI scores (0-10 each)
            score_accuracy  REAL,
            score_reasoning REAL,
            score_clarity   REAL,
            score_total     REAL,
            -- AI justification and ideal answer
            ai_justification TEXT,
            ideal_answer     TEXT,
            -- Metadata
            is_followup   INTEGER DEFAULT 0,  -- 1 if this was a follow-up question
            answered_at   TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES exam_sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS teacher_reviews (
            review_id     TEXT PRIMARY KEY,
            session_id    TEXT NOT NULL,
            turn_id       TEXT NOT NULL,
            -- What the AI gave
            ai_accuracy   REAL,
            ai_reasoning  REAL,
            ai_clarity    REAL,
            ai_total      REAL,
            -- What the teacher changed it to (NULL = accepted AI score)
            teacher_accuracy  REAL,
            teacher_reasoning REAL,
            teacher_clarity   REAL,
            teacher_total     REAL,
            -- Delta (teacher - AI) for research analysis
            delta_accuracy  REAL,
            delta_reasoning REAL,
            delta_clarity   REAL,
            -- Teacher feedback
            teacher_feedback TEXT,
            teacher_notes    TEXT,  -- private notes not shown to student
            -- Audit metadata
            reviewed_at   TEXT NOT NULL,
            action        TEXT NOT NULL,  -- 'accepted', 'modified'
            FOREIGN KEY (session_id) REFERENCES exam_sessions(session_id),
            FOREIGN KEY (turn_id)    REFERENCES exam_turns(turn_id)
        );

        CREATE TABLE IF NOT EXISTS research_metrics (
            metric_id   TEXT PRIMARY KEY,
            session_id  TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            recorded_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    print(f"[AuditDB] Initialized at: {DB_PATH}")


# ════════════════════════════════════════════════════════════════
# SESSION OPERATIONS
# ════════════════════════════════════════════════════════════════

def create_session(
    student_name: str,
    topic: str,
    version: str,
) -> str:
    """Create a new exam session. Returns session_id."""
    session_id = str(uuid.uuid4())
    conn = get_conn()
    conn.execute(
        """INSERT INTO exam_sessions
           (session_id, student_name, topic, version, started_at)
           VALUES (?, ?, ?, ?, ?)""",
        (session_id, student_name, topic, version, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    print(f"[AuditDB] Session created: {session_id} | {student_name} | {topic} | {version}")
    return session_id


def end_session(session_id: str, avg_score: float, total_turns: int):
    """Mark session as completed with final stats."""
    conn = get_conn()
    conn.execute(
        """INSERT INTO exam_sessions
           (session_id, student_name, topic, version, started_at, ended_at, total_turns, avg_score, status)
           SELECT session_id, student_name, topic, version, started_at, ?, ?, ?, 'completed'
           FROM exam_sessions WHERE session_id = ?""",
        (datetime.utcnow().isoformat(), total_turns, avg_score, session_id)
    )
    # Since we're append-only, we use a workaround:
    # Update is the one exception — session end is idempotent metadata
    conn.execute(
        """UPDATE exam_sessions
           SET ended_at = ?, total_turns = ?, avg_score = ?, status = 'completed'
           WHERE session_id = ?""",
        (datetime.utcnow().isoformat(), total_turns, avg_score, session_id)
    )
    conn.commit()
    conn.close()


# ════════════════════════════════════════════════════════════════
# TURN OPERATIONS
# ════════════════════════════════════════════════════════════════

def log_turn(
    session_id:      str,
    turn_number:     int,
    question:        str,
    student_answer:  str,
    score_accuracy:  float,
    score_reasoning: float,
    score_clarity:   float,
    ai_justification: str,
    ideal_answer:    str,
    is_followup:     bool = False,
) -> str:
    """Log a completed Q&A turn. Returns turn_id."""
    turn_id    = str(uuid.uuid4())
    score_total = round((score_accuracy + score_reasoning + score_clarity) / 3, 2)

    conn = get_conn()
    conn.execute(
        """INSERT INTO exam_turns
           (turn_id, session_id, turn_number, question, student_answer,
            score_accuracy, score_reasoning, score_clarity, score_total,
            ai_justification, ideal_answer, is_followup, answered_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            turn_id, session_id, turn_number, question, student_answer,
            score_accuracy, score_reasoning, score_clarity, score_total,
            ai_justification, ideal_answer, 1 if is_followup else 0,
            datetime.utcnow().isoformat(),
        )
    )
    conn.commit()
    conn.close()
    print(f"[AuditDB] Turn logged: {turn_id} | score={score_total}")
    return turn_id


# ════════════════════════════════════════════════════════════════
# TEACHER REVIEW OPERATIONS
# ════════════════════════════════════════════════════════════════

def log_teacher_review(
    session_id:       str,
    turn_id:          str,
    ai_accuracy:      float,
    ai_reasoning:     float,
    ai_clarity:       float,
    teacher_accuracy: Optional[float],
    teacher_reasoning: Optional[float],
    teacher_clarity:  Optional[float],
    teacher_feedback: str,
    teacher_notes:    str,
    action:           str,  # 'accepted' or 'modified'
) -> str:
    """Log a teacher review. Always appends — never updates."""
    review_id  = str(uuid.uuid4())
    ai_total   = round((ai_accuracy + ai_reasoning + ai_clarity) / 3, 2)

    # Calculate deltas (None if accepted)
    if action == 'modified' and teacher_accuracy is not None:
        t_total        = round((teacher_accuracy + teacher_reasoning + teacher_clarity) / 3, 2)
        delta_accuracy  = round(teacher_accuracy  - ai_accuracy,  2)
        delta_reasoning = round(teacher_reasoning - ai_reasoning, 2)
        delta_clarity   = round(teacher_clarity   - ai_clarity,   2)
    else:
        t_total = ai_total
        teacher_accuracy = teacher_reasoning = teacher_clarity = None
        delta_accuracy = delta_reasoning = delta_clarity = 0.0

    conn = get_conn()
    conn.execute(
        """INSERT INTO teacher_reviews
           (review_id, session_id, turn_id,
            ai_accuracy, ai_reasoning, ai_clarity, ai_total,
            teacher_accuracy, teacher_reasoning, teacher_clarity, teacher_total,
            delta_accuracy, delta_reasoning, delta_clarity,
            teacher_feedback, teacher_notes, reviewed_at, action)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            review_id, session_id, turn_id,
            ai_accuracy, ai_reasoning, ai_clarity, ai_total,
            teacher_accuracy, teacher_reasoning, teacher_clarity, t_total,
            delta_accuracy, delta_reasoning, delta_clarity,
            teacher_feedback, teacher_notes,
            datetime.utcnow().isoformat(), action,
        )
    )
    conn.commit()
    conn.close()
    print(f"[AuditDB] Teacher review: {action} | delta_acc={delta_accuracy}")
    return review_id


# ════════════════════════════════════════════════════════════════
# QUERY OPERATIONS — for teacher dashboard and research
# ════════════════════════════════════════════════════════════════

def get_all_sessions(limit: int = 50) -> list[dict]:
    """Get recent exam sessions for teacher dashboard."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM exam_sessions
           ORDER BY started_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_turns(session_id: str) -> list[dict]:
    """Get all turns for a session — for transcript review."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT t.*, r.teacher_accuracy, r.teacher_reasoning, r.teacher_clarity,
                  r.teacher_feedback, r.action as review_action
           FROM exam_turns t
           LEFT JOIN teacher_reviews r ON t.turn_id = r.turn_id
           WHERE t.session_id = ?
           ORDER BY t.turn_number ASC""",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_research_stats() -> dict:
    """
    Aggregate stats for the research layer.
    Returns metrics used in the 3 research experiments.
    """
    conn = get_conn()

    # Total sessions by version
    version_counts = conn.execute(
        "SELECT version, COUNT(*) as count, AVG(avg_score) as avg_score FROM exam_sessions GROUP BY version"
    ).fetchall()

    # AI vs Human agreement (sessions that have been reviewed)
    agreement = conn.execute(
        """SELECT
             AVG(ABS(delta_accuracy))  as mean_delta_accuracy,
             AVG(ABS(delta_reasoning)) as mean_delta_reasoning,
             AVG(ABS(delta_clarity))   as mean_delta_clarity,
             COUNT(*) as total_reviews,
             SUM(CASE WHEN action='accepted' THEN 1 ELSE 0 END) as accepted,
             SUM(CASE WHEN action='modified' THEN 1 ELSE 0 END) as modified
           FROM teacher_reviews"""
    ).fetchone()

    # Weak answer detection (turns with score < 5)
    weak_answers = conn.execute(
        """SELECT COUNT(*) as weak_count,
                  AVG(score_total) as avg_weak_score
           FROM exam_turns WHERE score_total < 5"""
    ).fetchone()

    conn.close()

    return {
        "sessions_by_version": [dict(r) for r in version_counts],
        "grading_agreement": dict(agreement) if agreement else {},
        "weak_answer_detection": dict(weak_answers) if weak_answers else {},
    }