# ── app/routes/stream.py ─────────────────────────────────────
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
# StreamingResponse tells FastAPI to send the response body
# as a stream of chunks instead of one big payload.
# The browser receives and renders each chunk as it arrives —
# this is what makes text appear word by word in the frontend.

from pydantic import BaseModel, Field
import json
# json.dumps() converts Python dicts to JSON strings.
# We use it to format each SSE event as JSON so the frontend
# can parse it easily.

from app.agents.orchestrator import stream_agent


# ── Request model ─────────────────────────────────────────────
class StreamRequest(BaseModel):
    """Request body for POST /api/stream"""
    message: str = Field(..., min_length=1)
    mode: str = Field(default="guided")
    chat_history: list[dict] = Field(default=[])


# ── SSE event formatters ──────────────────────────────────────
# SSE (Server-Sent Events) has a specific text format:
#   data: <your content here>\n\n
#
# The browser's EventSource API parses this format automatically.
# Each event MUST end with \n\n (two newlines) — one newline is
# part of the data, two newlines signal the end of one event.

def format_token_event(token: str) -> str:
    """
    Formats a single token as an SSE event.

    Example output:
        data: {"type": "token", "content": "Quantum"}\n\n

    The frontend reads event.data, parses the JSON,
    and appends event.content to the message being built.
    """
    payload = json.dumps({"type": "token", "content": token})
    return f"data: {payload}\n\n"


def format_done_event() -> str:
    """
    Signals to the frontend that streaming is complete.

    Example output:
        data: {"type": "done"}\n\n

    When the frontend receives this, it:
    1. Stops the typing indicator
    2. Adds the complete message to chat history
    3. Re-enables the input field
    """
    payload = json.dumps({"type": "done"})
    return f"data: {payload}\n\n"


def format_error_event(error: str) -> str:
    """
    Sends an error event if something goes wrong mid-stream.

    The frontend shows this as an error message in the chat
    instead of a broken partial response.
    """
    payload = json.dumps({"type": "error", "content": error})
    return f"data: {payload}\n\n"


# ── Router ────────────────────────────────────────────────────
router = APIRouter()


@router.post("/stream")
async def stream(request: StreamRequest):
    """
    Streaming chat endpoint using Server-Sent Events.

    This is the PRIMARY endpoint used by the frontend.
    Instead of waiting for a complete response, tokens
    are sent to the browser as they arrive from Groq.

    Flow:
    1. Frontend sends POST /api/stream with message + history
    2. Backend routes to correct agent
    3. Agent starts streaming tokens from Groq
    4. Each token is immediately forwarded to the frontend as SSE
    5. Frontend appends each token to the message in real time
    6. When done, backend sends {"type": "done"}
    7. Frontend finalizes the message

    Why POST instead of GET for SSE?
    Traditional SSE uses GET. But GET requests can't have a body,
    so we can't send the message + history in the URL (too long, insecure).
    POST with StreamingResponse solves this cleanly.
    """
    async def event_generator():
        """
        Inner async generator that produces SSE events.

        Why an inner function?
        StreamingResponse needs a callable that returns an async iterator.
        By defining the generator inside the route handler, it has access
        to `request` via closure — clean and no global state needed.
        """
        try:
            # Stream tokens from the orchestrator
            async for token in stream_agent(
                user_message=request.message,
                chat_history=request.chat_history,
                mode=request.mode,
            ):
                yield format_token_event(token)
                # Each yield sends one SSE event to the browser immediately.
                # The browser doesn't wait for the next yield —
                # it processes and renders each event as it arrives.

            # Signal completion
            yield format_done_event()

        except Exception as e:
            print(f"[/stream] Error during streaming: {e}")
            yield format_error_event(str(e))

    return StreamingResponse(
        event_generator(),
        # media_type tells the browser this is an SSE stream.
        # Without this, the browser buffers the entire response
        # and defeats the purpose of streaming.
        media_type="text/event-stream",
        headers={
            # Disable caching — SSE responses must never be cached
            "Cache-Control": "no-cache",
            # Keep the connection open between events
            "Connection": "keep-alive",
            # Required for SSE to work through some proxies/nginx
            "X-Accel-Buffering": "no",
        }
    )