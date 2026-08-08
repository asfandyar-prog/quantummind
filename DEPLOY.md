# Deploying QuantumMind

Backend → Railway (Docker). Frontend → Vercel (Vite SPA).

Nothing here has been deployed yet. This document is the checklist to do it by
hand; no deploy command has been run.

---

## 0. What you are creating

| Where | Service | Notes |
|---|---|---|
| Railway | **backend** | Docker, Root Directory `backend` |
| Railway | **Postgres** | Railway's managed plugin |
| Railway | **Redis** | Railway's managed plugin |
| Vercel | **frontend** | Vite preset, Root Directory `frontend` |

---

## 1. Railway — backend

### 1.1 Create the services

1. New Project → Deploy from GitHub → pick `asfandyar-prog/quantummind`.
2. On the service: **Settings → Root Directory → `backend`**. Required — the
   Dockerfile and `railway.toml` both live there and use paths relative to it.
3. Railway reads `backend/railway.toml` and will use the Dockerfile builder,
   `/health` as the healthcheck, and `alembic upgrade head` as the pre-deploy
   command. Nothing to configure by hand for those.
4. Add **+ New → Database → Postgres**.
5. Add **+ New → Database → Redis**.
6. Backend service → **Settings → Networking → Generate Domain**. Do this now,
   before the first successful deploy — you need the URL for step 2 and it is
   assigned immediately.

### 1.2 Environment variables

**Set as Railway references** (Variables tab; these resolve to the private
network, so no egress cost and no public exposure):

| Variable | Value |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |

> **Do not use `${{Postgres.DATABASE_URL}}` directly.** Railway hands out a
> `postgresql://…` URL. `app/db/database.py` passes `DATABASE_URL` straight into
> SQLAlchemy's `create_async_engine`, and the bare `postgresql://` scheme selects
> the *synchronous* psycopg2 dialect, which an async engine refuses. The app
> needs the `postgresql+psycopg://` form, so compose it from the component
> references above. Everything stays a reference — no credential is copied by
> hand, and rotating the database updates it automatically.

**Set by hand:**

| Variable | Value | Why |
|---|---|---|
| `GROQ_API_KEY` | your key from console.groq.com | Secret. Without it the app raises `ValidationError` **at import**, which also breaks `alembic upgrade head` |
| `APP_ENV` | `production` | Also disables `/docs` |
| `EXECUTOR` | `disabled` | Railway has no container runtime — see §4 |
| `FRONTEND_URL` | `https://<your-project>.vercel.app` | Exact CORS origin |
| `CORS_ALLOW_ORIGIN_REGEX` | `^https://<your-project>[a-z0-9-]*\.vercel\.app$` | Lets Vercel **preview** deployments call the API too |
| `TEACHER_PASSWORD` | a real password | Secret. See the warning in §6 |

**Leave unset** — the defaults in `app/core/config.py` are correct for
production: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_ROUTER_MODEL`, every
`LLM_*` resilience knob, `GRADING_BACKFILL_*`, `DB_POOL_SIZE`,
`DB_MAX_OVERFLOW`, `EXAM_STATE_TTL_SECONDS`, `CHROMA_PATH`.

`PORT` is injected by Railway; the Dockerfile's `CMD` reads it with an 8000
fallback. Do not set it yourself.

### 1.3 What "required" actually means here

Worth knowing, because it is not obvious: **no setting in `config.py` is
strictly required** — every field has a default. Things still break in three
distinct ways:

| Failure mode | Variables | Symptom |
|---|---|---|
| **Crashes at import** | `GROQ_API_KEY` | `ValidationError: LLM_PROVIDER=groq requires GROQ_API_KEY`. Kills both the server and the pre-deploy migration |
| **Crashes at startup** | `DATABASE_URL`, `REDIS_URL` | Defaults point at `localhost`. The lifespan hook runs `SELECT 1` and `PING` and exits on failure, so the healthcheck never answers |
| **Silently wrong** | `FRONTEND_URL`, `TEACHER_PASSWORD` | No crash. CORS quietly rejects the real frontend; the teacher password is not what you think it is |

---

## 2. Vercel — frontend

1. New Project → import the same repo.
2. **Root Directory → `frontend`**. Required — `vercel.json` lives there.
3. Framework preset **Vite**, build `npm run build`, output `dist`. These are
   already declared in `frontend/vercel.json` and match Vite's defaults, which
   was verified against a real build.
4. Environment variable:

   | Variable | Value |
   |---|---|
   | `VITE_API_URL` | `https://<backend>.up.railway.app` — the Railway domain from §1.1 step 6, **no trailing slash** |

   Set it for Production, Preview and Development so preview builds also reach
   the backend.

> `VITE_API_URL` is inlined at **build** time, not read at runtime. Changing it
> requires a redeploy — editing it in the Vercel dashboard alone changes
> nothing until the next build.

---

## 3. The ordering problem

The frontend needs the backend's URL (`VITE_API_URL`), and the backend needs the
frontend's URL (`FRONTEND_URL`, for CORS). Neither exists before the other is
created, which looks like a deadlock.

It isn't, because **both platforms assign domains before a successful deploy**.
Resolve it in this order:

1. **Railway: create the backend service and generate its domain** (§1.1 step 6).
   You now have the backend URL. The service does not need to be healthy yet.
2. **Railway: set every variable except the two CORS ones.** Deploy. It should
   go green; if it doesn't, fix that before continuing — a CORS failure looks
   identical to a broken backend from the browser, and you want them separated.
3. **Vercel: create the project with `VITE_API_URL`** = the URL from step 1.
   Deploy. Note the production URL it gives you.
4. **Railway: set `FRONTEND_URL` and `CORS_ALLOW_ORIGIN_REGEX`** from step 3.
   Railway redeploys automatically.

Shortcut: Vercel's production domain is `<project-name>.vercel.app`, which you
choose at creation. If you fix the project name up front you can set all the
Railway variables in one pass and skip the second redeploy. The regex matters
more than the exact URL — it covers production *and* every preview.

**Verify in this order**, so a failure tells you where it is:

```
curl https://<backend>.up.railway.app/health          # -> {"status":"ok",...}
curl -H "Origin: https://<project>.vercel.app" -i \
     https://<backend>.up.railway.app/health          # -> access-control-allow-origin echoed back
```

Then open the Vercel URL and check the browser console for CORS errors.

---

## 4. Code execution is off in this deployment

`EXECUTOR=disabled` is deliberate. The sandbox shells out to `docker run`, and a
Railway container has no Docker daemon.

With `disabled`, `POST /api/execute` returns **503** with
`"Code execution is temporarily unavailable."`, and Practice mode shows that
message in the output panel.

Leaving `EXECUTOR=docker` on Railway would not be *unsafe* — it fails closed,
returning `"Sandbox unavailable: docker not found on host."` in about 60ms with
no stack trace and no hang — but it reports an infrastructure gap as an HTTP 200
"your code failed", which is worse for both users and uptime checks.

Restoring execution needs a runtime that can start containers: a separate
execution service on a VM with a Docker socket, or a provider with nested
containers. That is out of scope here.

---

## 5. Ephemeral filesystem

Railway's disk does not survive a redeploy. Nothing here loses data that is not
regenerable, but know what goes:

| Path | Written by | Lost on redeploy | Needs a volume? |
|---|---|---|---|
| `/app/data/chroma` | `routes/upload.py` — embeddings of uploaded PDFs/notebooks | All uploaded course material | Only once RAG is reachable. Today nothing reads it (see §6) |
| `~/.cache/huggingface` | `all-MiniLM-L6-v2`, ~80 MB, fetched on first embedding call | The model | No — but it re-downloads at request time on first use, so the first upload after each deploy is slow |
| `/tmp/…` | `upload.py` staging, deleted in a `finally` | Nothing | No |

Postgres and Redis are separate managed services and are unaffected.

Note `settings.chroma_path` exists in config but is **never read** —
`upload.py` and `rag_agent.py` each compute their own absolute path. Setting
`CHROMA_PATH` today does nothing.

---

## 6. What is still broken after this deploy

Deploying does not fix any of these. Ordered by what a real student hits first.

**Broken:**

1. **Practice mode cannot run code** — §4. Returns 503 by design.
2. **Course mode never reads uploaded material.** `orchestrator.py` routes
   `"rag"` to a stub that falls back to the theory agent; the fully-built RAG
   graph is unreachable. The UI still says "Searching course materials…".
3. **Teacher auth is a single shared password.** `verify_teacher` reads
   `os.environ` directly, so setting `TEACHER_PASSWORD` on Railway *does* work —
   unlike local `.env`, where it is ignored in favour of a hardcoded
   `quantum2025`. Still: no rate limiting, no lockout, no timing-safe compare,
   and it guards every student's name, answers and scores.
4. **`POST /api/upload` is unauthenticated and unbounded.** Anyone can inject
   content into the vector store or OOM the container with one large file.
5. **No rate limiting on any LLM endpoint.** `/api/stream` is public and spends
   Groq tokens per call.

**Fragile under load:**

6. **Concurrent answers to one exam session can double-grade.** The idempotency
   check and the grading write are not atomic.
7. **Single worker only.** The LRU cache and executor semaphore are
   per-process — see the comment in `backend/Dockerfile`.
8. **Image is multi-GB.** `sentence-transformers` pulls torch and the full CUDA
   stack, for the RAG path that is currently unreachable. Expect slow builds.

**Smaller:**

9. `GET /api/exam/session/{id}` and `/api/cache/stats` need no auth.
10. `GET /api/history/{thread_id}` is a stub that always returns empty.
11. README still describes SQLite, subprocess execution and a `manual_labels`
    table, none of which exist.
