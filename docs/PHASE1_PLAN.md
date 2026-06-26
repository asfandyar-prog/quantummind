# Phase 1 — Durable & Shared State (Plan)

> Plan only. No code until approved. Grounded in the current code as of this writing
> (re-read `db/audit_db.py`, `core/memory.py`, `routes/exam.py`, `core/config.py`,
> `pyproject.toml`, and the checkpointer wiring across the agents). This is the
> launch-blocking phase: after it, state survives restarts and is shared across workers.

## 0. Current reality (what we're changing)

- **Durable store is SQLite, synchronous, per-request connections.** `db/audit_db.py`
  opens a fresh `sqlite3.connect()` in `get_conn()` (line 28) for **every** call; all
  functions (`create_session`, `end_session`, `log_turn`, `log_teacher_review`,
  `get_all_sessions`, `get_session_turns`, `get_research_stats`) are **sync** and run
  inside `async` routes — blocking the event loop. Schema is raw `CREATE TABLE IF NOT
  EXISTS` in `init_db()`; timestamps are TEXT (isoformat), `is_followup` is INTEGER 0/1.
  Tables: `exam_sessions`, `exam_turns`, `teacher_reviews`, `research_metrics`.
- **`end_session` is buggy** (`audit_db.py:139-158`): it does an `INSERT … SELECT` of the
  existing row (duplicate primary key) **then** an `UPDATE`. The INSERT violates the PK
  uniqueness constraint. Fixed here as part of the migration.
- **Active exam state is an in-memory dict.** `routes/exam.py:13` `_exam_state: dict = {}`.
  `start_exam` generates Q1 and stores `topic, version, student_name, turns, turn_number,
  followup_count, weak_areas, current_question, total_score` **only** in `_exam_state`
  (line 43). Completed turns are persisted via `log_turn`, but **`current_question` lives
  only in RAM** — on restart, `submit_answer` (line 62) 404s and the in-flight question is
  lost. Used at lines 13, 43, 62, 128, 146, 152.
- **Checkpointer is `MemorySaver` (RAM).** `core/memory.py` holds a global `_checkpointer`
  set by `init_checkpointer()` at lifespan startup. `theory_agent.py:64`,
  `code_agent.py:188`, `rag_agent.py:232` compile **with** `get_checkpointer()`; the
  **exam graphs** (`exam_agent.py:150,258`) and **lesson graphs**
  (`lesson_agent.py:117,181,240`) compile with **no checkpointer**. Every graph is built
  once and cached in a module global (`_graph`, `_q_graph`, `_grade_graph`, …).
- **Config** uses `pydantic-settings` with `extra = "forbid"` (Phase 0) — so **every new
  env var must be added as a `Settings` field** and to `.env`/`.env.example`, or startup
  fails. Good: that's the fail-fast we want.

## 1. Postgres for durable data

**Target:** a single `DATABASE_URL` connection string. Dev = local Postgres in Docker.
Managed vs self-hosted later changes **only that string** — nothing in code.

- **Driver: psycopg 3 (`psycopg[binary]`), one driver everywhere.** SQLAlchemy async uses
  `postgresql+psycopg://…`; Alembic runs the same URL synchronously; and the LangGraph
  Postgres checkpointer (§3) also uses psycopg 3. One driver across app + migrations +
  checkpointer keeps ops simple. (asyncpg would force a second driver — rejected.)
- **ORM + async pooled engine.** New `db/database.py`: a SQLAlchemy 2.0 **async engine**
  with a connection pool created once at startup, plus an async `sessionmaker` and a
  `get_session()` dependency. No per-request connect/disconnect. New `db/models.py`: ORM
  models for the four tables, replacing the hand-written `CREATE TABLE` SQL.
- **Schema modernization (via migration, behavior-preserving):** `TIMESTAMP WITH TIME
  ZONE` instead of TEXT timestamps, `BOOLEAN` for `is_followup`, `NUMERIC`/float for
  scores, proper FKs. Plus the **new in-flight columns** on `exam_sessions` (see §2).
- **Alembic migrations, not hand-run SQL.** `alembic init` under `backend/`; `env.py`
  reads `settings.database_url`, `target_metadata = Base.metadata`. One initial migration
  creates all four tables + in-flight columns. `init_db()`'s `CREATE TABLE` is deleted;
  schema creation is `alembic upgrade head`.
- **Reversible migrations (confirmation 2).** Every migration ships a real, tested
  `downgrade()`, not a `pass`/one-way stub — the initial migration's `downgrade()` drops
  exactly the tables/columns its `upgrade()` created, so `alembic downgrade -1` cleanly
  reverses it. This is enforced as a habit from the first migration because reversibility
  is essential once there is real graded data to protect.
- **Abandoning the dev `audit.db` is safe (confirmation 3).** Existing dev SQLite data is
  **not** migrated — it's disposable, gitignored dev data and we start clean on Postgres.
  Verified nothing else depends on it: the **only** readers of the SQLite store are
  `audit_db.py`'s own functions and their two importers, `routes/exam.py:8` and
  `main.py:11` (`init_db`) — all rewritten in this phase. No script, test, or frontend code
  touches `audit.db`; `langgraph-checkpoint-sqlite` is imported nowhere (`memory.py` uses
  `MemorySaver` from langgraph core). README's prose mention of the "SQLite audit trail" is
  updated to Postgres.
- **Rewrite the data layer async.** `audit_db.py` becomes an async repository (same
  function names/shapes so routes change minimally): `await create_session(...)`,
  `await log_turn(...)`, etc. **`end_session` becomes a single `UPDATE`** (bug fixed).
  Routes (`routes/exam.py` student + teacher endpoints) `await` them.
- **Lifespan:** `main.py` startup creates the engine/pool and (dev convenience) verifies
  the schema is at head; shutdown disposes the pool. The sync `init_db()` call is removed.

## 2. Retire `_exam_state` (Redis active state + durable in-flight question)

**Principle:** durable data → Postgres; shared-ephemeral hot copy → Redis; nothing
correctness-critical in process RAM.

- **Redis** (`REDIS_URL`, `redis.asyncio`) holds the **hot** active-exam blob under
  `exam:{session_id}` with a safety TTL. New `db/redis_client.py` (async client/pool
  created at startup) and `core/exam_state.py` with `save_active(session_id, state)`,
  `load_active(session_id)`, `clear_active(session_id)`.
- **Postgres is the source of truth for the in-flight question.** Add to `exam_sessions`:
  `current_question TEXT`, `current_turn_number INT`, `current_is_followup BOOL`,
  `followup_count INT`. These, plus `exam_turns`, make an exam **fully reconstructable from
  Postgres alone**.
- **`load_active(session_id)` reconstruction order:**
  1. Redis hit → return it.
  2. Redis miss → load `exam_sessions` row (incl. in-flight columns) + ordered
     `exam_turns`; rebuild the dict (`turns` from rows; `total_score` = Σ`score_total`;
     `weak_areas` = ∪`identify_weak_areas(acc,reas,clar)` per turn); repopulate Redis;
     return. If the session is missing or `status='completed'` → `None` (404).
- **Write ordering (graded data is sacred):** in `start_exam` and `submit_answer`, persist
  to **Postgres first** (the completed turn via `log_turn`, **and** the next
  `current_question` + counters via an `exam_sessions` UPDATE — ideally one transaction),
  **then** update the Redis hot copy, **then** respond. So a crash/restart at any point
  after the student is told "saved" loses nothing and the correct in-flight question is
  durable. Even immediately after `start_exam`, Q1 is already in Postgres.
- `routes/exam.py` is rewritten to use `core/exam_state` + the async repository;
  `_exam_state` and its `del` calls are removed entirely.

## 3. Persistent checkpointer (Postgres)

- Replace `MemorySaver` with **`AsyncPostgresSaver`** from `langgraph-checkpoint-postgres`
  (psycopg 3), so theory/code/rag conversation memory survives restarts and is shared
  across workers via the same Postgres.
- **Lifecycle vs module-global graph caches (the gotcha):** the saver needs a long-lived
  pool and a one-time `await saver.setup()` (creates checkpoint tables). `init_checkpointer()`
  builds it at lifespan startup **before** any request, stores it in the module global, and
  keeps it alive for the app's lifetime (closed on shutdown). Because graphs are built
  lazily and cached, the first build captures this saver — fine, since it's created first.
  Verify the cached `_graph` globals pick up the real saver (they will, as long as
  `init_checkpointer()` runs before the first agent call, which it does).
- **Exam & lesson graphs stay checkpointer-less — intentionally.** They are single-node,
  stateless-per-call graphs with no cross-call memory (exam loop state now lives in
  Redis+Postgres via §2; lesson plan/step/grade are pure functions). Adding a checkpointer
  there would persist nothing useful. This is documented so reviewers know it's deliberate,
  not an omission.
- **Version risk + fallback:** confirm `langgraph-checkpoint-postgres` resolves against the
  installed `langgraph==0.2.55` / checkpoint-core line at lock time (same way we vetted
  `langchain-openai`). If incompatible, implement a **thin custom persistent checkpointer**
  (`BaseCheckpointSaver` subclass over our Postgres) — the brief explicitly allows this.
- `langgraph-checkpoint-sqlite` (currently declared but unused) is **removed**.
- `chat.py`'s `/history` stub stays a stub for now (out of scope to implement; noted).

## 4. Statelessness

After Phase 1, two backend processes against the same Postgres + Redis behave identically:
- No durable/correctness state in process RAM (`_exam_state` gone; checkpointer in
  Postgres; active exam in Redis+Postgres).
- The per-process module-global **graph caches** are fine: they're stateless compiled
  graphs pointing at the **shared** Postgres checkpointer.
- The in-process `LRUCache` in `core/cache.py` (ideal answers, lesson plans) **stays
  in-process**: it is a *recomputable performance cache*, not durable/correctness state.
  Two workers may have independent caches (slightly lower hit rate) but produce **identical
  results**. Moving it to Redis is optional and deferred (Phase 2 already touches Redis).
- **Known limitation (noted, not fixed here):** ChromaDB remains file-based at
  `chroma_path`. Fine for multiple workers on one host (shared disk); true multi-host needs
  a shared Chroma service — out of scope for Phase 1.

## 5. New dependencies

- `sqlalchemy[asyncio]>=2.0` — declare explicitly (present transitively today).
- `psycopg[binary]>=3.2` — single Postgres driver (app async, Alembic sync, checkpointer).
- `alembic>=1.13` — migrations.
- `redis>=5.0` — `redis.asyncio` client.
- `langgraph-checkpoint-postgres>=2.0` — `AsyncPostgresSaver` (pin/verify at lock time).
- **Remove:** `langgraph-checkpoint-sqlite` (unused).
- **Dev:** `pytest-asyncio>=0.23` (async fixtures/tests for the integration suite).
- `uv lock` + `uv sync` to regenerate `uv.lock` and the venv, as in Phase 0.

## 6. New config / env vars

Added as `Settings` fields (required because `extra="forbid"`) and to `.env` +
`.env.example`:

| Setting | Example / default | Purpose |
|---|---|---|
| `database_url` | `postgresql+psycopg://quantummind:quantummind@localhost:5432/quantummind` | The one string that changes for managed vs self-hosted |
| `redis_url` | `redis://localhost:6379/0` | Shared active-exam store |
| `db_pool_size` | `10` | Async engine pool size |
| `db_max_overflow` | `5` | Pool overflow ceiling |
| `exam_state_ttl_seconds` | `86400` | Redis safety TTL (Postgres stays source of truth) |

Test URLs (`DATABASE_URL_TEST`, `REDIS_URL_TEST`) are read in the integration `conftest`,
not added to `Settings`, so they don't leak into app config.

## 7. Dev infrastructure (Docker, dev-only)

- New `docker-compose.dev.yml` with `postgres:16` and `redis:7` services (named volumes,
  exposed on localhost), matching the default `DATABASE_URL`/`REDIS_URL`. This is **dev
  infra only** — not the prod vLLM/sandbox images (those are later phases). The app still
  runs on the host via uvicorn against these containers.

## 8. Proof of done — the restart test (the most important test in the project)

Integration tests under `backend/tests/integration/` (need Postgres + Redis from the
compose stack; a `conftest` runs `alembic upgrade head` on a dedicated **test** database
and flushes the test Redis db in fixtures; skip with a clear message if unreachable). The
LLM seam is monkeypatched (deterministic, offline) exactly like the Phase 0 smoke tests, so
question/grade calls are canned.

**`test_exam_restart` (the gate):**
1. Start an exam → capture `session_id` and Q1.
2. Submit one answer → assert it's graded and the turn is persisted; capture the issued
   next question Q2.
3. **Simulate the restart:** dispose the engine/redis/checkpointer, **flush Redis**
   (proving "reconstructable from Postgres alone if Redis is flushed"), and build a **fresh**
   app/data-layer instance (new pool, new checkpointer, cleared graph caches).
4. Resume on the fresh instance: assert the reconstructed `current_question` **equals Q2**,
   the first turn is present **with its scores**, and submitting the next answer continues
   correctly (turn numbering, follow-up logic intact).

This requires an `create_app()` / re-initializable data layer so a "fresh process" can be
constructed in-test. A heavier variant — spawn uvicorn as a subprocess, `kill -9`, restart,
drive over HTTP — is documented as an optional manual/CI check; the in-process
fresh-instance + Redis-flush test is the automated gate.

**`test_two_workers_share_session`:** two independent data-layer instances (two engines +
redis clients) against the same Postgres+Redis — start/seed on "worker A", read and submit
the next answer on "worker B", assert identical view and correct continuation. Demonstrates
the brief's "two workers sharing one session."

Plus unit tests: `end_session` performs a single UPDATE and is idempotent (regression for
the fixed bug); `load_active` reconstructs correctly from Postgres with Redis empty.

## 9. Phase boundaries (explicitly NOT in Phase 1)

- **No auth / no GDPR / no identity-and-consent model.** Per your instruction, `student_name`
  stays free-text; consent/identity columns are deferred to **Phase 4**. (This diverges from
  the brief's original "design the consent columns now in Phase 1" — deferred deliberately.)

  **Confirmation 1 — Phase 4 is purely additive.** `exam_sessions` is keyed on `session_id`
  (an opaque UUID primary key), and `exam_turns`/`teacher_reviews`/`research_metrics` already
  foreign-key onto that `session_id` — identity is **not** part of any key, it's only the
  `student_name` value column. So Phase 4 can, in one additive migration: (a) create a
  `students` table (`student_id` PK, pseudonymous identifier, `consent_given`, `consent_at`,
  retention fields…); and (b) add a **nullable** `student_id` FK column to `exam_sessions`.
  Existing rows are untouched — they keep `student_name` and a `NULL` `student_id` until
  optionally backfilled (e.g. by matching `student_name`); no existing row is rewritten and
  no key changes. Reads then join `exam_sessions → students` on `student_id`, and
  pseudonymization is just "reference `student_id`, stop surfacing `student_name`". Because
  every child table keys on the stable `session_id`, none of those relationships change. The
  Phase 1 schema therefore does not block any Phase 4 GDPR work.
- **No retries/backoff/timeouts/concurrency limits/token budget** (Phase 2).
- **No code-execution sandboxing** (Phase 3).
- No prompt/behavior changes; grading/question logic is unchanged — only *where state lives*.

## 10. Proposed commit sequence (on approval)

One logical commit per step; each leaves the app runnable; local only, no push.

1. `chore: add Postgres/Redis dev stack, deps, and config` — `docker-compose.dev.yml`,
   new `Settings` fields + `.env`/`.env.example`, pyproject deps (add sqlalchemy, psycopg,
   alembic, redis, langgraph-checkpoint-postgres; remove checkpoint-sqlite; dev
   pytest-asyncio), `uv` lock/sync, Alembic scaffold. App still on SQLite — unchanged, green.
2. `feat: SQLAlchemy models, async engine, and initial Alembic migration` — `db/models.py`,
   `db/database.py`, the initial migration creating the Postgres schema incl. in-flight
   columns. New layer dormant; routes still on old `audit_db`. Green.
3. `refactor: move audit persistence to async Postgres repository` — rewrite `audit_db` as
   the async repository, switch `routes/exam.py` (student + teacher) to `await` it, **fix
   `end_session`**, swap lifespan `init_db` → engine/pool + schema-at-head check. Durable
   data now on Postgres; `_exam_state` still present. Green (Postgres required).
4. `feat: retire _exam_state — Redis active state + durable in-flight question` —
   `db/redis_client.py`, `core/exam_state.py`, the in-flight columns wired in, `routes/exam.py`
   rewritten, `_exam_state` removed. Green.
5. `feat: persistent LangGraph checkpointer (Postgres)` — `core/memory.py` →
   `AsyncPostgresSaver` with startup `setup()`; theory/code/rag use it; exam/lesson
   documented checkpointer-less. Green.
6. `test: Phase 1 proof — restart + two-worker integration tests` — integration `conftest`
   (migrate test DB, flush test Redis, skip-if-unavailable), `test_exam_restart`,
   `test_two_workers_share_session`, and the `end_session`/`load_active` unit tests.

Awaiting approval before writing any code.
