# QuantumMind — Production Hardening & Scaling Engineering Brief

## How to use this document
You are working on QuantumMind, an existing multi-agent AI quantum-computing
education platform (FastAPI + LangGraph + React). This brief is the north star
for taking it from a working prototype to a production system that will run
**live, graded examinations for ~100 students for a full university semester**
under **GDPR**.

**Before doing anything else:**
1. Read the actual repository in full — every file under `backend/app/` and
   `frontend/src/`, plus `pyproject.toml`/lockfile and `package.json`.
2. Produce a short written reconciliation: where does the real code differ from
   the assumptions in this brief? List concrete discrepancies (file names,
   function signatures, libraries already present/absent).
3. Do NOT start editing until that reconciliation is shown to me and I approve.
4. Work phase by phase. Do not begin a phase until the previous one is merged,
   tested, and I have explicitly said to proceed. Never collapse phases.

## Non-negotiable principles (apply to every phase)
- **State is the enemy.** No durable or shared state lives in a Python process's
  RAM. Durable data → Postgres. Shared-ephemeral data → Redis. Only
  per-request disposable data stays in memory.
- **One LLM seam.** No file outside the LLM module may import an LLM SDK
  (OpenAI, Groq, etc.) directly. All model access goes through one internal
  interface so the provider can be swapped by configuration.
- **Every external call can fail.** LLM, DB, cache, and code-execution calls are
  wrapped so their failure is contained, retried where safe, and never silently
  loses student data.
- **Graded data is sacred.** Anything touching a student's answers, scores, or
  audit trail is treated as data-integrity-critical: written durably before the
  student is told it succeeded, never lost on restart, always recoverable.
- **GDPR by design, not bolt-on.** Personal data is minimized, consented,
  encrypted at rest, exportable, and deletable from the first line of Phase 1
  schema, not retrofitted later.
- **Tests gate merges.** No phase is "done" without tests that prove its core
  guarantee (e.g. Phase 1 proves state survives a process restart).
- **Match the existing style.** Follow the repo's existing conventions, naming,
  and structure. Do not rewrite working code that isn't part of the current
  phase. Prefer the smallest change that meets the requirement.

---

## Phase 0 — LLM Abstraction Layer (the keystone)
**Goal:** A single internal interface for all model access, so OpenAI today and
self-hosted vLLM later is a config change, not a rewrite.

**Requirements:**
- Create one module (e.g. `backend/app/core/llm.py`) exposing a provider-agnostic
  interface: at minimum `async chat(messages, **opts)` and
  `async stream(messages, **opts)`, returning normalized results regardless of
  backend.
- The provider is selected by environment/config (e.g. `LLM_PROVIDER=openai`),
  with a base URL and model name read from settings. Because vLLM serves an
  OpenAI-compatible API, the OpenAI client path must work unchanged against a
  vLLM endpoint by only changing base URL + model + key.
- Refactor EVERY existing agent (theory, code, rag, lesson, exam, grade,
  orchestrator) to call this interface instead of importing `ChatGroq`/OpenAI
  directly. After this phase, grep the codebase: zero direct LLM-SDK imports
  outside `llm.py`.
- Centralize model parameters (temperature, max tokens) per call-type here.

**Proof of done:** A single config change switches provider with no other code
edits; all agents still function; no LLM SDK imported anywhere but `llm.py`.

---

## Phase 1 — Durable & Shared State (the correctness fix)
**Goal:** Survive restarts, crashes, and running multiple worker processes.
This is the launch-blocking phase.

**Requirements:**
- **Introduce Postgres** as the source of truth for all durable data. Migrate
  the existing SQLite audit schema (exam_sessions, exam_turns, teacher_reviews,
  and research tables) to Postgres using a proper migration tool (Alembic).
  Provide migrations, not hand-run SQL.
- **Add a student/identity model** and a consent record (see Phase 4 — design
  the columns now even if the consent UI comes later): store student identifier,
  and a timestamped consent flag. Minimize personal data — store only what the
  exam genuinely needs.
- **Retire `_exam_state` (the in-memory dict).** Active exam progress moves to
  Redis (fast, shared across workers) with the durable record of every completed
  turn written to Postgres immediately. An exam must be fully reconstructable
  from Postgres alone if Redis is flushed.
- **Replace LangGraph MemorySaver** with a persistent checkpointer backed by
  Postgres (or Redis) so conversation memory survives restarts and is shared
  across workers. If a persistent LangGraph checkpointer is unavailable for the
  installed version, implement a thin persistent checkpointer against our store.
- **Make the app stateless.** After this phase, two backend processes pointed at
  the same Postgres+Redis must behave identically; a request may hit either.
- **Connection management:** proper pooled DB connections; no per-request
  connect/disconnect; clean async usage throughout.

**Proof of done (must be a test):** Start an exam, answer one question, kill the
backend process, restart it, and resume the exam with full history intact —
scored answers preserved, next question correct. Demonstrate two workers sharing
one session.

---

## Phase 2 — Resilience Around the LLM
**Goal:** 100 students cannot take the system (or each other's exams) down, and
no student ever loses an answer to a transient failure.

**Requirements:**
- **Retry with exponential backoff + jitter** on transient LLM errors
  (rate limits/429, timeouts, 5xx), with a sane max-attempts ceiling.
- **Concurrency control / queue** in front of the LLM so simultaneous requests
  are bounded to what the backend can serve, rather than all firing at once.
  A Redis-backed limiter shared across workers (so the limit is real, not
  per-process).
- **Graceful degradation:** if the LLM is unavailable after retries, the
  student's submitted answer is already persisted (from Phase 1) and they see a
  clear "your answer is saved, we're catching up" state — never a crash, never
  lost work. Grading can complete asynchronously and backfill.
- **Timeouts** on every LLM call; no unbounded waits holding connections.
- **Token/cost guardrails:** centralized budget awareness in the LLM layer
  (count/limit), logged per request for later analysis.

**Proof of done (tests):** Simulate 429s and timeouts — submissions are never
lost, retries behave, and the user-facing failure mode is the safe one. Load
test bounded concurrency behaves under a burst of simultaneous submissions.

---

## Phase 3 — Secure Code Execution (the biggest security hole)
**Goal:** Student-submitted Python in Practice mode cannot harm the host,
other students, or the university's shared GPU box.

**Requirements:**
- Replace the bare subprocess with **sandboxed execution**: an isolated
  container per run (or an equivalent strong sandbox) with **no network**,
  strict **CPU, memory, wall-clock time limits**, a read-only/ephemeral
  filesystem, and a non-root user.
- Enforce a hard timeout and resource caps; a runaway or malicious submission is
  killed cleanly and reported as a normal "execution failed/limit exceeded"
  result, not a server incident.
- Only the minimal Qiskit runtime is available inside the sandbox; nothing from
  the main app, no secrets, no env vars, no DB access.
- The execution service is itself stateless and horizontally scalable.

**Proof of done (tests):** Submissions attempting network access, infinite
loops, excessive memory, or filesystem escape are all contained and return safe
errors. A normal Qiskit circuit still runs and returns output + diagram.

---

## Phase 4 — GDPR by Design
**Goal:** A defensible compliance posture for storing Hungarian students'
graded performance data. (University is the data controller; you build under
Prof. Gergő's direction — confirm specifics with him.)

**Requirements:**
- **Consent first:** explicit, recorded, timestamped consent before any exam
  data is collected; clear plain-language notice of what's stored and why.
- **Data minimization:** store the least personal data needed. Pseudonymize
  where feasible (student ID rather than full name where possible).
- **Encryption at rest** for personal data; secrets via environment/secret
  store, never in code or the repo.
- **Right to access & erasure:** endpoints/admin tooling to export all of a
  student's data and to delete it on request, with the audit trail handled
  appropriately (anonymize rather than break integrity where deletion conflicts
  with legitimate record-keeping — document the choice).
- **Retention policy:** defined retention period and a mechanism to expire data
  past it.
- **Access control:** the teacher/admin surfaces are properly authenticated and
  authorized (Phase-appropriate auth, not the current shared password) — student
  data is never exposed without authorization.
- **Processing record:** a short document in the repo listing what personal data
  is stored, where, why, legal basis, and retention — the engineering input to
  the university's compliance record.

**Proof of done:** Consent is enforced before data capture; export and erasure
work; personal data is encrypted at rest; no secrets in the repo; access to
student data requires auth.

---

## Phase 5 — Interactive UI & Experience (only after 0–4)
**Goal:** Make it genuinely excellent to use, now that it's safe to.
**Requirements (to be detailed when we reach it):** real-time interactivity,
responsive exam/tutoring UX, accessibility, clear feedback states (including the
Phase-2 "answer saved, catching up" state), and the dark/light, animated polish
the product already aims for. Do not start until 0–4 are merged and tested.

---

## Cross-cutting: Observability & Operations (build alongside, from Phase 1)
- **Structured logging** with correlation IDs per request and per exam session.
- **Health/readiness endpoints** that check DB, Redis, LLM reachability, and
  sandbox availability.
- **Metrics** for: LLM latency/error rate/token use, exam throughput, queue
  depth, DB pool usage.
- **Backups:** automated Postgres backups with a tested restore procedure —
  for graded data this is mandatory, not optional.
- **Configuration:** all environment-specific values via config/secrets; a
  documented `.env.example`; clear separation of dev (OpenAI) vs prod
  (vLLM on university GPU) settings — the only differences should be config.

## Deployment target (context for your choices)
- Dev: OpenAI via the LLM seam.
- Prod: self-hosted Llama 3.1 8B served by **vLLM** (OpenAI-compatible API) in a
  Docker container on the university's GPU node (80GB-class NVIDIA GPU), run by
  the university admin from an image you provide. Design the prod LLM and the
  code-execution sandbox as clean, self-contained Docker services suitable for
  hand-off, mirroring how MoleScan was deployed there.

## Definition of "launch-ready"
Phases 0–4 complete, each with passing proof-of-done tests; observability and
backups in place; a successful end-to-end rehearsal of a full exam under
simulated concurrency with at least one injected failure (LLM 429 + a process
restart) during which **no student data is lost**.