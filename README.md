<div align="center">

<img src="frontend/public/favicon.svg" width="88" height="88" alt="QuantumMind logo" />

# QuantumMind

**Where quantum theory meets practice.**

A production-grade, multi-agent AI platform for quantum computing education —
built by a student who designed and taught the course it's based on.

[![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph_0.2-FF6B35?style=for-the-badge&logo=chainlink&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Qiskit](https://img.shields.io/badge/Qiskit_2.3-6929C4?style=for-the-badge&logo=ibm&logoColor=white)](https://qiskit.org)
[![License](https://img.shields.io/badge/License-MIT-34C759?style=for-the-badge)](LICENSE)

[**Architecture**](#-architecture) &nbsp;·&nbsp;
[**Reliability**](#-reliability-engineering) &nbsp;·&nbsp;
[**Agents**](#-the-seven-agents) &nbsp;·&nbsp;
[**Research**](#-research-layer) &nbsp;·&nbsp;
[**Setup**](#-local-setup) &nbsp;·&nbsp;
[**Deploy**](DEPLOY.md)

---

*"The people who are crazy enough to think they can change the world are the ones who do."*

</div>

<br/>

## 🧭 The Idea

Most AI tutors are a chatbot with a quantum physics prompt taped to the front.

QuantumMind is a **multi-agent system**. Each learning mode is driven by a dedicated
LangGraph agent that actually runs your Qiskit code in a locked-down container,
grades your understanding on three separate dimensions, and adapts its next
question to your last answer.

It's the platform I wish existed when I designed and taught the University of
Debrecen's first Quantum Computing course for 60+ students. So I built it.

The interesting part isn't the agents — it's what surrounds them. **A tutor that
loses a student's exam answer when an API rate-limits is not a tutor.** Most of
the engineering below is about that: bounded concurrency, retries, durable
answers, and a worker that catches up on whatever the LLM missed.

<br/>

## 🎓 Five Ways to Learn

<div align="center">

| | Mode | Description | Access |
|---|---|---|---|
| ⚛ | **Theory** | AI tutor that infers your level from your question. Ask in plain English or Dirac notation — it adapts. | ![Free](https://img.shields.io/badge/Free-34C759?style=flat-square) |
| ⌨ | **Practice** | Monaco editor (VS Code engine). Write Qiskit, hit Run, see your circuit diagram appear as a live image. | ![Free](https://img.shields.io/badge/Free-34C759?style=flat-square) |
| 🎯 | **Guided** | Step-by-step lessons with mandatory check questions. You cannot advance until you demonstrate understanding. | ![Free](https://img.shields.io/badge/Free-34C759?style=flat-square) |
| 🎓 | **13-Week Course** | The full curriculum I designed for 60+ students at Debrecen, as a week-by-week tree. *Currently answers from general knowledge — see agent 07.* | ![Premium](https://img.shields.io/badge/Premium-FF9500?style=flat-square) |
| 📝 | **Exam Mode** | V1 static · V2 conditional · V3 fully adaptive. Scored on accuracy, reasoning, clarity. Voice input. Full audit trail. | ![Research](https://img.shields.io/badge/Research-7C3AED?style=flat-square) |

</div>

<sub>The Free / Premium / Research tags are roadmap labels, not enforced tiers —
there is no billing, no entitlement check and no user accounts yet. Every mode is
open to anyone who loads the app.</sub>

<br/>

## 🏗 Architecture

### System topology

```mermaid
graph TB
    UI["<b>React 19 · Vite 6</b><br/>Monaco · Zustand · Framer Motion · Web Speech"]
    CDN["<b>▲ Vercel</b> — static SPA<br/>VITE_API_URL points at Railway"]

    subgraph rail[" 🚂 Railway — FastAPI "]
        direction TB
        CORS["<b>CORS gate</b><br/>frontend_url + optional regex"]
        RT["<b>Routes</b><br/>/stream · /execute · /exam · /lesson · /upload · /teacher"]
        ORC["<b>🧠 Orchestrator</b><br/>practice short-circuits · 0 LLM calls"]

        subgraph ag[" 🤖 LangGraph agents "]
            direction LR
            T["⚛ Theory"]
            C["⌨ Code"]
            R["📚 RAG"]
            L["🎯 Lesson"]
            E["📝 Exam"]
            G["✓ Grade"]
        end

        SEAM["<b>🔌 LLM seam</b> · app/core/llm.py<br/><i>the only module importing an LLM SDK</i><br/>timeout · retry · accounting"]
        LIM["<b>🚦 Redis semaphore</b><br/>atomic Lua · self-healing · fail-open"]
        BF["<b>♻️ Backfill worker</b><br/>grades what the LLM missed"]
    end

    subgraph data[" 💾 Data plane "]
        direction LR
        PG[("<b>Postgres</b> · Neon<br/>audit trail · checkpointer<br/><i>source of truth</i>")]
        RD[("<b>Redis</b> · Upstash<br/>exam state · semaphore<br/>token counters")]
        CH[("<b>ChromaDB</b><br/>local vectors<br/>all-MiniLM-L6-v2")]
    end

    DK["<b>🔒 Docker sandbox</b> — one container per run<br/>no network · read-only FS · non-root<br/>cap-drop ALL · mem/CPU/PID caps"]
    GROQ["<b>☁ Groq</b> · llama-3.1-8b-instant · 500+ tok/s"]

    UI --> CDN
    CDN -->|"HTTPS · SSE"| CORS
    CORS --> RT
    RT --> ORC
    ORC --> ag
    ag --> SEAM
    SEAM --> LIM
    LIM --> GROQ
    C -.->|"student code"| DK
    R -.-> CH
    RT --> data
    BF --> data
    BF --> SEAM

    classDef svc   stroke:#2563eb,stroke-width:2px
    classDef agent stroke:#059669,stroke-width:2px
    classDef store stroke:#64748b,stroke-width:2px
    classDef danger stroke:#dc2626,stroke-width:2px
    classDef ext   stroke:#f97316,stroke-width:2px

    class UI,CDN,CORS,RT,ORC,SEAM,LIM,BF svc
    class T,C,R,L,E,G agent
    class PG,RD,CH store
    class DK danger
    class GROQ ext
```

### Request lifecycle — a streamed answer

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant R as POST /api/stream
    participant O as Orchestrator
    participant Z as Redis semaphore
    participant L as LLM seam
    participant P as Postgres

    B->>R: { message, mode, thread_id }
    R-->>B: event: progress · "Thinking…"
    Note over R,B: first byte in under 100ms, before any LLM work

    alt mode == "practice"
        O->>O: short-circuit to Code agent — zero LLM calls
    else every other mode
        O->>L: route() on LLM_ROUTER_MODEL
        L-->>O: {"agent": "..."}
        Note over O: invalid JSON or unknown name → fall back to Theory
    end

    O->>L: stream()
    L->>Z: acquire slot (prune + claim + count, one Lua script)
    alt no slot within 20s
        Z--xL: LLMBusy
    else admitted
        Z-->>L: token
        loop tokens as they arrive
            L-->>B: event: token
        end
        L->>Z: release slot
    end
    L-)P: usage + latency logged off the response path
    R-->>B: event: done
```

### Why it's fast

| Decision | What we did | Latency saved |
|---|---|---|
| **Deterministic routing** | Practice mode skips the router entirely; exam follow-ups use a `score < 5.0` threshold — zero LLM | ~2s per turn |
| **Deterministic sanitization** | Deprecated Qiskit replaced by string substitution, not a model round-trip | ~2s per code fix |
| **LRU cache** | Common theory questions served from memory (200 entries, 1 hr TTL) | ~3s → ~50ms |
| **Progress events** | SSE emits "Thinking…" before the LLM is even called | perceived latency |
| **1-call prompts** | XML-structured prompts replace analyze→generate→grade loops | ~6s per request |
| **Accounting off-path** | Token/cost logging runs as a tracked background task | never blocks a response |

<br/>

## 🛡 Reliability Engineering

The part that separates this from a demo. Every LLM-touching path assumes the
model provider will be slow, rate-limited, or simply down.

### One seam for every model call

`app/core/llm.py` is the **only** module in the codebase permitted to import an
LLM SDK — a rule with [a test enforcing it](backend/tests/test_llm_seam_isolation.py).
Every agent calls `llm.chat()` or `llm.stream()`.

Because Groq, OpenAI and self-hosted vLLM all speak the OpenAI chat-completions
protocol, one `ChatOpenAI` client serves all three; the provider only selects a
base URL and how the key resolves. **The dev path and the prod path are the same
code path** — swapping `LLM_PROVIDER=groq` for `vllm` changes no application logic.

Per-call-type temperatures live in one table (`route` 0.0, `code` 0.1, `theory` 0.7,
all grading 0.0) rather than scattered across agents.

### Bounded concurrency — a distributed semaphore

A per-process limit is a lie the moment you run two workers. The limiter is a
**Redis sorted set** (`llm:inflight`) driven by a single atomic Lua script:

```lua
ZREMRANGEBYSCORE  -- prune tokens from workers that died mid-call
ZADD              -- claim a slot, scored by acquisition time
if ZCARD <= limit then return 1 end
ZREM              -- over the limit: hand the slot back
return 0
```

| Property | How |
|---|---|
| **Honest global limit** | One `ZCARD` across all workers, not per-process |
| **No over-admission** | Prune, claim, count and conditional-release are one atomic script |
| **Counts, never ranks** | `ZRANK` breaks same-timestamp ties lexicographically and over-admits — `ZCARD` can't |
| **Self-healing** | A dead worker's token expires after `llm_limiter_stale_seconds`; no reconciliation job |
| **Fails open** | If Redis is unreachable the call proceeds unslotted — the limit is protective, not a correctness invariant |
| **Bounded wait** | No slot within `llm_acquire_timeout_seconds` → `LLMBusy`, never an unbounded queue |

### Retries that know what's worth retrying

Timeouts, dropped connections, 429s and 5xx are transient and retried with
exponential backoff + jitter. A 400 is a bug — it propagates immediately.

Streaming is the subtle case: **retrying after tokens have already shipped would
double-emit them.** So the stream retries only *before* the first token; once
output is flowing, a failure ends the stream as `LLMUnavailable`.

### Graceful degradation — answers are never lost

If the LLM is down when a student submits an exam answer, the answer is
**persisted first and graded later**. The student gets a 200, not a 500.

```mermaid
sequenceDiagram
    autonumber
    participant S as Student
    participant A as POST /api/exam/answer
    participant L as LLM seam
    participant P as Postgres
    participant W as Backfill worker

    S->>A: submit answer
    A->>L: grade_answer()
    L--xA: LLMUnavailable / LLMBusy

    A->>P: create_pending_turn(graded = false)
    A->>A: clear the stale Redis hot copy
    A-->>S: 200 · "saved_pending_grading"
    Note over S,A: durable before responding — nothing is lost

    loop every 15s, in every worker
        W->>P: get_pending_turns()
        W->>L: grade → decide follow-up → generate next question
        L-->>W: scores + next question
        W->>P: finalize_grade() · conditional UPDATE false→true
        Note right of P: only one worker can claim a turn
        W->>P: advance_in_flight_if(expected_turn)
        Note right of P: a second worker's advance is a no-op
    end

    S->>A: GET /api/exam/session/{id}/status
    A-->>S: graded · next question ready
```

Idempotency is enforced **in the database**, not with a lock: `finalize_grade`
flips `graded` false→true with a conditional `UPDATE`, and `advance_in_flight_if`
only mutates while the session is still parked at the expected turn. Running N
backfill workers is therefore safe by construction.

### Exam state — Redis for speed, Postgres for truth

Active exams live in Redis under `exam:{session_id}` with a safety TTL. **Flush
Redis mid-exam and nothing breaks**: the next access misses, rebuilds the state
from the Postgres session row plus its turns, repopulates Redis, and continues.
Postgres is the only source of truth; Redis is a cache that can always be thrown
away. There is [an integration test that does exactly this](backend/tests/integration/test_exam_restart.py).

### Accounting

Every call logs one structured JSON record — call type, model, provider, input and
output tokens, latency, outcome (`ok` / `busy` / `unavailable`) — and bumps shared
daily counters in Redis. It runs as a tracked background task, wrapped so that
**accounting can never break or slow an LLM call**. The daily token budget is
deliberately *warn-only*: a live exam must not fail because a counter tripped.

<br/>

## 🔒 The Sandbox

Student code is arbitrary code. It runs in a container built from
[`sandbox/Dockerfile`](sandbox/Dockerfile) that contains **only** the Qiskit
runtime — no app code, no DB drivers, no secrets — and is piped in over stdin.

| Flag | Guarantee |
|---|---|
| `--network none` | No egress at all. Cannot phone home, cannot reach your database |
| *(no `-e`, no `--env-file`)* | The container receives **none** of the app's environment — `os.environ` is clean |
| `--read-only` | Root filesystem is immutable |
| `--tmpfs /tmp:noexec,nosuid` | The only writable path — and nothing written there can be executed |
| `--user 1000:1000` | Non-root, enforced at both build and run time |
| `--cap-drop ALL` | Zero Linux capabilities |
| `--security-opt no-new-privileges` | setuid binaries cannot escalate |
| `--memory 256m --memory-swap 256m` | OOM-killed at the cap; equal swap closes the swap escape |
| `--cpus 0.5` | CPU bounded |
| `--pids-limit 64` | Fork and thread bombs contained |
| `--rm` + external `docker kill` | 30s wall clock, enforced from outside the container |

Six [containment tests](backend/tests/sandbox/test_containment.py) assert these
properties against a real container in CI — not against a mock.

**Three backends**, selected by `EXECUTOR`:

| Value | Behaviour |
|---|---|
| `docker` | Default. The only secure option — the table above |
| `subprocess` | Runs on the host. Insecure dev-only fallback: requires `ALLOW_INSECURE_EXECUTOR=true` **and** is refused outright when `APP_ENV=production` |
| `disabled` | Runs nothing; `/api/execute` answers `503` before the executor is ever entered |

> ⚠️ **Hosted deploys currently run `EXECUTOR=disabled`.** Railway containers have
> no Docker daemon, so execution is switched off there and Practice mode reports
> *"Code execution is temporarily unavailable."* Run locally with Docker for the
> real thing.

<br/>

## 🤖 The Seven Agents

<details>
<summary><b>01 · Theory Agent</b> — 1 LLM call + cache</summary>

**What it does:** Infers student level from question phrasing (beginner /
intermediate / advanced) and generates a calibrated explanation with proper Dirac
notation. Streams tokens directly.

**Key design:** An XML-structured system prompt replaces the old
analyze→generate→grade reflection loop. Common questions (*what is superposition?*,
*explain entanglement*) are cached for 1 hr — served in ~50 ms.

```python
# Single-node graph
generate_response → END
```
</details>

<details>
<summary><b>02 · Code Agent</b> — 1–2 LLM calls</summary>

**What it does:** Generates Qiskit code + explanation in one structured call, then
executes it in the locked-down container above. If it fails, retries once with the
error as context.

**Key design:** `temperature=0.1` for maximum reliability. Deprecated syntax
(`Aer.get_backend()`, `execute()`) is fixed **deterministically** by a lookup table
before execution — no second model round-trip. Returns real stdout plus the circuit
diagram as a base64 PNG.

```python
# Conditional retry loop
generate → execute → (fail?) → increment_retry → generate → execute → assemble → END
```
</details>

<details>
<summary><b>03 · RAG Agent</b> — 2 LLM calls · <b>built but not wired in</b></summary>

**What it does:** Retrieves chunks from ChromaDB filtered by week number, generates
an answer grounded in course materials, then grades that answer's quality.

**Key design:** Week-based metadata filtering means a student in Week 3 gets answers
from Week 3 content — not the whole course. Falls back to general knowledge when no
materials are uploaded.

> ⚠️ **Not reachable at runtime.** The graph is complete and compiles, but the
> orchestrator never routes to it — see agent 07. Documents uploaded via
> `/api/upload` are embedded into ChromaDB and then read by nothing.
</details>

<details>
<summary><b>04 · Lesson Agent</b> — 1 LLM call per operation</summary>

**What it does:** Three separate graphs — **plan** (generate a 3–4 step lesson),
**teach** (explain one step), **grade** (evaluate the student's answer). One call each.

**Key design:** Deprecated Qiskit patterns in generated code are sanitized
deterministically before the student ever sees them.
</details>

<details>
<summary><b>05 · Exam Agent</b> — 1 LLM call + deterministic routing</summary>

**What it does:** Generates questions for V1 (static bank), V2 (fixed + conditional
follow-up), or V3 (fully adaptive, conditioned on previous answers).

**Key design:** The follow-up decision is **100% deterministic** —
`avg_score < 5.0` → follow-up. Zero LLM calls for that branch, ~2s saved per turn,
and the routing logic is unit-testable without a model.
</details>

<details>
<summary><b>06 · Grade Agent</b> — 1 LLM call</summary>

**What it does:** Scores answers on three dimensions — **Accuracy** (0–10),
**Reasoning** (0–10), **Clarity** (0–10) — and returns a justification plus an ideal
answer for benchmarking.

**Key design:** All three scores, the justification and the ideal answer come back
in one structured JSON response. The old analyze→grade loop (2 calls) is merged into one.
</details>

<details>
<summary><b>07 · Orchestrator</b> — 1 LLM call, or 0 in Practice mode</summary>

**What it does:** Picks the agent for each request. `practice` short-circuits
deterministically to the Code agent with no LLM call. Every other mode goes through
`route()`, which asks the cheap router model (`LLM_ROUTER_MODEL`) to classify the
message and falls back to Theory if the reply isn't valid JSON or names an unknown agent.

**Key design:** Defensive by default — an LLM that returns garbage degrades to a
sensible agent rather than raising.

> ⚠️ **`course` does not reach the RAG agent.** The orchestrator's `rag` branch is
> still a stub that falls back to Theory, so Course mode answers from general
> knowledge and uploaded material is never retrieved — even though the RAG graph is
> fully built. Likewise `review` falls back to the Code agent.
</details>

<br/>

## 🔬 Research Layer

Aligned with **ETH Zurich's Agentic AI in Education** project direction.

### Research questions

| | Question |
|---|---|
| **RQ1** | To what extent do AI rubric scores agree with human teacher scores across accuracy, reasoning, and clarity? |
| **RQ2** | Do V3 (adaptive) exam students score higher than V1 (static) students on the same topic? |
| **RQ3** | Can the reasoning dimension reliably identify vague answers that accuracy alone misses? |
| **RQ4** | Do students who receive follow-up questions improve on subsequent turns? |

### Audit trail

Every exam event is written to **Postgres** through async SQLAlchemy and versioned
with Alembic. Teacher reviews are **append-only** — a review is always a new row,
never an update — so the AI's original score and the teacher's override both
survive. That's what makes the research reproducible.

```sql
exam_sessions    -- session_id, student_name, topic, version (V1/V2/V3), avg_score
exam_turns       -- question, answer, score_accuracy, score_reasoning, score_clarity,
                 --   ai_justification, ideal_answer, is_followup, graded
teacher_reviews  -- ai_scores, teacher_override_scores, delta, feedback, action
research_metrics -- aggregate metrics for the experiments below
```

Experiment 3's ground-truth labels have no table yet — label those 50 turns outside
the database for now.

### Three experiments

<details>
<summary><b>Experiment 1</b> — AI vs Human Grading Agreement</summary>

**Goal:** Measure how reliable AI rubric scoring is against human experts.

**Participants:** 15 exam sessions · 2 independent reviewers

**Method:** run 15 sessions → both reviewers independently score every turn in the
teacher dashboard → compare reviewer scores against AI scores.

**Metrics:** Pearson *r* per dimension (target > 0.7), MAE, agreement rate (|delta| ≤ 1.0)

**Publishable claim:** *"AI rubric scoring achieves r=X agreement with human experts on quantum computing oral examinations"*
</details>

<details>
<summary><b>Experiment 2</b> — Adaptive vs Static Questioning</summary>

**Goal:** Show V3 produces better learning outcomes than V1.

**Participants:** 30 students (10 per version)

**Method:** randomly assign to V1/V2/V3 → all take an exam on the same topic → one
week later all take a V1 post-test on that topic → compare pre/post deltas by group.

**Metrics:** Cohen's *d* for V3 vs V1, % improvement pre→post

**Publishable claim:** *"Adaptive multi-turn questioning improves post-test scores by X% vs static questioning"*
</details>

<details>
<summary><b>Experiment 3</b> — Vague Answer Detection</summary>

**Goal:** Validate that the reasoning dimension catches weak answers accuracy alone misses.

**Participants:** 50 existing exam turns — no new students needed

**Method:** manually label 50 turns as strong / vague / incorrect → compare against
AI reasoning scores → measure precision and recall as a vague-answer detector.

**Metrics:** Precision, recall, F1 vs an accuracy-only baseline

**Publishable claim:** *"Reasoning-dimension scoring detects vague answers with precision=X vs accuracy-only baseline"*
</details>

**Target venues:** EDM 2026 · LAK 2026 · AIED 2026

<br/>

## ⚡ Tech Stack

<div align="center">

| Layer | Technology | Why |
|-------|-----------|-----|
| **AI framework** | LangGraph 0.2.55 | Stateful graphs with conditional edges and persistent memory |
| **LLM** | Groq · llama-3.1-8b-instant | 500+ tokens/sec · free tier · sufficient quality |
| **Provider seam** | One `ChatOpenAI` client → groq \| openai \| vllm | Dev and prod share one code path; only base URL + key differ |
| **Resilience** | tenacity + a Redis Lua semaphore | Bounded global concurrency, backoff with jitter, fail-open |
| **RAG** | ChromaDB 0.5.18 + all-MiniLM-L6-v2 | Local · free · no API key. Torch pinned CPU-only to keep the image small |
| **Code execution** | Qiskit 2.3 + Aer 0.17 in a locked-down container | Per-run container, no network, read-only FS, non-root, resource caps |
| **Circuit diagrams** | matplotlib `qc.draw('mpl')` | base64 PNG returned straight to the frontend |
| **Backend** | FastAPI 0.115 + sse-starlette | Async · real-time token streaming |
| **Frontend** | React 19 + Vite 6 + Tailwind 4 + Framer Motion 12 | Fast · animated · production-quality |
| **State / routing** | Zustand 5 · React Router 7 | Minimal global store, no boilerplate |
| **Editor** | Monaco (the VS Code engine) | Syntax highlighting · themes · resizable |
| **Conversation memory** | LangGraph `AsyncPostgresSaver` | Survives restarts, shared across workers |
| **Cache** | In-memory LRU — 200 items, 1 hr TTL | Repeat questions answered instantly · per-process |
| **Audit DB** | Postgres · async SQLAlchemy 2 + psycopg 3 + Alembic | Exam trails · teacher overrides · research data |
| **Active exam state** | Redis, with Postgres as source of truth | Shared across workers; fully rebuildable from Postgres |
| **Voice** | Web Speech API | Browser-native · zero backend changes |
| **Hosting** | Railway (API) + Vercel (SPA) + Neon + Upstash | See [DEPLOY.md](DEPLOY.md) |

</div>

<br/>

## 🧪 Tests & CI

**48 tests** across three tiers, run by
[GitHub Actions](.github/workflows/ci.yml) on every push and pull request.

| Suite | Tests | What it proves |
|---|---|---|
| [`test_executor.py`](backend/tests/test_executor.py) | 10 | Backend selection, timeout enforcement, circuit parsing, the `disabled` short-circuit |
| [`test_llm_provider_switch.py`](backend/tests/test_llm_provider_switch.py) | 9 | groq / openai / vllm resolve the right base URL and key; bad config fails at startup |
| [`test_llm_resilience.py`](backend/tests/test_llm_resilience.py) | 6 | Transient vs permanent classification, backoff, **no double-emit on stream retry** |
| [`test_containment.py`](backend/tests/sandbox/test_containment.py) | 6 | Real containers: no network, no secrets, read-only FS, PID and memory caps hold |
| [`test_agents_smoke.py`](backend/tests/test_agents_smoke.py) | 4 | Every agent graph compiles and runs against a mocked model |
| [`test_llm_accounting.py`](backend/tests/test_llm_accounting.py) | 3 | Usage is recorded and a failing counter never breaks a call |
| [`test_grading_degradation.py`](backend/tests/integration/test_grading_degradation.py) | 3 | LLM down → answer persisted → backfill grades and advances it |
| [`test_llm_concurrency.py`](backend/tests/integration/test_llm_concurrency.py) | 2 | The semaphore never over-admits, and fails open when Redis dies |
| [`test_phase1_units.py`](backend/tests/integration/test_phase1_units.py) | 2 | Postgres + Redis wiring |
| [`test_exam_restart.py`](backend/tests/integration/test_exam_restart.py) | 1 | **Flush Redis mid-exam — the session rebuilds from Postgres and continues** |
| [`test_two_workers.py`](backend/tests/integration/test_two_workers.py) | 1 | Two workers share state without double-grading |
| [`test_llm_seam_isolation.py`](backend/tests/test_llm_seam_isolation.py) | 1 | No module outside `core/llm.py` imports an LLM SDK |

CI builds the real sandbox image so **containment tests always run against a live
container**. Integration tests run when `DATABASE_URL` and `REDIS_URL` secrets are
configured and skip cleanly when they aren't — the suite is green on a fork with no
credentials.

```bash
cd backend
uv run python -m pytest tests/ -q            # everything available
uv run python -m pytest tests/sandbox -q     # containment only (needs Docker)
```

<br/>

## 🔌 API Reference

All routes are mounted under `/api`.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/stream` | **Primary chat endpoint** — SSE with `progress` / `token` / `done` / `error` events |
| `POST` | `/chat` | Non-streaming equivalent |
| `GET` | `/history/{thread_id}` | Replay a conversation from the checkpointer |
| `GET` | `/cache/stats` | LRU hit rate and occupancy |
| `POST` | `/execute` | Run Qiskit code → stdout + base64 circuit PNG (`503` when `EXECUTOR=disabled`) |
| `POST` | `/lesson/plan` · `/lesson/teach` · `/lesson/grade` | Guided-mode lifecycle |
| `POST` | `/exam/start` · `/exam/answer` · `/exam/end` | Exam lifecycle — `answer` returns `saved_pending_grading` when degraded |
| `GET` | `/exam/session/{id}` · `/exam/session/{id}/status` | Full session, or a lightweight poll for pending grades |
| `GET` | `/teacher/sessions` · `/teacher/session/{id}` | Teacher dashboard listings |
| `POST` | `/teacher/review` | Append-only score override |
| `GET` | `/research/stats` | Aggregate research metrics |
| `POST` | `/upload` | PDF / notebook → chunked → embedded into ChromaDB |
| `GET` | `/upload/status` | What's currently indexed |
| `GET` | `/health` | Liveness + environment + active model *(unprefixed)* |

Interactive docs at `/docs` — **development only**; `APP_ENV=production` disables them.

<br/>

## 🚀 Local Setup

### Prerequisites

```
Python 3.12+    →  python.org
Node.js 18+     →  nodejs.org
uv              →  curl -LsSf https://astral.sh/uv/install.sh | sh
Groq API key    →  console.groq.com (free)
Postgres 14+    →  REQUIRED — the app exits at startup if it cannot connect
Redis 6+        →  REQUIRED — same
Docker          →  optional, only to actually run student code
```

Postgres and Redis are **not optional**: startup pings both and the process exits
if either is unreachable. Fastest path is the bundled stack —

```bash
docker compose -f docker-compose.dev.yml up -d    # Postgres + Redis
```

— or point `DATABASE_URL` / `REDIS_URL` at managed instances (Neon, Upstash).

### Backend

```bash
cd backend

uv sync                                   # install everything
cp .env.example .env                      # then add GROQ_API_KEY

uv run alembic upgrade head               # create the schema
uv run uvicorn app.main:app --reload --port 8000
# API docs → http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App → http://localhost:5173
```

### Sandbox image (for Practice mode)

```bash
docker build -t quantummind-sandbox sandbox/
```

Without Docker, set `EXECUTOR=disabled` — Practice mode then reports that execution
is unavailable and everything else works normally.

### Environment variables

```env
LLM_PROVIDER=groq                 # groq | openai | vllm
LLM_MODEL=llama-3.1-8b-instant    # or llama-3.3-70b-versatile
LLM_ROUTER_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=gsk_...              # from console.groq.com (used when LLM_PROVIDER=groq)
# LLM_API_KEY=                    # key for openai/vllm endpoints
# LLM_BASE_URL=                   # OpenAI-compatible base URL; required for vllm

# Datastores — both REQUIRED, startup fails without them
DATABASE_URL=postgresql+psycopg://quantummind:quantummind@localhost:5432/quantummind
REDIS_URL=redis://localhost:6379/0

APP_ENV=development
FRONTEND_URL=http://localhost:5173
TEACHER_PASSWORD=change_me        # for the /teacher dashboard
EXECUTOR=docker                   # docker | subprocess | disabled

# Optional — resilience tuning (sane defaults in config.py)
# LLM_MAX_CONCURRENCY=8           # global in-flight LLM calls, shared via Redis
# LLM_TIMEOUT_SECONDS=30
# LLM_MAX_ATTEMPTS=4
# GRADING_BACKFILL_INTERVAL_SECONDS=15
# CHROMA_PATH=./data/chroma       # relative paths resolve against backend/
# CORS_ALLOW_ORIGIN_REGEX=        # extra CORS rule, e.g. for Vercel previews
```

> **`postgresql+psycopg://` is required, not cosmetic.** The app builds an *async*
> SQLAlchemy engine; a bare `postgresql://` URL selects the synchronous psycopg2
> dialect and fails at startup.

> **`.env` keys are validated strictly** (`extra = "forbid"`). A misspelled key
> crashes at startup rather than silently falling back to a default. Note this
> applies to the *file* — unknown OS environment variables (Railway's `PORT`,
> `RAILWAY_*`) are ignored.

`backend/.env.example` is the authoritative, fully-commented list.

### Upload course content

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@lecture_week1.pdf" -F "week=1"

curl -X POST http://localhost:8000/api/upload \
  -F "file=@lab_week3.ipynb" -F "week=3"

curl http://localhost:8000/api/upload/status
```

<sub>Uploads embed successfully today, but nothing reads them back until the
orchestrator routes to the RAG agent — see agent 07.</sub>

<br/>

## ☁ Deployment

**[DEPLOY.md](DEPLOY.md) is the full runbook.** The target topology:

| Piece | Host | Notes |
|---|---|---|
| API | **Railway** | Dockerfile build, Alembic runs pre-deploy |
| SPA | **Vercel** | `VITE_API_URL` points at the Railway domain |
| Postgres | **Neon** | Serverless, `sslmode=require` |
| Redis | **Upstash** | `rediss://` — TLS selected by the scheme |
| Execution | *off* | `EXECUTOR=disabled` — no Docker daemon on Railway |

Two things to get right, because they fail quietly:

- **`FRONTEND_URL` must be your real Vercel origin**, not the localhost default.
  If a `CORS_ALLOW_ORIGIN_REGEX` is also set, the site will appear to work while
  localhost stays a trusted credentialed origin in production.
- **`TEACHER_PASSWORD` has a default** (`quantum2026`) that is published in this
  repo. Not overriding it ships that password.

No public demo URL yet.

<br/>

## 📁 Project Structure

```
quantummind/
├── .github/workflows/ci.yml         # build sandbox → full suite on every push
├── docker-compose.dev.yml           # local Postgres + Redis
├── sandbox/Dockerfile               # Qiskit-only image · no app code, no secrets
├── DEPLOY.md · NORTHSTAR.md · docs/
│
├── backend/
│   ├── Dockerfile                   # non-root, uv-based, CPU-only torch
│   ├── railway.toml
│   ├── alembic/versions/            # 0001 initial schema · 0002 exam_turns.graded
│   ├── app/
│   │   ├── main.py                  # lifespan: checkpointer → PG → Redis → backfill
│   │   ├── agents/
│   │   │   ├── orchestrator.py      # routing · practice short-circuits, LLM elsewhere
│   │   │   ├── theory_agent.py      # 1 call · XML prompt · LRU cache
│   │   │   ├── code_agent.py        # generate → execute → fix loop
│   │   │   ├── rag_agent.py         # ChromaDB retrieval + grading (built, unwired)
│   │   │   ├── lesson_agent.py      # plan + teach + grade (1 call each)
│   │   │   └── exam_agent.py        # V1/V2/V3 adaptive questioning
│   │   ├── core/
│   │   │   ├── llm.py               # ⭐ the ONLY module importing an LLM SDK
│   │   │   ├── llm_limiter.py       # ⭐ Redis Lua semaphore · self-healing · fail-open
│   │   │   ├── llm_errors.py        # LLMUnavailable · LLMBusy
│   │   │   ├── grading_backfill.py  # ⭐ reconciles turns the LLM couldn't grade
│   │   │   ├── executor.py          # sandbox seam: docker | subprocess | disabled
│   │   │   ├── exam_state.py        # Redis hot copy + Postgres-only rebuild
│   │   │   ├── memory.py            # AsyncPostgresSaver checkpointer + pool
│   │   │   ├── cache.py             # LRU, 200 items, 1 hr TTL
│   │   │   ├── config.py            # pydantic settings · fail-fast validators
│   │   │   └── prompts.py
│   │   ├── db/
│   │   │   ├── models.py            # SQLAlchemy models
│   │   │   ├── database.py          # async engine + pool
│   │   │   ├── audit_db.py          # audit trail · idempotent conditional UPDATEs
│   │   │   └── redis_client.py      # shared async Redis pool
│   │   └── routes/
│   │       ├── stream.py            # SSE streaming + progress events
│   │       ├── chat.py              # non-streaming chat + history
│   │       ├── execute.py           # Qiskit execution + circuit PNG
│   │       ├── upload.py            # PDF/notebook → ChromaDB
│   │       ├── lesson.py            # guided lesson API
│   │       └── exam.py              # exam + teacher + research API
│   └── tests/                       # 48 tests: unit · sandbox · integration
│       ├── sandbox/                 # real-container containment proofs
│       └── integration/             # degradation · restart · two-worker
│
└── frontend/
    └── src/
        ├── components/
        │   ├── LandingPage.jsx      # dark/light toggle
        │   ├── SplashScreen.jsx
        │   ├── MainApp.jsx · Sidebar.jsx · ModeSelector.jsx
        │   ├── ChatPanel.jsx        # streaming · progress indicators
        │   ├── CodeEditor.jsx       # Monaco + Run
        │   ├── CircuitVisualizer.jsx# base64 circuit PNG
        │   ├── PracticeAssistant.jsx
        │   ├── GuidedPanel.jsx      # step-by-step lesson UI
        │   ├── CoursePanel.jsx · CourseSidebar.jsx
        │   ├── ConceptCards.jsx
        │   ├── ExamMode.jsx         # V1/V2/V3 + voice input
        │   ├── TeacherDashboard.jsx # review + override + research
        │   └── ui/                  # Badge · Button
        ├── data/curriculum.js       # 13-week course structure
        ├── hooks/useAppState.js     # Zustand global state
        └── lib/api.js               # API_BASE from VITE_API_URL
```

<br/>

## 👤 About

<div align="center">

**Asfand Yar** — BSc Computer Science, University of Debrecen, Hungary *(graduating August 2027)*

</div>

| Achievement | Detail |
|---|---|
| 🎓 **Course designer** | Designed and taught Debrecen's first Intro to Quantum Computing course — 60+ students |
| ⚛ **Qiskit Fall Fest 2025** | Led the event, 120+ participants |
| 👥 **GDG Debrecen** | Co-Lead, Google Developer Groups Debrecen |
| 🏛 **Student Union** | VP, International Students' Union |
| 🔬 **BSc thesis** | JEPA-RobustViT — Joint Embedding Predictive Architectures + Vision Transformers + Test-Time Adaptation |
| 🌐 **GSoC 2026** | Proposal submitted: Kubeflow docs-agent |

**Research interests:** Agentic AI systems · AI in education · Quantum computing

<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-asfandyar--prog-181717?style=for-the-badge&logo=github)](https://github.com/asfandyar-prog)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-asfand--yar-0077B5?style=for-the-badge&logo=linkedin)](https://linkedin.com/in/asfand-yar-3966b8291)
[![Email](https://img.shields.io/badge/Email-yarasfand886@gmail.com-EA4335?style=for-the-badge&logo=gmail)](mailto:yarasfand886@gmail.com)

</div>

<br/>

## 🔗 Related Repositories

| Repository | Description |
|-----------|-------------|
| [quantum-insight-rag](https://github.com/asfandyar-prog/quantum-insight-rag) | Original RAG system for quantum computing docs |
| [framework-free-agent](https://github.com/asfandyar-prog/framework-free-agent) | ReAct agent built from scratch without frameworks |
| [agentic-systems-with-langgraph](https://github.com/asfandyar-prog/agentic-systems-with-langgraph) | LangGraph workflow experiments |
| [fastapi-ai-backend](https://github.com/asfandyar-prog/fastapi-ai-backend) | FastAPI backend architecture patterns |

<br/>

---

<div align="center">

**QuantumMind** · University of Debrecen · 2026

*Built with intention. Every component earned its place.*

</div>
