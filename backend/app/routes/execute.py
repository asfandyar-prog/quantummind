# ── app/routes/execute.py ────────────────────────────────────
#
# POST /api/execute
# Runs student Qiskit code in a subprocess.
# Returns: stdout output + circuit diagram as base64 PNG.

import os
import sys
import subprocess
import tempfile
import base64
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
    """
    Execute Qiskit code and return results + circuit diagram.

    The code is wrapped in a harness that:
    1. Runs the student's code normally
    2. Finds any QuantumCircuit objects and draws them
    3. Returns the diagram as base64 PNG

    This means students don't need to add drawing code themselves —
    it happens automatically after their code runs.
    """
    # Wrap student code in a harness that auto-draws circuits
    harness = f'''
import sys
import json
import base64
import io

# ── Student code ──────────────────────────────────────────────
{request.code}

# ── Auto circuit drawing harness ──────────────────────────────
# After student code runs, find any QuantumCircuit objects
# in the local scope and draw the last one found.
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend — no GUI window
    import matplotlib.pyplot as plt
    from qiskit import QuantumCircuit

    circuit_b64 = ""
    last_circuit = None

    # Search all local variables for QuantumCircuit instances
    for var_name, var_value in list(locals().items()):
        if isinstance(var_value, QuantumCircuit):
            last_circuit = var_value

    if last_circuit is not None:
        fig = last_circuit.draw('mpl', style='iqp', fold=-1)
        # fold=-1 means never fold — show full circuit on one line

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buf.seek(0)
        circuit_b64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)

    # Print circuit image as a special marker line
    # The parent process reads this line to extract the image
    print(f"__CIRCUIT_IMAGE__{{circuit_b64}}__CIRCUIT_IMAGE__")

except Exception as draw_err:
    print(f"__CIRCUIT_IMAGE____CIRCUIT_IMAGE__")  # empty = no diagram
'''

    # Resolve venv Python
    venv = os.environ.get('VIRTUAL_ENV', '')
    if venv:
        python_exe = os.path.join(venv, 'Scripts', 'python.exe') if sys.platform == 'win32' \
                     else os.path.join(venv, 'bin', 'python')
        if not os.path.exists(python_exe):
            python_exe = sys.executable
    else:
        python_exe = sys.executable

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.py', delete=False, encoding='utf-8'
    ) as f:
        f.write(harness)
        tmp_path = f.name

    import time
    start = time.time()

    try:
        result = subprocess.run(
            [python_exe, tmp_path],
            capture_output=True,
            text=True,
            timeout=45,
        )
        elapsed = round(time.time() - start, 2)

        if result.returncode != 0:
            return ExecuteResponse(
                success=False,
                output="",
                error=clean_traceback(result.stderr),
                circuit_image="",
                execution_time=elapsed,
            )

        # Extract circuit image from output
        stdout     = result.stdout
        circuit_b64 = ""

        marker_start = "__CIRCUIT_IMAGE__"
        marker_end   = "__CIRCUIT_IMAGE__"

        if marker_start in stdout:
            start_idx = stdout.find(marker_start) + len(marker_start)
            end_idx   = stdout.find(marker_end, start_idx)
            if end_idx > start_idx:
                circuit_b64 = stdout[start_idx:end_idx].strip()

            # Remove the marker line from displayed output
            lines = stdout.split('\n')
            clean_lines = [l for l in lines if marker_start not in l]
            stdout = '\n'.join(clean_lines).strip()

        return ExecuteResponse(
            success=True,
            output=stdout,
            error="",
            circuit_image=circuit_b64,
            execution_time=elapsed,
        )

    except subprocess.TimeoutExpired:
        return ExecuteResponse(
            success=False,
            output="",
            error="Execution timed out (45 seconds). Check for infinite loops.",
            circuit_image="",
            execution_time=45.0,
        )
    except Exception as e:
        return ExecuteResponse(
            success=False,
            output="",
            error=str(e),
            circuit_image="",
            execution_time=0.0,
        )
    finally:
        os.unlink(tmp_path)


def clean_traceback(stderr: str) -> str:
    """
    Makes Python tracebacks more readable for students.
    Removes the temp file path which is confusing noise.
    """
    lines = stderr.split('\n')
    clean = []
    for line in lines:
        # Remove the temp file reference from traceback
        if 'tmp' in line.lower() and '.py' in line and 'File' in line:
            line = line.replace(line.split('"')[1], 'your_code.py') if '"' in line else line
        clean.append(line)
    return '\n'.join(clean).strip()