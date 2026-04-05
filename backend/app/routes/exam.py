# ── app/agents/exam_agent.py ─────────────────────────────────
#
# LangGraph AI Examiner — V1/V2/V3 adaptive questioning
#
# Three graphs:
#   1. QuestionGraph  — generates the next question (1 LLM call)
#   2. GradeGraph     — grades answer + generates ideal (1 LLM call)
#   3. FollowUpGraph  — decides if follow-up needed (DETERMINISTIC — 0 LLM calls)
#
# The follow-up decision is deterministic:
#   avg_score < 5.0 → generate follow-up question
#   avg_score >= 5.0 → move to next question
# No LLM needed for this decision — saves latency.

import json
import re
from typing import TypedDict, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from app.core.config import settings
from app.core.cache import cache


def get_llm(temperature: float = 0.3) -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=temperature,
    )


# ════════════════════════════════════════════════════════════════
# QUESTION BANK — V1 static questions per topic
# Used as baseline for research comparison
# ════════════════════════════════════════════════════════════════

STATIC_QUESTIONS = {
    "superposition": [
        "What is quantum superposition? Explain in your own words.",
        "What happens to a qubit in superposition when you measure it?",
        "How does the Hadamard gate create superposition?",
        "What is the mathematical representation of a qubit in superposition?",
        "How does superposition differ from classical probability?",
    ],
    "entanglement": [
        "What is quantum entanglement?",
        "Explain the EPR paradox and what it means for entanglement.",
        "What are the four Bell states?",
        "How do you create an entangled state using Qiskit?",
        "Why can't entanglement be used to transmit information faster than light?",
    ],
    "grover": [
        "What problem does Grover's algorithm solve?",
        "What is the quantum speedup of Grover's algorithm?",
        "Explain amplitude amplification in plain language.",
        "What is the role of the oracle in Grover's algorithm?",
        "How many iterations of Grover's algorithm are optimal?",
    ],
}

def get_static_questions(topic: str) -> list[str]:
    """Get static questions for a topic. Falls back to generic if topic not found."""
    topic_lower = topic.lower()
    for key, questions in STATIC_QUESTIONS.items():
        if key in topic_lower:
            return questions
    return [
        f"What is {topic}? Explain in your own words.",
        f"What are the key mathematical concepts in {topic}?",
        f"How is {topic} implemented in Qiskit?",
        f"What are the practical applications of {topic}?",
        f"How does {topic} relate to quantum advantage?",
    ]


# ════════════════════════════════════════════════════════════════
# QUESTION GENERATION GRAPH — 1 LLM call
# ════════════════════════════════════════════════════════════════

class QuestionState(TypedDict):
    topic:          str
    version:        str       # V1, V2, V3
    turn_number:    int
    previous_qa:    list[dict]  # previous Q&A pairs for context
    weak_areas:     list[str]   # areas where student scored low
    is_followup:    bool
    question:       str

QUESTION_PROMPT = """You are a rigorous quantum computing examiner at a university.

<context>
Topic: {topic}
Exam version: {version}
Question number: {turn_number}
</context>

<previous_exchanges>
{previous_qa}
</previous_exchanges>

<weak_areas>
{weak_areas}
</weak_areas>

<task>
Generate ONE examination question.

Rules:
- If is_followup=true: probe deeper into a weak area from previous answers
- If V3 (adaptive): base the question on gaps in previous answers
- If V1/V2: generate a clear factual/conceptual question
- Questions must be specific and unambiguous
- No hints, no leading questions
- Increase difficulty progressively through the exam
- Return ONLY the question text — no preamble, no numbering
</task>

is_followup: {is_followup}"""


async def generate_question_node(state: QuestionState) -> dict:
    """1 LLM call — generates the next exam question."""

    # V1: always use static questions
    if state["version"] == "V1":
        questions = get_static_questions(state["topic"])
        idx = min(state["turn_number"] - 1, len(questions) - 1)
        print(f"[ExamAgent/Q] V1 static question #{state['turn_number']}")
        return {"question": questions[idx]}

    # V2/V3: AI-generated questions
    llm = get_llm(temperature=0.4)
    prev = "\n".join([
        f"Q{i+1}: {qa['question']}\nA{i+1}: {qa['answer']}\nScore: {qa.get('score', 'N/A')}/10"
        for i, qa in enumerate(state.get("previous_qa", []))
    ]) or "None yet"

    weak = ", ".join(state.get("weak_areas", [])) or "None identified"

    prompt = QUESTION_PROMPT.format(
        topic=state["topic"],
        version=state["version"],
        turn_number=state["turn_number"],
        previous_qa=prev,
        weak_areas=weak,
        is_followup=state["is_followup"],
    )

    print(f"[ExamAgent/Q] {state['version']} question #{state['turn_number']} (1 LLM call)")
    question = await (llm | StrOutputParser()).ainvoke([HumanMessage(content=prompt)])
    return {"question": question.strip()}


def build_question_graph():
    g = StateGraph(QuestionState)
    g.add_node("generate_question", generate_question_node)
    g.set_entry_point("generate_question")
    g.add_edge("generate_question", END)
    return g.compile()

_q_graph = None
def get_question_graph():
    global _q_graph
    if _q_graph is None:
        _q_graph = build_question_graph()
    return _q_graph


# ════════════════════════════════════════════════════════════════
# GRADING GRAPH — 1 LLM call
# Returns: accuracy, reasoning, clarity scores + justification + ideal answer
# ════════════════════════════════════════════════════════════════

class GradeState(TypedDict):
    topic:          str
    question:       str
    student_answer: str
    score_accuracy:  float
    score_reasoning: float
    score_clarity:   float
    score_total:     float
    justification:  str
    ideal_answer:   str
    is_weak:        bool    # True if avg_score < 5

GRADE_PROMPT = """You are a university quantum computing examiner grading a student's answer.

<question>{question}</question>
<student_answer>{student_answer}</student_answer>
<topic>{topic}</topic>

Grade on THREE dimensions (0-10 each):

ACCURACY (0-10): Is the answer factually correct?
  10 = completely correct, 5 = partially correct, 0 = wrong

REASONING (0-10): Does the student show understanding of WHY?
  10 = deep understanding, 5 = surface level, 0 = no reasoning shown

CLARITY (0-10): Is the answer well-structured and precise?
  10 = crystal clear, 5 = understandable but vague, 0 = incomprehensible

Return ONLY valid JSON — no explanation, no fences:
{{
  "accuracy": <0-10>,
  "reasoning": <0-10>,
  "clarity": <0-10>,
  "justification": "2-3 sentences explaining the scores",
  "ideal_answer": "what a perfect answer would say (2-4 sentences)"
}}"""


async def grade_answer_node(state: GradeState) -> dict:
    """1 LLM call — grades answer on 3 dimensions."""

    # Cache ideal answers per question (they don't change)
    cached_ideal = cache.get("ideal_answer", state["question"])

    llm = get_llm(temperature=0.0)
    print(f"[ExamAgent/Grade] Grading answer (1 LLM call)")

    response = await (llm | StrOutputParser()).ainvoke([
        HumanMessage(content=GRADE_PROMPT.format(
            question=state["question"],
            student_answer=state["student_answer"],
            topic=state["topic"],
        ))
    ])

    try:
        raw = re.sub(r"```(?:json)?\n?", "", response).strip().rstrip("`").strip()
        result = json.loads(raw)
        acc  = float(result.get("accuracy",  5.0))
        reas = float(result.get("reasoning", 5.0))
        clar = float(result.get("clarity",   5.0))
        total = round((acc + reas + clar) / 3, 2)
        just  = str(result.get("justification", ""))
        ideal = str(result.get("ideal_answer",  ""))

        # Cache ideal answer for this question
        if ideal:
            cache.set("ideal_answer", state["question"], ideal)

    except Exception as e:
        print(f"[ExamAgent/Grade] Parse error: {e}")
        acc = reas = clar = total = 5.0
        just  = "Could not parse grading response."
        ideal = ""

    print(f"[ExamAgent/Grade] acc={acc} reas={reas} clar={clar} total={total}")

    return {
        "score_accuracy":  acc,
        "score_reasoning": reas,
        "score_clarity":   clar,
        "score_total":     total,
        "justification":   just,
        "ideal_answer":    ideal,
        "is_weak":         total < 5.0,
    }


def build_grade_graph():
    g = StateGraph(GradeState)
    g.add_node("grade_answer", grade_answer_node)
    g.set_entry_point("grade_answer")
    g.add_edge("grade_answer", END)
    return g.compile()

_grade_graph = None
def get_grade_graph():
    global _grade_graph
    if _grade_graph is None:
        _grade_graph = build_grade_graph()
    return _grade_graph


# ════════════════════════════════════════════════════════════════
# FOLLOW-UP DECISION — DETERMINISTIC (0 LLM calls)
# This is the core of the adaptive system
# ════════════════════════════════════════════════════════════════

FOLLOWUP_THRESHOLD = 5.0   # avg score below this triggers a follow-up
MAX_FOLLOWUPS      = 2     # max consecutive follow-ups per main question
MAX_TURNS          = 10    # hard cap on total exam turns

def should_generate_followup(
    score_total:    float,
    version:        str,
    followup_count: int,
    turn_number:    int,
    weak_areas:     list[str],
) -> tuple[bool, str]:
    """
    Deterministic follow-up decision — zero LLM calls.

    Returns (should_followup: bool, reason: str)

    Logic:
    - V1: never follow up (static exam)
    - V2: follow up once if score < threshold
    - V3: follow up up to MAX_FOLLOWUPS times if score < threshold
    - Never exceed MAX_TURNS total
    """
    if version == "V1":
        return False, "V1 — static exam, no follow-ups"

    if turn_number >= MAX_TURNS:
        return False, f"Max turns ({MAX_TURNS}) reached"

    if followup_count >= MAX_FOLLOWUPS:
        return False, f"Max follow-ups ({MAX_FOLLOWUPS}) reached"

    if version == "V2" and followup_count >= 1:
        return False, "V2 — only one follow-up allowed"

    if score_total < FOLLOWUP_THRESHOLD:
        reason = f"Score {score_total} below threshold {FOLLOWUP_THRESHOLD}"
        return True, reason

    return False, f"Score {score_total} acceptable — moving on"


def identify_weak_areas(
    score_accuracy:  float,
    score_reasoning: float,
    score_clarity:   float,
) -> list[str]:
    """
    Deterministically identify which dimensions need improvement.
    Used to direct follow-up questions.
    """
    weak = []
    if score_accuracy < 5.0:
        weak.append("factual accuracy")
    if score_reasoning < 5.0:
        weak.append("conceptual reasoning")
    if score_clarity < 5.0:
        weak.append("answer clarity and structure")
    return weak


# ════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE
# ════════════════════════════════════════════════════════════════

async def generate_question(
    topic:       str,
    version:     str,
    turn_number: int,
    previous_qa: list[dict] | None = None,
    weak_areas:  list[str]  | None = None,
    is_followup: bool = False,
) -> str:
    """Generate the next exam question."""
    result = await get_question_graph().ainvoke({
        "topic":       topic,
        "version":     version,
        "turn_number": turn_number,
        "previous_qa": previous_qa or [],
        "weak_areas":  weak_areas or [],
        "is_followup": is_followup,
        "question":    "",
    })
    return result["question"]


async def grade_answer(
    topic:          str,
    question:       str,
    student_answer: str,
) -> dict:
    """Grade a student answer. Returns scores + justification + ideal answer."""
    result = await get_grade_graph().ainvoke({
        "topic":          topic,
        "question":       question,
        "student_answer": student_answer,
        "score_accuracy":  0.0,
        "score_reasoning": 0.0,
        "score_clarity":   0.0,
        "score_total":     0.0,
        "justification":  "",
        "ideal_answer":   "",
        "is_weak":        False,
    })
    return {
        "accuracy":      result["score_accuracy"],
        "reasoning":     result["score_reasoning"],
        "clarity":       result["score_clarity"],
        "total":         result["score_total"],
        "justification": result["justification"],
        "ideal_answer":  result["ideal_answer"],
        "is_weak":       result["is_weak"],
        "weak_areas":    identify_weak_areas(
            result["score_accuracy"],
            result["score_reasoning"],
            result["score_clarity"],
        ),
    }


def decide_followup(
    score_total:    float,
    version:        str,
    followup_count: int,
    turn_number:    int,
    weak_areas:     list[str],
) -> dict:
    """Deterministic follow-up decision. Zero LLM calls."""
    should, reason = should_generate_followup(
        score_total, version, followup_count, turn_number, weak_areas
    )
    return {"should_followup": should, "reason": reason}