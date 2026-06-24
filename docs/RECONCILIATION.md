# QuantumMind — Day-One Repo Reconciliation

> Companion to [`NORTHSTAR.md`](../NORTHSTAR.md). This is the record of where the
> **actual code** diverged from the engineering brief's assumptions, captured before
> any hardening work began. It reflects the repository as of the first reconciliation
> pass and is intentionally frozen as a day-one snapshot — later phases update
> `NORTHSTAR.md`, not this file.

Scope reviewed: every module under `backend/app/` (22 files), `frontend/src/`,
`backend/pyproject.toml` + `backend/uv.lock`, and both `package.json` files.

---

## 1. LLM provider — the biggest assumption gap (Phase 0)

The brief says "OpenAI today, vLLM later" and "`ChatGroq`/OpenAI". Reality: the system
is **100% Groq via `langchain-groq`**, and **OpenAI is entirely absent**.

- Declared dep: `langchain-groq==0.2.1`. No `openai`, no `langchain-openai` anywhere
  (confirmed in `pyproject.toml` and `uv.lock`).
- There is **no `backend/app/core/llm.py`**. `backend/app/core/` contains only
  `config.py`, `memory.py`, `prompts.py`, `cache.py`.
- **7 separate `get_llm()`-style functions** instantiate `ChatGroq` directly, each
  hardcoding its own temperature:
  - `theory_agent.py:20` `temperature=0.7` · `code_agent.py:37` `0.1` ·
    `rag_agent.py:55` `0.3/0.0` · `lesson_agent.py:16` `0.2/0.5/0.0` ·
    `exam_agent.py:26` `0.4/0.0/0.3` · `orchestrator.py:27` `0.0`.
  - The orchestrator **hardcodes `model="llama-3.1-8b-instant"`**, ignoring
    `settings.groq_model`; every other agent reads `settings.groq_model`.
- **Important for the vLLM target:** vLLM is OpenAI-compatible, **not** Groq-compatible.
  The current seam (`ChatGroq`) cannot point at vLLM by URL change. Phase 0 must
  *introduce* an OpenAI-style client (`langchain-openai` or the `openai` SDK — both
  currently absent) as the seam, not just relocate the Groq calls. The brief's "OpenAI
  client path works unchanged against vLLM" is true, but the repo has no such path today.

## 2. The agent roster doesn't match the brief's list

Brief says refactor "theory, code, rag, lesson, exam, grade, orchestrator." Reality:

- **No standalone "grade" agent.** Grading lives inside `exam_agent.py`
  (`grade_answer_node`) and `lesson_agent.py` (`grade_node`). Two different
  `grade_answer()` public signatures exist.
- **`rag` and `review` are dead routes.** `orchestrator.py:136-145`: a `"rag"` decision
  falls back to the theory agent, and `"review"` falls back to code. So `rag_agent.py`
  (a full retrieve→generate→grade graph) is **never actually invoked** by chat/stream —
  nothing calls `run_rag_agent`. `review` has no agent file at all.
- Orchestrator only special-cases `mode=="practice"` → code. The frontend's `course`
  mode (`CoursePanel.jsx`) just goes through normal `route()`, so course/RAG retrieval
  by week never fires through the orchestrator.
- Real public entrypoints: `run_theory_agent(user_message, chat_history=None,
  thread_id="default")`, `run_code_agent(...)`, `run_rag_agent(..., week=0)`.
  **Streaming is mostly fake**: only `stream_theory_agent` truly streams from the LLM;
  `stream_code_agent`/`stream_rag_agent` run to completion then yield word-by-word.

## 3. `config.py`

- Uses `pydantic_settings.BaseSettings` with the **legacy inner `class Config`** (not v2
  `SettingsConfigDict`/`model_config`), at `config.py:55`.
- **`pydantic-settings` is not declared** in `pyproject.toml`. It resolves only
  transitively (via `langchain-community`, `uv.lock`, v2.13.1). Works today, fragile.
- Fields: `groq_api_key` (required), `groq_model="llama-3.1-8b-instant"`, `app_env`,
  `frontend_url`, `chroma_path`, `teacher_password="quantum2026"`. **No** DB URL, Redis
  URL, provider/base-URL, timeouts, or budget knobs.
- Module-level `settings = get_settings()` runs at import (`config.py:90`) — fail-fast,
  but also means any import requires a valid env (matters for tests).

## 4. `memory.py` (the LangGraph checkpointer)

- 18 lines: a global `MemorySaver()` (RAM). The file's own comment says *"Lost on server
  restart"* and *"swap MemorySaver for AsyncPostgresSaver in one line."*
- `langgraph==0.2.55`. **`langgraph-checkpoint-sqlite>=2.0.11` is declared but completely
  unused** — even the durable option already installed isn't wired. No
  `langgraph-checkpoint-postgres` present.
- Subtlety the brief doesn't anticipate: theory/code/rag graphs compile **with** the
  checkpointer, but **exam and lesson graphs compile with no checkpointer**
  (`g.compile()` — `exam_agent.py:161`, `lesson_agent.py:128`). Graphs are built once and
  cached in module globals, so swapping the checkpointer means rebuilding cached graphs too.
- `chat.py:112-137` `/history/{thread_id}` is a **stub** — it always returns
  `{"messages": []}`.

## 5. `_exam_state` and live state (Phase 1 core)

- It exists exactly as the brief fears: `_exam_state: dict = {}` module global at
  `exam.py:13`. Holds turns, `current_question`, scores, weak_areas; `del`'d on completion.
- **The brief's "reconstructable from Postgres alone" is not currently true even for
  SQLite:** `start_exam` generates Q1 and stores the *current question* **only** in
  `_exam_state` (`exam.py:43`); it is never written to the DB. Completed turns *are*
  persisted immediately via `log_turn`, but if the process restarts mid-exam, the session
  row survives while `_exam_state` is gone → `submit_answer` returns **404 "Session not
  found"** (`exam.py:62-64`). So the in-flight question is the missing durable piece.
- A second RAM-global store: the LRU cache in `cache.py:73` (ideal answers + lesson
  plans), whose comment also says "Upgrade to Redis when you have multiple instances."

## 6. Database — `audit_db.py`

- **SQLite via synchronous `sqlite3`**, file `backend/data/audit.db`. `get_conn()` opens a
  **fresh connection per call** (`audit_db.py:28`) — the opposite of the brief's "pooled,
  no per-request connect/disconnect." All calls are **blocking sync inside async routes**
  (blocks the event loop). `aiosqlite` is installed (transitive) but unused.
- Tables match the brief: `exam_sessions`, `exam_turns`, `teacher_reviews`, plus the
  research table named **`research_metrics`**.
- `exam_sessions.student_name TEXT NOT NULL` stores the **full student name as free text**
  — no student-ID, no pseudonym, no consent column, no encryption. This is the GDPR focal
  point.
- **No Alembic, no migrations dir, no SQLAlchemy models** (`sqlalchemy` present
  transitively, unused). Schema is raw `CREATE TABLE IF NOT EXISTS` in `init_db()`.
- Likely latent bug to verify in Phase 1: `end_session` (`audit_db.py:139`) does an
  `INSERT … SELECT` of the existing row (duplicate PK) *then* an `UPDATE`; the INSERT looks
  like it would raise a UNIQUE/IntegrityError. Flagged, not asserted — worth a test when we
  touch it.

## 7. Code execution — `execute.py` + `code_agent.py` (Phase 3)

- **Two** bare-`subprocess` execution paths, both running on the **host venv Python**
  (`VIRTUAL_ENV`), with full network / filesystem / env access:
  - `execute.py` `/api/execute` — wraps student code in an auto-draw harness, `timeout=45s`.
  - `code_agent.py:130` `execute_code` — runs LLM-generated code, `timeout=30s`.
- No container, no CPU/memory caps, no network isolation, no non-root, no read-only FS.
  Student/LLM code can `import` anything installed, read `backend/.env`/secrets, and reach
  the network. Exactly the Phase-3 hole, ×2 call sites.

## 8. Dependencies present / absent

- **Declared & present:** fastapi 0.115, uvicorn, sse-starlette, langchain 0.3.7,
  langchain-groq 0.2.1, langgraph 0.2.55, langchain-community, chromadb 0.5.18,
  langchain-huggingface, sentence-transformers, **qiskit ≥2.3.1** / qiskit-aer,
  langgraph-checkpoint-sqlite, pypdf, httpx, pydantic 2.9.2, python-multipart, matplotlib,
  pylatexenc, python-dotenv. Dev: pytest 8.3.3, httpx.
- **Present transitively (usable but undeclared):** `pydantic-settings`, `sqlalchemy`,
  **`tenacity`** (handy for Phase-2 retry), `aiosqlite`, `bcrypt`.
- **Absent (Phases will need to add):** `redis`, `psycopg`/`asyncpg`, `alembic`,
  `langgraph-checkpoint-postgres`, `langchain-openai`/`openai` (the vLLM seam), any
  Docker/sandbox tooling.
- Minor drift: qiskit is **≥2.x**, but every prompt/sanitizer text says "Qiskit 1.x"
  (e.g. `code_agent.py:50`). Harmless but inconsistent.

## 9. GDPR / identity / auth (Phase 4)

- Identity = a **free-text `student_name`** typed in `Exammode.jsx:41`, POSTed to
  `/api/exam/start`. No login, no student ID, **no consent screen or consent record**
  anywhere.
- Teacher auth = shared password with **two disagreeing sources of truth**: `config.py`
  default `"quantum2026"` vs. `exam.py:17` `verify_teacher` reading
  `os.environ["TEACHER_PASSWORD"]` default **`"quantum2025"`** — and it bypasses the config
  seam by reading the env directly. Sent plaintext via `X-Teacher-Password` header.
- Secrets: `backend/.env` **is** git-ignored (verified — untracked), and `backend/data/`
  (DB + Chroma) is ignored too. But `.gitignore` claims *"`.env.example` IS committed"* and
  **no `backend/.env.example` actually exists** — so the documented template is missing.
  Env keys present: `GROQ_API_KEY, GROQ_MODEL, APP_ENV, FRONTEND_URL, CHROMA_PATH,
  TEACHER_PASSWORD`.

## 10. Tests, Docker, observability, ops (cross-cutting)

- **Zero application tests** — no `backend/tests/`, no `test_*.py` under `app/`, no
  `conftest.py`. pytest is declared but unused. The brief's "tests gate merges" starts from
  nothing.
- **No Dockerfile / docker-compose** anywhere in the project. The brief's "hand-off as
  Docker services" has no starting point.
- Observability = `print()` statements throughout. `/health` exists (`main.py:40`) but is
  **static** — it doesn't check DB/Redis/LLM. No structured logging, correlation IDs, or
  metrics.
- CORS inconsistency: `main.py` restricts to `settings.frontend_url`, but the SSE response
  in `stream.py:70` hardcodes `Access-Control-Allow-Origin: *`.
- Frontend hardcodes `http://localhost:8000` in **six** components (no `VITE_` env var), so
  deployment config isn't externalized on the frontend either.

---

## Net assessment vs. the brief

The brief is directionally right but wrong on the single most load-bearing assumption:
**the provider is Groq, not OpenAI, and there is no LLM seam or OpenAI/vLLM client at all**
— so Phase 0 is a genuine build, not a relocation. Everything else the brief targets
(`_exam_state`, `MemorySaver`, SQLite + per-request sync connections, bare subprocess ×2,
free-text student name, shared password, no tests/Docker/observability) is present and
matches its description, with a few extra wrinkles it didn't know about (unused sqlite
checkpointer, undeclared `pydantic-settings`, the dead RAG route, the unpersisted in-flight
exam question, the teacher-password split-brain, the missing `.env.example`).
