import pytest

from app import llm
from app import models as m
from app.config import settings


def test_stub_outputs_are_schema_valid():
    c = m.ClarificationOut.model_validate(llm.chat_json("checkin_clarify", [], {"item": "fatigue", "before": 2, "now": 4}))
    assert "tiredness" in c.text and len(c.options) == 3
    d = m.DigestOut.model_validate(llm.chat_json("digest", [], {"first_name": "Sarah", "events": [
        {"category": "symptoms", "text": "check-in"}, {"category": "alerts", "text": "review"}]}))
    assert d.summary and len(d.tasks) <= 3


def test_unknown_stub_is_unavailable():
    with pytest.raises(llm.LLMUnavailable):
        llm.chat_json("nope", [])


def test_off_mode_raises(monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "off")
    with pytest.raises(llm.LLMUnavailable):
        llm.chat_json("digest", [])
    with pytest.raises(llm.LLMUnavailable):
        llm.chat_tools("investigation", [], [])


def test_live_errors_become_unavailable(monkeypatch):
    class Boom:
        class chat:
            @staticmethod
            def complete(**kw):
                raise TimeoutError("read timeout")
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(llm, "_client", Boom)
    monkeypatch.setattr(settings, "mistral_api_key", "x")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    with pytest.raises(llm.LLMUnavailable):
        llm.chat_json("digest", [{"role": "user", "content": "hi"}])


def test_live_missing_key_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(settings, "mistral_api_key", "")
    with pytest.raises(llm.LLMUnavailable):
        llm.chat_tools("investigation", [], [])


def test_live_tool_call_parsing(monkeypatch):
    from types import SimpleNamespace as NS
    msg = NS(content="", tool_calls=[NS(id="abc123def", function=NS(name="get_medication_context", arguments="{}"))])

    class Fake:
        class chat:
            @staticmethod
            def complete(**kw):
                assert kw["parallel_tool_calls"] is False and kw["tools"]
                return NS(choices=[NS(message=msg)])
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(settings, "mistral_api_key", "x")
    monkeypatch.setattr(llm, "_client", Fake)
    r = llm.chat_tools("investigation", [{"role": "user", "content": "go"}], [{"type": "function"}])
    assert r.tool_calls[0].name == "get_medication_context" and r.message["tool_calls"][0]["id"] == "abc123def"
