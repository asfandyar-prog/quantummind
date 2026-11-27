"""The lesson answer key never leaves the server.

/lesson/plan returns the plan without check_answer, /lesson/grade grades
against the stored copy, and a request that sends its own correct_answer is
rejected. Hermetic: fake LLM, in-memory stand-in for Redis, the real HTTP layer.
"""
import json

from fastapi.testclient import TestClient

import app.core.llm as llm_mod
from app.core import lesson_store
from app.main import app

client = TestClient(app)   # no context manager, so the lifespan never runs

SECRET = "AerSimulator from qiskit_aer."
PLAN = {
    "topic": "answer-key test topic",
    "description": "d",
    "steps": [
        {"id": 1, "title": "Intro", "objective": "o", "teaching_points": ["p"],
         "check_question": "Which class simulates circuits?", "check_answer": SECRET},
        {"id": 2, "title": "Math", "objective": "o", "teaching_points": ["p"],
         "check_question": "q2", "check_answer": "a2"},
    ],
}


class FakeRedis:
    def __init__(self):
        self.data = {}

    async def set(self, key, value, ex=None):
        self.data[key] = value

    async def get(self, key):
        return self.data.get(key)


def _setup(monkeypatch):
    prompts = []

    async def fake_chat(messages, *, call_type=None, **kwargs):
        prompts.append((call_type, "\n".join(m.content for m in messages)))
        if call_type == "lesson_plan":
            return json.dumps(PLAN)
        return '{"passed": true, "feedback": "Right."}'

    redis = FakeRedis()
    monkeypatch.setattr(llm_mod, "chat", fake_chat)
    monkeypatch.setattr(lesson_store, "get_redis", lambda: redis)
    return prompts, redis


def test_plan_response_has_no_answer_key(monkeypatch):
    _, redis = _setup(monkeypatch)
    res = client.post("/api/lesson/plan", json={"topic": "answer-key test topic"})
    assert res.status_code == 200
    body = res.json()
    assert body["plan_id"]
    assert SECRET not in res.text
    assert all("check_answer" not in s for s in body["steps"])
    assert SECRET in redis.data[f"lesson:{body['plan_id']}"]   # kept server-side


def test_grade_uses_the_stored_key(monkeypatch):
    prompts, _ = _setup(monkeypatch)
    plan_id = client.post("/api/lesson/plan", json={"topic": "answer-key test topic"}).json()["plan_id"]
    res = client.post("/api/lesson/grade", json={"plan_id": plan_id, "step_num": 1, "student_answer": "AerSimulator"})
    assert res.status_code == 200 and res.json()["passed"] is True
    grade_prompt = [p for t, p in prompts if t == "lesson_grade"][-1]
    assert SECRET in grade_prompt
    assert "Which class simulates circuits?" in grade_prompt


def test_client_supplied_answer_key_is_rejected(monkeypatch):
    _setup(monkeypatch)
    plan_id = client.post("/api/lesson/plan", json={"topic": "answer-key test topic"}).json()["plan_id"]
    res = client.post("/api/lesson/grade", json={
        "plan_id": plan_id, "step_num": 1, "student_answer": "x", "correct_answer": "x",
    })
    assert res.status_code == 422


def test_unknown_or_expired_plan_is_404_and_bad_step_is_400(monkeypatch):
    _setup(monkeypatch)
    res = client.post("/api/lesson/grade", json={"plan_id": "nope", "step_num": 1, "student_answer": "x"})
    assert res.status_code == 404
    plan_id = client.post("/api/lesson/plan", json={"topic": "answer-key test topic"}).json()["plan_id"]
    res = client.post("/api/lesson/grade", json={"plan_id": plan_id, "step_num": 3, "student_answer": "x"})
    assert res.status_code == 400
