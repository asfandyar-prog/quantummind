# ── app/core/logging_setup.py ────────────────────────────────
# One logging configuration for the whole app: JSON lines on stdout, level from
# LOG_LEVEL, and the current request's id on every record.
#
# Before this existed nothing configured logging, so Python's default (WARNING,
# no handler) silently dropped every logger.info, including the per-call LLM
# accounting records in core/llm.py.

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

# The id of the request being handled, or "-" outside a request (startup, the
# backfill worker). A ContextVar follows the request into tasks it creates, so
# the off-path accounting task logs with its request's id too.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

REQUEST_ID_HEADER = "x-request-id"


class JsonFormatter(logging.Formatter):
    """One JSON object per line. A message that is itself a JSON object (the
    llm_call accounting records) is merged in, not nested as a string."""

    def format(self, record: logging.LogRecord) -> str:
        line = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": request_id_var.get(),
        }
        msg = record.getMessage()
        fields = None
        if msg.startswith("{"):
            try:
                fields = json.loads(msg)
            except ValueError:
                fields = None
        if isinstance(fields, dict):
            line.update(fields)
        else:
            line["msg"] = msg
        if record.exc_info:
            line["exc"] = self.formatException(record.exc_info)
        return json.dumps(line, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Send the app's loggers (quantummind.*) to stdout as JSON at `level`.

    Only the quantummind logger tree is configured; uvicorn keeps its own
    handlers for access and server logs. Safe to call more than once.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    app_logger = logging.getLogger("quantummind")
    app_logger.handlers = [handler]
    app_logger.setLevel(level.upper())
    # Propagation stays on: the root logger has no handler under uvicorn, so
    # nothing is printed twice, and test tools that listen on root still see
    # these records.


class RequestIdMiddleware:
    """Pure ASGI middleware: take X-Request-ID from the request or mint one,
    expose it to logging through request_id_var, and echo it on the response.
    Pure ASGI (not BaseHTTPMiddleware) so it doesn't buffer the SSE stream."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        incoming = dict(scope.get("headers") or []).get(REQUEST_ID_HEADER.encode())
        rid = incoming.decode("latin-1")[:64] if incoming else uuid.uuid4().hex
        token = request_id_var.set(rid)

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"] = list(message["headers"]) + [(REQUEST_ID_HEADER.encode(), rid.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)
