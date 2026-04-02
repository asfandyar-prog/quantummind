# ── app/agents/theory_agent.py ────────────────────────────────
#
# LangGraph Theory Agent
#
# Graph flow:
#   analyze_depth → generate_explanation → grade_explanation
#                                               ↙         ↘
#                                         refine        END
#                                      (max 1 retry)

from typing import TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.core.prompts import THEORY_PROMPT
from app.core.memory import checkpointer


# ── STATE ─────────────────────────────────────────────────────
class TheoryAgentState(TypedDict):
    user_message: str
    chat_history: list
    student_level: str       # beginner / intermediate / advanced
    explanation: str         # generated explanation
    grade_feedback: str      # pass / fail from grader
    retry_count: int
    final_response: str


def get_llm(temperature: float = 0.7) -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=temperature,
    )


# ════════════════════════════════════════════════════════════════
# NODES
# ════════════════════════════════════════════════════════════════

async def analyze_depth(state: TheoryAgentState) -> dict:
    """
    Node 1 — Infer the student's knowledge level from their question.

    A beginner asks "what is superposition?"
    An intermediate asks "how does decoherence affect superposition?"
    An advanced student asks "what is the mathematical relationship
    between superposition and the Bloch sphere representation?"

    The level is used by generate_explanation to calibrate depth.
    """
    llm = get_llm(temperature=0.0)

    prompt = f"""Classify this quantum computing question by student level.

Question: {state["user_message"]}

Respond with ONLY one word:
- "beginner"      → basic concepts, no prior quantum knowledge assumed
- "intermediate"  → familiar with qubits and basic gates
- "advanced"      → comfortable with linear algebra and quantum formalism"""

    level = await (llm | StrOutputParser()).ainvoke([HumanMessage(content=prompt)])
    level = level.strip().lower()
    if level not in ("beginner", "intermediate", "advanced"):
        level = "beginner"

    print(f"[TheoryAgent] analyze_depth → {level}")
    return {"student_level": level}


async def generate_explanation(state: TheoryAgentState) -> dict:
    """
    Node 2 — Generate explanation calibrated to student level.

    Adapts the Theory system prompt with level-specific instructions.
    On retry: uses grade_feedback to improve the explanation.
    """
    llm = get_llm(temperature=0.7)

    level = state.get("student_level", "beginner")

    level_instructions = {
        "beginner":     "Use simple analogies. Avoid heavy math. Build intuition first.",
        "intermediate": "Include gate matrices. Use Dirac notation. Assume qubit familiarity.",
        "advanced":     "Include full mathematical formalism. Reference relevant theorems.",
    }

    # Build level-aware system prompt
    system = f"""{THEORY_PROMPT}

IMPORTANT: This student is at {level.upper()} level.
{level_instructions[level]}"""

    messages = [SystemMessage(content=system)]

    for msg in state.get("chat_history", []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            messages.append(AIMessage(content=msg["content"]))

    # On retry — include feedback so LLM knows what to improve
    if state.get("grade_feedback") == "fail" and state.get("retry_count", 0) > 0:
        refine_msg = f"""Your previous explanation was not clear enough.
Previous explanation: {state["explanation"]}

Please rewrite it with:
- Clearer analogies
- Better structure
- More concrete examples

Student question: {state["user_message"]}"""
        messages.append(HumanMessage(content=refine_msg))
    else:
        messages.append(HumanMessage(content=state["user_message"]))

    explanation = await (llm | StrOutputParser()).ainvoke(messages)
    print(f"[TheoryAgent] generate_explanation → {len(explanation)} chars")
    return {"explanation": explanation, "grade_feedback": ""}


async def grade_explanation(state: TheoryAgentState) -> dict:
    """
    Node 3 — Reflection: is the explanation clear for this student's level?

    Same reflection pattern as the Code Agent.
    A second LLM judges the first LLM's output before the student sees it.
    """
    llm = get_llm(temperature=0.0)

    level = state.get("student_level", "beginner")

    prompt = f"""Grade this quantum computing explanation for a {level} student.

Explanation:
{state["explanation"]}

Does it match the student's level? Is it clear and accurate?
Respond with ONLY: "pass" or "fail"
Only fail if genuinely confusing, inaccurate, or wrong level."""

    grade = await (llm | StrOutputParser()).ainvoke([HumanMessage(content=prompt)])
    grade = grade.strip().lower()
    if grade not in ("pass", "fail"):
        grade = "pass"

    print(f"[TheoryAgent] grade_explanation → {grade}")
    return {"grade_feedback": grade}


async def refine_explanation(state: TheoryAgentState) -> dict:
    """
    Node 4 — Increment retry counter before looping back.
    """
    count = state.get("retry_count", 0) + 1
    print(f"[TheoryAgent] refine_explanation → retry {count}/1")
    return {"retry_count": count}


async def assemble_response(state: TheoryAgentState) -> dict:
    """
    Node 5 — Pass explanation to final_response.
    """
    return {"final_response": state.get("explanation", "")}


# ════════════════════════════════════════════════════════════════
# CONDITIONAL EDGES
# ════════════════════════════════════════════════════════════════

def should_refine_or_end(state: TheoryAgentState) -> str:
    grade       = state.get("grade_feedback", "pass")
    retry_count = state.get("retry_count", 0)

    if grade == "fail" and retry_count < 1:
        return "refine"
    return "done"


# ════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ════════════════════════════════════════════════════════════════

def build_theory_agent_graph():
    graph = StateGraph(TheoryAgentState)

    graph.add_node("analyze_depth",        analyze_depth)
    graph.add_node("generate_explanation", generate_explanation)
    graph.add_node("grade_explanation",    grade_explanation)
    graph.add_node("refine_explanation",   refine_explanation)
    graph.add_node("assemble_response",    assemble_response)

    graph.set_entry_point("analyze_depth")

    graph.add_edge("analyze_depth",        "generate_explanation")
    graph.add_edge("generate_explanation", "grade_explanation")
    graph.add_edge("refine_explanation",   "generate_explanation")
    graph.add_edge("assemble_response",    END)

    graph.add_conditional_edges(
        "grade_explanation",
        should_refine_or_end,
        {"refine": "refine_explanation", "done": "assemble_response"}
    )

    return graph.compile(checkpointer=checkpointer)


theory_agent_graph = build_theory_agent_graph()


# ════════════════════════════════════════════════════════════════
# PUBLIC INTERFACE
# ════════════════════════════════════════════════════════════════

async def run_theory_agent(
    user_message: str,
    chat_history: list | None = None,
    thread_id: str = "default",
) -> str:
    initial_state: TheoryAgentState = {
        "user_message":  user_message,
        "chat_history":  chat_history or [],
        "student_level": "beginner",
        "explanation":   "",
        "grade_feedback": "",
        "retry_count":   0,
        "final_response": "",
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await theory_agent_graph.ainvoke(initial_state, config=config)
    return result.get("final_response", "Sorry, I could not generate a response.")


async def stream_theory_agent(
    user_message: str,
    chat_history: list | None = None,
    thread_id: str = "default",
):
    response = await run_theory_agent(user_message, chat_history, thread_id)
    words = response.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")