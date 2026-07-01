"""Gate for the sandbox containment tests.

These run the REAL Docker sandbox. They skip with a clear message when Docker (or
the sandbox image) is unavailable — so they skip locally on a box without Docker
but RUN in CI, where the workflow builds the image first. An untested sandbox is
not a sandbox.
"""
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


@pytest.fixture(autouse=True)
def require_docker_sandbox():
    if not DOCKER_OK:
        pytest.skip(f"sandbox containment tests need Docker + image: {SKIP_REASON}")
    settings.executor = "docker"   # exercise the real container backend
    yield
