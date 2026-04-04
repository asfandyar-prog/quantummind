from typing import TypedDict, Annotated
import operator
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from app.core.config import settings
from app.core.prompts import THEORY_PROMPT
from app.core.memory import get_checkpointer


class TheoryAgentState(TypedDict):
    # Annotated with operator.add means LangGraph APPENDS to this list
    # instead of replacing it. This is how memory accumulates naturally.
    messages: Annotated[list[BaseMessage], operator.add]
    student_level: str
    explanation: str
    grade_feedback: str
    retry_count: int
    final_response: str


def get_llm(temperature: float = 0.7) -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=temperature,
    )


async def analyze_depth(state: TheoryAgentState) -> dict:
    """Infer student level from their latest message."""
    llm = get_llm(temperature=0.0)
    # Get the last human message
    last_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_msg = msg.content
            break

    prompt = f"""Classify this quantum computing question by student level.
Question: {last_msg}
Respond with ONLY one word: "beginner", "intermediate", or "advanced" """

    level = await (llm | StrOutputParser()).ainvoke([HumanMessage(content=prompt)])
    level = level.strip().lower()
    if level not in ("beginner", "intermediate", "advanced"):
        level = "beginner"

    print(f"[TheoryAgent] analyze_depth → {level}")
    return {"student_level": level, "grade_feedback": ""}


async def generate_explanation(state: TheoryAgentState) -> dict:
    """Generate explanation using full message history for context."""
    llm = get_llm(temperature=0.7)
    level = state.get("student_level", "beginner")

    level_instructions = {
        "beginner":     "Use simple analogies. Avoid heavy math. Build intuition first.",
        "intermediate": "Include gate matrices. Use Dirac notation. Assume qubit familiarity.",
        "advanced":     "Include full mathematical formalism. Reference relevant theorems.",
    }

    system = f"""{THEORY_PROMPT}

IMPORTANT: This student is at {level.upper()} level.
{level_instructions[level]}"""

    # Build messages: system prompt + full conversation history
    # The messages list in state contains the FULL history automatically
    # because of the Annotated[list, operator.add] — LangGraph accumulates it
    messages = [SystemMessage(content=system)] + state["messages"]

    # On retry — add feedback
    if state.get("grade_feedback") == "fail" and state.get("retry_count", 0) > 0:
        messages.append(HumanMessage(content=f"Please rewrite your last explanation more clearly. Previous attempt: {state['explanation']}"))

    explanation = await (llm | StrOutputParser()).ainvoke(messages)
    print(f"[TheoryAgent] generate_explanation → {len(explanation)} chars")
    return {"explanation": explanation}


async def grade_explanation(state: TheoryAgentState) -> dict:
    """Quality-check the explanation."""
    llm = get_llm(temperature=0.0)
    level = state.get("student_level", "beginner")

    prompt = f"""Grade this quantum computing explanation for a {level} student.
Explanation: {state["explanation"]}
Respond with ONLY: "pass" or "fail" """

    grade = await (llm | StrOutputParser()).ainvoke([HumanMessage(content=prompt)])
    grade = grade.strip().lower()
    if grade not in ("pass", "fail"):
        grade = "pass"

    print(f"[TheoryAgent] grade_explanation → {grade}")
    return {"grade_feedback": grade}


async def refine_explanation(state: TheoryAgentState) -> dict:
    count = state.get("retry_count", 0) + 1
    print(f"[TheoryAgent] refine → retry {count}/1")
    return {"retry_count": count}


async def assemble_response(state: TheoryAgentState) -> dict:
    explanation = state.get("explanation", "")
    # Add the AI response to the messages history so it's remembered
    return {
        "final_response": explanation,
        "messages": [AIMessage(content=explanation)],
    }


def should_refine_or_end(state: TheoryAgentState) -> str:
    grade      = state.get("grade_feedback", "pass")
    retry_count = state.get("retry_count", 0)
    if grade == "fail" and retry_count < 1:
        return "refine"
    return "done"


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

    return graph.compile(checkpointer=get_checkpointer())


_theory_graph = None

def get_theory_graph():
    global _theory_graph
    if _theory_graph is None:
        _theory_graph = build_theory_agent_graph()
    return _theory_graph


async def run_theory_agent(
    user_message: str,
    chat_history: list | None = None,
    thread_id: str = "default",
) -> str:
    initial_state: TheoryAgentState = {
        # Only pass the NEW user message — history comes from checkpointer
        "messages":      [HumanMessage(content=user_message)],
        "student_level": "beginner",
        "explanation":   "",
        "grade_feedback": "",
        "retry_count":   0,
        "final_response": "",
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await get_theory_graph().ainvoke(initial_state, config=config)
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