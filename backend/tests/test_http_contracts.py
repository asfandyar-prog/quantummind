"""HTTP-level contracts, exercised through FastAPI's test client.

The lifespan (Postgres, Redis, the backfill worker) is deliberately not started:
every case here is decided before any database or model call.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app

client = TestClient(app)   # not used as a context manager, so the lifespan never runs


def test_execute_answers_503_when_execution_is_disabled(monkeypatch):
    monkeypatch.setattr(settings, "executor", "disabled")
    res = client.post("/api/execute", json={"code": "print(1)"})
    assert res.status_code == 503
    assert res.json()["detail"] == "Code execution is temporarily unavailable."


@pytest.mark.parametrize("path", [
    "/api/teacher/sessions",
    "/api/teacher/session/any-session",
    "/api/research/stats",
    "/api/exam/session/any-session",
    "/api/upload/status",
])
def test_teacher_endpoints_reject_a_missing_or_wrong_password(monkeypatch, path):
    monkeypatch.setattr(settings, "teacher_password", "right")
    for headers in ({}, {"X-Teacher-Password": "wrong"}):
        assert client.get(path, headers=headers).status_code == 401, (path, headers)


def test_upload_requires_the_teacher_password(monkeypatch):
    monkeypatch.setattr(settings, "teacher_password", "right")
    res = client.post("/api/upload", files={"file": ("notes.md", b"# notes")}, data={"week": "1"})
    assert res.status_code == 401


def test_upload_rejects_an_oversized_file(monkeypatch):
    monkeypatch.setattr(settings, "teacher_password", "right")
    monkeypatch.setattr("app.routes.upload.MAX_UPLOAD_BYTES", 10)
    res = client.post(
        "/api/upload", headers={"X-Teacher-Password": "right"},
        files={"file": ("notes.md", b"x" * 11)}, data={"week": "1"},
    )
    assert res.status_code == 413


def test_modified_review_needs_all_three_scores(monkeypatch):
    monkeypatch.setattr(settings, "teacher_password", "right")
    res = client.post(
        "/api/teacher/review", headers={"X-Teacher-Password": "right"},
        json={"session_id": "s", "turn_id": "t", "action": "modified", "teacher_accuracy": 8},
    )
    assert res.status_code == 400


def test_an_empty_answer_is_rejected_before_any_work():
    res = client.post("/api/exam/answer", json={"session_id": "s", "student_answer": ""})
    assert res.status_code == 422


def test_production_refuses_the_published_teacher_password():
    with pytest.raises(Exception) as exc:
        Settings(_env_file=None, groq_api_key="k", app_env="production", executor="docker")
    assert "TEACHER_PASSWORD" in str(exc.value)
    ok = Settings(_env_file=None, groq_api_key="k", app_env="production", executor="docker",
                  teacher_password="something-else")
    assert ok.app_env == "production"
