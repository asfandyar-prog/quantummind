# ── app/core/executor.py ─────────────────────────────────────
# The single seam for running student / LLM-generated code. Both execution sites
# (routes/execute.py and agents/code_agent.py) call run_code() — never a raw
# subprocess.
#
# Backends (selected by EXECUTOR):
#   - docker     : a fresh, locked-down container per run (secure; the default).
#   - subprocess : runs on the host (INSECURE). A dev-only fallback, gated by the
#                  Settings validator — forbidden in production, requires
#                  ALLOW_INSECURE_EXECUTOR=true.
#
# Code is piped to the runner via stdin (no bind mounts, no host temp files). The
# circuit-drawing harness runs inside the runner and emits the diagram as a
# base64 marker on stdout, which the executor parses back out.

import asyncio
import logging
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("quantummind.executor")

_MARKER = "__CIRCUIT_IMAGE__"


@dataclass
class ExecResult:
    success: bool
    stdout: str
    stderr: str
    circuit_image: str   # base64 PNG, or ""
    duration: float


# The drawing harness, appended after the user's code (markers baked in once).
_HARNESS_TAIL = f"""
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from qiskit import QuantumCircuit
    _b64 = ''
    _last = None
    for _n, _v in list(locals().items()):
        if isinstance(_v, QuantumCircuit):
            _last = _v
    if _last is not None:
        _fig = _last.draw('mpl', style='iqp', fold=-1)
        _buf = io.BytesIO()
        _fig.savefig(_buf, format='png', dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
        _buf.seek(0)
        _b64 = base64.b64encode(_buf.read()).decode('utf-8')
        plt.close(_fig)
    print("{_MARKER}" + _b64 + "{_MARKER}")
except Exception:
    print("{_MARKER}{_MARKER}")
"""


def _wrap(code: str, draw: bool) -> str:
    """Wrap code with the circuit-drawing harness (draw=True) or run it as-is."""
    if not draw:
        return code
    return "import base64, io\n" + code + "\n" + _HARNESS_TAIL


def _parse_circuit(stdout: str) -> tuple[str, str]:
    """Pull the base64 circuit image out of stdout; return (clean_stdout, b64)."""
    b64 = ""
    if _MARKER in stdout:
        start = stdout.find(_MARKER) + len(_MARKER)
        end = stdout.find(_MARKER, start)
        if end > start:
            b64 = stdout[start:end].strip()
        stdout = "\n".join(l for l in stdout.split("\n") if _MARKER not in l).strip()
    return stdout, b64


_sem: Optional[asyncio.Semaphore] = None


def _semaphore() -> asyncio.Semaphore:
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(settings.executor_max_concurrency)
    return _sem


async def run_code(code: str, *, timeout: Optional[float] = None, draw: bool = True) -> ExecResult:
    """Run code in the configured sandbox. Never raises for code errors — a failed,
    timed-out, or limit-exceeded run returns a safe ExecResult(success=False)."""
    timeout = timeout if timeout is not None else settings.executor_timeout_seconds
    program = _wrap(code, draw)
    async with _semaphore():
        if settings.executor == "docker":
            return await _run_docker(program, timeout)
        logger.warning("INSECURE subprocess executor in use — code runs on the host (dev only).")
        return await _run_subprocess(program, timeout)


# Run a blocking subprocess off the event loop. Uses sync subprocess.run (not
# asyncio.create_subprocess_exec) because the latter needs the Proactor loop on
# Windows, which conflicts with the SelectorEventLoop psycopg requires. to_thread
# keeps it non-blocking and portable; executor_max_concurrency bounds the threads.
def _sync_run(args: list[str], program: str, timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, input=program.encode(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
    )


# ── Docker backend (secure) ───────────────────────────────────

async def _run_docker(program: str, timeout: float) -> ExecResult:
    name = f"qm-sandbox-{uuid.uuid4().hex[:12]}"
    args = [
        "docker", "run", "--rm", "-i", "--name", name,
        "--network", "none",                         # no network
        "--memory", settings.sandbox_memory,         # memory cap (OOM-kill)
        "--memory-swap", settings.sandbox_memory,    # swap == mem ⇒ no swap escape
        "--cpus", str(settings.sandbox_cpus),        # CPU cap
        "--pids-limit", str(settings.sandbox_pids_limit),  # fork/thread bomb
        "--read-only",                               # read-only root FS
        "--tmpfs", f"/tmp:rw,size={settings.sandbox_tmpfs_size},noexec,nosuid",
        "--user", "1000:1000",                       # non-root
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        # NOTE: no -e / --env-file — the container gets none of our secrets.
        settings.sandbox_image, "python", "-",
    ]
    start = time.monotonic()
    try:
        result = await asyncio.to_thread(_sync_run, args, program, timeout)
    except subprocess.TimeoutExpired:
        await asyncio.to_thread(_docker_kill, name)   # authoritative wall-clock enforcement
        return ExecResult(False, "", f"Execution timed out ({timeout:.0f}s).", "", time.monotonic() - start)
    except FileNotFoundError:
        return ExecResult(False, "", "Sandbox unavailable: docker not found on host.", "", time.monotonic() - start)

    duration = time.monotonic() - start
    stdout, b64 = _parse_circuit(result.stdout.decode(errors="replace"))
    return ExecResult(result.returncode == 0, stdout, result.stderr.decode(errors="replace"), b64, duration)


def _docker_kill(name: str) -> None:
    try:
        subprocess.run(["docker", "kill", name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except Exception:
        pass


# ── Subprocess backend (INSECURE — dev only, gated by config) ─

async def _run_subprocess(program: str, timeout: float) -> ExecResult:
    start = time.monotonic()
    try:
        result = await asyncio.to_thread(_sync_run, [sys.executable, "-"], program, timeout)
    except subprocess.TimeoutExpired:
        return ExecResult(False, "", f"Execution timed out ({timeout:.0f}s).", "", time.monotonic() - start)

    duration = time.monotonic() - start
    stdout, b64 = _parse_circuit(result.stdout.decode(errors="replace"))
    return ExecResult(result.returncode == 0, stdout, result.stderr.decode(errors="replace"), b64, duration)
