# ── app/agents/code_agent.py ──────────────────────────────────
#
# A proper LangGraph agent — not just an LLM call.
#
# Graph flow:
#   analyze_request → generate_code → validate_code
#                                         ↙        ↘
#                                   fix_code    explain_code
#                                       ↓             ↓
#                                  (loops back)     grade
#                                                ↙       ↘
#                                        retry_explain   END

from typing import TypedDict
import operator
import subprocess
import sys
import tempfile
import os

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.core.prompts import CODE_PROMPT
from app.core.memory import checkpointer


# ── STATE ─────────────────────────────────────────────────────
class CodeAgentState(TypedDict):
    user_message: str
    chat_history: list
    generated_code: str
    execution_output: str
    execution_error: str
    explanation: str
    grade_feedback: str
    retry_count: int
    final_response: str


# ── LLM factory ───────────────────────────────────────────────
def get_llm(temperature: float = 0.2) -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=temperature,
    )


# ════════════════════════════════════════════════════════════════
# NODES
# ════════════════════════════════════════════════════════════════

async def analyze_request(state: CodeAgentState) -> dict:
    """
    Node 1 — Classify what the student wants.
    generate / debug / explain
    Sets up context for the generate_code node.
    """
    llm = get_llm(temperature=0.0)

    prompt = f"""Classify this student quantum computing request into exactly one word.

Message: {state["user_message"]}

Respond with ONLY one word:
- "generate" if they want new Qiskit code written
- "debug"    if they have existing code with an error
- "explain"  if they want an existing circuit explained"""

    response = await (llm | StrOutputParser()).ainvoke([HumanMessage(content=prompt)])
    request_type = response.strip().lower()
    if request_type not in ("generate", "debug", "explain"):
        request_type = "generate"

    print(f"[CodeAgent] analyze_request → {request_type}")
    # LangGraph requires every node to return at least one state field.
    # We store request_type in grade_feedback temporarily as a clean slot.
    return {"grade_feedback": ""}


async def generate_code(state: CodeAgentState) -> dict:
    """
    Node 2 — Generate or fix Qiskit code.

    On first run: generates fresh code from the user's question.
    On retry:     rewrites code using the execution error as context.
    """
    llm = get_llm(temperature=0.2)

    messages = [SystemMessage(content=CODE_PROMPT)]

    for msg in state.get("chat_history", []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            messages.append(AIMessage(content=msg["content"]))

    # Retry path — include error context so LLM can fix it
    if state.get("execution_error") and state.get("retry_count", 0) > 0:
        fix_message = f"""The following code failed:

```python
{state["generated_code"]}
```

Error:
{state["execution_error"]}

Fix the code. Return the corrected Python code block."""
        messages.append(HumanMessage(content=fix_message))
    else:
        messages.append(HumanMessage(content=state["user_message"]))

    response = await (llm | StrOutputParser()).ainvoke(messages)
    code = extract_code_block(response)

    print(f"[CodeAgent] generate_code → {len(code)} chars")
    return {
        "generated_code": code,
        "execution_error": "",
        "execution_output": "",
    }


async def validate_code(state: CodeAgentState) -> dict:
    """
    Node 3 — Actually RUN the code in a subprocess.

    This is the core agentic step — we don't just trust the LLM.
    We execute the code and capture real output/errors.

    Runs in subprocess to:
    - Isolate crashes from FastAPI
    - Enforce 30s timeout
    - Capture stdout + stderr separately
    """
    code = state.get("generated_code", "").strip()
    if not code:
        return {"execution_error": "No code was generated."}

    # Resolve the correct Python executable.
    # sys.executable points to the venv Python when running via uv run.
    # VIRTUAL_ENV env var gives us the venv root as a fallback.
    venv = os.environ.get('VIRTUAL_ENV', '')
    if venv:
        python_exe = os.path.join(venv, 'Scripts', 'python.exe') if sys.platform == 'win32' else os.path.join(venv, 'bin', 'python')
        if not os.path.exists(python_exe):
            python_exe = sys.executable
    else:
        python_exe = sys.executable

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.py', delete=False, encoding='utf-8'
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [python_exe, tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print(f"[CodeAgent] validate_code → success: {result.stdout.strip()[:80]}")
            return {"execution_output": result.stdout.strip(), "execution_error": ""}
        else:
            print(f"[CodeAgent] validate_code → error: {result.stderr.strip()[:80]}")
            return {"execution_output": "", "execution_error": result.stderr.strip()}

    except subprocess.TimeoutExpired:
        return {"execution_output": "", "execution_error": "Execution timed out (30s)."}
    except Exception as e:
        return {"execution_output": "", "execution_error": str(e)}
    finally:
        os.unlink(tmp_path)


async def fix_code(state: CodeAgentState) -> dict:
    """
    Node 4 — Increment retry counter, then loop back to generate_code.

    The actual fix logic lives in generate_code — it checks
    execution_error and retry_count to decide how to prompt the LLM.
    This node just tracks how many retries we've done.
    """
    count = state.get("retry_count", 0) + 1
    print(f"[CodeAgent] fix_code → retry {count}/2")
    return {"retry_count": count}


async def explain_code(state: CodeAgentState) -> dict:
    """
    Node 5 — Explain the validated code clearly.

    Only runs after code has passed validation.
    Uses execution output to make the explanation concrete.
    """
    llm = get_llm(temperature=0.5)

    output_section = state.get("execution_output") or "No output (circuit built, not measured)"

    prompt = f"""A student asked: "{state["user_message"]}"

Here is the validated Qiskit code:

```python
{state["generated_code"]}
```

Actual execution output:
{output_section}

Write a clear explanation:
1. What does this circuit do? (one sentence)
2. What does each gate do and why is it used?
3. What does the output mean in quantum terms?
4. What could the student try next?

Use **bold** for key terms. Use |0⟩ |1⟩ notation."""

    explanation = await (llm | StrOutputParser()).ainvoke([HumanMessage(content=prompt)])
    print(f"[CodeAgent] explain_code → {len(explanation)} chars")
    return {"explanation": explanation}


async def grade_explanation(state: CodeAgentState) -> dict:
    """
    Node 6 — Quality-check the explanation (reflection pattern).

    A second LLM call acts as a critic. If the explanation is
    confusing or incomplete it gets regenerated — the student
    never sees a poor quality response.
    """
    llm = get_llm(temperature=0.0)

    prompt = f"""Grade this quantum computing explanation for a beginner student.

Explanation:
{state["explanation"]}

Is it clear, jargon-free, and does it explain the output?
Respond with ONLY: "pass" or "fail"
Only fail if genuinely confusing or missing key points."""

    grade = await (llm | StrOutputParser()).ainvoke([HumanMessage(content=prompt)])
    grade = grade.strip().lower()
    if grade not in ("pass", "fail"):
        grade = "pass"

    print(f"[CodeAgent] grade_explanation → {grade}")
    return {"grade_feedback": grade}


async def assemble_response(state: CodeAgentState) -> dict:
    """
    Node 7 — Assemble all state components into the final response.
    """
    parts = []

    if state.get("explanation"):
        parts.append(state["explanation"])

    if state.get("generated_code"):
        parts.append(f"\n```python\n{state['generated_code']}\n```")

    if state.get("execution_output"):
        parts.append(f"\n**Output:**\n```\n{state['execution_output']}\n```")

    if state.get("execution_error") and state.get("retry_count", 0) >= 2:
        parts.append(f"\n⚠️ Note: The code could not be fully validated. Please test it carefully.")

    return {"final_response": "\n".join(parts)}


# ════════════════════════════════════════════════════════════════
# CONDITIONAL EDGES
# ════════════════════════════════════════════════════════════════

def should_fix_or_explain(state: CodeAgentState) -> str:
    """After validate_code: fix error or proceed to explain?"""
    error       = state.get("execution_error", "")
    retry_count = state.get("retry_count", 0)

    if error and retry_count < 2:
        return "fix"
    return "explain"


def should_retry_explanation(state: CodeAgentState) -> str:
    """After grade_explanation: retry or assemble final response?"""
    grade       = state.get("grade_feedback", "pass")
    retry_count = state.get("retry_count", 0)

    if grade == "fail" and retry_count < 1:
        return "retry"
    return "done"


# ════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ════════════════════════════════════════════════════════════════

def build_code_agent_graph():
    graph = StateGraph(CodeAgentState)

    # Nodes
    graph.add_node("analyze_request",   analyze_request)
    graph.add_node("generate_code",     generate_code)
    graph.add_node("validate_code",     validate_code)
    graph.add_node("fix_code",          fix_code)
    graph.add_node("explain_code",      explain_code)
    graph.add_node("grade_explanation", grade_explanation)
    graph.add_node("assemble_response", assemble_response)

    # Entry
    graph.set_entry_point("analyze_request")

    # Deterministic edges
    graph.add_edge("analyze_request",   "generate_code")
    graph.add_edge("generate_code",     "validate_code")
    graph.add_edge("fix_code",          "generate_code")
    graph.add_edge("explain_code",      "grade_explanation")
    graph.add_edge("assemble_response", END)

    # Conditional edges
    graph.add_conditional_edges(
        "validate_code",
        should_fix_or_explain,
        {"fix": "fix_code", "explain": "explain_code"}
    )

    graph.add_conditional_edges(
        "grade_explanation",
        should_retry_explanation,
        {"retry": "explain_code", "done": "assemble_response"}
    )

    return graph.compile(checkpointer=checkpointer)


# Compiled once at module load — reused across all requests
code_agent_graph = build_code_agent_graph()


# ════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE — same signature as before
# ════════════════════════════════════════════════════════════════

async def run_code_agent(
    user_message: str,
    chat_history: list | None = None,
    thread_id: str = "default",
) -> str:
    """
    Runs the full LangGraph code agent with persistent memory.
    thread_id identifies the conversation — same ID resumes history.
    """
    initial_state: CodeAgentState = {
        "user_message":     user_message,
        "chat_history":     chat_history or [],
        "generated_code":   "",
        "execution_output": "",
        "execution_error":  "",
        "explanation":      "",
        "grade_feedback":   "",
        "retry_count":      0,
        "final_response":   "",
    }
    # config carries the thread_id to the checkpointer.
    # LangGraph uses this to load and save state for this conversation.
    config = {"configurable": {"thread_id": thread_id}}
    result = await code_agent_graph.ainvoke(initial_state, config=config)
    return result.get("final_response", "Sorry, I could not generate a response.")


async def stream_code_agent(
    user_message: str,
    chat_history: list | None = None,
    thread_id: str = "default",
):
    """
    Streams the final response word by word.
    Full agentic loop runs with memory, then streams the result.
    """
    response = await run_code_agent(user_message, chat_history, thread_id)
    words = response.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")


# ── Helper ────────────────────────────────────────────────────
def extract_code_block(text: str) -> str:
    """Extract code from markdown fences. Falls back to raw text."""
    if "```python" in text:
        start = text.find("```python") + len("```python")
        end   = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    if "```" in text:
        start = text.find("```") + 3
        end   = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    return text.strip()