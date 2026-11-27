"""Logs actually come out, as JSON, tagged with the request id.

Before, nothing configured logging, so every logger.info (the per-call LLM
accounting included) was dropped by Python's WARNING default.
"""
import asyncio
import io
import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.core.llm as llm_mod
from app.core import logging_setup
from app.core.logging_setup import JsonFormatter, RequestIdMiddleware, request_id_var
from app.main import app as main_app


def _capture():
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("quantummind")
    logger.addHandler(handler)
    return buf, handler, logger


def test_importing_the_app_configures_the_quantummind_logger():
    logger = logging.getLogger("quantummind")
    assert logger.getEffectiveLevel() <= logging.INFO
    assert any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers)


def test_llm_accounting_record_is_emitted_as_json(monkeypatch):
    async def no_counters(total):   # keep Redis out of it
        return None

    monkeypatch.setattr(llm_mod, "_bump_counters", no_counters)
    buf, handler, logger = _capture()
    token = request_id_var.set("req-123")
    try:
        asyncio.run(llm_mod._account("theory", "llama-3.1-8b-instant", None, 42, "ok"))
    finally:
        request_id_var.reset(token)
        logger.removeHandler(handler)
    lines = [json.loads(l) for l in buf.getvalue().splitlines()]
    rec = next(l for l in lines if l.get("event") == "llm_call")
    assert rec["level"] == "INFO" and rec["logger"] == "quantummind.llm"
    assert rec["request_id"] == "req-123"
    assert rec["call_type"] == "theory" and rec["latency_ms"] == 42   # merged, not a nested string


def test_request_id_is_echoed_or_generated():
    client = TestClient(main_app)
    res = client.get("/health", headers={"X-Request-ID": "abc-1"})
    assert res.headers["x-request-id"] == "abc-1"
    generated = client.get("/health").headers["x-request-id"]
    assert len(generated) == 32


def test_logs_inside_a_request_carry_its_id():
    tiny = FastAPI()
    tiny.add_middleware(RequestIdMiddleware)

    @tiny.get("/ping")
    async def ping():
        logging.getLogger("quantummind.test").info("inside the request")
        return {"ok": True}

    buf, handler, logger = _capture()
    try:
        TestClient(tiny).get("/ping", headers={"X-Request-ID": "rid-9"})
    finally:
        logger.removeHandler(handler)
    rec = next(json.loads(l) for l in buf.getvalue().splitlines() if "inside the request" in l)
    assert rec["request_id"] == "rid-9" and rec["msg"] == "inside the request"


def test_level_comes_from_settings():
    logging_setup.configure_logging("WARNING")
    try:
        assert logging.getLogger("quantummind").level == logging.WARNING
    finally:
        logging_setup.configure_logging("INFO")
