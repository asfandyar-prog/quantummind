"""Phase 3 commit 3: sandbox containment proof (real Docker).

Each test asserts a class of malicious/runaway submission is CONTAINED and returns
a safe result, and that a normal Qiskit circuit still works. Skipped locally when
Docker is absent (see conftest); RUN in CI on Linux runners.
"""
import asyncio

from app.core import executor


def _run(code: str, *, draw: bool = False, timeout: float = 30.0):
    return asyncio.run(executor.run_code(code, draw=draw, timeout=timeout))


def test_normal_circuit_runs_and_draws():
    code = (
        "from qiskit import QuantumCircuit\n"
        "from qiskit_aer import AerSimulator\n"
        "qc = QuantumCircuit(2, 2)\n"
        "qc.h(0); qc.cx(0, 1); qc.measure([0, 1], [0, 1])\n"
        "print(AerSimulator().run(qc, shots=128).result().get_counts())\n"
    )
    r = _run(code, draw=True, timeout=60)
    assert r.success, r.stderr
    assert "{" in r.output and "}" in r.output       # a counts dict was printed
    assert len(r.circuit_image) > 100                # a real base64 PNG diagram


def test_network_is_blocked():
    code = (
        "import socket\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=5)\n"
        "    print('NETWORK_OK')\n"
        "except OSError:\n"
        "    print('NETWORK_BLOCKED')\n"
    )
    r = _run(code, timeout=30)
    assert r.success                                  # the code ran; the network didn't
    assert "NETWORK_BLOCKED" in r.output
    assert "NETWORK_OK" not in r.output


def test_infinite_loop_is_killed():
    r = _run("while True:\n    pass\n", timeout=4)
    assert not r.success
    assert "timed out" in r.stderr.lower()
    assert r.duration < 15                            # killed promptly, not hung


def test_memory_bomb_is_contained():
    # 1 GiB allocation under a 256m cap → OOM-killed, not a host OOM.
    code = "x = bytearray(1024 * 1024 * 1024)\nprint('ALLOCATED', len(x))\n"
    r = _run(code, timeout=30)
    assert not r.success
    assert "ALLOCATED" not in r.output


def test_filesystem_is_read_only_except_tmp():
    code = (
        "res = {}\n"
        "try:\n"
        "    open('/evil.txt', 'w').write('x'); res['root'] = 'ALLOWED'\n"
        "except OSError:\n"
        "    res['root'] = 'BLOCKED'\n"
        "try:\n"
        "    open('/tmp/ok.txt', 'w').write('x'); res['tmp'] = 'ALLOWED'\n"
        "except OSError:\n"
        "    res['tmp'] = 'BLOCKED'\n"
        "print(res)\n"
    )
    r = _run(code, timeout=30)
    assert r.success, r.stderr
    assert "'root': 'BLOCKED'" in r.output            # read-only root FS
    assert "'tmp': 'ALLOWED'" in r.output             # ephemeral writable /tmp


def test_no_secrets_or_app_in_sandbox():
    # The headline regression guard against today's env leak.
    code = (
        "import os\n"
        "secret_keys = ['GROQ_API_KEY', 'LLM_API_KEY', 'DATABASE_URL', 'REDIS_URL', 'TEACHER_PASSWORD']\n"
        "leaked = [k for k in secret_keys if os.environ.get(k)]\n"
        "print('LEAKED:', leaked)\n"
        "try:\n"
        "    import app\n"
        "    print('APP_IMPORTABLE')\n"
        "except ImportError:\n"
        "    print('APP_ABSENT')\n"
    )
    r = _run(code, timeout=30)
    assert r.success, r.stderr
    assert "LEAKED: []" in r.output                   # no secrets reach the sandbox
    assert "APP_ABSENT" in r.output                   # app code is not present
