# ── app/routes/chat.py ────────────────────────────────────────
from fastapi import APIRouter, HTTPException
# APIRouter is like a mini FastAPI app.
# Instead of putting all routes in main.py, we split them into
# separate files and register each router in main.py.
# This keeps main.py clean and each route file focused.
#
# HTTPException is how you return error responses in FastAPI.
# raise HTTPException(status_code=400, detail="Bad request")
# automatically sends the right HTTP error to the frontend.

from pydantic import BaseModel, Field
# BaseModel: base class for all request/response shapes.
# Field: adds validation rules and documentation to fields.

from app.agents.orchestrator import run_agent


# ── Request / Response models ─────────────────────────────────
# These Pydantic models do three things simultaneously:
# 1. Validate incoming JSON (wrong types = automatic 422 error)
# 2. Document the API (shows up in /docs automatically)
# 3. Give you type hints inside your route functions

class MessageDict(BaseModel):
    """A single message in the chat history."""
    role: str = Field(..., description="Either 'user' or 'ai'")
    content: str = Field(..., description="The message text")

    # ... means the field is REQUIRED (no default value)
    # If the frontend doesn't send it, Pydantic raises a 422 error
    # with a clear message explaining what's missing.


class ChatRequest(BaseModel):
    """Request body for POST /api/chat"""
    message: str = Field(..., min_length=1, description="The student's question")
    # min_length=1 prevents empty strings from reaching the LLM.
    # Pydantic validates this before your code even runs.

    mode: str = Field(default="guided", description="App mode: theory, practice, or guided")

    chat_history: list[MessageDict] = Field(
        default=[],
        description="Previous conversation turns for context"
    )


class ChatResponse(BaseModel):
    """Response body for POST /api/chat"""
    response: str = Field(..., description="The agent's response")
    agent_used: str = Field(..., description="Which agent handled this message")


# ── Router ────────────────────────────────────────────────────
router = APIRouter()
# We register this router in main.py with prefix="/api"
# so this route becomes: POST /api/chat


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Single-turn chat endpoint.

    Receives the student's message, routes it to the correct agent,
    waits for the full response, then returns it.

    Use this for:
    - Simple Q&A where streaming isn't needed
    - Testing agents without SSE complexity

    For real-time streaming responses use POST /api/stream instead.
    """
    try:
        # Convert Pydantic models back to plain dicts for the agents.
        # Our agent functions expect list[dict], not list[MessageDict].
        history = [msg.model_dump() for msg in request.chat_history]
        # model_dump() converts a Pydantic model → Python dict
        # MessageDict(role="user", content="hi") → {"role": "user", "content": "hi"}

        response = await run_agent(
            user_message=request.message,
            chat_history=history,
            mode=request.mode,
        )

        # We don't have a clean way to get agent_used from run_agent yet.
        # For now we return "orchestrator" — we'll improve this later.
        return ChatResponse(
            response=response,
            agent_used="orchestrator",
        )

    except Exception as e:
        # Catch ALL exceptions so the server never returns a raw 500 error.
        # Raw 500s expose stack traces to the frontend — a security risk.
        # HTTPException gives a clean JSON error response instead.
        print(f"[/chat] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@router.get("/chat/health")
async def chat_health():
    """Quick check that the chat route is registered and reachable."""
    return {"status": "ok", "route": "/api/chat"}


@router.get("/history/{thread_id}")
async def get_history(thread_id: str):
    """
    Returns the conversation history for a thread_id.
    Called by the frontend on page load to restore previous messages.
    """
    from app.core.memory import get_checkpointer
    try:
        cp = get_checkpointer()
        if cp is None:
            return {"messages": []}

        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = await cp.aget(config)

        if not checkpoint:
            return {"messages": []}

        # Extract messages from checkpoint state
        # LangGraph stores the full state — we pull chat_history
        state = checkpoint.get("channel_values", {})
        messages = []

        # Reconstruct from the agent's final responses
        # We look for user messages and AI responses in the state
        return {"messages": messages, "found": True}

    except Exception as e:
        print(f"[/history] Error: {e}")
        return {"messages": []}