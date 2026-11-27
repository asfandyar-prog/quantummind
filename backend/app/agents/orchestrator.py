

# ── app/agents/orchestrator.py ────────────────────────────────
import json
# json is Python's built-in JSON parser.
# We use it to parse the Orchestrator's routing decision.
# The LLM outputs a JSON string → json.loads() converts it to a dict.

from langchain_core.messages import SystemMessage, HumanMessage

from app.core import llm
from app.core.config import settings
from app.core.prompts import ORCHESTRATOR_PROMPT
from app.agents.theory_agent import run_theory_agent, stream_theory_agent
from app.agents.code_agent import run_code_agent, stream_code_agent

import logging

logger = logging.getLogger("quantummind.agents.router")


# Valid agent names — used to validate the LLM's routing decision
VALID_AGENTS = {"theory", "code", "rag", "review"}

# Fallback agent if routing fails
DEFAULT_AGENT = "theory"


async def route(user_message: str) -> str:
    """
    Asks the Orchestrator LLM which agent should handle this message.

    Returns the agent name as a string: "theory", "code", "rag", or "review"

    This function is defensive — if the LLM returns invalid JSON,
    or an unknown agent name, we fall back to "theory" rather than crashing.
    Defensive programming is critical in production AI systems because
    LLMs can occasionally produce unexpected output.
    """
    messages = [
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        HumanMessage(content=user_message),
    ]

    raw_response = await llm.chat(messages, call_type="route", model=settings.llm_router_model)
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
            logger.warning(f"Unknown agent '{agent}', falling back to '{DEFAULT_AGENT}'")
            return DEFAULT_AGENT

        logger.info(f"Routing to '{agent}': {reason}")
        return agent

    except json.JSONDecodeError:
        # LLM didn't return valid JSON — this can happen occasionally
        logger.warning(f"Failed to parse routing decision: {raw_response}")
        logger.warning(f"Falling back to '{DEFAULT_AGENT}'")
        return DEFAULT_AGENT


# Router label → the workflow that actually handles it. One table, used by both
# the /chat and /stream paths, so they can never disagree.
#   review → code : there is no Review agent; the Code workflow is the closest fit
#   rag    → theory: the RAG workflow is built but not routed yet
WORKFLOW_FOR_LABEL = {
    "theory": "theory",
    "code":   "code",
    "review": "code",
    "rag":    "theory",
}


async def pick_workflow(user_message: str, mode: str) -> str:
    """Which workflow handles this message: "theory" or "code".

    Practice mode always goes to Code with no LLM call; otherwise the router
    labels the message and WORKFLOW_FOR_LABEL maps the label.
    """
    if mode == "practice":
        logger.info("Practice mode — forcing route to 'code'")
        return "code"
    label = await route(user_message)
    workflow = WORKFLOW_FOR_LABEL.get(label, DEFAULT_AGENT)
    if workflow != label:
        logger.info(f"'{label}' has no workflow of its own, using '{workflow}'")
    return workflow


async def run_agent(
    user_message: str,
    chat_history: list[dict] | None = None,
    mode: str = "guided",
    thread_id: str = "default",
    week: int = 0,
) -> str:
    """Route the message, run the chosen workflow, return its complete answer."""
    workflow = await pick_workflow(user_message, mode)
    if workflow == "code":
        return await run_code_agent(user_message, chat_history or [], thread_id)
    return await run_theory_agent(user_message, chat_history or [], thread_id)


async def stream_agent(
    user_message: str,
    chat_history: list[dict] | None = None,
    mode: str = "guided",
    thread_id: str = "default",
    week: int = 0,
):
    """Route the message, then stream the chosen workflow's answer.

    Routing itself is not streamed: the workflow is picked first, then its
    answer streams. Theory streams real tokens; Code's stream is simulated (the
    finished answer is sent word by word).
    """
    workflow = await pick_workflow(user_message, mode)
    if workflow == "code":
        async for token in stream_code_agent(user_message, chat_history or [], thread_id):
            yield token
    else:
        async for token in stream_theory_agent(user_message, chat_history or [], thread_id):
            yield token
