# Phase 2 — Resilience Around the LLM (Plan)

> Plan only. No code until approved. Grounded in the current code: the LLM seam
> (`core/llm.py`), the agents that call it, and the Phase 1 exam flow
> (`routes/exam.py` + `core/exam_state.py` + `db/audit_db.py`).
>
> Goal: 100 students cannot take the system down, and **no student ever loses an
> answer to a transient LLM failure**. Most of this lives inside the seam, so no
> agent changes; the one exception is the exam answer path, which gains a durable
> "answer saved, grading will catch up" mode built directly on Phase 1.

## 0. Current reality (what we're hardening)

- `llm.chat(...)` / `llm.stream(...)` build a fresh `ChatOpenAI` per call and
  `await (client | StrOutputParser()).ainvoke(...)`. **No timeout, no retry, no
  concurrency limit, and token usage is discarded** (StrOutputParser keeps only
  text). Exceptions propagate raw to callers.
- The exam answer path (`submit_answer`): `grade_answer` (1 LLM call) →
  `generate_question` (1 LLM call) → `advance_exam`/`complete_exam` (Phase 1,
  one transaction). **The answer is persisted only as part of the graded turn**,
  so if grading raises, the answer is never written. `exam_turns` scores are
  nullable; there is no `graded` flag.
- LLM errors from the seam surface cleanly: `grade_answer_node`/
  `generate_question_node` call `llm.chat` outside their JSON `try/except`, so a
  seam exception propagates up to `submit_answer` where we can catch it.
- Redis (Upstash) and Postgres (Neon) are wired and shared across workers
  (Phase 1). The in-process `LRUCache` in `core/cache.py` is unchanged.

## 1. Retry with backoff + jitter (in the seam)

- Wrap the model call inside `chat()` (and `stream()`'s initial connect) with
  retry on **transient** errors only: `openai.RateLimitError` (429),
  `openai.APITimeoutError`, `openai.APIConnectionError`, and 5xx
  (`openai.InternalServerError` / `APIStatusError` with `status >= 500`). These
  come from the `openai` SDK under `langchain-openai` and are imported lazily in
  the seam (keeping the "one LLM seam" rule intact).
- **Non-transient** errors (400, 401, 422, content issues) are **not** retried —
  they raise immediately; retrying them wastes budget and hides bugs.
- Exponential backoff with jitter: `delay = min(base * 2**attempt, max) + random
  jitter`, capped at `LLM_MAX_ATTEMPTS`. Use **`tenacity`** (clean async retry;
  already transitive via langchain — declare it explicitly).
- After attempts are exhausted, raise a **typed seam exception**
  `LLMUnavailable` (wrapping the last error). This single typed error is what the
  exam route catches for graceful degradation (§5); everywhere else it surfaces
  as the existing error path (e.g. the SSE `error` event in `stream.py`).
- `stream()` nuance: retry only covers establishing the stream / first chunk.
  Once tokens have been yielded we do **not** silently restart (that would
  double-emit); a mid-stream failure ends the stream with the typed error.

## 2. Timeouts (in the seam)

- Pass a per-call timeout to the client (`ChatOpenAI(timeout=...)`), sourced from
  `LLM_TIMEOUT_SECONDS`, so the underlying HTTP call cannot hang unbounded.
- Backstop every call with `asyncio.wait_for(..., timeout=...)` so even a wedged
  client is bounded; a timeout maps to `APITimeoutError` → retried (§1) → finally
  `LLMUnavailable`. Optional per-call-type overrides (grading can be tighter than
  a long tutoring stream) via a small map mirroring `CALL_TEMPERATURES`.

## 3. Bounded concurrency / queue (Redis-backed, in the seam)

- A **shared** limiter so total in-flight LLM calls across all workers ≤
  `LLM_MAX_CONCURRENCY`, not per-process. New `core/llm_limiter.py`.
- **Design: a self-healing sorted-set semaphore in Redis** (avoids the stale-token
  leak of a token-list approach):
  - acquire: `ZADD llm:inflight <now> <uuid>`; `ZREMRANGEBYSCORE` to prune entries
    older than a max-hold window (≥ longest expected call); `ZCARD` to count. If
    count ≤ limit → proceed; else `ZREM` our member and retry with small sleeps up
    to `LLM_ACQUIRE_TIMEOUT_SECONDS`.
  - release: `ZREM llm:inflight <uuid>` in a `finally`.
  - A worker that dies mid-call leaves an entry that auto-expires via the prune
    window — capacity self-heals, no manual reconciliation.
- On acquire timeout, raise typed `LLMBusy` (transient) → the exam path degrades
  exactly like `LLMUnavailable` (§5); other paths surface a clear "system busy".
- Gates both `chat()` and `stream()`. Streaming holds its slot for the stream
  duration; the prune window is sized to cover it (documented caveat).

## 4. Token / cost guardrails (in the seam)

- Refactor `chat()` to call `client.ainvoke(messages)` → `AIMessage` (instead of
  piping straight to `StrOutputParser`), read `usage_metadata`
  (`input_tokens`/`output_tokens`/`total_tokens`), then return `.content`. Public
  signature stays `-> str`; **no agent changes**. (Streaming usage is best-effort:
  enable `stream_usage=True` and sum the final chunk; documented as approximate.)
- **Per-request structured log** (stdlib `logging`, not `print`): `call_type`,
  model, provider, tokens (in/out/total), latency_ms, attempts, outcome
  (ok/retried/unavailable/busy). One line per call, for later analysis.
- **Cumulative counters in Redis** (shared): e.g. `llm:tokens:{YYYY-MM-DD}` and
  `llm:tokens:session:{id}`, incremented per call. Optional **soft budget**:
  `LLM_TOKEN_BUDGET_PER_DAY` (0 = unlimited) — when exceeded, log a warning
  (hard refusal is deliberately out of scope; we don't want to block a live exam
  on a budget counter).

## 5. Graceful degradation — "answer saved, grading will catch up"

This is the heart of the phase and where Phase 1 durability pays off.

**Schema (additive, reversible Alembic migration):** add
`exam_turns.graded BOOLEAN NOT NULL DEFAULT true` (existing rows = graded). A
pending turn has `graded = false` with NULL scores. This is the durable marker of
"answer received, grade owed." The migration ships a **real `downgrade()`** that
drops the column (reversible, like the Phase 1 initial migration — verified with
`alembic downgrade`).

**New repository ops (`db/audit_db.py`):**
- `create_pending_turn(session_id, turn_number, question, student_answer,
  is_followup) -> turn_id` — persists the answer with `graded=false`, scores NULL.
  One INSERT; the answer is durable in Neon **before** we respond.
- `finalize_grade(turn_id, scores…, justification, ideal) ` — UPDATE the pending
  turn to graded.
- `get_pending_turns(...)` — turns with `graded=false` (for the backfill worker /
  startup recovery sweep).

**`submit_answer` restructured (happy path unchanged):**
1. `load_active` (Phase 1) → state.
2. `try: grading = await grade_answer(...)` — seam handles retry/timeout/limit.
3. **Success** → exactly today's path: `generate_question` + `advance_exam` /
   `complete_exam` (one txn, `graded=true`) + `save_active`; respond with scores +
   next question.
4. **`LLMUnavailable` / `LLMBusy`** → `create_pending_turn(...)` (answer durable
   now), mark the Redis hot copy "awaiting_grade", enqueue a backfill job, and
   respond `{"status": "saved_pending_grading", "turn_id": ...}` — never a 500,
   never lost work.

**How this *is* Phase 1, reused:** the pending turn lives in the same
`exam_turns` table, durable in Postgres immediately; `load_active` already rebuilds
turns from Postgres, so a restart mid-pending still has the answer; and because the
durable truth is shared Postgres, **any** worker can complete the grade. Nothing
new about durability — we're extending Phase 1's "persist before you acknowledge"
to the answer itself.

**Backfill (asynchronous completion):**
- Durable source of truth = `exam_turns.graded = false` in Postgres. A **Redis
  list** (`llm:grading:queue`) is just a fast wake-up, mirroring the exam_state
  hot-copy/Postgres pattern.
- A background worker (one `asyncio` task per process, started in the lifespan)
  consumes the queue and also runs a **startup + periodic sweep** of
  `get_pending_turns()` (so a job lost from Redis, or a turn left by a dead worker,
  is still picked up). For each pending turn it: grades (seam retries) →
  `finalize_grade` → then advances the in-flight question (`generate_question` +
  the session UPDATE) → refreshes the Redis hot copy.
- A turn needs at most two LLM steps (grade, then next question). The worker
  reconciles from Postgres: ungraded → grade; graded-but-not-advanced → advance.
  The common failure (grading, the first call) is the primary path; the
  rarer next-question failure is handled by the same reconciliation.

**Status endpoint for the frontend to poll:** `GET /exam/session/{id}/status`
→ `{awaiting_grade: bool, last_turn_graded: bool, scores?, next_question?,
exam_complete?}`. Phase 2 ships the **backend** state + endpoint; the actual
"catching up" UI is Phase 5 (the brief scopes UI there) — this plan only fixes the
API contract Phase 5 will consume.

**Non-exam paths** (theory/code/rag chat) have no sacred answer to protect; on
`LLMUnavailable`/`LLMBusy` they surface the existing SSE `error` event with a clear
message. No durable queue for them.

## 6. New dependencies

- **`tenacity`** (declare explicitly; already transitive) — async retry/backoff.
- No new infra: Redis (limiter, counters, grading queue) and Postgres (pending
  turns) are already present. `openai` exception types come from the installed
  `openai` package.

## 7. New config / env vars (added as `Settings` fields; `extra="forbid"`)

| Setting | Default | Purpose |
|---|---|---|
| `llm_timeout_seconds` | `30` | Per-call timeout |
| `llm_max_attempts` | `4` | Retry ceiling (incl. first try) |
| `llm_retry_base_delay` | `0.5` | Backoff base (seconds) |
| `llm_retry_max_delay` | `8.0` | Backoff cap (seconds) |
| `llm_max_concurrency` | `8` | Global in-flight LLM calls (shared) |
| `llm_acquire_timeout_seconds` | `20` | Max wait for a concurrency slot before degrading |
| `llm_token_budget_per_day` | `0` | Soft daily token budget (0 = unlimited) |
| `grading_backfill_interval_seconds` | `15` | Sweep cadence for the backfill worker |

`.env` + `.env.example` updated with the same keys (placeholders only).

## 8. Proof-of-done tests

**Unit (mock the client; no network, hermetic):**
1. Retry behaves — a stub client raising `RateLimitError`/`APITimeoutError`
   `n-1` times then succeeding → `chat()` returns; assert attempt count and
   backoff invoked.
2. Ceiling + typed error — always-failing transient → raises `LLMUnavailable`
   after `llm_max_attempts`; a non-transient (400) raises immediately, **not**
   retried.
3. Timeout — a hanging stub bounded by `asyncio.wait_for` → `LLMUnavailable`.
4. Token capture — stub returns usage metadata → seam logs in/out/total and
   increments the (fake) Redis counter.

**Integration (Neon + Upstash, LLM mocked):**
5. **Answer never lost / safe failure** — mock `grade_answer` to raise
   `LLMUnavailable`; `submit_answer` returns `saved_pending_grading` and the
   answer row exists in Postgres with `graded=false`. No 500, no lost work.
6. **Backfill completes** — from state (5), let the mock LLM "recover", run the
   backfill worker once → the turn becomes `graded=true` with scores and the exam
   advances (next in-flight question set); status endpoint reflects it.
7. **Bounded concurrency** — fire a burst of `N` concurrent `chat()` calls
   against a slow stub that records peak concurrency → peak ≤
   `llm_max_concurrency`; excess calls wait then proceed (or hit
   `LLMBusy` → safe path if the burst exceeds the acquire timeout).
8. **Status endpoint** — `GET /exam/session/{id}/status` returns
   `awaiting_grade=true` while a turn is pending, and after the backfill runs it
   returns the scores + next question. Explicit coverage because **Phase 5 will
   consume this contract** — it must not silently drift.

## 9. Phase boundaries (explicitly NOT here)

- **No code-execution sandboxing** → Phase 3.
- **No auth / GDPR** → Phase 4.
- **No exam "catching up" UI** → Phase 5 (Phase 2 ships only the backend state +
  status endpoint).
- No prompt/grading-logic changes; we change *how calls are made and recovered*,
  not what they ask.

## 10. Proposed commit sequence (on approval)

One logical commit per step; each leaves the app green; local only, no push.

1. `feat: LLM retry + timeout + typed errors in the seam` — tenacity dep, config
   knobs, `LLMUnavailable` + non-transient passthrough, `asyncio.wait_for` +
   client timeout. Unit tests (mock client). Agents unchanged.
2. `feat: token/cost accounting in the seam` — capture usage via `AIMessage`,
   structured per-request logging, Redis cumulative counters + soft budget warn.
3. `feat: Redis-backed LLM concurrency limiter` — `core/llm_limiter.py`
   (sorted-set semaphore) gating `chat`/`stream`, `LLMBusy`, lifespan/config
   wiring. Integration test (burst stays bounded).
4. `feat: graceful exam grading degradation + async backfill` — migration
   (`exam_turns.graded`, with a reversible `downgrade()`),
   `create_pending_turn`/`finalize_grade`/`get_pending_turns`, `submit_answer`
   fallback, `/exam/session/{id}/status`, backfill worker (lifespan) + startup
   sweep. Integration tests: answer never lost; backfill completes; **and the
   status endpoint contract** (Phase 5's dependency).

Awaiting approval before writing any code.
