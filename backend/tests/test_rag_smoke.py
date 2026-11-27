"""The RAG workflow is reachable and retrieves by week.

Real ChromaDB in a temp directory with a deterministic fake embedding model (no
model download), real upload ingestion, real graph; only the LLM is faked.
"""
import asyncio

from langchain_core.embeddings import DeterministicFakeEmbedding
from langgraph.checkpoint.memory import MemorySaver

import app.core.llm as llm_mod
from app.agents import orchestrator, rag_agent
from app.core import memory, vectorstore
from app.routes import upload


def _setup(monkeypatch, tmp_path, label="rag"):
    prompts = []

    async def fake_chat(messages, *, call_type=None, **kwargs):
        if call_type == "route":
            return '{"agent": "%s", "reason": "test"}' % label
        prompts.append((call_type, "\n".join(m.content for m in messages)))
        return "pass" if call_type == "rag_grade" else "An answer from the notes."

    monkeypatch.setattr(llm_mod, "chat", fake_chat)
    monkeypatch.setattr(vectorstore, "CHROMA_DIR", str(tmp_path / "chroma"))
    monkeypatch.setattr(vectorstore, "get_embeddings", lambda: DeterministicFakeEmbedding(size=32))
    monkeypatch.setattr(memory, "_checkpointer", MemorySaver())
    monkeypatch.setattr(rag_agent, "_rag_graph", None)
    return prompts


def _ingest(tmp_path, name, text, week):
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return upload.ingest_file(str(f), ".md", name, week)


def test_rag_label_retrieves_that_weeks_material(monkeypatch, tmp_path):
    prompts = _setup(monkeypatch, tmp_path)
    assert _ingest(tmp_path, "w3.md", "Week three: the Deutsch-Jozsa oracle is balanced or constant.", 3) >= 1
    assert _ingest(tmp_path, "w5.md", "Week five: Shor's algorithm factors integers.", 5) >= 1

    answer = asyncio.run(orchestrator.run_agent(
        "What does the Deutsch-Jozsa oracle decide?", mode="course", thread_id="t-rag", week=3))

    generate_prompt = next(p for t, p in prompts if t == "rag_generate")
    assert "Deutsch-Jozsa oracle is balanced" in generate_prompt   # week 3 retrieved
    assert "Shor" not in generate_prompt                           # week 5 filtered out
    assert "Week 3 course materials" in answer


def test_empty_store_answers_without_loading_the_model(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)

    def must_not_load():
        raise AssertionError("embedding model loaded for an empty store")

    monkeypatch.setattr(vectorstore, "get_embeddings", must_not_load)
    answer = asyncio.run(orchestrator.run_agent("Any notes on Grover?", mode="course", thread_id="t-empty"))
    assert "General knowledge" in answer


def test_rag_streams_through_stream_agent(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _ingest(tmp_path, "w2.md", "Week two: the Hadamard gate creates superposition.", 2)

    async def collect():
        return "".join([t async for t in orchestrator.stream_agent(
            "What creates superposition?", mode="course", thread_id="t-stream", week=2)])

    assert "Week 2 course materials" in asyncio.run(collect())
