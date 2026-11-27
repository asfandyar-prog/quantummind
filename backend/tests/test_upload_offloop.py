"""Upload ingestion runs off the event loop.

Embedding is blocking work; inside the async route it stalled every other
request. The fake vector store checks it is called from a thread with no
running event loop. Hermetic: no Chroma, no embedding model.
"""
import asyncio

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.routes import upload

client = TestClient(app)


def test_ingestion_runs_in_a_worker_thread(monkeypatch):
    seen = {}

    class FakeStore:
        def add_documents(self, chunks):
            try:
                asyncio.get_running_loop()
                seen["on_loop"] = True
            except RuntimeError:
                seen["on_loop"] = False
            seen["chunks"] = len(chunks)

    monkeypatch.setattr(settings, "teacher_password", "right")
    monkeypatch.setattr(upload, "get_vectorstore", lambda: FakeStore())
    res = client.post(
        "/api/upload", headers={"X-Teacher-Password": "right"},
        files={"file": ("notes.md", b"# Week 1\n\nA qubit is a two-level system.")}, data={"week": "1"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["chunks"] == seen["chunks"] >= 1
    assert seen["on_loop"] is False


def test_file_with_no_text_is_a_400(monkeypatch):
    monkeypatch.setattr(settings, "teacher_password", "right")
    monkeypatch.setattr(upload, "get_vectorstore", lambda: None)
    res = client.post(
        "/api/upload", headers={"X-Teacher-Password": "right"},
        files={"file": ("empty.ipynb", b'{"cells": []}')}, data={"week": "1"},
    )
    assert res.status_code == 400
