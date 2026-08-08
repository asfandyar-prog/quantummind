# Deploying QuantumMind

Backend → Railway (Docker). Frontend → Vercel (Vite SPA).
Datastores → **Neon Postgres** and **Upstash Redis**, both external and managed.

Nothing here has been deployed yet. This is the checklist to do it by hand; no
deploy command has been run.

---

## 0. What you are creating

| Where | Service | Notes |
|---|---|---|
| Railway | **backend** — one service, nothing else | Docker, Root Directory `backend` |
| Vercel | **frontend** | Vite preset, Root Directory `frontend` |
| Neon | Postgres | already provisioned, connection string in `backend/.env` |
| Upstash | Redis | already provisioned, connection string in `backend/.env` |

**Do not add Railway's Postgres or Redis plugins.** The app points at Neon and
Upstash, so a Railway datastore would sit unused and cost you a service slot.
Railway runs exactly one service: the backend container.

---

## 1. Railway — backend

### 1.1 Create the service

1. New Project → Deploy from GitHub → `asfandyar-prog/quantummind`.
2. **Settings → Root Directory → `backend`**. Required: the Dockerfile and
   `railway.toml` live there and use paths relative to it.
3. Railway reads `backend/railway.toml` and picks up the Dockerfile builder,
   `/health` as the healthcheck, and `alembic upgrade head` as the pre-deploy
   command. Nothing to configure by hand for those.
4. **Settings → Networking → Generate Domain.** Do this before the first
   successful deploy — the URL is assigned immediately and you need it in §2.

### 1.2 Environment variables

Every value is set by hand. There are no `${{...}}` service references, because
there are no other Railway services to reference.

| Variable | Value | Notes |
|---|---|---|
| `DATABASE_URL` | copy verbatim from `backend/.env` | Neon. **Must keep the `postgresql+psycopg://` scheme** — see §1.3 |
| `REDIS_URL` | copy verbatim from `backend/.env` | Upstash, `rediss://` |
| `GROQ_API_KEY` | from console.groq.com | Secret. Missing → `ValidationError` at **import**, which also breaks the migration step |
| `APP_ENV` | `production` | Also disables `/docs` |
| `EXECUTOR` | `disabled` | Railway has no Docker daemon — see §5 |
| `FRONTEND_URL` | `https://<your-project>.vercel.app` | Exact CORS origin, set in §3 |
| `CORS_ALLOW_ORIGIN_REGEX` | see §4 | Lets Vercel preview deploys through |
| `TEACHER_PASSWORD` | a real password | Secret. There is a default (`quantum2026`) — if you skip this, that default is live |

**Leave unset** — the defaults in `app/core/config.py` are already right:
`LLM_PROVIDER`, `LLM_MODEL`, `LLM_ROUTER_MODEL`, all `LLM_*` resilience knobs,
`GRADING_BACKFILL_*`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`,
`EXAM_STATE_TTL_SECONDS`, `CHROMA_PATH`.

`PORT` is injected by Railway and read by the Dockerfile `CMD` with an 8000
fallback. Do not set it.

### 1.3 The Neon connection string — verified

**Your existing string is already correct.** Checked against the live database:

| Property | Value | Verdict |
|---|---|---|
| Scheme | `postgresql+psycopg://` | ✅ correct |
| Query params | `?sslmode=require` | ✅ accepted |
| Live connection | `PostgreSQL 18.4` via the app's own async engine | ✅ works |

This is the single most likely thing to break a first deploy, and in your case it
is already right — so **copy the string verbatim and change nothing**.

Why it matters: `app/db/database.py` passes `DATABASE_URL` straight into
SQLAlchemy's `create_async_engine`. The bare `postgresql://` scheme selects the
*synchronous* psycopg2 dialect, which an async engine rejects at startup. If you
ever re-copy the string from the Neon console, Neon hands out
`postgresql://…` — you must re-add `+psycopg`:

```
postgresql://user:pass@host/neondb?sslmode=require           ← Neon gives you this
postgresql+psycopg://user:pass@host/neondb?sslmode=require   ← the app needs this
```

**TLS.** Neon enforces TLS and `sslmode=require` is passed through SQLAlchemy to
psycopg 3 and on to libpq, which handles it — verified by a real connection.
`channel_binding=require` is also a libpq parameter and would be passed through
the same way, but your current string does not include it and connects fine, so
the simplest safe move is to keep the string exactly as it is.

One harmless oddity: `SHOW ssl` reports `off` on the server side even over a
TLS connection, because Neon terminates TLS at its proxy rather than at Postgres
itself. That is expected and not a sign your connection is unencrypted.

### 1.4 The Upstash connection string

`rediss://` is all that is needed — **no extra TLS flag.** `app/db/redis_client.py`
calls `redis.from_url(settings.redis_url)`, and redis-py 8.0.1 maps the `rediss://`
scheme to an `SSLConnection` automatically. Verified by inspecting the pool the
URL produces:

```
rediss://…  ->  SSLConnection
redis://…   ->  Connection
```

⚠️ **I could not reach your Upstash instance to confirm it is alive.** The whole
`upstash.io` domain fails DNS resolution from the machine this was checked on —
not just your database, the apex domain too, while Neon and GitHub resolved
normally through the same resolver. That points at local DNS filtering rather
than a deleted database, but it means the instance is **unverified**. This is
also why the integration test suite has been skipping its Redis tests all along.

Before you deploy, confirm it from another network or the Upstash console. If
the database has lapsed, the backend will boot-loop: `app/main.py`'s lifespan
pings Redis and exits if it cannot connect.

---

## 2. Vercel — frontend

1. New Project → import the same repo.
2. **Root Directory → `frontend`**. Required — `vercel.json` lives there.
3. Framework preset **Vite**, build `npm run build`, output `dist`. Already
   declared in `frontend/vercel.json` and matched against a real build.
4. Environment variable:

   | Variable | Value |
   |---|---|
   | `VITE_API_URL` | the Railway domain from §1.1 step 4, **no trailing slash** |

   Set it for Production, Preview and Development so preview builds also reach
   the backend.

> `VITE_API_URL` is inlined at **build** time, not read at runtime. Changing it in
> the dashboard does nothing until the next build.

---

## 3. The ordering problem

The frontend needs the backend's URL; the backend needs the frontend's URL for
CORS. Neither exists before the other is created — but both platforms assign
domains before a successful deploy, so it is not a deadlock.

1. **Railway: create the backend service and generate its domain** (§1.1 step 4).
   You now have the backend URL; the service need not be healthy yet.
2. **Railway: set every variable except the two CORS ones.** Deploy and get it
   green. Fix any failure here before continuing — a CORS problem and a broken
   backend look identical from the browser, and you want them separated.
3. **Vercel: create the project with `VITE_API_URL`** = the URL from step 1.
   Deploy. Note the production URL.
4. **Railway: set `FRONTEND_URL` and `CORS_ALLOW_ORIGIN_REGEX`** from step 3.
   Railway redeploys automatically.

Shortcut: Vercel's production domain is `<project-name>.vercel.app`, and you
choose the project name at creation. Fix the name up front and you can set all
Railway variables in one pass, skipping the second redeploy.

**Verify in this order**, so a failure tells you where it is:

```bash
# 1. backend alive
curl https://<backend>.up.railway.app/health
# -> {"status":"ok","environment":"production","model":"llama-3.1-8b-instant"}

# 2. CORS accepts your frontend
curl -H "Origin: https://<project>.vercel.app" -i \
     https://<backend>.up.railway.app/health | grep -i access-control-allow-origin
# -> access-control-allow-origin: https://<project>.vercel.app

# 3. CORS rejects everything else
curl -H "Origin: https://evil.example.com" -i \
     https://<backend>.up.railway.app/health | grep -i access-control-allow-origin
# -> (no header at all)
```

Then open the Vercel URL and check the browser console.

---

## 4. CORS_ALLOW_ORIGIN_REGEX — the exact value

Substituting your Vercel project name for `quantummind`:

```
^https://quantummind[a-z0-9-]*\.vercel\.app$
```

It is matched in **full** against the `Origin` header, as a second rule OR'd with
the exact `FRONTEND_URL`. Verified behaviour:

| Origin | Result | Why |
|---|---|---|
| `https://quantummind.vercel.app` | ✅ allowed | production |
| `https://quantummind-git-main-asfand.vercel.app` | ✅ allowed | branch preview |
| `https://quantummind-a1b2c3.vercel.app` | ✅ allowed | commit preview |
| `https://totally-other.vercel.app` | ❌ rejected | another project |
| `https://quantummind.vercel.app.evil.com` | ❌ rejected | suffix attack — `$` anchor |
| `https://evil.example.com` | ❌ rejected | unrelated |
| `http://quantummind.vercel.app` | ❌ rejected | scheme is pinned to https |

**Do not loosen this to `.*\.vercel\.app$`.** That would let every site hosted on
Vercel — by anyone — call your API with credentials.

---

## 5. Code execution is off in this deployment

`EXECUTOR=disabled` is deliberate: the sandbox shells out to `docker run`, and a
Railway container has no Docker daemon.

`POST /api/execute` returns **503** with `"Code execution is temporarily
unavailable."`, and Practice mode shows that message in its output panel.

Leaving `EXECUTOR=docker` would not be unsafe — it fails closed, returning
`"Sandbox unavailable: docker not found on host."` in ~60ms with no stack trace
and no hang — but it reports missing infrastructure as an HTTP 200 "your code
failed", which misleads both students and uptime checks.

---

## 6. First deploy failed? Check these

In rough order of likelihood.

**1. Build succeeds, container exits immediately, healthcheck never answers**

```
sqlalchemy.exc.InvalidRequestError: The asyncio extension requires an async driver
```

`DATABASE_URL` lost its `+psycopg`. You pasted from the Neon console instead of
from `backend/.env`. Fix: `postgresql+psycopg://…` — see §1.3.

**2. Deploy aborts during the pre-deploy step, before the app ever starts**

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
  Value error, LLM_PROVIDER=groq requires GROQ_API_KEY (or LLM_API_KEY)
```

`GROQ_API_KEY` is unset. `alembic/env.py` imports the full settings model, so the
migration needs the LLM variables too — not just `DATABASE_URL`.

**3. Container boot-loops, restarts ~10 times, then stops**

```
redis.exceptions.ConnectionError: Error … connecting to <host>.upstash.io:6379
```

Upstash is unreachable or the database has lapsed. Startup pings Redis and exits
on failure. See the warning in §1.4 — verify the instance is alive first. The
same shape of failure with a Postgres traceback means Neon is unreachable or
still waking from scale-to-zero.

**4. Backend is green, frontend loads, every request fails in the browser**

```
Access to fetch at 'https://…up.railway.app/api/stream' from origin
'https://….vercel.app' has been blocked by CORS policy
```

`FRONTEND_URL` still holds its `http://localhost:5173` default, or does not
exactly match the deployed origin (trailing slash, `http` vs `https`, or a
preview URL that needs the regex from §4).

**5. Frontend loads but calls `localhost:8000`**

`VITE_API_URL` was added after the build. It is inlined at build time — redeploy
the Vercel project.

---

## 7. Ephemeral filesystem

Railway's disk does not survive a redeploy. Nothing lost here is irreplaceable:

| Path | Written by | Lost on redeploy | Needs a volume? |
|---|---|---|---|
| `<CHROMA_PATH>` | `routes/upload.py` — embeddings of uploaded PDFs/notebooks | uploaded course material | Only once RAG is reachable; today nothing reads it |
| `~/.cache/huggingface` | `all-MiniLM-L6-v2`, ~80 MB on first embedding call | the model | No, but it re-downloads at request time, so the first upload after each deploy is slow |
| `/tmp/…` | `upload.py` staging, removed in a `finally` | nothing | No |

Neon and Upstash are external and completely unaffected by redeploys — that is
the main practical advantage of this setup over Railway plugins.

`CHROMA_PATH` is authoritative: `upload.py` and `rag_agent.py` both resolve it
through `settings.chroma_dir`. If you attach a Railway volume, point
`CHROMA_PATH` at the mount and both readers follow. A relative value resolves
against the backend package root, not the working directory.

---

## 8. What is still broken after this deploy

Deploying fixes none of these. Ordered by what a real student hits first.

**Broken:**

1. **Practice mode cannot run code** — §5, by design.
2. **Course mode never reads uploaded material.** The orchestrator's `rag`
   branch is a stub that falls back to the theory agent; the fully-built RAG
   graph is unreachable. The UI still says "Searching course materials…".
3. **Teacher auth is one shared password.** Constant-time and read from
   settings, but no rate limiting, no lockout, no accounts — and it guards every
   student's name, answers and scores.
4. **`POST /api/upload` is unauthenticated and unbounded.** Anyone can inject
   content into the vector store or exhaust memory with one large file.
5. **No rate limiting on any LLM endpoint.** `/api/stream` is public and spends
   Groq tokens per call.

**Fragile under load:**

6. **Concurrent answers to one exam session can double-grade** — the idempotency
   check and the grading write are not atomic.
7. **Single worker only** — the LRU cache and executor semaphore are
   per-process. See the comment in `backend/Dockerfile`.

**Smaller:**

8. `GET /api/exam/session/{id}` and `/api/cache/stats` need no auth.
9. `GET /api/history/{thread_id}` is a stub that always returns empty.
