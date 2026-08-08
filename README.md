<div align="center">

<svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="80" height="80" rx="20" fill="#0066FF" fill-opacity="0.1"/>
  <ellipse cx="40" cy="40" rx="28" ry="11" stroke="#0066FF" stroke-width="2" fill="none"/>
  <ellipse cx="40" cy="40" rx="28" ry="11" stroke="#0066FF" stroke-width="2" fill="none" transform="rotate(60 40 40)"/>
  <ellipse cx="40" cy="40" rx="28" ry="11" stroke="#0066FF" stroke-width="2" fill="none" transform="rotate(120 40 40)"/>
  <circle cx="40" cy="40" r="5" fill="#0066FF"/>
</svg>

# QuantumMind

**Where quantum theory meets practice.**

A production-grade, multi-agent AI platform for quantum computing education —
built by a student who designed and taught the course it's based on.

[![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React_19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-FF6B35?style=for-the-badge&logo=chainlink&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Qiskit](https://img.shields.io/badge/Qiskit-6929C4?style=for-the-badge&logo=ibm&logoColor=white)](https://qiskit.org)
[![License](https://img.shields.io/badge/License-MIT-34C759?style=for-the-badge)](LICENSE)

[**📖 Docs**](#-local-setup) &nbsp;·&nbsp; [**🔬 Research**](#-research-layer) &nbsp;·&nbsp; [**🚀 Deploying**](DEPLOY.md)

*Live demo coming soon — not yet deployed.*

---

*"The people who are crazy enough to think they can change the world are the ones who do."*

</div>

<br/>

## The Idea

Most AI tutors are just chatbots with a quantum physics prompt.

QuantumMind is different. It's a **multi-agent system** where each learning mode is powered by a dedicated LangGraph agent — one that actually runs your Qiskit code, grades your understanding on three dimensions, and adapts its questions based on your answers.

It's the platform I wish existed when I designed and taught the University of Debrecen's first Quantum Computing course for 60+ students. So I built it.

<br/>

## 🎓 Five Ways to Learn

<div align="center">

| | Mode | Description | Access |
|---|---|---|---|
| ⚛ | **Theory** | AI tutor that infers your level from your question. Ask in plain English or Dirac notation — it adapts. | ![Free](https://img.shields.io/badge/Free-34C759?style=flat-square) |
| ⌨ | **Practice** | Monaco editor (VS Code engine). Write Qiskit, hit Run, see your circuit diagram appear as a live image. | ![Free](https://img.shields.io/badge/Free-34C759?style=flat-square) |
| 🎯 | **Guided** | Step-by-step lessons with mandatory check questions. You cannot advance until you demonstrate understanding. | ![Free](https://img.shields.io/badge/Free-34C759?style=flat-square) |
| 🎓 | **13-Week Course** | The full quantum computing curriculum I designed for 60+ students at the University of Debrecen, as a week-by-week tree. *Currently answers from general knowledge — see agent 07.* | ![Premium](https://img.shields.io/badge/Premium-FF9500?style=flat-square) |
| 📝 | **Exam Mode** | V1 static · V2 conditional · V3 fully adaptive. Scored on accuracy, reasoning, clarity. Voice input. Full audit trail. | ![Research](https://img.shields.io/badge/Research-7C3AED?style=flat-square) |

</div>

<sub>The Free / Premium / Research tags are roadmap labels, not enforced tiers —
there is no billing, no entitlement check and no user accounts yet. Every mode is
open to anyone who loads the app.</sub>

<br/>

## 🏗 Architecture

<div align="center">

```mermaid
graph TD
    ORC["🧠 ORCHESTRATOR<br/>1 LLM call to route<br/>(practice skips it)"]

    ORC --> T["⚛ THEORY<br/>1 LLM call<br/>XML prompt + LRU cache"]
    ORC --> C["⌨ CODE<br/>1–2 LLM calls<br/>Qiskit in a Docker sandbox"]
    ORC -.->|not wired| R["📚 RAG<br/>2 LLM calls<br/>ChromaDB week-filtered"]
    ORC --> L["🎯 LESSON<br/>1 call each<br/>Plan · Teach · Grade"]
    ORC --> E["📝 EXAM<br/>1 call + det. routing<br/>V1 · V2 · V3 adaptive"]

    T --> MEM["💾 POSTGRES · REDIS · LRU CACHE"]
    C --> MEM
    R --> MEM
    E --> MEM

    style ORC fill:#0066FF,color:#fff,stroke:#0066FF
    style T  fill:#1a1a2e,color:#6ea8fe,stroke:#0066FF
    style C  fill:#1a1a2e,color:#6ee7b7,stroke:#059669
    style R  fill:#1a1a2e,color:#c4b5fd,stroke:#7C3AED
    style L  fill:#1a1a2e,color:#fdba74,stroke:#FF6B00
    style E  fill:#1a1a2e,color:#fca5a5,stroke:#FF3B30
    style MEM fill:#111,color:#888,stroke:#333
```

</div>

### Why it's fast

| Decision | What we did | Latency saved |
|---|---|---|
| **Deterministic routing** | Follow-up decision uses `score < 5.0` threshold — zero LLM | ~2s per turn |
| **Deterministic sanitization** | Deprecated Qiskit replaced by string substitution | ~2s per code fix |
| **LRU cache** | Common theory questions answered from cache | ~3s → ~50ms |
| **Progress events** | SSE sends "Thinking…" in <100ms before LLM responds | perceived latency |
| **1-call prompts** | XML-structured prompts replace analyze→generate→grade loops | ~6s per request |

<br/>

## 🤖 The Seven Agents

<details>
<summary><b>01 · Theory Agent</b> — 1 LLM call + cache</summary>

**What it does:** Infers student level from question phrasing (beginner/intermediate/advanced) and generates a calibrated explanation with proper Dirac notation. Streams tokens directly.

**Key design:** XML-structured system prompt replaces the old analyze→generate→grade reflection loop. Common questions (what is superposition?, explain entanglement) are cached for 1hr — served in ~50ms.

```python
# Single node graph
generate_response → END
```
</details>

<details>
<summary><b>02 · Code Agent</b> — 1–2 LLM calls</summary>

**What it does:** Generates Qiskit code + explanation in one structured call, then executes it in a locked-down Docker container. If it fails, retries once with the error context.

**Key design:** `temperature=0.1` for code generation — maximum reliability. Deprecated syntax (`Aer.get_backend()`, `execute()`) is fixed deterministically before execution. Returns real output + circuit diagram as base64 PNG.

**Execution backends** (`EXECUTOR`): `docker` is the default and the only secure one — a fresh container per run with no network, a read-only root filesystem, a non-root user, all capabilities dropped, and memory/CPU/PID caps. `subprocess` runs on the host and is an insecure dev-only fallback, gated behind `ALLOW_INSECURE_EXECUTOR=true` and refused outright when `APP_ENV=production`. `disabled` runs nothing and answers 503.

> ⚠️ **Hosted deploys currently run `EXECUTOR=disabled`.** Railway containers have no Docker daemon, so code execution is switched off there and Practice mode reports *"Code execution is temporarily unavailable."* Running locally with Docker gives you the real thing.

```python
# Conditional retry loop
generate → execute → (fail?) → increment_retry → generate → execute → assemble → END
```
</details>

<details>
<summary><b>03 · RAG Agent</b> — 2 LLM calls · <b>built but not wired in</b></summary>

**What it does:** Retrieves relevant chunks from ChromaDB filtered by week number, generates an answer grounded in course materials, grades the answer quality.

**Key design:** Week-based metadata filtering means a student in Week 3 only gets answers from Week 3 content — not the entire course. Falls back to general knowledge if no materials uploaded.

> ⚠️ **Not reachable at runtime.** The graph is complete and compiles, but the orchestrator never routes to it — see agent 07. Documents uploaded via `/api/upload` are embedded into ChromaDB and then read by nothing.
</details>

<details>
<summary><b>04 · Lesson Agent</b> — 1 LLM call per operation</summary>

**What it does:** Three separate graphs — plan (generates 3-4 step lesson), teach (explains one step), grade (evaluates student answer). Each is 1 LLM call.

**Key design:** Deprecated Qiskit patterns in generated code are sanitized deterministically — a lookup table of string replacements runs before the student ever sees the code.
</details>

<details>
<summary><b>05 · Exam Agent</b> — 1 LLM call + deterministic routing</summary>

**What it does:** Generates exam questions for V1 (static bank), V2 (fixed + conditional follow-up), or V3 (fully adaptive based on previous answers).

**Key design:** The follow-up decision is 100% deterministic — `avg_score < 5.0` → generate follow-up. Zero LLM calls for this routing decision. Saves ~2s per turn.
</details>

<details>
<summary><b>06 · Grade Agent</b> — 1 LLM call</summary>

**What it does:** Scores student answers on three dimensions: **Accuracy** (0–10), **Reasoning** (0–10), **Clarity** (0–10). Returns justification and an ideal answer for benchmarking.

**Key design:** All three scores + justification + ideal answer returned in one structured JSON response. The old analyze→grade loop (2 calls) is merged into one.
</details>

<details>
<summary><b>07 · Orchestrator</b> — 1 LLM call (routing), or 0 in Practice mode</summary>

**What it does:** Picks the agent for each request. `practice` short-circuits deterministically to the Code agent with no LLM call. Every other mode goes through `route()`, which asks the cheap router model (`LLM_ROUTER_MODEL`) to classify the message and falls back to the Theory agent if the reply is not valid JSON or names an unknown agent.

**Key design:** Only Practice mode is deterministic. Routing elsewhere costs one real LLM call.

> ⚠️ **`course` does not reach the RAG agent.** The orchestrator's `rag` branch is still a stub that falls back to the Theory agent, so Course mode answers from general knowledge and uploaded material is never retrieved — even though the RAG graph below is fully built. Likewise `review` falls back to the Code agent.
</details>

<br/>

## 🔬 Research Layer

Aligned with **ETH Zurich's Agentic AI in Education** project direction.

### Research Questions

| | Question |
|---|---|
| **RQ1** | To what extent do AI rubric scores agree with human teacher scores across accuracy, reasoning, and clarity? |
| **RQ2** | Do V3 (adaptive) exam students score higher than V1 (static) students on the same topic? |
| **RQ3** | Can the reasoning dimension reliably identify vague answers that accuracy alone misses? |
| **RQ4** | Do students who receive follow-up questions improve on subsequent turns? |

### Audit Trail

Every exam event is logged to **Postgres**, accessed through async SQLAlchemy and
versioned with Alembic. Teacher reviews are **append-only** — a review is always a
new row, never an update — so the AI's original score and the teacher's override
both survive. This guarantees reproducibility and fairness.

```sql
exam_sessions    -- session_id, student_name, topic, version (V1/V2/V3), avg_score
exam_turns       -- question, answer, score_accuracy, score_reasoning, score_clarity
                 --   ai_justification, ideal_answer, is_followup, graded
teacher_reviews  -- ai_scores, teacher_override_scores, delta, feedback, action
research_metrics -- aggregate metrics for the experiments below
```

Experiment 3's ground-truth labels have no table yet — label those 50 turns
outside the database for now.

### Three Experiments

<details>
<summary><b>Experiment 1</b> — AI vs Human Grading Agreement</summary>

**Goal:** Measure how reliable AI rubric scoring is compared to human experts.

**Participants:** 15 exam sessions · 2 independent reviewers

**Method:**
1. Run 15 exam sessions (any version, any topic)
2. Both reviewers independently score all turns via teacher dashboard
3. Compare reviewer scores vs AI scores

**Metrics:** Pearson r per dimension (target > 0.7), MAE, agreement rate (|delta| ≤ 1.0)

**Publishable claim:** *"AI rubric scoring achieves r=X agreement with human experts on quantum computing oral examinations"*
</details>

<details>
<summary><b>Experiment 2</b> — Adaptive vs Static Questioning</summary>

**Goal:** Show V3 produces better learning outcomes than V1.

**Participants:** 30 students (10 per version)

**Method:**
1. Randomly assign students to V1, V2, or V3
2. All students take exam on the same topic (e.g. Quantum Superposition)
3. One week later, same students take V1 post-test on same topic
4. Compare pre/post score changes by group

**Metrics:** Cohen's d for V3 vs V1, % improvement from pre to post-test

**Publishable claim:** *"Adaptive multi-turn questioning improves post-test scores by X% vs static questioning"*
</details>

<details>
<summary><b>Experiment 3</b> — Vague Answer Detection</summary>

**Goal:** Validate that the reasoning dimension catches weak answers that accuracy alone misses.

**Participants:** 50 existing exam turns (no new students needed)

**Method:**
1. Manually label 50 turns as: "strong" / "vague" / "incorrect"
2. Compare labels to AI reasoning scores
3. Measure precision/recall of reasoning as vague-answer detector

**Metrics:** Precision, recall, F1 score vs accuracy-only baseline

**Publishable claim:** *"Reasoning-dimension scoring detects vague answers with precision=X vs accuracy-only baseline"*
</details>

**Target venues:** EDM 2026 · LAK 2026 · AIED 2026

<br/>

## ⚡ Tech Stack

<div align="center">

| Layer | Technology | Why |
|-------|-----------|-----|
| **AI Framework** | LangGraph 0.2 | Stateful graphs with conditional edges and memory |
| **LLM** | Groq llama-3.1-8b-instant | 500+ tokens/sec · free tier · sufficient quality |
| **RAG** | ChromaDB + HuggingFace all-MiniLM-L6-v2 | Local · free · no API key required |
| **Code Execution** | Qiskit + AerSimulator in a locked-down Docker container | Per-run container: no network, read-only FS, non-root, memory/CPU/PID caps |
| **Circuit Diagrams** | matplotlib `qc.draw('mpl')` | base64 PNG returned directly to frontend |
| **Backend** | FastAPI + SSE streaming | Async · real-time token streaming |
| **Frontend** | React 19 + Vite + Framer Motion | Fast · animated · production-quality |
| **Editor** | Monaco (VS Code engine) | Syntax highlighting · themes · resizable |
| **Memory** | LangGraph `AsyncPostgresSaver` | Conversation memory survives restarts, shared across workers |
| **Cache** | In-memory LRU (200 items, 1hr TTL) | Repeated questions answered instantly · per-process, so single-worker only |
| **Audit DB** | Postgres (async SQLAlchemy + Alembic) | Exam trails · teacher overrides · research data |
| **Active exam state** | Redis, with Postgres as source of truth | Shared across workers; rebuildable from Postgres alone |
| **Voice** | Web Speech API | Browser-native · zero backend changes |
| **Hosting** | Railway + Vercel | Configured, **not yet deployed** — see [DEPLOY.md](DEPLOY.md) |

</div>

<br/>

## 🚀 Local Setup

### Prerequisites

```
Python 3.12+    →  python.org
Node.js 18+     →  nodejs.org
uv              →  curl -LsSf https://astral.sh/uv/install.sh | sh
Groq API key    →  console.groq.com (free)
Postgres 14+    →  required — the app exits at startup if it cannot connect
Redis 6+        →  required — same
Docker          →  optional, only for Practice mode code execution locally
```

Postgres and Redis are **not optional**: startup verifies both and the process
exits if either is unreachable. The quickest local setup is the bundled stack —

```bash
docker compose -f docker-compose.dev.yml up -d    # Postgres + Redis
```

— or point `DATABASE_URL` / `REDIS_URL` at managed instances (Neon, Upstash).

Docker is separately needed to *run student code*. Without it, set
`EXECUTOR=disabled` and Practice mode reports that execution is unavailable;
everything else works.

### Backend

```bash
cd backend

# Install all dependencies
uv sync

# Configure environment
cp .env.example .env
# Add GROQ_API_KEY to .env

# Start server
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

### Environment Variables

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
TEACHER_PASSWORD=your_password    # for /teacher dashboard
EXECUTOR=docker                   # docker | subprocess | disabled
# CHROMA_PATH=./data/chroma       # relative paths resolve against backend/
# CORS_ALLOW_ORIGIN_REGEX=        # extra CORS rule, e.g. for preview deploys
```

> The `postgresql+psycopg://` scheme is required, not cosmetic — the app builds
> an **async** SQLAlchemy engine, and a bare `postgresql://` URL selects the
> synchronous psycopg2 dialect and fails at startup.

`backend/.env.example` is the authoritative, fully-commented list.

### Upload Course Content

```bash
# Upload lecture notes for Week 1
curl -X POST http://localhost:8000/api/upload \
  -F "file=@lecture_week1.pdf" \
  -F "week=1"

# Upload Jupyter notebook for Week 3
curl -X POST http://localhost:8000/api/upload \
  -F "file=@lab_week3.ipynb" \
  -F "week=3"

# Check what's indexed
curl http://localhost:8000/api/upload/status
```

<br/>

## 📁 Project Structure

```
quantummind/
├── backend/
│   └── app/
│       ├── agents/
│       │   ├── theory_agent.py       # 1 call · XML prompt · LRU cache
│       │   ├── code_agent.py         # generate → execute → fix loop
│       │   ├── rag_agent.py          # ChromaDB retrieval + grading
│       │   ├── lesson_agent.py       # plan + teach + grade (1 call each)
│       │   ├── exam_agent.py         # V1/V2/V3 adaptive questioning
│       │   └── orchestrator.py       # deterministic mode-based routing
│       ├── core/
│       │   ├── config.py             # pydantic settings
│       │   ├── memory.py             # AsyncPostgresSaver checkpointer
│       │   ├── executor.py           # sandbox seam: docker | subprocess | disabled
│       │   ├── exam_state.py         # active exam state (Redis + Postgres)
│       │   ├── cache.py              # LRU cache (200 items)
│       │   └── prompts.py            # system prompts
│       ├── db/
│       │   ├── models.py             # SQLAlchemy models
│       │   ├── database.py           # async engine + pool
│       │   └── audit_db.py           # async Postgres audit trail
│       └── routes/
│           ├── stream.py             # SSE streaming + progress events
│           ├── execute.py            # Qiskit execution + circuit PNG
│           ├── upload.py             # PDF/notebook → ChromaDB
│           ├── lesson.py             # guided lesson API
│           └── exam.py               # exam + teacher + research API
└── frontend/
    └── src/
        ├── components/
        │   ├── LandingPage.jsx       # Jobs-style · dark/light toggle
        │   ├── ModeSelector.jsx      # 5 modes · 3+2 grid
        │   ├── ChatPanel.jsx         # streaming · progress indicators
        │   ├── CodeEditor.jsx        # Monaco + Run + circuit diagram
        │   ├── GuidedPanel.jsx       # step-by-step lesson UI
        │   ├── CoursePanel.jsx       # RAG lesson + Ask AI
        │   ├── CourseSidebar.jsx     # 13-week curriculum tree
        │   ├── ExamMode.jsx          # V1/V2/V3 + voice input
        │   └── TeacherDashboard.jsx  # review + override + research
        ├── data/
        │   └── curriculum.js         # 13-week course structure
        ├── lib/
        │   └── api.js                # API_BASE, from VITE_API_URL
        └── hooks/
            └── useAppState.js        # Zustand global state
```

<br/>

## 👤 About

<div align="center">

**Asfand Yar** — BSc Computer Science, University of Debrecen, Hungary *(graduating August 2027)*

</div>

| Achievement | Detail |
|---|---|
| 🎓 **Course Designer** | Designed and taught University of Debrecen's first Intro to Quantum Computing course — 60+ students |
| ⚛ **Qiskit Fall Fest 2025** | Led the event with 120+ participants |
| 👥 **GDG Debrecen** | Co-Lead, Google Developer Groups Debrecen |
| 🏛 **Student Union** | VP, International Students' Union |
| 🔬 **BSc Thesis** | JEPA-RobustViT — Joint Embedding Predictive Architectures + Vision Transformers + Test-Time Adaptation |
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
