"""An LLM outage at /exam/start writes nothing.

The first question is generated before the session exists; if that fails the
student gets a 503 and no empty "active" session is left behind. On success the
session is created holding its first question in one write. Hermetic: the
repository and Redis calls are replaced, the real HTTP layer is used.
"""
from fastapi.testclient import TestClient

from app.core.llm_errors import LLMUnavailable
from app.main import app
from app.routes import exam as exam_route

client = TestClient(app)   # no lifespan: no database or Redis


def _setup(monkeypatch, question_or_error):
    writes = []

    async def fake_generate_question(**kwargs):
        if isinstance(question_or_error, Exception):
            raise question_or_error
        return question_or_error

    async def fake_create_session(name, topic, version, first_question=None):
        writes.append(("create_session", first_question))
        return "sid-1"

    async def fake_save_active(session_id, state):
        writes.append(("save_active", state["current_question"]))

    monkeypatch.setattr(exam_route, "generate_question", fake_generate_question)
    monkeypatch.setattr(exam_route, "create_session", fake_create_session)
    monkeypatch.setattr(exam_route, "save_active", fake_save_active)
    return writes


def test_llm_outage_at_start_writes_nothing(monkeypatch):
    writes = _setup(monkeypatch, LLMUnavailable("groq down"))
    res = client.post("/api/exam/start", json={"student_name": "Ada", "topic": "grover", "version": "V2"})
    assert res.status_code == 503
    assert writes == []                      # no session row, no Redis copy


def test_start_creates_the_session_with_its_first_question(monkeypatch):
    writes = _setup(monkeypatch, "What does Grover's algorithm search?")
    res = client.post("/api/exam/start", json={"student_name": "Ada", "topic": "grover", "version": "V2"})
    assert res.status_code == 200
    assert res.json()["session_id"] == "sid-1"
    assert writes == [
        ("create_session", "What does Grover's algorithm search?"),
        ("save_active", "What does Grover's algorithm search?"),
    ]
