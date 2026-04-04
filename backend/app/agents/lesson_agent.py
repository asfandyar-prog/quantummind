# ── app/agents/lesson_agent.py ───────────────────────────────
# Performance: 1 LLM call per operation + cache for lesson plans
# Plan cache: same topic = same plan, cache for 1 hour

import json
import re
from typing import TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from app.core.config import settings
from app.core.cache import cache


def get_llm(temperature: float = 0.2) -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=temperature,
    )


# ── Deterministic code sanitizer ──────────────────────────────
DEPRECATED_PATTERNS = [
    ("from qiskit import Aer, execute",   "from qiskit_aer import AerSimulator"),
    ("from qiskit import Aer",            "from qiskit_aer import AerSimulator"),
    ("from qiskit import execute, ",      "from qiskit import "),
    ("from qiskit import execute",        ""),
    ("Aer.get_backend('aer_simulator')",  "AerSimulator()"),
    ("Aer.get_backend('qasm_simulator')", "AerSimulator()"),
    ("execute(qc, backend=sim, shots=1024).result()", "sim.run(qc, shots=1024).result()"),
    ("execute(qc, sim, shots=1024).result()",         "sim.run(qc, shots=1024).result()"),
    ("execute(qc, backend=sim).result()",             "sim.run(qc, shots=1024).result()"),
    ("execute(qc, sim).result()",                     "sim.run(qc, shots=1024).result()"),
]

def sanitize_code(code: str) -> str:
    for old, new in DEPRECATED_PATTERNS:
        code = code.replace(old, new)
    if "AerSimulator()" in code and "from qiskit_aer import AerSimulator" not in code:
        code = "from qiskit_aer import AerSimulator\n" + code
    return code

def sanitize_content(content: str) -> str:
    parts = re.split(r"(```(?:python)?\n.*?```)", content, flags=re.DOTALL)
    result = []
    for part in parts:
        if part.startswith("```"):
            lang_match = re.match(r"```(\w*)\n", part)
            lang = lang_match.group(1) if lang_match else ""
            code = re.sub(r"```\w*\n", "", part).rstrip("`").strip()
            result.append(f"```{lang}\n{sanitize_code(code)}\n```")
        else:
            result.append(part)
    return "".join(result)


# ════════════════════════════════════════════════════════════════
# PLAN GRAPH — 1 LLM call + cache
# ════════════════════════════════════════════════════════════════

class PlanState(TypedDict):
    topic: str
    plan:  dict

PLAN_PROMPT = """You are an expert quantum computing curriculum designer.

<task>
Generate a lesson plan for the given topic.
Return ONLY a JSON object — no explanation, no markdown fences.
</task>

<format>
{
  "topic": "string",
  "description": "one sentence overview",
  "steps": [
    {
      "id": 1,
      "title": "3-5 word title",
      "objective": "what student learns",
      "teaching_points": ["point 1", "point 2", "point 3"],
      "check_question": "specific verifiable question",
      "check_answer": "correct answer in 1-2 sentences"
    }
  ]
}
</format>

<rules>
- Exactly 3-4 steps
- Step 1: intuition/analogy only — NO math, NO code
- Step 2: mathematical formalism with |0⟩ |1⟩ notation
- Step 3: Qiskit implementation using AerSimulator (modern syntax)
- Step 4 optional: real-world application
- check_question must have a clear correct answer
</rules>"""

async def generate_plan_node(state: PlanState) -> dict:
    # Check cache first — lesson plans are expensive and deterministic
    cached = cache.get("plan", state["topic"])
    if cached:
        print(f"[LessonAgent/Plan] Cache hit for: {state['topic']}")
        return {"plan": json.loads(cached)}

    llm = get_llm(temperature=0.2)
    print(f"[LessonAgent/Plan] Generating plan (1 LLM call)")
    response = await (llm | StrOutputParser()).ainvoke([
        SystemMessage(content=PLAN_PROMPT),
        HumanMessage(content=f"Topic: {state['topic']}"),
    ])
    raw = response.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        plan = json.loads(raw)
        assert "steps" in plan and len(plan["steps"]) >= 2
        cache.set("plan", state["topic"], json.dumps(plan))
        return {"plan": plan}
    except Exception as e:
        print(f"[LessonAgent/Plan] Parse failed: {e} — using fallback")
        return {"plan": _fallback_plan(state["topic"])}

def build_plan_graph():
    g = StateGraph(PlanState)
    g.add_node("generate_plan", generate_plan_node)
    g.set_entry_point("generate_plan")
    g.add_edge("generate_plan", END)
    return g.compile()

_plan_graph = None
def get_plan_graph():
    global _plan_graph
    if _plan_graph is None:
        _plan_graph = build_plan_graph()
    return _plan_graph


# ════════════════════════════════════════════════════════════════
# STEP GRAPH — 1 LLM call + deterministic sanitization
# ════════════════════════════════════════════════════════════════

class StepState(TypedDict):
    topic:         str
    step:          dict
    step_num:      int
    final_content: str

STEP_PROMPT = """You are QuantumMind's Guided Learning Agent — expert quantum computing tutor.

<context>
Teaching Step {step_num}: "{step_title}"
Topic: {topic}
Objective: {objective}
</context>

<teaching_points>
{teaching_points}
</teaching_points>

<rules>
- Use **bold** for every key term introduced
- Use |0⟩ |1⟩ Dirac notation for quantum states
- Build from intuition → formalism
- For code: ONLY modern Qiskit syntax inside ```python fences
  CORRECT: from qiskit_aer import AerSimulator; sim = AerSimulator(); sim.run(qc, shots=1024)
  FORBIDDEN: Aer.get_backend(), execute()
- End with exactly: ✓ Ready for the check question?
</rules>"""

async def generate_step_node(state: StepState) -> dict:
    llm = get_llm(temperature=0.5)
    step   = state["step"]
    points = "\n".join([f"  • {p}" for p in step.get("teaching_points", [])])
    prompt = STEP_PROMPT.format(
        step_num=state["step_num"],
        step_title=step["title"],
        topic=state["topic"],
        objective=step["objective"],
        teaching_points=points,
    )
    print(f"[LessonAgent/Step] Generating step {state['step_num']} (1 LLM call)")
    content = await (llm | StrOutputParser()).ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=f"Teach: {step['title']}"),
    ])
    return {"final_content": sanitize_content(content)}

def build_step_graph():
    g = StateGraph(StepState)
    g.add_node("generate_step", generate_step_node)
    g.set_entry_point("generate_step")
    g.add_edge("generate_step", END)
    return g.compile()

_step_graph = None
def get_step_graph():
    global _step_graph
    if _step_graph is None:
        _step_graph = build_step_graph()
    return _step_graph


# ════════════════════════════════════════════════════════════════
# GRADE GRAPH — 1 LLM call, merged analyze+grade
# ════════════════════════════════════════════════════════════════

class GradeState(TypedDict):
    question:       str
    correct_answer: str
    student_answer: str
    passed:         bool
    feedback:       str

GRADE_PROMPT = """Grade a student's quantum computing answer.

<question>{question}</question>
<correct_answer>{correct_answer}</correct_answer>
<student_answer>{student_answer}</student_answer>

<rules>
- Be generous — accept answers capturing the core concept
- Different wording is fine if the meaning is correct
- Return ONLY valid JSON, nothing else
</rules>

{{"passed": true or false, "feedback": "one encouraging sentence"}}"""

async def grade_node(state: GradeState) -> dict:
    llm = get_llm(temperature=0.0)
    print(f"[LessonAgent/Grade] Grading (1 LLM call)")
    response = await (llm | StrOutputParser()).ainvoke([
        HumanMessage(content=GRADE_PROMPT.format(
            question=state["question"],
            correct_answer=state["correct_answer"],
            student_answer=state["student_answer"],
        ))
    ])
    try:
        raw = re.sub(r"```(?:json)?\n?", "", response).strip().rstrip("`").strip()
        result = json.loads(raw)
        return {
            "passed":   bool(result.get("passed", False)),
            "feedback": str(result.get("feedback", "Good effort!")),
        }
    except:
        return {"passed": True, "feedback": "Good effort! Let's continue."}

def build_grade_graph():
    g = StateGraph(GradeState)
    g.add_node("grade", grade_node)
    g.set_entry_point("grade")
    g.add_edge("grade", END)
    return g.compile()

_grade_graph = None
def get_grade_graph():
    global _grade_graph
    if _grade_graph is None:
        _grade_graph = build_grade_graph()
    return _grade_graph


# ════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE
# ════════════════════════════════════════════════════════════════

async def generate_lesson_plan(topic: str) -> dict:
    result = await get_plan_graph().ainvoke({"topic": topic, "plan": {}})
    return result.get("plan") or _fallback_plan(topic)

async def teach_step(topic: str, step: dict, step_num: int) -> str:
    result = await get_step_graph().ainvoke({
        "topic": topic, "step": step,
        "step_num": step_num, "final_content": ""
    })
    return result.get("final_content", "Failed to generate content.")

async def grade_answer(question: str, correct_answer: str, student_answer: str) -> dict:
    result = await get_grade_graph().ainvoke({
        "question": question,
        "correct_answer": correct_answer,
        "student_answer": student_answer,
        "passed": False, "feedback": "",
    })
    return {"passed": result.get("passed", False), "feedback": result.get("feedback", "Good effort!")}

def _fallback_plan(topic: str) -> dict:
    return {
        "topic": topic,
        "description": f"A structured introduction to {topic}.",
        "steps": [
            {"id":1,"title":"Intuition & Analogy","objective":f"Build intuition for {topic}.","teaching_points":[f"What is {topic}?","Classical vs quantum comparison"],"check_question":f"In your own words, what is {topic}?","check_answer":f"{topic} is a fundamental quantum computing concept."},
            {"id":2,"title":"Mathematical Formalism","objective":"Understand the math.","teaching_points":["Dirac notation","State vectors"],"check_question":"What notation do we use for quantum states?","check_answer":"Dirac (bra-ket) notation: |0⟩ and |1⟩."},
            {"id":3,"title":"Qiskit Implementation","objective":"Implement using Qiskit.","teaching_points":["Circuit construction","AerSimulator execution"],"check_question":"Which class simulates Qiskit circuits locally?","check_answer":"AerSimulator from qiskit_aer."},
        ],
    }