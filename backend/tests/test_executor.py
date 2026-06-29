"""Phase 3 commit 1: executor seam — hermetic unit tests (no Docker).

Covers harness wrapping, circuit-image marker parsing, and — critically — the
fail-fast gate proving the insecure subprocess executor cannot run in production.
"""
import pytest

from app.core import executor
from app.core.config import Settings


# ── harness wrapping ──────────────────────────────────────────
def test_wrap_draw_includes_code_and_harness():
    prog = executor._wrap("qc = make_bell()", draw=True)
    assert "qc = make_bell()" in prog
    assert "QuantumCircuit" in prog          # the drawing harness is appended
    assert executor._MARKER in prog


def test_wrap_no_draw_is_passthrough():
    assert executor._wrap("print(42)", draw=False) == "print(42)"


# ── circuit-image marker parsing ──────────────────────────────
def test_parse_circuit_extracts_b64_and_cleans_stdout():
    out = f"counts: {{'00': 512}}\n{executor._MARKER}QUJD{executor._MARKER}\ntail"
    clean, b64 = executor._parse_circuit(out)
    assert b64 == "QUJD"
    assert executor._MARKER not in clean
    assert "counts" in clean and "tail" in clean


def test_parse_circuit_empty_marker_returns_no_image():
    out = f"hello\n{executor._MARKER}{executor._MARKER}"
    clean, b64 = executor._parse_circuit(out)
    assert b64 == ""
    assert clean == "hello"


def test_parse_circuit_no_marker():
    clean, b64 = executor._parse_circuit("just output")
    assert b64 == ""
    assert clean == "just output"


# ── fail-fast safety gate (the required production-refusal proof) ──
def test_subprocess_executor_refused_in_production():
    with pytest.raises(Exception) as exc:
        Settings(
            _env_file=None, groq_api_key="k",
            executor="subprocess", app_env="production", allow_insecure_executor=True,
        )
    assert "production" in str(exc.value)


def test_subprocess_executor_requires_opt_in():
    with pytest.raises(Exception):
        Settings(
            _env_file=None, groq_api_key="k",
            executor="subprocess", app_env="development", allow_insecure_executor=False,
        )


def test_subprocess_executor_allowed_in_dev_with_opt_in():
    s = Settings(
        _env_file=None, groq_api_key="k",
        executor="subprocess", app_env="development", allow_insecure_executor=True,
    )
    assert s.executor == "subprocess"


def test_docker_executor_is_fine():
    s = Settings(_env_file=None, groq_api_key="k", executor="docker", app_env="production")
    assert s.executor == "docker"


def test_unknown_executor_rejected():
    with pytest.raises(Exception):
        Settings(_env_file=None, groq_api_key="k", executor="bogus")
