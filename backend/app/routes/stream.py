# ── app/routes/stream.py ─────────────────────────────────────
# SSE streaming with progress events.
# Progress events tell the frontend what's happening during processing
# so users see activity immediately instead of a blank loading state.

import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.agents.orchestrator import stream_agent

router = APIRouter()


class StreamRequest(BaseModel):
    message:      str        = Field(..., min_length=1)
    mode:         str        = Field(default="guided")
    chat_history: list[dict] = Field(default=[])
    thread_id:    str        = Field(default="default")
    week:         int        = Field(default=0)


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
                "course":   "Searching course materials…",
            }
            progress_msg = mode_labels.get(request.mode, "Processing…")
            yield sse_event({"type": "progress", "content": progress_msg})

            # Small delay to ensure progress event is flushed
            await asyncio.sleep(0.05)

            # Stream tokens as they arrive
            token_count = 0
            async for token in stream_agent(
                user_message=request.message,
                chat_history=request.chat_history,
                mode=request.mode,
                thread_id=request.thread_id,
                week=request.week,
            ):
                yield sse_event({"type": "token", "content": token})
                token_count += 1

            yield sse_event({"type": "done", "token_count": token_count})

        except Exception as e:
            print(f"[/stream] Error: {e}")
            yield sse_event({"type": "error", "content": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/cache/stats")
async def cache_stats():
    """Monitor cache performance — check this to see hit rates."""
    from app.core.cache import cache
    return cache.stats()