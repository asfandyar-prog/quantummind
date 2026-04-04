# ── app/agents/theory_agent.py ────────────────────────────────
# OPTIMIZED: 1 LLM call per request (down from 4-5)
# Strategy: Single rich prompt that handles calibration + quality
# in one shot instead of analyze → generate → grade → refine loop

from typing import TypedDict, Annotated
import operator
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from app.core.config import settings
from app.core.memory import get_checkpointer

# ── STATE ─────────────────────────────────────────────────────
class TheoryAgentState(TypedDict):
    messages:       Annotated[list[BaseMessage], operator.add]
    final_response: str

def get_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.7,
    )

# Single rich prompt replaces: analyze_depth + generate + grade + refine
# The prompt itself handles calibration by instructing the model to
# infer level from the question and self-correct in one pass.
THEORY_SYSTEM = """You are QuantumMind AI — an expert quantum computing tutor.

RESPONSE RULES (follow every time, no exceptions):
1. Infer the student's level from their question:
   - Simple "what is X" → beginner: use analogy first, then math
   - "How does X relate to Y" → intermediate: use notation directly
   - Formal/technical phrasing → advanced: full formalism
2. Structure EVERY response:
   - Start with one clear intuition sentence
   - Build up to the math/notation
   - Use **bold** for every key term introduced
   - Use |0⟩ |1⟩ Dirac notation for quantum states
   - If relevant, show a minimal Qiskit snippet (modern syntax only)
   - End with ONE follow-up question to deepen understanding
3. Do NOT generate Qiskit code unless the student asks for it
4. Keep responses focused — answer exactly what was asked
5. If the student mentions their name or introduces themselves, 
   just greet them and ask what they want to learn. Do NOT launch 
   into quantum concepts unprompted.

Modern Qiskit syntax (use ONLY these):
  from qiskit_aer import AerSimulator
  sim = AerSimulator()
  job = sim.run(qc, shots=1024)
  counts = job.result().get_counts()"""


async def generate_response(state: TheoryAgentState) -> dict:
    """Single node — one LLM call handles everything."""
    llm = get_llm()
    messages = [SystemMessage(content=THEORY_SYSTEM)] + state["messages"]
    print(f"[TheoryAgent] Generating response (1 LLM call)")
    response = await (llm | StrOutputParser()).ainvoke(messages)
    return {
        "final_response": response,
        "messages": [AIMessage(content=response)],
    }


def build_theory_graph():
    g = StateGraph(TheoryAgentState)
    g.add_node("generate_response", generate_response)
    g.set_entry_point("generate_response")
    g.add_edge("generate_response", END)
    return g.compile(checkpointer=get_checkpointer())

_graph = None
def get_theory_graph():
    global _graph
    if _graph is None:
        _graph = build_theory_graph()
    return _graph

async def run_theory_agent(
    user_message: str,
    chat_history: list | None = None,
    thread_id: str = "default",
) -> str:
    initial: TheoryAgentState = {
        "messages":       [HumanMessage(content=user_message)],
        "final_response": "",
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await get_theory_graph().ainvoke(initial, config=config)
    return result.get("final_response", "")

async def stream_theory_agent(
    user_message: str,
    chat_history: list | None = None,
    thread_id: str = "default",
):
    """Stream directly from LLM — no waiting for full response."""
    llm = get_llm()

    # Build message history from checkpointer if available
    messages = [SystemMessage(content=THEORY_SYSTEM)]

    # Add chat history for context
    for msg in (chat_history or []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    print(f"[TheoryAgent] Streaming response (1 LLM call)")
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content