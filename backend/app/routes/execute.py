# ── app/routes/execute.py ────────────────────────────────────
#
# POST /api/execute
# Runs student Qiskit code through the sandbox seam (app.core.executor) and
# returns stdout + a circuit diagram as a base64 PNG. All isolation/resource
# limits and the circuit-draw harness live in the seam — nothing runs inline here.

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core import executor

router = APIRouter()


class ExecuteRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Qiskit Python code to execute")
    shots: int = Field(default=1024, ge=1, le=8192)


class ExecuteResponse(BaseModel):
    success: bool
    output: str           # stdout from execution
    error: str            # stderr if execution failed
    circuit_image: str    # base64 PNG of circuit diagram (empty if failed)
    execution_time: float # seconds


@router.post("/execute", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    """Execute Qiskit code in the sandbox and return its output + circuit diagram.

    The seam wraps the code with the auto-draw harness, runs it under the
    configured executor (a locked-down container in prod), and returns a safe
    result for any failure/timeout/limit — never an unhandled error.
    """
    result = await executor.run_code(request.code, draw=True)
    return ExecuteResponse(
        success=result.success,
        output=result.stdout,
        error=clean_traceback(result.stderr) if not result.success else "",
        circuit_image=result.circuit_image,
        execution_time=round(result.duration, 2),
    )


def clean_traceback(stderr: str) -> str:
    """Make tracebacks readable for students — the sandbox runs code from stdin,
    so surface it as 'your_code.py' rather than '<stdin>' (or an old temp path)."""
    lines = stderr.split("\n")
    clean = []
    for line in lines:
        line = line.replace("<stdin>", "your_code.py")
        if "tmp" in line.lower() and ".py" in line and "File" in line:
            line = line.replace(line.split('"')[1], "your_code.py") if '"' in line else line
        clean.append(line)
    return "\n".join(clean).strip()
