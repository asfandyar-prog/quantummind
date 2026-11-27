<div align="center">

<img src="frontend/public/favicon.svg" width="88" height="88" alt="QuantumMind logo" />

# QuantumMind

**Where quantum theory meets practice.**

A quantum computing tutor built as an LLM router in front of specialised
LangGraph workflows, with a reliability layer around the model: durable exam
answers, bounded LLM concurrency and a locked-down code sandbox. It's a prototype
that hasn't been used by a real class yet, built by a student who designed and
taught the course it's based on.

[![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph_0.2-FF6B35?style=for-the-badge&logo=chainlink&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Qiskit](https://img.shields.io/badge/Qiskit_2.3-6929C4?style=for-the-badge&logo=ibm&logoColor=white)](https://qiskit.org)
[![License](https://img.shields.io/badge/License-MIT-34C759?style=for-the-badge)](LICENSE)

[**Architecture**](#-architecture) &nbsp;·&nbsp;
[**Reliability**](#-reliability-engineering) &nbsp;·&nbsp;
[**Workflows**](#-router-and-workflows) &nbsp;·&nbsp;
[**Research**](#-research-layer) &nbsp;·&nbsp;
[**Setup**](#-local-setup) &nbsp;·&nbsp;
[**Deploy**](DEPLOY.md)

---

*"The people who are crazy enough to think they can change the world are the ones who do."*

</div>

<br/>

## 🧭 The Idea

Most AI tutors are a chatbot with a quantum physics prompt taped to the front.

QuantumMind is an **LLM router in front of specialised LangGraph workflows**. One
classification call picks a workflow; each workflow is a small, fixed graph. The
code workflow is the only one that loops: it generates Qiskit code, runs it in a
locked-down container and, if the run fails, feeds the traceback back to the model
once (a bounded execute-and-repair loop). The exam workflow grades an answer on
three dimensions and writes the next question from your earlier answers.

The control flow is deterministic code. The models classify, generate and grade;
nothing calls tools, and no model decides what happens next or when to stop. By the
usual definition, where an agent is an LLM choosing its own actions in a loop,
these are **workflows, not agents**.

It's the platform I wish existed when I designed and taught the University of
Debrecen's first Quantum Computing course, for 36 students. So I built it.

The interesting part isn't the agents — it's what surrounds them. **A tutor that
loses a student's exam answer when an API rate-limits is not a tutor.** Most of
the engineering below is about that: bounded concurrency, retries, durable
answers, and a worker that catches up on whatever the LLM missed.

<br/>

## 🎓 Five Ways to Learn

<div align="center">

| | Mode | Description | Access |
|---|---|---|---|
| ⚛ | **Theory** | AI tutor prompted to pitch its answer to the level your question suggests, and to follow the conversation. Ask in plain English or Dirac notation. | ![Free](https://img.shields.io/badge/Free-34C759?style=flat-square) |
| ⌨ | **Practice** | Monaco editor (VS Code engine). Write Qiskit, hit Run, see your circuit diagram appear as a live image. *Running code needs Docker, so it works locally only; the hosted deploy has execution switched off.* | ![Free](https://img.shields.io/badge/Free-34C759?style=flat-square) |
| 🎯 | **Guided** | Step-by-step lessons with a check question per step. The next step unlocks when the AI marks your answer as a pass. | ![Free](https://img.shields.io/badge/Free-34C759?style=flat-square) |
| 🎓 | **13-Week Course** | The curriculum I designed and taught to 36 students at Debrecen, as a week-by-week tree. *Questions the router labels as course-material lookups search that week's uploaded notes (see 03). With nothing uploaded, as on a fresh Railway deploy, it answers from general knowledge and says so.* | ![Premium](https://img.shields.io/badge/Premium-FF9500?style=flat-square) |
| 📝 | **Exam Mode** | V1 fixed questions · V2 and V3 AI-generated from your earlier answers, with one or up to two follow-ups on a weak answer. Scored on accuracy, reasoning, clarity. Voice input. Full audit trail. | ![Research](https://img.shields.io/badge/Research-7C3AED?style=flat-square) |

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
        ORC["<b>🧠 Router</b> (orchestrator.py)<br/>1 classification call · 0 in practice mode"]

        subgraph ag[" 🔀 LangGraph workflows "]
            direction LR
            T["⚛ Theory"]
            C["⌨ Code<br/><i>execute-and-repair, max 1 retry</i>"]
            R["📚 RAG<br/><i>retrieve by week</i>"]
            L["🎯 Lesson"]
            E["📝 Exam + grader"]
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
    GROQ["<b>☁ Groq</b> · llama-3.1-8b-instant"]

    UI --> CDN
    CDN -->|"HTTPS · SSE"| CORS
    CORS --> RT
    RT --> ORC
    ORC --> T
    ORC --> C
    ORC --> R
    RT --> L
    RT --> E
    ag --> SEAM
    SEAM --> LIM
    LIM --> GROQ
    C -.->|"generated code<br/>(local + CI only)"| DK
    RT -.->|"/execute (local + CI only)"| DK
    R -->|"retrieves (week filter)"| CH
    RT -->|"/upload writes"| CH
    RT --> data
    BF --> data
    BF --> SEAM

    classDef svc   stroke:#2563eb,stroke-width:2px
    classDef agent stroke:#059669,stroke-width:2px
    classDef store stroke:#64748b,stroke-width:2px
    classDef danger stroke:#dc2626,stroke-width:2px
    classDef ext   stroke:#f97316,stroke-width:2px

    class UI,CDN,CORS,RT,ORC,SEAM,LIM,BF svc
    class T,C,R,L,E agent
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
    participant O as Router
    participant Z as Redis
    participant L as LLM seam

    B->>R: { message, mode, thread_id, recent history }
    R-->>B: event: progress · "Thinking…"
    Note over R,B: first byte in under 100ms, before any LLM work

    alt mode == "practice"
        O->>O: short-circuit to Code agent — zero routing calls
        Note over O: the Code agent runs to completion, then its answer is sent word by word
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
    L-)Z: call, latency and outcome counted, off the response path
    R-->>B: event: done
```

### Why it's fast

Nothing here has been benchmarked; each row says which LLM call it avoids, not how
much time that saves.

| Decision | What we did | Effect |
|---|---|---|
| **Deterministic routing** | Practice mode skips the router; exam follow-ups use a `score < 5.0` threshold | one fewer LLM call per request / per answer |
| **Deterministic sanitization** | Deprecated Qiskit replaced by string substitution, not a model round-trip | no repair call for known deprecations |
| **Lesson-plan cache** | A repeated topic reuses its generated plan (200 entries, 1 hr TTL, per process) | one LLM call saved per repeat |
| **Progress events** | SSE emits "Thinking…" before the LLM is even called | perceived latency only |
| **1-call prompts** | One structured prompt per step instead of analyze→generate→grade loops | 1 call instead of several |
| **Accounting off-path** | Usage accounting runs as a tracked background task | never blocks a response |

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

This is a **concurrency limit, not a rate limit**: it caps how many LLM calls are in
flight at once, across all workers. It doesn't limit how many requests one client
can send, and there is no per-user rate limiting anywhere yet.

### Retries that know what's worth retrying

Timeouts, dropped connections, 408/409/429 and 5xx are transient and retried with
exponential backoff + jitter. A 400 is a bug — it propagates immediately. tenacity
is the only retry layer: the openai client's own retries are switched off, or each
attempt would quietly retry twice more inside it (up to 12 requests for one call).

Streaming is the subtle case: **retrying after tokens have already shipped would
double-emit them.** So the stream retries only *before* the first token; once
output is flowing, a failure ends the stream as `LLMUnavailable`
([tested](backend/tests/test_llm_stream.py)).

### Graceful degradation — an LLM outage doesn't lose an answer

If the LLM is down or saturated when a student submits an exam answer, the answer
is **persisted first and graded later**. The student gets a 200, not a 500, and the
exam screen shows the answer as saved, then polls `/status` until it's graded and
the next question is ready. This covers transient failures (timeouts, 429s, 5xx, no
concurrency slot); a permanent error such as a bad API key still fails the request.

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

Idempotency is enforced **in the database**, not with an application lock:
`finalize_grade` flips `graded` false→true with a conditional `UPDATE`, and
`advance_in_flight_if` only mutates while the session is still parked at the
expected turn. The writes are idempotent; the work isn't. Two workers can both
call the LLM for the same pending answer before one of them wins the `UPDATE`.

The live answer path is guarded the same way. `advance_exam` updates the session
only while it's still at the answered turn, and that `UPDATE` takes the row lock
first, so a second concurrent submit matches nothing and gets a `409` with the real
current question. A unique `(session_id, turn_number)` constraint is the backstop
for every path that writes a turn
([tested](backend/tests/integration/test_exam_idempotency.py)).

### Exam state — Redis for speed, Postgres for truth

Active exams live in Redis under `exam:{session_id}` with a safety TTL. **Flush
Redis mid-exam and nothing breaks**: the next access misses, rebuilds the state
from the Postgres session row plus its turns, repopulates Redis, and continues.
Postgres is the only source of truth; Redis is a cache that can always be thrown
away. There is [an integration test that does exactly this](backend/tests/integration/test_exam_restart.py).
A *stale* copy, left by a Redis write that failed after the Postgres commit, can't
record an answer twice either: the guarded advance rejects it and the copy is
dropped.

### Accounting

Every call, streamed or not, emits one structured JSON record: call type, model,
provider, input and output tokens, latency, and outcome (`ok` / `busy` /
`unavailable` / `cancelled` / `error`). It also bumps shared daily counters in
Redis. It runs as a tracked background task, wrapped so that **accounting can
never break or slow an LLM call**.

All app logging is JSON lines on stdout (`core/logging_setup.py`), one object per
line with `ts`, `level`, `logger` and the `request_id` that `RequestIdMiddleware`
takes from `X-Request-ID` or mints, and echoes back. `LOG_LEVEL` sets the level.
The `llm_call` record is merged into that line, so it can be filtered on
`event`. Until this was added, nothing configured logging and Python's default
silently dropped every INFO record, these included.

Streamed calls carry token counts only if the
provider reports usage in the stream, and the Groq client isn't asked to, so
streamed answers are counted by calls and latency. The daily token budget is
deliberately *warn-only*: a live exam must not fail because a counter tripped.

### Grading never invents a score

The grader's JSON is parsed tolerantly (code fences, prose around it) and each
score is clamped to 0–10. A reply with a missing or non-numeric score gets one
retry that shows the model its own output. If that fails too, the answer is stored
with **no scores** and a needs-review note, the exam moves on without a follow-up,
and the answer is left out of averages. It used to become 5.0 on every dimension,
indistinguishable from a real grade.

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

Seven [containment tests](backend/tests/sandbox/test_containment.py) run real
containers: a normal circuit runs and draws, and the network, secrets, filesystem,
runaway loop, memory bomb and fork bomb are all contained. They need Docker; CI
sets `REQUIRE_SANDBOX=1` so a missing image fails the build instead of skipping them.

This is container isolation, not a VM: the kernel is shared (Docker's default
seccomp profile, no gVisor), and the API process needs the Docker socket to launch
containers, which is root-equivalent on that host.

**Three backends**, selected by `EXECUTOR`:

| Value | Behaviour |
|---|---|
| `docker` | Default. The only secure option — the table above |
| `subprocess` | Runs on the host. Insecure dev-only fallback: requires `ALLOW_INSECURE_EXECUTOR=true` **and** is refused outright when `APP_ENV=production` |
| `disabled` | Runs nothing: `/api/execute` answers `503`, and the code agent answers without retrying, saying the code wasn't run |

> ⚠️ **Hosted deploys currently run `EXECUTOR=disabled`.** Railway containers have
> no Docker daemon, so execution is switched off there and Practice mode reports
> *"Code execution is temporarily unavailable."* Run locally with Docker for the
> real thing.

<br/>

## 🔀 Router and Workflows

An LLM router plus specialised LangGraph workflows: five workflow modules built as
eight small graphs. Six of the eight are a single node. Only the Code and RAG graphs
have a conditional edge, and both loop at most once. The router is one
classification call followed by plain `if`/`elif`. Nothing here calls tools, and no
model decides when to stop. The engineering is in the deterministic code around
these steps, described above.

| Component | Where the control flow is decided | Honest label |
|---|---|---|
| Router | code, using one validated LLM label | LLM classifier |
| Theory | code | single prompt |
| Code | code: retry iff the run failed and no retry yet | bounded execute-and-repair loop (max 1 repair) |
| Lesson | code | three single-prompt calls (plan, teach, grade) |
| Exam questions | code; V1 uses no LLM | single prompt + deterministic follow-up rule |
| Graders (exam, lesson) | code: re-ask iff the reply fails Pydantic validation | single prompt + one validation retry, then fail closed |
| RAG | code: retry iff an LLM judge says "fail" | retrieve → generate → judge pipeline (max 1 retry) |

<details>
<summary><b>01 · Theory</b> — 1 LLM call</summary>

**What it does:** Answers a conceptual question with an explanation pitched to the
level the question suggests (the prompt asks the model to judge beginner /
intermediate / advanced from the phrasing), with proper Dirac notation. Streams
tokens directly.

**Key design:** One structured system prompt replaces the old
analyze→generate→grade reflection loop. Streaming bypasses the graph, so the
conversation comes from the client: the last 12 turns are replayed into each
answer. The non-streaming `/chat` path runs the graph with the Postgres
checkpointer instead, replaying the same last 12 messages; the frontend never calls
`/chat`.

```python
# Single-node graph
generate_response → END
```
</details>

<details>
<summary><b>02 · Code</b> — 1–2 LLM calls · the only loop that's live</summary>

**What it does:** Generates Qiskit code + explanation in one structured call, then
executes it in the locked-down container above. If the code fails, it retries once
with the traceback as context. If the sandbox itself is off, as on the hosted
deploy, it doesn't retry: the answer says the code wasn't run.

**Key design:** `temperature=0.1` for maximum reliability. Deprecated syntax
(`Aer.get_backend()`, `execute()`) is fixed **deterministically** by a lookup table
before execution — no second model round-trip. Conversation memory is the Postgres
checkpointer, which survives a restart
([tested](backend/tests/integration/test_checkpointer_postgres.py)); only the last
12 messages are replayed into a prompt. **Its streaming is simulated:** the graph
runs to completion, then the finished answer is split on spaces and sent word by
word.

```python
# Conditional retry loop
generate → execute → (fail?) → increment_retry → generate → execute → assemble → END
```
</details>

<details>
<summary><b>03 · RAG</b> — 2–3 LLM calls · reached through the router's <code>rag</code> label</summary>

**What it does:** Retrieves chunks from ChromaDB filtered by week number, generates
an answer grounded in course materials, then grades that answer's quality.

**Key design:** Week-based metadata filtering means a student in Week 3 gets answers
from Week 3 content — not the whole course; `week` (0 = all weeks) comes from the
request on both `/chat` and `/stream`. Retrieval runs in a worker thread, and the
embedding model is loaded once per process (`core/vectorstore.py`). While nothing
is uploaded it skips retrieval without loading the model and answers from general
knowledge, saying so. Smoke tests run a real Chroma with a fake embedding to
check the week filter.

> ⚠️ **Only when the router picks it.** Course mode still goes through the LLM
> router; a question it labels `theory` is answered by Theory, not RAG. Like
> Code, its stream is simulated. On Railway the Chroma directory is wiped on
> every redeploy, so uploads need re-ingesting (or a volume) to stay searchable.
</details>

<details>
<summary><b>04 · Lesson</b> — 1 LLM call per operation</summary>

**What it does:** Three separate graphs — **plan** (generate a 3–4 step lesson),
**teach** (explain one step), **grade** (evaluate the student's answer). One call each.

**Key design:** Deprecated Qiskit patterns in generated code are sanitized
deterministically before the student ever sees them. The check-question grader is
told to be generous, but it **fails closed**: a reply that doesn't validate after one
retry is not a pass. The answer key stays on the server: the full plan is stored
in Redis under its `plan_id`, the browser gets it without any `check_answer`, and
`/lesson/grade` takes only `plan_id`, `step_num` and the answer (anything else is a
`422`). Which steps are unlocked still lives in the browser.
</details>

<details>
<summary><b>05 · Exam questions</b> — 1 LLM call (0 for V1) + a deterministic follow-up rule</summary>

**What it does:** V1 asks from a static bank. V2 and V3 generate each question from
the previous answers, scores and weak areas; they differ in follow-ups, with V2
allowing one per main question and V3 up to two.

**Key design:** The follow-up decision is **100% deterministic**. It fires when the
answer just given scores `< 5.0` (the mean of its three dimensions, not a session
average). Zero LLM calls for that branch, and the logic is unit-testable without a
model.
</details>

<details>
<summary><b>06 · Grader</b> — 1 LLM call (2 on a corrective retry) · part of the exam agent</summary>

**What it does:** Scores answers on three dimensions — **Accuracy** (0–10),
**Reasoning** (0–10), **Clarity** (0–10) — and returns a justification plus an ideal
answer for benchmarking.

**Key design:** All three scores, the justification and the ideal answer come back
in one structured JSON response. It isn't a separate agent: it's the grading graph
in `exam_agent.py`. The reply is validated as a Pydantic `ExamGrade`; one that
doesn't validate gets one corrective retry, after which the answer is stored
ungraded and flagged, never given a default score.

**Student text is data.** The rubric is a system message saying tagged student
text is untrusted. The answer, topic and earlier answers go in `<tags>` with `&`,
`<` and `>` escaped, so an answer can't close its tag and append instructions. That
makes injection harder, not impossible: a model can still be talked into a score,
which is one reason teacher review exists.
</details>

<details>
<summary><b>07 · Router</b> (<code>orchestrator.py</code>) — 1 LLM call, or 0 in Practice mode</summary>

**What it does:** Picks the agent for each request. `practice` short-circuits
deterministically to the Code agent with no LLM call. Every other mode goes through
`route()`, which asks the cheap router model (`LLM_ROUTER_MODEL`) to classify the
message. The reply is validated as a Pydantic `RouteDecision`; an invalid one gets
one corrective retry, then falls back to Theory.

**Key design:** Defensive by default — an LLM that returns garbage degrades to a
sensible agent rather than raising. It isn't a graph: one classification call and
plain `if`/`elif` through one table, `WORKFLOW_FOR_LABEL`, that both `/chat` and
`/stream` use: `theory` → Theory, `code` → Code, `rag` → RAG, `review` → Code.

> ⚠️ **There is no Review agent.** The router prompt still offers a `review`
> label for "student code wants feedback"; it runs the Code workflow, which writes
> code rather than reviewing the student's.
</details>

<br/>

## 🔬 Research Layer

A planned study, not a finished one: the schema and the teacher review flow exist,
and no data has been collected.

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
survive. The AI's half of a review is copied from the stored turn, never from the
request. Append-only is enforced by the application, not by database permissions,
and teachers share one password, so a review records what changed but not who
changed it.

```sql
exam_sessions    -- session_id, student_name, topic, version (V1/V2/V3), avg_score
exam_turns       -- question, answer, score_accuracy, score_reasoning, score_clarity,
                 --   ai_justification, ideal_answer, is_followup, graded
teacher_reviews  -- ai_scores, teacher_override_scores, delta, feedback, action
research_metrics -- reserved for the experiments below; nothing writes to it yet
```

Experiment 3's ground-truth labels have no table yet — label those 50 turns outside
the database for now.

**No experiment has been run yet.** `/api/research/stats` returns descriptive
aggregates today: sessions by version, the mean absolute teacher–AI difference per
dimension, answers scoring under 5, and answers that couldn't be graded. The
correlations and precision/recall below are the plan, not implemented metrics.

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

**Caveat:** V2 and V3 share the question generator and differ only in how many
follow-ups they allow, so V3 vs V1 is the cleaner comparison.

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

<br/>

## ⚡ Tech Stack

<div align="center">

| Layer | Technology | Why |
|-------|-----------|-----|
| **AI framework** | LangGraph 0.2.55 | Stateful graphs with conditional edges and persistent memory |
| **LLM** | Groq · llama-3.1-8b-instant | Free tier and fast; an 8B model's grading and JSON reliability is the main quality limit |
| **Provider seam** | One `ChatOpenAI` client → groq \| openai \| vllm | Dev and prod share one code path; only base URL + key differ |
| **Resilience** | tenacity + a Redis Lua semaphore | Bounded global concurrency, backoff with jitter, fail-open |
| **RAG** | ChromaDB 0.5.18 + all-MiniLM-L6-v2 | Local · free · no API key · per-week filter. Torch pinned CPU-only to keep the image small. Chroma telemetry off |
| **Code execution** | Qiskit 2.3 + Aer 0.17 in a locked-down container | Per-run container, no network, read-only FS, non-root, resource caps |
| **Circuit diagrams** | matplotlib `qc.draw('mpl')` | base64 PNG returned straight to the frontend |
| **Backend** | FastAPI 0.115 · SSE via `StreamingResponse` | Async · token streaming |
| **Frontend** | React 19 + Vite 6 + Tailwind 4 + Framer Motion 12 | Fast dev server · animated UI |
| **State / routing** | Zustand 5 · React Router 7 | Minimal global store, no boilerplate |
| **Editor** | Monaco (the VS Code engine) | Syntax highlighting · themes · resizable |
| **Conversation memory** | LangGraph `AsyncPostgresSaver` (code workflow) · recent history from the client (streamed theory) | Checkpointed memory survives restarts; streaming bypasses the graph, so the two paths remember different things |
| **Cache** | In-memory LRU for lesson plans — 200 items, 1 hr TTL | A repeated topic skips the LLM · per-process |
| **Audit DB** | Postgres · async SQLAlchemy 2 + psycopg 3 + Alembic | Exam trails · teacher overrides · research data |
| **Active exam state** | Redis, with Postgres as source of truth | Shared across workers; fully rebuildable from Postgres |
| **Voice** | Web Speech API | Browser-native · zero backend changes |
| **Hosting** | Railway (API) + Vercel (SPA) + Neon + Upstash | See [DEPLOY.md](DEPLOY.md) |

</div>

<br/>

## 🧪 Tests & CI

**125 test functions** in three tiers (a few are parametrized into more cases),
run by [GitHub Actions](.github/workflows/ci.yml) on every push and pull request.

**Unit — no services needed**

| Suite | Tests | What it proves |
|---|---|---|
| [`test_executor.py`](backend/tests/test_executor.py) | 10 | Harness wrapping, circuit-image parsing, and the settings gate that refuses the subprocess executor in production |
| [`test_llm_provider_switch.py`](backend/tests/test_llm_provider_switch.py) | 9 | groq / openai / vllm resolve the right base URL and key; bad provider config fails at startup; the client is built with SDK retries off |
| [`test_llm_resilience.py`](backend/tests/test_llm_resilience.py) | 6 | Transient vs permanent error classification; retries up to the ceiling; timeouts become `LLMUnavailable` |
| [`test_llm_stream.py`](backend/tests/test_llm_stream.py) | 4 | Streams retry only before the first token (no double-emit), fail as `LLMUnavailable` after it, and are accounted |
| [`test_llm_accounting.py`](backend/tests/test_llm_accounting.py) | 3 | Usage is logged and counted; the budget only warns; a failing counter never breaks a call |
| [`test_llm_limiter.py`](backend/tests/test_llm_limiter.py) | 1 | The limiter fails open when Redis is down |
| [`test_llm_seam_isolation.py`](backend/tests/test_llm_seam_isolation.py) | 1 | No module outside `core/llm.py` imports an LLM SDK (an AST check) |
| [`test_agents_smoke.py`](backend/tests/test_agents_smoke.py) | 4 | Router JSON parsing and fallback, the theory graph, and the exam grader, on a mocked model |
| [`test_structured_output.py`](backend/tests/test_structured_output.py) | 9 | Router, lesson-grade and exam-grade replies are validated; an invalid reply gets one retry, then each fails closed |
| [`test_prompt_injection.py`](backend/tests/test_prompt_injection.py) | 5 | Rubric in the system message; student text delimited and escaped; a fake model that obeys outside text isn't fooled |
| [`test_lesson_grading.py`](backend/tests/test_lesson_grading.py) | 3 | The lesson grader fails closed; only a JSON `true` passes |
| [`test_lesson_answer_key.py`](backend/tests/test_lesson_answer_key.py) | 4 | The answer key never reaches the browser; grading uses the stored copy; a client-sent key is a `422` |
| [`test_routing.py`](backend/tests/test_routing.py) | 3 | `/chat` and `/stream` route every label alike, and `week` reaches RAG |
| [`test_rag_smoke.py`](backend/tests/test_rag_smoke.py) | 3 | Real Chroma + fake embedding: week filter, empty store loads no model, `/stream` reaches RAG |
| [`test_exam_start.py`](backend/tests/test_exam_start.py) | 2 | An LLM outage at `/exam/start` writes nothing and returns `503` |
| [`test_backfill_ended_sessions.py`](backend/tests/test_backfill_ended_sessions.py) | 2 | A pending answer of an ended exam is still graded and averaged |
| [`test_upload_offloop.py`](backend/tests/test_upload_offloop.py) | 2 | Upload ingestion runs off the event loop |
| [`test_logging.py`](backend/tests/test_logging.py) | 5 | JSON log lines, the `llm_call` record emitted, request ids echoed and attached, `LOG_LEVEL` respected |
| [`test_exam_grading.py`](backend/tests/test_exam_grading.py) | 6 | Grader replies are parsed tolerantly and clamped; an unusable reply gets one retry, then `GradingFailed`, never a default score |
| [`test_code_agent.py`](backend/tests/test_code_agent.py) | 3 | No retry against a disabled sandbox, one retry on a code error, the message sent once, bounded history |
| [`test_chat_routes.py`](backend/tests/test_chat_routes.py) | 3 | `/chat` callers get separate threads; `/history` returns what the checkpointer stored; replayed history is capped |
| [`test_stream_history.py`](backend/tests/test_stream_history.py) | 3 | Streamed theory answers replay recent client history; `/stream` validates it |
| [`test_http_contracts.py`](backend/tests/test_http_contracts.py) | 8 | Through the HTTP layer: teacher auth on protected routes, the upload size cap, `503` for disabled execution, validation, production refusing the default password |

**Sandbox — real Docker containers**

| Suite | Tests | What it proves |
|---|---|---|
| [`test_containment.py`](backend/tests/sandbox/test_containment.py) | 7 | A normal circuit runs and draws; network blocked; no secrets or app code inside; read-only filesystem; infinite loop killed; memory bomb and fork bomb contained |

**Integration — real Postgres and Redis**

| Suite | Tests | What it proves |
|---|---|---|
| [`test_exam_idempotency.py`](backend/tests/integration/test_exam_idempotency.py) | 3 | Concurrent submits record one turn (the other gets `409`); a stale Redis copy can't duplicate a turn; the unique constraint holds |
| [`test_grading_degradation.py`](backend/tests/integration/test_grading_degradation.py) | 3 | LLM down: answer saved ungraded, re-submits don't duplicate it, the backfill grades and advances it once; the `/status` contract |
| [`test_status_turn_result.py`](backend/tests/integration/test_status_turn_result.py) | 1 | `/status` hands a pending answer's result back once it's graded |
| [`test_end_with_pending_answer.py`](backend/tests/integration/test_end_with_pending_answer.py) | 1 | Ending an exam with an answer pending: the backfill still grades it, once, and the average includes it |
| [`test_ungradable_answer.py`](backend/tests/integration/test_ungradable_answer.py) | 2 | An unreadable grade is stored with no scores and flagged, with no follow-up; the backfill finalizes it once |
| [`test_teacher_reviews.py`](backend/tests/integration/test_teacher_reviews.py) | 2 | A turn reviewed twice is listed once; a review stores the turn's AI scores, not the client's |
| [`test_exam_restart.py`](backend/tests/integration/test_exam_restart.py) | 1 | Redis loses the exam and every data-layer singleton is disposed; the exam rebuilds from Postgres and continues |
| [`test_two_workers.py`](backend/tests/integration/test_two_workers.py) | 1 | A fresh data-layer instance sees the same exam and continues it (sequential, in one process) |
| [`test_checkpointer_postgres.py`](backend/tests/integration/test_checkpointer_postgres.py) | 1 | Code-agent memory survives a restart on the real Postgres checkpointer |
| [`test_llm_concurrency.py`](backend/tests/integration/test_llm_concurrency.py) | 2 | The Lua semaphore never over-admits a burst and raises `LLMBusy` under saturation (one process, real Redis) |
| [`test_phase1_units.py`](backend/tests/integration/test_phase1_units.py) | 2 | `end_session` is one idempotent `UPDATE`; active state rebuilds from Postgres with Redis empty |

CI starts throwaway `postgres:16` and `redis:7` service containers and builds the
real sandbox image, then runs the whole suite with `REQUIRE_INTEGRATION=1` and
`REQUIRE_SANDBOX=1`: if a service or the image is missing, the build fails rather
than skipping those tiers. A second job builds the frontend. Integration tests call
route and repository functions directly; the HTTP layer is covered by
`test_http_contracts.py`. **Untested:** lesson-plan and step generation (grading is
tested), retrieval quality with the real embedding model, and the whole frontend.

```bash
cd backend
uv run python -m pytest tests/ -q            # integration + sandbox tiers skip without services

# integration tier against local containers
docker compose -f ../docker-compose.dev.yml up -d
DATABASE_URL_TEST=postgresql+psycopg://quantummind:quantummind@localhost:5432/quantummind \
REDIS_URL_TEST=redis://localhost:6379/0 \
uv run python -m pytest tests/integration -q

uv run python -m pytest tests/sandbox -q     # needs Docker + the sandbox image
```

> Without the `*_TEST` variables the integration tier falls back to `DATABASE_URL` /
> `REDIS_URL` from `.env`, which may be a hosted database.

<br/>

## 🔌 API Reference

All routes are mounted under `/api`.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/stream` | **Primary chat endpoint** — SSE with `progress` / `token` / `done` / `error` events |
| `POST` | `/chat` | Non-streaming equivalent · not called by the frontend |
| `GET` | `/history/{thread_id}` | Replay a conversation from the checkpointer |
| `GET` | `/cache/stats` | Lesson-plan cache hit rate and occupancy |
| `POST` | `/execute` | Run Qiskit code → stdout + base64 circuit PNG (`503` when `EXECUTOR=disabled`) |
| `POST` | `/lesson/plan` · `/lesson/teach` · `/lesson/grade` | Guided-mode lifecycle; `plan` returns a `plan_id` and no answer keys, `grade` takes `plan_id` + `step_num` + answer |
| `POST` | `/exam/start` · `/exam/answer` · `/exam/end` | Exam lifecycle — `start` returns `503` and stores nothing if the LLM is down; `answer` returns `saved_pending_grading` when degraded, `409` if that turn is already recorded |
| `GET` | `/exam/session/{id}/status` | Poll a pending grade; `?turn_id=` returns that answer's result once graded |
| `GET` | `/exam/session/{id}` 🔒 | Full transcript with ideal answers |
| `GET` | `/teacher/sessions` · `/teacher/session/{id}` 🔒 | Teacher dashboard listings |
| `POST` | `/teacher/review` 🔒 | Append-only review; the AI's scores come from the stored turn |
| `GET` | `/research/stats` 🔒 | Descriptive aggregates for the research layer |
| `POST` | `/upload` 🔒 | PDF / notebook → chunked → embedded into ChromaDB (20 MB cap), off the event loop · read by the RAG workflow |
| `GET` | `/upload/status` 🔒 | What's currently indexed |
| `GET` | `/health` | Liveness + environment + active model *(unprefixed)* |

🔒 = requires the `X-Teacher-Password` header.

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
TEACHER_PASSWORD=change_me        # teacher dashboard + uploads; production refuses the default
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
  -H "X-Teacher-Password: $TEACHER_PASSWORD" \
  -F "file=@lecture_week1.pdf" -F "week=1"

curl -X POST http://localhost:8000/api/upload \
  -H "X-Teacher-Password: $TEACHER_PASSWORD" \
  -F "file=@lab_week3.ipynb" -F "week=3"

curl -H "X-Teacher-Password: $TEACHER_PASSWORD" http://localhost:8000/api/upload/status
```

<sub>Uploads are embedded in a worker thread and read by the RAG workflow when the
router labels a question `rag` (see 03).</sub>

<br/>

## 🚧 Known Limitations and Roadmap

Stated plainly, so nobody has to dig it out of the code.

### Not built

- **No tool calling, no MCP.** The workflows don't choose tools or actions; the
  deterministic code around them decides what happens next.
- **No Review agent.** The router's `review` label runs the Code workflow.
- **No user accounts.** Students type a name and teachers share one password. There
  is no consent record or deletion path for student answers yet, and no rate limiting.
- **The Docker executor has only run locally and in CI.** Hosted deploys use
  `EXECUTOR=disabled`, because Railway containers have no Docker daemon to launch
  sandbox containers with.

### Known bugs and gaps

- **Prompt injection is mitigated, not solved.** Student text is delimited and
  escaped and the rubric says it's data (see 06), but an 8B model can still be
  persuaded. Teacher review is the backstop.
- **Code and RAG streaming is simulated** (see 02): the finished answer is sent
  word by word.
- **Memory depends on the route.** Streamed Theory answers remember the client's
  recent turns; the Code workflow remembers its own checkpointed turns. A chat that
  switches between them loses context at the switch. RAG has a third, separate
  checkpointed thread.
- **No input length caps** on exam answers or chat messages, and `/api/stream` is
  public, so one client can spend the LLM budget.
- **Single worker in production.** The lesson-plan cache and the executor semaphore
  are per process (see `backend/Dockerfile`). The exam and LLM paths are built to be
  shared across workers, but production doesn't exercise that.
- **No research study has been run**, and the stats endpoint returns descriptive
  aggregates only.
- **LangGraph is 0.2.55**, while `langgraph-checkpoint-postgres` 3.x warns that it
  expects 0.5 or later. The Postgres checkpointer is integration-tested on this
  pairing, but the upgrade is due.

### Roadmap, in order

1. Cap input sizes and add a per-client rate limit on `/api/stream`.
2. One memory source for every workflow (the checkpointer), and real token
   streaming for Code and RAG.
3. Run code somewhere that has a container runtime, so Practice works when hosted.
4. Accounts and per-user rate limits, then the GDPR work in
   [NORTHSTAR.md](NORTHSTAR.md) (consent, export, deletion), before any real exam.
5. Run Experiment 1 (AI vs teacher grading agreement).

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

Three things to get right, because they fail quietly:

- **`FRONTEND_URL` must be your real Vercel origin**, not the localhost default.
  If a `CORS_ALLOW_ORIGIN_REGEX` is also set, the site will appear to work while
  localhost stays a trusted credentialed origin in production.
- **`TEACHER_PASSWORD` has a default** (`quantum2026`) that is published in this
  repo. With `APP_ENV=production` the app refuses to start until you change it.
- **Migration `0003` refuses to run over duplicate exam turns.** It adds a unique
  `(session_id, turn_number)` constraint; if the database already holds duplicates,
  the pre-deploy step fails and the previous version keeps serving.

No public demo URL yet.

<br/>

## 📁 Project Structure

```
quantummind/
├── .github/workflows/ci.yml         # service containers · sandbox · full suite · frontend build
├── docker-compose.dev.yml           # local Postgres + Redis
├── sandbox/Dockerfile               # Qiskit-only image · no app code, no secrets
├── DEPLOY.md · NORTHSTAR.md · docs/
│
├── backend/
│   ├── Dockerfile                   # non-root, uv-based, CPU-only torch
│   ├── railway.toml
│   ├── alembic/versions/            # 0001 schema · 0002 exam_turns.graded · 0003 unique turn
│   ├── app/
│   │   ├── main.py                  # lifespan: checkpointer → PG → Redis → backfill
│   │   ├── agents/
│   │   │   ├── orchestrator.py      # LLM router · practice short-circuits
│   │   │   ├── theory_agent.py      # 1 call · streams · client-sent history
│   │   │   ├── code_agent.py        # generate → execute → fix once
│   │   │   ├── rag_agent.py         # week-filtered retrieval → generate → judge
│   │   │   ├── lesson_agent.py      # plan + teach + grade (1 call each)
│   │   │   └── exam_agent.py        # V1/V2/V3 questions · grader · follow-up rule
│   │   ├── core/
│   │   │   ├── llm.py               # ⭐ the ONLY module importing an LLM SDK
│   │   │   ├── llm_limiter.py       # ⭐ Redis Lua semaphore · self-healing · fail-open
│   │   │   ├── llm_errors.py        # LLMUnavailable · LLMBusy
│   │   │   ├── grading_backfill.py  # ⭐ reconciles turns the LLM couldn't grade
│   │   │   ├── executor.py          # sandbox seam: docker | subprocess | disabled
│   │   │   ├── exam_state.py        # Redis hot copy + Postgres-only rebuild
│   │   │   ├── memory.py            # AsyncPostgresSaver checkpointer + pool
│   │   │   ├── cache.py             # lesson-plan LRU, 200 items, 1 hr TTL
│   │   │   ├── lesson_store.py      # server-side lesson plans + answer keys (Redis)
│   │   │   ├── structured.py        # Pydantic-validated LLM replies · one retry · fail closed
│   │   │   ├── logging_setup.py     # JSON logs · request-id middleware
│   │   │   ├── vectorstore.py       # shared Chroma + embedding model
│   │   │   ├── auth.py              # shared teacher-password check
│   │   │   ├── config.py            # pydantic settings · fail-fast validators
│   │   │   └── prompts.py           # router + RAG prompts · untrusted-text escaping
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
│   └── tests/                       # unit · sandbox · integration
│       ├── sandbox/                 # real-container containment proofs
│       └── integration/             # degradation · idempotency · restart · checkpointer
│
└── frontend/
    └── src/
        ├── components/
        │   ├── LandingPage.jsx      # dark/light toggle
        │   ├── MainApp.jsx · Sidebar.jsx · ModeSelector.jsx
        │   ├── ChatPanel.jsx        # streaming · progress indicators
        │   ├── CodeEditor.jsx       # Monaco + Run + circuit PNG
        │   ├── PracticeAssistant.jsx
        │   ├── GuidedPanel.jsx      # step-by-step lesson UI
        │   ├── CoursePanel.jsx · CourseSidebar.jsx
        │   ├── ExamMode.jsx         # V1/V2/V3 + voice input
        │   ├── TeacherDashboard.jsx # review + override + research
        │   └── ui/Badge.jsx
        ├── data/curriculum.js       # 13-week course structure
        ├── hooks/useAppState.js     # Zustand global state
        └── lib/                     # api.js (API_BASE) · chat.js (recent history)
```

<br/>

## 👤 About

<div align="center">

**Asfand Yar** — BSc Computer Science, University of Debrecen, Hungary *(graduating August 2027)*

</div>

| Achievement | Detail |
|---|---|
| 🎓 **Course designer** | Designed and taught Debrecen's first Intro to Quantum Computing course — 36 students |
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

</div>
