
# ── app/agents/orchestrator.py ────────────────────────────────
import json
# json is Python's built-in JSON parser.
# We use it to parse the Orchestrator's routing decision.
# The LLM outputs a JSON string → json.loads() converts it to a dict.

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.core.prompts import ORCHESTRATOR_PROMPT
from app.agents.theory_agent import run_theory_agent, stream_theory_agent
from app.agents.code_agent import run_code_agent, stream_code_agent
from app.agents.rag_agent import run_rag_agent, stream_rag_agent


# Valid agent names — used to validate the LLM's routing decision
VALID_AGENTS = {"theory", "code", "rag", "review"}

# Fallback agent if routing fails
DEFAULT_AGENT = "theory"


def get_orchestrator_llm() -> ChatGroq:
    """
    LLM for routing decisions.

    temperature=0.0 — fully deterministic.
    The Orchestrator must make consistent routing decisions.
    The same message should always go to the same agent.
    Any randomness here would make the system unpredictable.

    We also use the fast 8b model regardless of what's in settings
    because routing is a simple classification task — it doesn't
    need a powerful model, just a fast and reliable one.
    """
    return ChatGroq(
        api_key=settings.groq_api_key,
        model="llama-3.1-8b-instant",
        temperature=0.0,
    )


async def route(user_message: str) -> str:
    """
    Asks the Orchestrator LLM which agent should handle this message.

    Returns the agent name as a string: "theory", "code", "rag", or "review"

    This function is defensive — if the LLM returns invalid JSON,
    or an unknown agent name, we fall back to "theory" rather than crashing.
    Defensive programming is critical in production AI systems because
    LLMs can occasionally produce unexpected output.
    """
    llm = get_orchestrator_llm()
    chain = llm | StrOutputParser()

    messages = [
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        HumanMessage(content=user_message),
    ]

    raw_response = await chain.ainvoke(messages)
    # raw_response is a string like: '{"agent": "theory", "reason": "..."}'

    try:
        parsed = json.loads(raw_response)
        # json.loads converts the JSON string to a Python dict:
        # {"agent": "theory", "reason": "Conceptual question"}

        agent = parsed.get("agent", DEFAULT_AGENT)
        # .get() with a default is safer than parsed["agent"]
        # If "agent" key is missing, we get DEFAULT_AGENT instead of KeyError

        reason = parsed.get("reason", "No reason provided")

        if agent not in VALID_AGENTS:
            # LLM returned a valid JSON but with an unknown agent name
            print(f"[Orchestrator] Unknown agent '{agent}', falling back to '{DEFAULT_AGENT}'")
            return DEFAULT_AGENT

        print(f"[Orchestrator] Routing to '{agent}': {reason}")
        return agent

    except json.JSONDecodeError:
        # LLM didn't return valid JSON — this can happen occasionally
        print(f"[Orchestrator] Failed to parse routing decision: {raw_response}")
        print(f"[Orchestrator] Falling back to '{DEFAULT_AGENT}'")
        return DEFAULT_AGENT


async def run_agent(
    user_message: str,
    chat_history: list[dict] | None = None,
    mode: str = "guided",
    thread_id: str = "default",
    week: int = 0,
) -> str:
    """
    Full pipeline: route the message then run the correct agent.
    Returns the complete response string (non-streaming).

    Args:
        user_message: The student's question
        chat_history: Previous conversation turns
        mode: The app mode ("theory", "practice", "guided")
              Used to bias routing — in practice mode, code questions
              should go to code agent even if ambiguous.

    Returns:
        Complete response string from the selected agent
    """
    if chat_history is None:
        chat_history = []

    # In practice mode, always route to code agent
    # This overrides the LLM's routing decision for clear UX
    if mode == "practice":
        agent_name = "code"
        print(f"[Orchestrator] Practice mode — forcing route to 'code'")
    else:
        agent_name = await route(user_message)

    # Route to the correct agent
    # We use if/elif instead of a dict of functions because each agent
    # might need different arguments in future (RAG needs context, etc.)
    if agent_name == "theory":
        return await run_theory_agent(user_message, chat_history, thread_id)

    elif agent_name == "code":
        return await run_code_agent(user_message, chat_history, thread_id)

    elif agent_name == "rag":
        # RAG agent not built yet — fall back to theory agent
        # with a note. We'll replace this in Phase 2.
        print("[Orchestrator] RAG agent not yet implemented, using theory agent")
        return await run_theory_agent(user_message, chat_history, thread_id)

    elif agent_name == "review":
        # Review agent not built yet — fall back to code agent
        print("[Orchestrator] Review agent not yet implemented, using code agent")
        return await run_code_agent(user_message, chat_history, thread_id)

    else:
        return await run_theory_agent(user_message, chat_history, thread_id)


async def stream_agent(
    user_message: str,
    chat_history: list[dict] | None = None,
    mode: str = "guided",
    thread_id: str = "default",
    week: int = 0,
):
    """
    Full pipeline in STREAMING mode.
    Routes the message then streams tokens from the correct agent.

    This is an async generator — it yields tokens one at a time.
    The streaming route (POST /stream) iterates over this to push
    tokens to the frontend via SSE.

    Note: routing itself is NOT streamed — we first get the agent name
    (fast, ~200ms), then stream the actual response.
    """
    if chat_history is None:
        chat_history = []

    if mode == "practice":
        agent_name = "code"
    else:
        agent_name = await route(user_message)

    # Stream from the correct agent
    if agent_name in ("theory", "rag", "review"):
        async for token in stream_theory_agent(user_message, chat_history, thread_id):
            yield token

    elif agent_name == "code":
        async for token in stream_code_agent(user_message, chat_history, thread_id):
            yield token
