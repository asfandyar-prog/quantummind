"""Gate for the sandbox containment tests.

These run the REAL Docker sandbox. They skip with a clear message when Docker (or
the sandbox image) is unavailable — so they skip locally on a box without Docker
but RUN in CI, where the workflow builds the image first. An untested sandbox is
not a sandbox.
"""
import os
import shutil
import subprocess

import pytest

from app.core.config import settings


def _docker_ready():
    if shutil.which("docker") is None:
        return False, "docker CLI not found"
    try:
        subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=20, check=True)
    except Exception as e:
        return False, f"docker daemon not reachable: {e}"
    try:
        subprocess.run(["docker", "image", "inspect", settings.sandbox_image],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, check=True)
    except Exception:
        return False, (f"sandbox image '{settings.sandbox_image}' not built "
                       f"(docker build -t {settings.sandbox_image} sandbox/)")
    return True, ""


DOCKER_OK, SKIP_REASON = _docker_ready()

# CI sets REQUIRE_SANDBOX=1 so a missing Docker daemon or image fails the run
# instead of silently skipping the one suite that proves containment.
if not DOCKER_OK and os.environ.get("REQUIRE_SANDBOX") == "1":
    raise RuntimeError(f"REQUIRE_SANDBOX=1 but the sandbox is unavailable: {SKIP_REASON}")


@pytest.fixture(autouse=True)
def require_docker_sandbox():
    if not DOCKER_OK:
        pytest.skip(f"sandbox containment tests need Docker + image: {SKIP_REASON}")
    previous = settings.executor
    settings.executor = "docker"   # exercise the real container backend
    yield
    settings.executor = previous   # don't leak the backend into later tests
