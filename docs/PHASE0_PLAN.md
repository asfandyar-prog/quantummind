# Phase 0 — LLM Abstraction Layer (Plan)

> Plan only. No code in this document and none to be written until approved. This plan is
> written against the **real** repo (see [`RECONCILIATION.md`](RECONCILIATION.md)): the
> system is 100% Groq via `langchain-groq`, there is **no** OpenAI client and **no**
> `core/llm.py`, and model/temperature are scattered across six agent modules. Phase 0 is
> therefore a genuine build of the seam, not a relocation of existing OpenAI calls.

## 0. Resolved questions (findings)

Two questions were resolved against the installed source before finalizing this plan.

**(1) Single `ChatOpenAI` client for all providers — including Groq.** `ChatGroq`
(`langchain_groq/chat_models.py`) wraps the **`groq` SDK**, a different HTTP client from the
`openai` SDK that `ChatOpenAI`/vLLM use — but everything above it is OpenAI-shaped (OpenAI
message dicts in, `AIMessage`/`AIMessageChunk.content` out). Our agents only ever do
`ainvoke → StrOutputParser → str`, `astream → chunk.content`, and parse JSON from the
**string** themselves; we use no tool-calling, `with_structured_output`, JSON mode, logprobs,
or `n>1` — i.e. none of the features where the two APIs diverge. Groq exposes an
OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`), so Groq is reachable via
`ChatOpenAI` by base-URL + key. **Decision: use one `ChatOpenAI` client for groq/openai/vllm
and drop `langchain-groq`.** This makes dev exercise the exact prod (vLLM) client path
continuously, which is the whole point of the seam. The isolation test still bans
`langchain_groq`/`groq` imports to catch regressions.

**(2) Drop the `groq_model` alias.** Safe. The only non-agent readers are `main.py:15`
(startup banner) and `main.py:42` (`/health` `"model"` field), which repoint to
`settings.llm_model`. `README.md` and the real `backend/.env` reference `GROQ_MODEL` (docs /
local config, not code); README is updated and `.env.example` uses the `LLM_*` names. A
leftover `GROQ_MODEL` in a local `.env` is silently ignored by pydantic-settings (degrades to
the default model, never crashes), so the only migration note is "rename `GROQ_MODEL` →
`LLM_MODEL`". No permanent back-compat alias is kept.

## 1. Objective

One internal interface for all model access so that **provider, model, and per-call
parameters are config, not code**. After Phase 0:

- Exactly one module imports an LLM SDK; every agent calls the seam.
- Switching `LLM_PROVIDER` (groq → openai → vllm) is a `.env` change with no code edits.
- The production target (self-hosted **vLLM**, OpenAI-compatible) is reached by the **same
  `ChatOpenAI` client path** used for dev (Groq) and OpenAI — only base URL + model + key
  differ. The prod path is therefore exercised continuously in development.
- Behavior of the Groq dev path is **functionally equivalent** (same model, same
  temperatures, same OpenAI wire protocol) — the client library moves from the `groq` SDK to
  the `openai` SDK against Groq's OpenAI-compatible endpoint, which makes no observable
  difference to our call patterns (see §0). Graded output must not drift, so temperatures and
  models are reproduced exactly.

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

## 3. The client (single `ChatOpenAI` path)

One client class — `ChatOpenAI` (`langchain-openai`) — serves all three providers. The
provider only selects a **base URL** (and how the API key is resolved); see §0 for why a
single client is correct and preferred.

| `LLM_PROVIDER` | Client class | Base URL | API key source |
|---|---|---|---|
| `groq` (dev default) | `ChatOpenAI` | `https://api.groq.com/openai/v1` (default) | `llm_api_key` or existing `groq_api_key` |
| `openai` | `ChatOpenAI` | SDK default (`api.openai.com`) | `llm_api_key` |
| `vllm` (prod) | `ChatOpenAI` | `llm_base_url` (university vLLM) | `llm_api_key` or `"EMPTY"` |

- `llm_base_url` always overrides the per-provider default when set (e.g. a self-hosted
  Groq-compatible proxy), so the table values are defaults, not hardcodes.
- `langchain-openai` is the one new runtime dependency; **`langchain-groq` is removed**.
  `openai` arrives transitively. The SDK is **lazy-imported inside the seam** (not at module
  load) so importing `app.core.llm` — and therefore every agent — stays cheap and does not
  drag the SDK into import-time.
- Client construction is per-call (matching the pre-seam code, which built a new client each
  call); connection reuse/pooling is deferred to Phase 2, where the seam already centralizes
  it.

## 4. Configuration model (`config.py`)

New settings (all optional with defaults that **preserve today's behavior**, so
module-level `settings = get_settings()` still imports without new required env):

| Setting | Default | Purpose |
|---|---|---|
| `llm_provider` | `"groq"` | Selects the client. groq \| openai \| vllm |
| `llm_model` | `"llama-3.1-8b-instant"` | The single model knob (replaces per-agent `groq_model` reads) |
| `llm_router_model` | `"llama-3.1-8b-instant"` | Preserves the orchestrator's pinned fast routing model |
| `llm_base_url` | `None` | Overrides the per-provider base URL; **required when provider is `vllm`** |
| `llm_api_key` | `None` | Key for `openai`/`vllm`; `groq` falls back to existing `groq_api_key` |

- **`groq_model` is removed** (no alias). `llm_model` is the single source of truth; the two
  `settings.groq_model` reads in `main.py` move to `settings.llm_model`, and README +
  `.env.example` use `LLM_MODEL`.
- **`groq_api_key` becomes optional** (was required) so prod (vLLM, no Groq key) can start. A
  `model_validator` on `Settings` enforces provider-appropriate config **at startup**
  (fail-fast): `groq` needs a key (`llm_api_key` or `groq_api_key`), `openai` needs
  `llm_api_key`, `vllm` needs `llm_base_url`, and any unknown provider is rejected.
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

One **non-agent** edit beyond the call sites: `main.py:15` and `main.py:42` read
`settings.groq_model` (startup banner + `/health` `"model"` field) and move to
`settings.llm_model` when the field is renamed.

Streaming note: `stream_code_agent` / `stream_rag_agent` already "fake-stream" (run to
completion, then yield word-by-word); they call `run_*` which now route through the seam, so
no extra change is needed. Only `stream_theory_agent` uses real token streaming and moves to
`llm.stream`.

## 6. Dependency changes

- **Add:** `langchain-openai` (runtime). `openai` arrives transitively.
- **Remove:** `langchain-groq` (no longer used — Groq is reached via `ChatOpenAI`).
- **Declare explicitly (already transitive):** `pydantic-settings`.
- `uv lock` + `uv sync` regenerate `uv.lock` and the venv to match. If the lock/sync cannot
  run (offline), the source change still stands and the isolation + provider-logic + agent
  smoke tests pass without `langchain-openai` installed (see §8); only the real-client
  construction test is skipped until the dep is present.
- `langgraph-checkpoint-sqlite` stays declared-but-unused until Phase 1.

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
   to `groq` / `openai` / `vllm`, assert the seam resolves the expected base URL and API key
   for each provider (pure functions — no SDK import, always runs), and that an unknown
   provider / missing vLLM base URL fails fast in the validator. A second, `importorskip`-
   guarded case stubs `ChatOpenAI` to capture constructor kwargs and confirms the right
   base_url/model/key are passed — **with no other code edited**. No real network.
3. **Agent smoke test** (`tests/test_agents_smoke.py`): monkeypatch the seam to return canned
   output and drive `run_theory_agent`, `orchestrator.route` (still parses JSON), and
   `exam_agent.grade_answer` (still returns the score dict) — proving agents still function
   through the seam.
4. **Manual integration checklist** (needs a real `GROQ_API_KEY`, documented in the PR):
   - `LLM_PROVIDER=groq`: `/api/stream` (guided + practice), `/api/lesson/*`, and
     `/api/exam/start` + `/api/exam/answer` all return sensible responses.
   - Flip `LLM_PROVIDER` to `openai` (or a vLLM endpoint) and confirm the app runs with
     **only** the `.env` changed — no code edits — demonstrating the config-only swap that
     the vLLM hand-off depends on. Because dev itself uses `ChatOpenAI` against Groq, this is
     the *same* client path, only base URL + model + key differ.

## 9. Risks & mitigations

- **Graded-output drift.** Mitigated by reproducing exact temperatures/models (table in §4);
  the provider wire protocol (OpenAI chat-completions) is unchanged from today's Groq calls.
- **Orchestrator's pinned fast model.** Preserved via `llm_router_model`; not folded into
  `llm_model`.
- **Import-time failure.** All new settings are optional with defaults; provider-specific
  requirements (groq key / openai key / vllm base URL) are enforced by a `model_validator` at
  startup, which is the intended fail-fast — not an unexpected break.
- **Reliance on Groq's OpenAI-compatible endpoint.** This is Groq's own recommended path for
  OpenAI-SDK clients and is exercised continuously as the dev default, so any incompatibility
  surfaces immediately in development rather than at prod hand-off.

## 10. Proposed commit sequence (on approval)

Per the project rule — one logical commit per step, clear message, local only, no push.
Each commit leaves the app runnable on Groq:

1. `feat: add LLM seam (core/llm.py) with provider/model/temperature config` — adds
   `core/llm.py`, the new `config.py` settings + validator, `langchain-openai` (and
   `pydantic-settings`) in `pyproject.toml` with `uv` lock/sync, and `backend/.env.example`.
   `groq_model` is still present and agents still use it, so the app is unchanged and green.
2. `refactor: route all agents through the LLM seam` — edits the six agent modules
   (orchestrator, theory, code, rag, lesson, exam), removes every `langchain_groq` import,
   drops the `groq_model` field, and repoints `main.py` + README to `llm_model`.
3. `test: prove single LLM seam (isolation, provider switch, agent smoke)` — adds
   `backend/tests/` + `conftest.py` and the three proof-of-done tests.

Proceeding to code on this plan.
