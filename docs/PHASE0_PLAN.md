# Phase 0 — LLM Abstraction Layer (Plan)

> Plan only. No code in this document and none to be written until approved. This plan is
> written against the **real** repo (see [`RECONCILIATION.md`](RECONCILIATION.md)): the
> system is 100% Groq via `langchain-groq`, there is **no** OpenAI client and **no**
> `core/llm.py`, and model/temperature are scattered across six agent modules. Phase 0 is
> therefore a genuine build of the seam, not a relocation of existing OpenAI calls.

## 1. Objective

One internal interface for all model access so that **provider, model, and per-call
parameters are config, not code**. After Phase 0:

- Exactly one module imports an LLM SDK; every agent calls the seam.
- Switching `LLM_PROVIDER` (groq → openai → vllm) is a `.env` change with no code edits.
- The production target (self-hosted **vLLM**, OpenAI-compatible) is reached by the same
  client path used for OpenAI — only base URL + model + key differ.
- Behavior of the existing Groq dev path is **unchanged** (same models, same
  temperatures) — important because graded output must not drift.

## 2. The seam

New module: **`backend/app/core/llm.py`**. Provider-agnostic, async, returns normalized
results so callers don't change their downstream handling.

Interface (matches how agents use the LLM today — they build LangChain message objects and
then `StrOutputParser()` to a string, or `astream` content chunks):

```python
# backend/app/core/llm.py  (signatures only — illustrative, not final code)
from langchain_core.messages import BaseMessage
from typing import AsyncIterator

async def chat(
    messages: list[BaseMessage],
    *,
    call_type: str | None = None,   # selects default temperature (+ optional model)
    temperature: float | None = None,  # explicit override wins over call_type default
    max_tokens: int | None = None,
    model: str | None = None,
) -> str: ...

async def stream(
    messages: list[BaseMessage],
    *,
    call_type: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> AsyncIterator[str]: ...   # yields content strings (tokens)
```

- `chat` returns a plain `str` (the seam applies `StrOutputParser` internally), so an agent
  call goes from `await (get_llm() | StrOutputParser()).ainvoke(msgs)` to
  `await llm.chat(msgs, call_type="theory")` — a near-mechanical substitution.
- `stream` yields `chunk.content` strings, matching `stream_theory_agent` today.
- Messages stay as LangChain `BaseMessage` objects (no new message abstraction) to keep the
  change minimal and behavior identical.
- The seam is the single future home for Phase 2 concerns (retry, timeout, token/cost
  budget). Phase 0 leaves a clear seam for them but does **not** implement them (no phase
  collapsing).

## 3. The client(s) introduced

A small internal provider resolver inside `llm.py` maps `LLM_PROVIDER` → a LangChain chat
client. Clients are cached by `(provider, model, temperature, max_tokens)`.

| `LLM_PROVIDER` | Client class | Source pkg | Base URL | Notes |
|---|---|---|---|---|
| `groq` (dev default) | `ChatGroq` | `langchain-groq` (already present) | n/a | Keeps today's behavior byte-for-byte |
| `openai` | `ChatOpenAI` | `langchain-openai` (**to add**) | default OpenAI | The OpenAI-compatible path |
| `vllm` (prod) | `ChatOpenAI` | `langchain-openai` (**to add**) | `LLM_BASE_URL` (university vLLM) | Same class as `openai`; only URL/model/key differ |

**Why keep `ChatGroq` rather than point `ChatOpenAI` at Groq's OpenAI-compatible endpoint:**
lowest risk — the existing dev path is unchanged, satisfying the "don't rewrite working
code" principle. Because Groq *also* exposes an OpenAI-compatible endpoint, we can later
collapse `groq` onto `ChatOpenAI` if we want a single client class; that simplification is
optional and explicitly **not** part of Phase 0.

`langchain-openai` is the only new runtime dependency the seam needs (`openai` comes in
transitively). It is **not imported until** `LLM_PROVIDER` is `openai`/`vllm` (lazy import
inside the resolver), so dev installs that only use Groq still work.

## 4. Configuration model (`config.py`)

New settings (all optional with defaults that **preserve today's behavior**, so
module-level `settings = get_settings()` still imports without new required env):

| Setting | Default | Purpose |
|---|---|---|
| `llm_provider` | `"groq"` | Selects the client. groq \| openai \| vllm |
| `llm_model` | `"llama-3.1-8b-instant"` | The single model knob (replaces per-agent `groq_model` reads) |
| `llm_router_model` | `"llama-3.1-8b-instant"` | Preserves the orchestrator's pinned fast routing model |
| `llm_base_url` | `None` | Required when provider is `vllm` (validated lazily in the seam, not at import) |
| `llm_api_key` | `None` | Key for `openai`/`vllm`; `groq` continues to use existing `groq_api_key` |

- `groq_model` is kept as a back-compat alias of `llm_model` for this phase so nothing
  breaks; the agents stop reading it directly.
- **Temperature centralization** lives in the seam as a `call_type → params` table that
  reproduces the current temperatures exactly (no behavior drift):

| `call_type` | temp | current source |
|---|---|---|
| `route` | 0.0 | `orchestrator.get_orchestrator_llm` |
| `theory` | 0.7 | `theory_agent.get_llm` |
| `code` | 0.1 | `code_agent.get_llm(0.1)` |
| `rag_generate` | 0.3 | `rag_agent.get_llm(0.3)` |
| `rag_grade` | 0.0 | `rag_agent.get_llm(0.0)` |
| `lesson_plan` | 0.2 | `lesson_agent.get_llm(0.2)` |
| `lesson_step` | 0.5 | `lesson_agent.get_llm(0.5)` |
| `lesson_grade` | 0.0 | `lesson_agent.get_llm(0.0)` |
| `exam_question` | 0.4 | `exam_agent.get_llm(0.4)` |
| `exam_grade` | 0.0 | `exam_agent.get_llm(0.0)` |

- Hygiene fixes that belong here because Phase 0 already edits `config.py`: **declare
  `pydantic-settings` explicitly** in `pyproject.toml` (currently only transitive), and
  **add `backend/.env.example`** documenting the new `LLM_*` vars (the `.gitignore` claims
  this file exists but it doesn't).

## 5. Call-site inventory & refactor map

Every current `ChatGroq` instantiation and how it routes through the seam. These are the
"seven call sites" the brief refers to (the brief's separate "grade" agent does not exist —
grading lives inside `exam_agent` and `lesson_agent`):

| # | File / function | Today | After |
|---|---|---|---|
| 1 | `orchestrator.py:27` `get_orchestrator_llm` (model pinned to 8b, temp 0.0) | `route()` builds `llm \| StrOutputParser` | `await llm.chat(messages, call_type="route", model=settings.llm_router_model)` |
| 2 | `theory_agent.py:20` `get_llm` (0.7) — `generate_response` + `stream_theory_agent` | `ainvoke` / `astream` | `await llm.chat(msgs, call_type="theory")` / `async for t in llm.stream(msgs, call_type="theory")` |
| 3 | `code_agent.py:37` `get_llm(0.1)` — `generate` node | `ainvoke` | `await llm.chat(msgs, call_type="code")` |
| 4 | `rag_agent.py:55` `get_llm(0.3)` — `generate_answer` | `ainvoke` | `await llm.chat(msgs, call_type="rag_generate")` |
| 5 | `rag_agent.py:55` `get_llm(0.0)` — `grade_answer` | `ainvoke` | `await llm.chat(msgs, call_type="rag_grade")` |
| 6 | `lesson_agent.py:16` `get_llm(0.2/0.5/0.0)` — plan / step / grade nodes | `ainvoke` | `await llm.chat(msgs, call_type="lesson_plan" \| "lesson_step" \| "lesson_grade")` |
| 7 | `exam_agent.py:26` `get_llm(0.4/0.0)` — question / grade nodes | `ainvoke` | `await llm.chat(msgs, call_type="exam_question" \| "exam_grade")` |

Each agent file loses `from langchain_groq import ChatGroq` and its local `get_llm`, and
gains `from app.core import llm`. The LangGraph graphs are built once and cached, but the
LLM is constructed **inside node functions at call time** (not at graph-build), so swapping
to the seam needs no graph rebuild — that interaction is a Phase 1 concern, untouched here.

Streaming note: `stream_code_agent` / `stream_rag_agent` already "fake-stream" (run to
completion, then yield word-by-word); they call `run_*` which now route through the seam, so
no extra change is needed. Only `stream_theory_agent` uses real token streaming and moves to
`llm.stream`.

## 6. Dependency changes

- **Add:** `langchain-openai` (runtime). `openai` arrives transitively.
- **Declare explicitly (already transitive):** `pydantic-settings`.
- **Keep:** `langchain-groq` (groq provider).
- No removals. `langgraph-checkpoint-sqlite` stays declared-but-unused until Phase 1.

## 7. Out of scope (phase boundaries)

Explicitly **not** in Phase 0, to avoid collapsing phases:

- Retry / backoff / timeouts / concurrency limits / token budgeting → Phase 2 (the seam
  reserves the single place these will live).
- Persistence, Postgres/Redis, checkpointer swap → Phase 1.
- Wiring the dead RAG route, sandboxing code execution, auth/GDPR → later phases.
- No prompt/behavior changes; temperatures and models are reproduced exactly.

## 8. Proof of done

Phase 0 is "done" only when all of the following pass. This also **bootstraps the repo's
first test suite** (`backend/tests/` + `conftest.py` with a settings override), which later
phases extend.

1. **Single-seam isolation test** (`tests/test_llm_seam_isolation.py`): walks every module
   under `backend/app/` and asserts that **no file except `core/llm.py`** imports an LLM SDK
   (`langchain_groq`, `langchain_openai`, `openai`, `groq`). This is the brief's
   "grep the codebase: zero direct LLM-SDK imports outside `llm.py`" encoded as a test.
2. **Provider-switch test** (`tests/test_llm_provider_switch.py`): with settings monkeypatched
   to `groq` vs `openai`/`vllm`, assert the seam builds the expected client class and base
   URL and that `chat`/`stream` return the normalized types — **with no other code edited**.
   No real network: the provider client is stubbed.
3. **Agent smoke test** (`tests/test_agents_smoke.py`): monkeypatch the seam to return canned
   output and drive `run_theory_agent`, `orchestrator.route` (still parses JSON), and
   `exam_agent.grade_answer` (still returns the score dict) — proving agents still function
   through the seam.
4. **Manual integration checklist** (needs a real `GROQ_API_KEY`, documented in the PR):
   - `LLM_PROVIDER=groq`: `/api/stream` (guided + practice), `/api/lesson/*`, and
     `/api/exam/start` + `/api/exam/answer` all return sensible responses.
   - Flip `LLM_PROVIDER` (e.g. to an OpenAI-compatible endpoint) and confirm the app runs
     with **only** the `.env` changed — no code edits — demonstrating the config-only swap
     that the vLLM hand-off depends on.

## 9. Risks & mitigations

- **Graded-output drift.** Mitigated by reproducing exact temperatures/models (table in §4)
  and keeping `ChatGroq` for the groq path.
- **Orchestrator's pinned fast model.** Preserved via `llm_router_model`; not folded into
  `llm_model`.
- **Import-time failure.** All new settings are optional with defaults; `vllm` base-URL
  requirement is validated lazily in the seam, so `settings = get_settings()` still imports.
- **Groq vs vLLM message parity.** Avoided for dev by keeping `ChatGroq`; the
  `ChatOpenAI`→vLLM path is validated in the manual checklist before prod hand-off.

## 10. Proposed commit sequence (on approval)

Per the project rule — one logical commit per step, clear message, local only, no push:

1. `feat: add LLM seam (core/llm.py) with provider/model/temperature config` — adds
   `core/llm.py`, the new `config.py` settings, `langchain-openai` + `pydantic-settings` in
   `pyproject.toml`, and `backend/.env.example`. No agent edits yet; app still runs on Groq.
2. `refactor: route all agents through the LLM seam` — edits the six agent modules
   (orchestrator, theory, code, rag, lesson, exam); removes every `langchain_groq` import.
3. `test: prove single LLM seam (isolation, provider switch, agent smoke)` — adds
   `backend/tests/` + `conftest.py` and the three proof-of-done tests.

Awaiting approval before writing any code.
