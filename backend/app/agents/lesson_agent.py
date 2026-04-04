# ── app/agents/lesson_agent.py ───────────────────────────────
#
# LangGraph Lesson Agent
#
# Graph flow for PLAN generation:
#   generate_plan → validate_plan → END
#                       ↙
#                 fix_plan (if invalid JSON)
#
# Graph flow for STEP teaching:
#   generate_step_content → extract_code → validate_code → END
#                                               ↙
#                                        fix_code (if deprecated syntax)
#
# Graph flow for GRADING:
#   analyze_answer → grade → END

import json
import re
from typing import TypedDict, Annotated
import operator

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.core.memory import get_checkpointer


# ════════════════════════════════════════════════════════════════
# STATES
# ════════════════════════════════════════════════════════════════

class PlanState(TypedDict):
    topic:        str
    raw_response: str
    plan:         dict
    retry_count:  int
    error:        str


class StepState(TypedDict):
    topic:        str
    step:         dict
    step_num:     int
    raw_content:  str
    code_blocks:  list[str]
    fixed_code:   list[str]
    code_valid:   bool
    retry_count:  int
    final_content: str


class GradeState(TypedDict):
    question:       str
    correct_answer: str
    student_answer: str
    analysis:       str
    passed:         bool
    feedback:       str


# ════════════════════════════════════════════════════════════════
# LLM
# ════════════════════════════════════════════════════════════════

def get_llm(temperature: float = 0.3) -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=temperature,
    )


# ════════════════════════════════════════════════════════════════
# PLAN GRAPH NODES
# ════════════════════════════════════════════════════════════════

PLAN_PROMPT = """You are an expert quantum computing curriculum designer.

Generate a structured lesson plan with exactly 3-4 steps for the topic provided.

RETURN ONLY VALID JSON — no explanation, no markdown fences, just the JSON object:
{
  "topic": "string",
  "description": "one sentence overview of this topic",
  "steps": [
    {
      "id": 1,
      "title": "short title (3-5 words)",
      "objective": "what student understands after this step",
      "teaching_points": ["point 1", "point 2", "point 3"],
      "check_question": "specific question student must answer",
      "check_answer": "correct answer in 1-3 sentences"
    }
  ]
}

Rules:
- Step 1: always intuition/analogy — NO math, NO code
- Step 2: mathematical formalism using |0⟩ |1⟩ notation
- Step 3: hands-on Qiskit implementation
- Step 4 (optional): synthesis or advanced application
- check_question must have a clear correct answer
- Generate exactly the JSON, nothing else"""


async def generate_plan(state: PlanState) -> dict:
    """Node 1 — Ask LLM to generate a lesson plan as JSON."""
    llm = get_llm(temperature=0.3)
    print(f"[LessonAgent/Plan] Generating plan for: {state['topic']}")

    response = await (llm | StrOutputParser()).ainvoke([
        SystemMessage(content=PLAN_PROMPT),
        HumanMessage(content=f"Generate a lesson plan for: {state['topic']}"),
    ])
    return {"raw_response": response.strip(), "retry_count": state.get("retry_count", 0)}


async def validate_plan(state: PlanState) -> dict:
    """Node 2 — Try to parse the JSON. If invalid, set error for retry."""
    raw = state["raw_response"]

    # Strip markdown fences if present
    if "```" in raw:
        raw = re.sub(r"```(?:json)?\n?", "", raw).strip().rstrip("`").strip()

    try:
        plan = json.loads(raw)
        # Validate required fields
        assert "topic" in plan
        assert "steps" in plan
        assert len(plan["steps"]) >= 2
        for step in plan["steps"]:
            assert "title" in step
            assert "check_question" in step
            assert "check_answer" in step

        print(f"[LessonAgent/Plan] Valid plan: {len(plan['steps'])} steps")
        return {"plan": plan, "error": ""}

    except Exception as e:
        print(f"[LessonAgent/Plan] Invalid JSON: {e}")
        return {"error": str(e), "plan": {}}


async def fix_plan(state: PlanState) -> dict:
    """Node 3 — Ask LLM to fix its invalid JSON output."""
    llm = get_llm(temperature=0.1)
    count = state.get("retry_count", 0) + 1
    print(f"[LessonAgent/Plan] Fixing plan — attempt {count}")

    fix_prompt = f"""Your previous response was not valid JSON. Error: {state['error']}

Previous response:
{state['raw_response']}

Return ONLY the corrected JSON object. No explanation, no fences."""

    response = await (llm | StrOutputParser()).ainvoke([
        HumanMessage(content=fix_prompt)
    ])
    return {"raw_response": response.strip(), "retry_count": count}


def plan_is_valid(state: PlanState) -> str:
    if state.get("plan") and not state.get("error"):
        return "done"
    if state.get("retry_count", 0) >= 2:
        return "done"  # give up after 2 retries
    return "fix"


# ── Plan Graph ─────────────────────────────────────────────────
def build_plan_graph():
    g = StateGraph(PlanState)
    g.add_node("generate_plan", generate_plan)
    g.add_node("validate_plan", validate_plan)
    g.add_node("fix_plan",      fix_plan)
    g.set_entry_point("generate_plan")
    g.add_edge("generate_plan", "validate_plan")
    g.add_conditional_edges("validate_plan", plan_is_valid, {"fix": "fix_plan", "done": END})
    g.add_edge("fix_plan", "validate_plan")
    return g.compile()


_plan_graph = None
def get_plan_graph():
    global _plan_graph
    if _plan_graph is None:
        _plan_graph = build_plan_graph()
    return _plan_graph


# ════════════════════════════════════════════════════════════════
# STEP TEACHING GRAPH NODES
# ════════════════════════════════════════════════════════════════

STEP_PROMPT = """You are QuantumMind's Guided Learning Agent — an expert quantum computing tutor.

Teaching Step {step_num}: "{step_title}"
Topic: {topic}
Objective: {objective}

Teaching points to cover:
{teaching_points}

RULES:
1. Use **bold** for every key term introduced
2. Use |0⟩ |1⟩ Dirac notation for quantum states
3. Start with intuition/analogy, then go deeper
4. For code steps use ONLY modern Qiskit syntax inside ```python fences:
   CORRECT: from qiskit_aer import AerSimulator; sim = AerSimulator(); sim.run(qc, shots=1024)
   WRONG:   Aer.get_backend(), execute() — these are deprecated, never use them
5. End with exactly: ✓ Ready for the check question?

Stay strictly within the teaching points. Do not reveal the check question."""


async def generate_step_content(state: StepState) -> dict:
    """Node 1 — Generate teaching content for this step."""
    llm = get_llm(temperature=0.6)
    step = state["step"]
    points = "\n".join([f"  • {p}" for p in step.get("teaching_points", [])])

    prompt = STEP_PROMPT.format(
        step_num=state["step_num"],
        step_title=step["title"],
        topic=state["topic"],
        objective=step["objective"],
        teaching_points=points,
    )

    print(f"[LessonAgent/Step] Generating content for step {state['step_num']}: {step['title']}")
    content = await (llm | StrOutputParser()).ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=f"Teach step {state['step_num']}: {step['title']}"),
    ])
    return {"raw_content": content, "retry_count": state.get("retry_count", 0)}


async def extract_code(state: StepState) -> dict:
    """Node 2 — Extract all code blocks from the content."""
    content = state["raw_content"]
    blocks  = re.findall(r"```(?:python)?\n(.*?)```", content, re.DOTALL)
    cleaned = [b.strip() for b in blocks]
    print(f"[LessonAgent/Step] Extracted {len(cleaned)} code blocks")
    return {"code_blocks": cleaned}


async def validate_code(state: StepState) -> dict:
    """
    Node 3 — Check if code uses deprecated Qiskit patterns.
    If found, mark as invalid so fix_code node runs.
    """
    deprecated = [
        "Aer.get_backend",
        "from qiskit import Aer",
        "execute(qc",
        "execute(circuit",
    ]
    blocks = state.get("code_blocks", [])
    is_valid = True

    for block in blocks:
        for pattern in deprecated:
            if pattern in block:
                print(f"[LessonAgent/Step] Deprecated pattern found: {pattern}")
                is_valid = False
                break

    return {"code_valid": is_valid}


async def fix_code(state: StepState) -> dict:
    """
    Node 4 — Use LLM to rewrite deprecated code with modern Qiskit syntax.
    Also applies deterministic replacements for common patterns.
    """
    llm = get_llm(temperature=0.1)
    count = state.get("retry_count", 0) + 1
    print(f"[LessonAgent/Step] Fixing code — attempt {count}")

    fixed_blocks = []
    for block in state.get("code_blocks", []):
        fixed = await (llm | StrOutputParser()).ainvoke([
            SystemMessage(content="""You are a Qiskit code modernizer.
Rewrite this code using ONLY modern Qiskit 1.x syntax.
- Replace: from qiskit import Aer → from qiskit_aer import AerSimulator
- Replace: Aer.get_backend(...) → AerSimulator()
- Replace: execute(qc, sim, shots=N).result() → sim.run(qc, shots=N).result()
- Keep all other code identical
Return ONLY the corrected code, no explanation, no fences."""),
            HumanMessage(content=block),
        ])
        fixed_blocks.append(fixed.strip())

    # Rebuild content with fixed code blocks
    content   = state["raw_content"]
    originals = re.findall(r"```(?:python)?\n(.*?)```", content, re.DOTALL)
    for orig, fixed in zip(originals, fixed_blocks):
        content = content.replace(f"```python\n{orig}```", f"```python\n{fixed}\n```", 1)
        content = content.replace(f"```\n{orig}```", f"```python\n{fixed}\n```", 1)

    return {
        "raw_content": content,
        "fixed_code":  fixed_blocks,
        "code_blocks": fixed_blocks,
        "retry_count": count,
        "code_valid":  True,
    }


async def assemble_step(state: StepState) -> dict:
    """Node 5 — Finalize the content as the output."""
    print(f"[LessonAgent/Step] Step content ready")
    return {"final_content": state["raw_content"]}


def code_needs_fix(state: StepState) -> str:
    if not state.get("code_valid", True) and state.get("retry_count", 0) < 2:
        return "fix"
    return "done"


# ── Step Graph ─────────────────────────────────────────────────
def build_step_graph():
    g = StateGraph(StepState)
    g.add_node("generate_step_content", generate_step_content)
    g.add_node("extract_code",          extract_code)
    g.add_node("validate_code",         validate_code)
    g.add_node("fix_code",              fix_code)
    g.add_node("assemble_step",         assemble_step)
    g.set_entry_point("generate_step_content")
    g.add_edge("generate_step_content", "extract_code")
    g.add_edge("extract_code",          "validate_code")
    g.add_conditional_edges("validate_code", code_needs_fix, {"fix": "fix_code", "done": "assemble_step"})
    g.add_edge("fix_code",              "extract_code")  # re-validate after fix
    g.add_edge("assemble_step",         END)
    return g.compile()


_step_graph = None
def get_step_graph():
    global _step_graph
    if _step_graph is None:
        _step_graph = build_step_graph()
    return _step_graph


# ════════════════════════════════════════════════════════════════
# GRADING GRAPH NODES
# ════════════════════════════════════════════════════════════════

async def analyze_answer(state: GradeState) -> dict:
    """Node 1 — Analyze the student's answer before grading."""
    llm = get_llm(temperature=0.0)

    analysis = await (llm | StrOutputParser()).ainvoke([
        HumanMessage(content=f"""Compare these two answers about quantum computing.

Question: {state['question']}
Correct answer: {state['correct_answer']}
Student answer: {state['student_answer']}

Does the student's answer capture the core concept?
Write one sentence analysis.""")
    ])
    print(f"[LessonAgent/Grade] Analysis: {analysis[:80]}")
    return {"analysis": analysis}


async def grade(state: GradeState) -> dict:
    """Node 2 — Grade based on analysis. Be generous with partial credit."""
    llm = get_llm(temperature=0.0)

    response = await (llm | StrOutputParser()).ainvoke([
        HumanMessage(content=f"""Grade a student's quantum computing answer.

Question: {state['question']}
Correct answer: {state['correct_answer']}
Student answer: {state['student_answer']}
Analysis: {state['analysis']}

Be generous — accept answers that capture the core concept even with different wording.
Return ONLY valid JSON:
{{"passed": true or false, "feedback": "one encouraging sentence"}}""")
    ])

    # Parse JSON
    try:
        clean = re.sub(r"```(?:json)?\n?", "", response).strip().rstrip("`").strip()
        result = json.loads(clean)
        passed   = bool(result.get("passed", False))
        feedback = str(result.get("feedback", "Good effort!"))
    except:
        passed   = True
        feedback = "Good effort! Let's continue."

    print(f"[LessonAgent/Grade] Result: {'PASS' if passed else 'FAIL'}")
    return {"passed": passed, "feedback": feedback}


# ── Grade Graph ────────────────────────────────────────────────
def build_grade_graph():
    g = StateGraph(GradeState)
    g.add_node("analyze_answer", analyze_answer)
    g.add_node("grade",          grade)
    g.set_entry_point("analyze_answer")
    g.add_edge("analyze_answer", "grade")
    g.add_edge("grade",          END)
    return g.compile()


_grade_graph = None
def get_grade_graph():
    global _grade_graph
    if _grade_graph is None:
        _grade_graph = build_grade_graph()
    return _grade_graph


# ════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE — same signatures as before
# ════════════════════════════════════════════════════════════════

async def generate_lesson_plan(topic: str) -> dict:
    """Run the plan graph and return the lesson plan."""
    initial: PlanState = {
        "topic":        topic,
        "raw_response": "",
        "plan":         {},
        "retry_count":  0,
        "error":        "",
    }
    result = await get_plan_graph().ainvoke(initial)
    plan = result.get("plan", {})

    if not plan:
        return _fallback_plan(topic)
    return plan


async def teach_step(topic: str, step: dict, step_num: int) -> str:
    """Run the step graph and return validated, clean teaching content."""
    initial: StepState = {
        "topic":         topic,
        "step":          step,
        "step_num":      step_num,
        "raw_content":   "",
        "code_blocks":   [],
        "fixed_code":    [],
        "code_valid":    True,
        "retry_count":   0,
        "final_content": "",
    }
    result = await get_step_graph().ainvoke(initial)
    return result.get("final_content", "Failed to generate content.")


async def grade_answer(question: str, correct_answer: str, student_answer: str) -> dict:
    """Run the grade graph and return pass/fail + feedback."""
    initial: GradeState = {
        "question":       question,
        "correct_answer": correct_answer,
        "student_answer": student_answer,
        "analysis":       "",
        "passed":         False,
        "feedback":       "",
    }
    result = await get_grade_graph().ainvoke(initial)
    return {
        "passed":   result.get("passed", False),
        "feedback": result.get("feedback", "Good effort!"),
    }


def _fallback_plan(topic: str) -> dict:
    return {
        "topic": topic,
        "description": f"A structured introduction to {topic}.",
        "steps": [
            {"id": 1, "title": "Intuition & Analogy", "objective": f"Build intuition for {topic}.", "teaching_points": [f"What is {topic}?", "Classical vs quantum comparison"], "check_question": f"In your own words, what is {topic}?", "check_answer": f"{topic} is a fundamental quantum computing concept."},
            {"id": 2, "title": "Mathematical Formalism", "objective": "Understand the math.", "teaching_points": ["Dirac notation", "State vectors"], "check_question": "What notation do we use for quantum states?", "check_answer": "Dirac (bra-ket) notation, e.g. |0⟩ and |1⟩."},
            {"id": 3, "title": "Qiskit Implementation", "objective": "Implement using Qiskit.", "teaching_points": ["Circuit construction", "AerSimulator execution"], "check_question": "Which class do we use to simulate Qiskit circuits locally?", "check_answer": "AerSimulator from qiskit_aer."},
        ],
    }