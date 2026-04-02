# ── app/agents/theory_agent.py ────────────────────────────────
from langchain_groq import ChatGroq
# ChatGroq is LangChain's wrapper around the Groq API.
# It handles: authentication, request formatting, retries,
# and gives us a consistent interface regardless of which
# LLM provider we use. If we ever switch from Groq to OpenAI,
# we only change this one import — everything else stays the same.

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
# These are LangChain's message types. Every LLM conversation is a
# list of messages, each with a role:
#   SystemMessage  → the system prompt (agent's instructions)
#   HumanMessage   → what the user said
#   AIMessage      → what the AI previously responded
# LangChain converts these into the exact format each LLM provider expects.

from langchain_core.output_parsers import StrOutputParser
# StrOutputParser extracts just the text string from the LLM's response.
# Without it, LangChain returns an AIMessage object.
# With it, you get a plain string — much easier to work with.

from app.core.config import settings
from app.core.prompts import THEORY_PROMPT


def get_theory_llm() -> ChatGroq:
    """
    Creates and returns the LLM instance for the Theory agent.

    Why a function instead of a module-level variable?
    Because if we put ChatGroq() at module level, it gets created
    when Python imports the file — even in tests where we don't
    want real API calls. A function gives us control over when
    the LLM is actually instantiated.

    temperature=0.7 means:
    - 0.0 → completely deterministic, same input always gives same output
    - 1.0 → very creative and varied
    - 0.7 → balanced: consistent but not robotic. Good for explanations.
    """
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.7,
    )


def build_messages(user_message: str, chat_history: list[dict]) -> list:
    """
    Converts raw chat history into LangChain message objects.

    Args:
        user_message: The current message from the student
        chat_history: Previous messages as list of dicts:
                      [{"role": "user"|"ai", "content": "..."}]

    Returns:
        List of LangChain message objects ready to send to the LLM

    Why do we need this conversion?
    The frontend sends chat history as plain dicts (JSON-serializable).
    LangChain requires typed message objects. This function bridges the gap.

    The final message list looks like:
    [SystemMessage, HumanMessage, AIMessage, HumanMessage, ...]
                                  ↑ history ↑              ↑ current
                                
    """
    messages = [SystemMessage(content=THEORY_PROMPT)]
    # Always start with the system prompt.
    # This goes first so it sets the context before any conversation.

    # Convert history dicts → LangChain message objects
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            messages.append(AIMessage(content=msg["content"]))
        # We silently skip any unrecognized roles rather than crashing.

    # Add the current user message last
    messages.append(HumanMessage(content=user_message))

    return messages


async def run_theory_agent(
    user_message: str,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Runs the Theory agent and returns a complete response string.

    This is the NON-streaming version — it waits for the full response
    before returning. Used by POST /chat (single turn).

    Args:
        user_message: The student's question
        chat_history: Previous conversation turns (optional)

    Returns:
        The agent's complete response as a string

    Usage:
        response = await run_theory_agent(
            user_message="What is superposition?",
            chat_history=[{"role": "user", "content": "hi"}, ...]
        )
    """
    if chat_history is None:
        chat_history = []
    # Always default mutable arguments to None, not [].
    # Python reuses the same list object across calls if you use [] as default.
    # This is a classic Python gotcha that causes very subtle bugs.

    llm = get_theory_llm()
    parser = StrOutputParser()

    # LangChain chain: llm → parser
    # The | operator is LangChain's "pipe" — chains steps together.
    # llm returns an AIMessage, parser extracts the .content string.
    chain = llm | parser

    messages = build_messages(user_message, chat_history)

    # ainvoke = async invoke. We use async because FastAPI is async.
    # Calling a synchronous function inside an async route blocks the
    # entire server — no other requests can be processed while waiting.
    # ainvoke releases control back to the event loop while waiting for Groq.
    response = await chain.ainvoke(messages)

    return response


async def stream_theory_agent(
    user_message: str,
    chat_history: list[dict] | None = None,
):
    """
    Runs the Theory agent in STREAMING mode.

    Instead of waiting for the full response, this yields tokens
    as they arrive from Groq — word by word.

    This is an async GENERATOR function (note: yield instead of return).
    The caller iterates over it to get tokens one at a time.

    Usage:
        async for token in stream_theory_agent("What is superposition?"):
            print(token, end="", flush=True)

    The streaming route (POST /stream) will use this to push
    tokens to the frontend via Server-Sent Events.
    """
    if chat_history is None:
        chat_history = []

    llm = get_theory_llm()
    messages = build_messages(user_message, chat_history)

    # astream = async streaming version of ainvoke.
    # It yields AIMessageChunk objects as they arrive.
    # .content on each chunk is the next token(s) from the LLM.
    async for chunk in llm.astream(messages):
        if chunk.content:
            # Only yield non-empty chunks.
            # Sometimes LLMs send empty chunks at start/end.
            yield chunk.content