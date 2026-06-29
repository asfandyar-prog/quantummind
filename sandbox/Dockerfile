# Minimal Qiskit runtime for the code-execution sandbox (Phase 3).
#
# Deliberately contains ONLY the Qiskit runtime — no app code, no secrets, no DB
# drivers. Combined with `docker run` passing no env and --network none, a
# submission's os.environ is clean and the app/DB are unreachable. Code is piped
# in via stdin:  docker run -i ... quantummind-sandbox python -
#
# Build:  docker build -t quantummind-sandbox sandbox/
FROM python:3.12-slim

RUN pip install --no-cache-dir \
    "qiskit==2.3.1" \
    "qiskit-aer==0.17.2" \
    "matplotlib==3.10.8" \
    "pylatexenc==2.10"

# Everything writable must live under the tmpfs /tmp (root FS is mounted read-only
# at runtime). Point HOME and matplotlib's cache there; force the Agg backend.
ENV HOME=/tmp \
    MPLCONFIGDIR=/tmp/mpl \
    MPLBACKEND=Agg \
    PYTHONUNBUFFERED=1

# Non-root user; runtime adds --user 1000:1000 --cap-drop ALL --no-new-privileges.
RUN useradd -m -u 1000 sandbox
USER 1000
WORKDIR /tmp

CMD ["python", "-"]
