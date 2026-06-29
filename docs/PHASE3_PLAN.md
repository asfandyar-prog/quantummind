# Phase 3 — Secure Code Execution (Plan)

> Plan only. No code until approved. Grounded in the two real execution sites:
> `routes/execute.py` (`/api/execute`, Practice mode — student code) and
> `agents/code_agent.py` (the `execute_code` node — LLM-generated code).
>
> This is the biggest security hole in the system: today both run arbitrary
> Python on the host with the app's full identity, secrets, and network.

## 0. Current reality — exactly how code runs today

Both sites do the same unsafe thing:

1. **Host interpreter.** They resolve `python_exe` from `$VIRTUAL_ENV`
   (`execute.py:92-99`, `code_agent.py:123-130`), falling back to
   `sys.executable` — i.e. the **app's own venv**. Student/LLM code therefore runs
   with every installed package available, including the app's own (`import app…`
   works) and the DB/Redis drivers.
2. **Temp file + blocking subprocess.** Code is written to a host
   `NamedTemporaryFile(suffix='.py', delete=False)` and run via
   `subprocess.run([python_exe, tmp_path], capture_output=True, text=True,
   timeout=N)` — `execute.py:111` (N=45s) and `code_agent.py:137` (N=30s). This is
   **synchronous**, so it also blocks the event loop for the duration.
3. **Full environment inherited.** Neither call passes `env=`, so the child
   inherits the entire parent `os.environ` — **`GROQ_API_KEY`, `LLM_API_KEY`, the
   Neon `DATABASE_URL` (with password), the Upstash `REDIS_URL` (with token), and
   `TEACHER_PASSWORD`**. `import os; os.environ` inside a submission reads them all.
4. **No isolation, no resource caps.** Only a wall-clock `timeout`. No CPU cap, no
   memory cap, no PID cap, no network restriction, no filesystem restriction.

**What a submission can do today (the threat):**
- **Exfiltrate every secret** — read `os.environ` and POST it anywhere (network is
  open); or connect directly to Neon/Upstash with the leaked credentials.
- **Read/write the host filesystem** as the app user — read the repo and `.env`,
  the ChromaDB store, app code; write or delete files.
- **Reach the network** — internal services, the GPU box, the internet.
- **Exhaust the host** — memory bomb (`[0]*10**10`), CPU spin to the timeout, or a
  fork/thread bomb (the subprocess `timeout` kills the direct child but not a
  process group it spawned).
- **Touch the app** — `import app.*`, the same interpreter and packages.

On the shared university GPU box this is catastrophic. Phase 3 closes it.

## 1. What we must contain (the controls)

Per the brief, every run must have: **no network**, hard **CPU / memory /
wall-clock** limits, a **read-only / ephemeral** filesystem, a **non-root** user,
and **no access to secrets, env, the app, or the DB**. A runaway or malicious
submission is killed and reported as a normal "execution failed / limit exceeded"
result — never a server incident. The executor itself is stateless.

## 2. Sandboxing approach — options & recommendation

### Options evaluated

| Approach | Isolation | Infra needed | Verdict |
|---|---|---|---|
| **A. Docker container-per-run** | Strong (namespaces, cgroups, no-net, caps) | A Docker daemon on the host | **Recommended** — matches the MoleScan deployment; hand-off as an image |
| B. gVisor / Firecracker | Stronger (syscall filter / microVM) | gVisor runtime or KVM microVMs | Defense-in-depth upgrade later; more infra to hand off |
| C. nsjail / bubblewrap | Strong, lightweight, no daemon | Linux-only, tool installed | Good prod alt to Docker, but **no Windows dev**, and still host-level |
| D. `resource.setrlimit` + chroot in-process | Weak (no real net isolation; Python escapes) | None | **Insufficient for untrusted code** — rejected as the sandbox |
| E. Separate executor microservice | Same as its backend | A container runtime under it | The clean scale-out; still needs A/B/C beneath |

### Recommendation: Docker container-per-run, behind an executor seam

- **Prod: Docker** (Option A) — a minimal `quantummind-sandbox` image with only the
  Qiskit runtime, run fresh per submission with strict flags (§3). Matches how
  MoleScan was deployed on the GPU box; the hand-off artifact is the image.
- **One internal seam** (`app/core/executor.py`) like the LLM seam: a single
  `run_code(...)` interface with a pluggable backend selected by config
  (`EXECUTOR=docker|subprocess`). Both execution sites call only the seam.

### Honest infra dependency (your Docker/WSL/disk situation)

The secure path **requires a working Docker daemon**. On the dev Windows box that
means Docker Desktop + WSL2, which you've had disk/WSL trouble with. I won't
pretend around it:

- The **`docker` backend is the only secure one**, and it can't run without the
  daemon. WSL2 also has caveats: `--memory` limits need cgroup support (cgroup v2
  in recent WSL2) and `--cpus` needs the daemon's cgroup driver — both work on a
  healthy Docker Desktop but are exactly what breaks when WSL is unhealthy.
- To keep you developing while Docker is down, the seam keeps the **current
  subprocess behavior as an explicitly-insecure, dev-only fallback**
  (`EXECUTOR=subprocess`): it logs a loud warning on every run, and **refuses to
  start when `APP_ENV=production`** (and is gated behind an extra
  `ALLOW_INSECURE_EXECUTOR=true` so it can never be selected by accident). The
  secure default is `EXECUTOR=docker`. This is a deliberate, visible compromise —
  not a second supported mode.
- The **proof-of-done containment tests need a Docker host**. If local Docker is
  unhealthy, run them on any Linux Docker box or in CI (GitHub Actions has Docker)
  — they're gated to skip with a clear message when Docker is absent, just like the
  Phase 1 Neon/Upstash integration tests.
- **No bind mounts.** Code is piped to the container via **stdin** (`docker run -i
  … python -`), not a `-v` volume — this sidesteps the Windows/WSL bind-mount pain
  entirely and leaves no host temp file.

## 3. Enforcement — how each control is applied (Docker backend)

`docker run` is invoked via **async** subprocess (`asyncio.create_subprocess_exec`,
so it doesn't block the event loop) with:

| Control | Mechanism |
|---|---|
| No network | `--network none` |
| Memory cap (OOM-kill) | `--memory 256m --memory-swap 256m` (swap=mem ⇒ no swap escape) |
| CPU cap | `--cpus 0.5` (cgroup quota) |
| Fork/thread bomb | `--pids-limit 64` |
| Wall-clock | host-side `asyncio.wait_for` + `docker run` `--rm`; on timeout, `docker kill` the container |
| Read-only root FS | `--read-only` |
| Ephemeral scratch only | `--tmpfs /tmp:rw,size=64m,noexec,nosuid` |
| Non-root | image `USER 1000`; `--user 1000:1000` |
| No privilege escalation | `--cap-drop ALL --security-opt no-new-privileges` |
| No secrets / no env | **no `-e` / `--env-file`** — the container gets only Docker's default env; the image contains no app code, no `.env`, no DB creds |
| No app / no DB reachable | image has only the Qiskit runtime; `--network none` + no creds ⇒ Neon/Upstash unreachable even if code tries |
| Minimal runtime | image installs only `qiskit`, `qiskit-aer`, `matplotlib`, `pylatexenc` (pinned), nothing else |

- **The circuit-diagram harness moves into the sandbox.** Today `execute.py` wraps
  student code with a matplotlib/qiskit harness that finds `QuantumCircuit`s and
  emits `__CIRCUIT_IMAGE__{base64}__CIRCUIT_IMAGE__` on stdout. That harness runs
  *inside* the container; the executor parses the marker out of stdout. Output
  (text + the base64 PNG) comes back over **stdout only** — no files leave the box.
- **Image build / hand-off:** a new `sandbox/Dockerfile` builds
  `quantummind-sandbox` (`docker build -t quantummind-sandbox sandbox/`). Built
  locally for dev and shipped as the image for the GPU box, mirroring MoleScan.
- **Deployment topology (noted):** the app shells to the host Docker daemon
  (simplest, MoleScan-style). If the app is itself containerized in prod, that
  means mounting the Docker socket — a privilege to call out explicitly — or
  running the sandbox as a **separate executor service** the app calls over HTTP
  (the cleaner horizontal scale-out). Baseline = local daemon; the seam makes the
  service split a later change, not a rewrite.

## 4. The executor seam + migrating both sites

- **New `app/core/executor.py`:** `async def run_code(code: str, *, timeout: float,
  draw: bool = True) -> ExecResult` returning `{success, stdout, stderr,
  circuit_image, duration}`. Backends: `_run_docker(...)` (secure) and
  `_run_subprocess(...)` (the gated dev fallback, lifted from today's code). The
  harness wrapping + marker parsing live here, shared by both sites.
- **`routes/execute.py`:** replace the inline harness/temp-file/`subprocess.run`
  with `await executor.run_code(request.code, timeout=settings.executor_timeout)`
  and map `ExecResult` → the existing `ExecuteResponse` (success/output/error/
  circuit_image/execution_time). The API shape is unchanged, so the frontend
  needs nothing (UI is Phase 5).
- **`agents/code_agent.py`:** the `execute_code` node calls
  `await executor.run_code(state["generated_code"], timeout=settings.executor_timeout,
  draw=False)` and maps to `execution_output` / `execution_error`. The deprecated-
  pattern pre-fix and the single retry stay as they are.
- Both sites stop resolving `$VIRTUAL_ENV` / `sys.executable` and stop touching
  host temp files entirely.
- **Bounded execution concurrency:** containers are heavier than the old
  subprocess; under a class of 100 a burst could exhaust the host. Bound concurrent
  sandbox runs with `EXECUTOR_MAX_CONCURRENCY` (a simple in-process
  `asyncio.Semaphore` for the single-host baseline; can graduate to the Phase-2
  Redis limiter pattern if we split to a shared executor service). Over the limit,
  runs queue briefly then return a clear "executor busy, try again" result — never
  pile up.

## 5. New dependencies / infra

- **No new Python package** for the Docker backend (shell out to the `docker` CLI
  via `asyncio.create_subprocess_exec`). Avoids the docker-SDK + daemon-socket
  dependency in code and keeps the seam thin. (Docker SDK is an option but not
  needed.)
- **New infra:** Docker Engine on the execution host; a `sandbox/Dockerfile` +
  built `quantummind-sandbox` image. Add the image to `docker-compose.dev.yml` as
  a `build`-only entry for convenience (it is not a long-running service — it's run
  per execution).
- **CI:** a `.github/workflows/ci.yml` (Linux runners, Docker preinstalled) builds
  the sandbox image and runs the full test suite incl. the containment tests, so
  the security guarantees are verified on every push.
- **New config / env (`Settings`):** `EXECUTOR` (`docker`|`subprocess`, default
  `docker`), `ALLOW_INSECURE_EXECUTOR` (bool, default false),
  `SANDBOX_IMAGE` (`quantummind-sandbox`), `EXECUTOR_TIMEOUT_SECONDS` (default 30),
  `SANDBOX_MEMORY` (`256m`), `SANDBOX_CPUS` (`0.5`), `SANDBOX_PIDS_LIMIT` (64),
  `SANDBOX_TMPFS_SIZE` (`64m`), `EXECUTOR_MAX_CONCURRENCY` (e.g. 4). `.env` +
  `.env.example` updated (placeholders only).

## 6. Proof-of-done tests

Containment tests need a Docker host; gate the suite to **skip with a clear
message when Docker is unavailable** (like the Neon/Upstash integration tests), so
the unit suite stays infra-free.

**Containment (Docker integration suite):**
1. **Normal Qiskit works** — a Bell circuit returns `success=true`, counts in
   stdout, and a non-empty base64 circuit image.
2. **Network blocked** — code attempting an outbound connection/HTTP fails and is
   returned as a safe error (`success=false`), no host effect.
3. **Infinite loop** — `while True: pass` is killed at the wall-clock limit and
   returns a safe "timed out" result.
4. **Memory bomb** — a large allocation is OOM-killed by `--memory` and returned
   as a safe error, not a host OOM.
5. **Filesystem** — writing outside `/tmp` fails (read-only root); `/tmp` works but
   is ephemeral.
6. **No secrets / no app** — inside the sandbox `os.environ` contains **none** of
   `GROQ_API_KEY` / `DATABASE_URL` / `REDIS_URL` / `TEACHER_PASSWORD`, and
   `import app` fails. (This is the headline regression guard against today's leak.)
7. **Fork/thread bomb** (optional) — hits `--pids-limit`, contained.

**Hermetic unit tests (no Docker):**
- The harness wrapping + `__CIRCUIT_IMAGE__` marker parsing (feed canned stdout →
  correct `ExecResult`).
- **Production-refusal (required proof):** a test asserting that
  `EXECUTOR=subprocess` + `APP_ENV=production` **raises**, and that
  `EXECUTOR=subprocess` without `ALLOW_INSECURE_EXECUTOR` also raises — so "can't
  run insecurely in prod" is proven, not hoped. Enforced fail-fast in the Settings
  validator.

**CI:** a GitHub Actions workflow runs the full suite on Linux runners (Docker is
preinstalled there), so the Docker-gated containment suite actually executes on
every push — an untested sandbox isn't a sandbox.

## 7. Phase boundaries (explicitly NOT here)

- **No auth / GDPR** → Phase 4.
- **No UI** → Phase 5 (the "ran in a sandbox / limit exceeded" presentation; the
  API response shape is unchanged so the current frontend keeps working).
- No change to code *generation* or grading — only *where and how* code runs.

## 8. Proposed commit sequence (on approval)

One logical commit per step; each leaves the app runnable; local only, no push.

1. `feat: sandbox image + executor seam (Docker backend, gated subprocess fallback)`
   — `sandbox/Dockerfile` (minimal, non-root Qiskit image), `app/core/executor.py`
   (`run_code` interface, Docker backend via async subprocess with all §3 flags +
   in-sandbox harness, and the insecure subprocess fallback gated dev-only with a
   prod refusal), config/env, compose build entry. Hermetic unit tests (marker
   parsing + the safety gate). Not yet wired into routes.
2. `refactor: route both execution sites through the executor seam` — `execute.py`
   and `code_agent.py` call `executor.run_code`; remove the inline subprocess,
   host-interpreter resolution, and temp files. API/response shapes unchanged.
3. `test: sandbox containment proof + CI` — the §6 containment suite (skipped
   cleanly when Docker is unavailable locally) plus `.github/workflows/ci.yml` that
   builds the sandbox image and runs the suite on Linux runners, so the security
   tests actually execute on every push.

Awaiting approval before writing any code.
