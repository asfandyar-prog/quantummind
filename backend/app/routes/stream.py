# ── app/routes/stream.py ─────────────────────────────────────
# SSE streaming with progress events.
# Progress events tell the frontend what's happening during processing
# so users see activity immediately instead of a blank loading state.

import json
import asyncio
import uuid
from typing import Literal
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.agents.orchestrator import stream_agent

import logging

logger = logging.getLogger("quantummind.routes.stream")

router = APIRouter()


class HistoryMessage(BaseModel):
    """One earlier turn the client sends back so the tutor can follow the conversation."""
    role:    Literal["user", "ai"]
    content: str = Field(..., max_length=8000)


class StreamRequest(BaseModel):
    message:      str                  = Field(..., min_length=1)
    mode:         str                  = Field(default="guided")
    chat_history: list[HistoryMessage] = Field(default=[], max_length=50)
    # Omit it and the request gets a fresh thread, never one shared with other callers.
    thread_id:    str                  = Field(default_factory=lambda: f"stream-{uuid.uuid4().hex}")
    week:         int                  = Field(default=0, ge=0, le=13)   # RAG: course week, 0 = all


def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/stream")
async def stream_response(request: StreamRequest):
    async def generate():
        try:
            # Send immediate progress event — user sees activity in <100ms
            # This is the key UX improvement: never show a blank spinner
            mode_labels = {
                "theory":   "Thinking about your question…",
                "practice": "Analyzing your code…",
                "guided":   "Preparing your lesson…",
                "course":   "Thinking about your question…",  # the router decides whether to search
            }
            progress_msg = mode_labels.get(request.mode, "Processing…")
            yield sse_event({"type": "progress", "content": progress_msg})

            # Small delay to ensure progress event is flushed
            await asyncio.sleep(0.05)

            # Stream tokens as they arrive
            token_count = 0
            async for token in stream_agent(
                user_message=request.message,
                chat_history=[m.model_dump() for m in request.chat_history],
                mode=request.mode,
                thread_id=request.thread_id,
                week=request.week,
            ):
                yield sse_event({"type": "token", "content": token})
                token_count += 1

            yield sse_event({"type": "done", "token_count": token_count})

        except Exception as e:
            logger.exception(f"Error: {e}")
            yield sse_event({"type": "error", "content": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            # No Access-Control-Allow-Origin here. CORSMiddleware in app/main.py
            # sets it from FRONTEND_URL for every response, streaming included;
            # hardcoding "*" here overrode that and let any origin read the
            # stream — the one endpoint that carries the LLM's answers.
        },
    )


@router.get("/cache/stats")
async def cache_stats():
    """Monitor cache performance — check this to see hit rates."""
    from app.core.cache import cache
    return cache.stats()