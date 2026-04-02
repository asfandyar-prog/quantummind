# ── app/agents/code_agent.py ──────────────────────────────────
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.core.prompts import CODE_PROMPT


def get_code_llm() -> ChatGroq:
    """
    LLM for the Code agent.

    temperature=0.2 — much lower than the Theory agent.
    Why? Code needs to be CORRECT, not creative.
    A higher temperature might hallucinate syntax or wrong API calls.
    0.2 keeps the output consistent and accurate while still allowing
    the LLM to adapt its explanation style.
    """
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.2,
    )


def build_messages(user_message: str, chat_history: list[dict]) -> list:
    """
    Same pattern as theory_agent — converts history dicts to
    LangChain message objects with the Code system prompt.

    We duplicate this function across agents intentionally.
    Each agent might need to pre-process messages differently in future.
    Sharing a single function would create hidden coupling between agents.
    """
    messages = [SystemMessage(content=CODE_PROMPT)]

    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))
    return messages


async def run_code_agent(
    user_message: str,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Runs the Code agent. Returns complete response.
    Used by POST /chat for single-turn non-streaming responses.
    """
    if chat_history is None:
        chat_history = []

    llm = get_code_llm()
    chain = llm | StrOutputParser()
    messages = build_messages(user_message, chat_history)

    return await chain.ainvoke(messages)


async def stream_code_agent(
    user_message: str,
    chat_history: list[dict] | None = None,
):
    """
    Streams the Code agent response token by token.
    Used by POST /stream for real-time frontend updates.

    Code responses tend to be longer than theory responses
    (full code blocks + explanations), so streaming matters
    more here — the student sees output immediately instead
    of waiting 5-10 seconds for the full response.
    """
    if chat_history is None:
        chat_history = []

    llm = get_code_llm()
    messages = build_messages(user_message, chat_history)

    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content
            