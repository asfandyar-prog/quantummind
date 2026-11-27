

# ── app/agents/orchestrator.py ────────────────────────────────
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings
from app.core.prompts import ORCHESTRATOR_PROMPT
from app.core.structured import RouteDecision, ask_validated
from app.agents.theory_agent import run_theory_agent, stream_theory_agent
from app.agents.code_agent import run_code_agent, stream_code_agent
from app.agents.rag_agent import run_rag_agent, stream_rag_agent

import logging

logger = logging.getLogger("quantummind.agents.router")


# Fallback agent if routing fails
DEFAULT_AGENT = "theory"


async def route(user_message: str) -> str:
    """
    Asks the Orchestrator LLM which agent should handle this message.

    Returns the agent name as a string: "theory", "code", "rag", or "review"

    The reply is validated as RouteDecision (core/structured.py). An invalid
    reply gets one corrective retry; if that fails too, we fall back to "theory".
    Defensive programming is critical in production AI systems because
    LLMs can occasionally produce unexpected output.
    """
    messages = [
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        HumanMessage(content=user_message),
    ]

    decision = await ask_validated(
        messages, RouteDecision, call_type="route", model=settings.llm_router_model,
    )
    if decision is None:
        # Fail closed to the safe default: Theory answers without running code.
        logger.warning(f"Router reply invalid after one retry, falling back to '{DEFAULT_AGENT}'")
        return DEFAULT_AGENT
    logger.info(f"Routing to '{decision.agent}': {decision.reason}")
    return decision.agent


# Router label → the workflow that actually handles it. One table, used by both
# the /chat and /stream paths, so they can never disagree.
#   review → code: there is no Review agent; the Code workflow is the closest fit
WORKFLOW_FOR_LABEL = {
    "theory": "theory",
    "code":   "code",
    "review": "code",
    "rag":    "rag",
}


async def pick_workflow(user_message: str, mode: str) -> str:
    """Which workflow handles this message: "theory", "code" or "rag".

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
    if workflow == "rag":
        return await run_rag_agent(user_message, chat_history or [], thread_id, week)
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
    answer streams. Theory streams real tokens; the Code and RAG streams are
    simulated (the finished answer is sent word by word). `week` filters RAG
    retrieval to that course week; 0 searches every week.
    """
    workflow = await pick_workflow(user_message, mode)
    if workflow == "code":
        async for token in stream_code_agent(user_message, chat_history or [], thread_id):
            yield token
    elif workflow == "rag":
        async for token in stream_rag_agent(user_message, chat_history or [], thread_id, week):
            yield token
    else:
        async for token in stream_theory_agent(user_message, chat_history or [], thread_id):
            yield token
