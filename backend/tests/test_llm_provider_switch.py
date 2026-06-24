"""Proof: switching the provider is config-only — the seam resolves the right
base URL + key per provider, the validator fails fast on bad config, and the
client is constructed with the expected kwargs. No real network."""
import pytest

from app.core import llm
from app.core.config import Settings, settings


# ── base URL + API key resolution (pure functions; always run) ────────────────

def test_groq_uses_openai_compatible_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "llm_base_url", None)
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.setattr(settings, "groq_api_key", "gk")
    assert llm._resolve_base_url() == "https://api.groq.com/openai/v1"
    assert llm._resolve_api_key() == "gk"


def test_openai_uses_sdk_default(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_base_url", None)
    monkeypatch.setattr(settings, "llm_api_key", "ok")
    assert llm._resolve_base_url() is None
    assert llm._resolve_api_key() == "ok"


def test_vllm_uses_base_url_and_placeholder_key(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "vllm")
    monkeypatch.setattr(settings, "llm_base_url", "http://gpu:8000/v1")
    monkeypatch.setattr(settings, "llm_api_key", None)
    assert llm._resolve_base_url() == "http://gpu:8000/v1"
    assert llm._resolve_api_key() == "EMPTY"


def test_base_url_override_wins(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "llm_base_url", "http://proxy/v1")
    assert llm._resolve_base_url() == "http://proxy/v1"


# ── temperature centralization ────────────────────────────────────────────────

def test_call_type_resolves_expected_temperature():
    assert llm._resolve_params("theory", None, None)[1] == 0.7
    assert llm._resolve_params("code", None, None)[1] == 0.1
    assert llm._resolve_params("exam_grade", None, None)[1] == 0.0
    # explicit override wins over the call_type default
    assert llm._resolve_params("theory", 0.0, None)[1] == 0.0
    # unknown call_type falls back to the default
    assert llm._resolve_params("nope", None, None)[1] == llm.DEFAULT_TEMPERATURE


# ── fail-fast validator ───────────────────────────────────────────────────────

def test_unknown_provider_fails_fast():
    with pytest.raises(Exception):
        Settings(_env_file=None, llm_provider="bogus", groq_api_key="x")


def test_vllm_without_base_url_fails_fast():
    with pytest.raises(Exception):
        Settings(_env_file=None, llm_provider="vllm", llm_base_url=None, llm_api_key=None)


def test_groq_without_key_fails_fast():
    with pytest.raises(Exception):
        Settings(_env_file=None, llm_provider="groq", groq_api_key=None, llm_api_key=None)


# ── client construction (needs langchain-openai installed) ────────────────────

def test_build_client_passes_groq_params(monkeypatch):
    pytest.importorskip("langchain_openai")
    import langchain_openai

    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "llm_base_url", None)
    monkeypatch.setattr(settings, "groq_api_key", "gk")
    monkeypatch.setattr(settings, "llm_api_key", None)

    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(langchain_openai, "ChatOpenAI", FakeChatOpenAI)

    llm._build_client("some-model", 0.0, None)
    assert captured["base_url"] == "https://api.groq.com/openai/v1"
    assert captured["model"] == "some-model"
    assert str(captured["api_key"]) == "gk" or captured["api_key"] == "gk"
