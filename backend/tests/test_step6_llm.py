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


def test_permanent_errors_not_retried_rate_limits_are(monkeypatch):
    calls = {"n": 0}

    class Err(Exception):
        def __init__(self, status):
            super().__init__(f"status {status}")
            self.status_code = status

    def make(status):
        class Fake:
            class chat:
                @staticmethod
                def complete(**kw):
                    calls["n"] += 1
                    raise Err(status)
        return Fake
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(settings, "mistral_api_key", "x")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    monkeypatch.setattr(llm, "_client", make(403))  # e.g. model not in subscription tier
    with pytest.raises(llm.LLMUnavailable):
        llm.chat_json("digest", [{"role": "user", "content": "hi"}])
    assert calls["n"] == 1
    calls["n"] = 0
    monkeypatch.setattr(llm, "_client", make(429))
    with pytest.raises(llm.LLMUnavailable):
        llm.chat_tools("investigation", [], [])
    assert calls["n"] == 5


def test_groq_provider_maps_openai_response(monkeypatch):
    import httpx
    sent = {}

    class Resp:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": None, "tool_calls": [
                {"id": "call_1", "type": "function",
                 "function": {"name": "get_vitals_trend", "arguments": "{\"metric\": \"hr\", \"hours\": 24}"}}]}}]}

    def fake_post(url, json, timeout, headers):
        sent.update(url=url, body=json)
        return Resp()
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(settings, "llm_provider", "groq")
    monkeypatch.setattr(settings, "groq_api_key", "gsk_test")
    monkeypatch.setattr(httpx, "post", fake_post)
    r = llm.chat_tools("investigation", [{"role": "user", "content": "go"}], [{"type": "function"}],
                       tool_choice="any")
    assert "groq.com" in sent["url"] and sent["body"]["tool_choice"] == "required"
    assert r.tool_calls[0].name == "get_vitals_trend" and r.tool_calls[0].arguments == {"metric": "hr", "hours": 24}


def test_retry_after_parsed_from_groq_message():
    body = "Rate limit reached ... Please try again in 6.825s. Need more tokens?"
    assert llm._retry_after({}, body) == 6.825
    assert llm._retry_after({}, "Please try again in 1m2.5s.") == 62.5
    assert llm._retry_after({"retry-after": "3"}, "") == 3.0


def test_prefixed_tool_names_are_normalised(monkeypatch):
    from types import SimpleNamespace as NS
    msg = NS(content="", tool_calls=[NS(id="x1", function=NS(name="name=functions.finish_investigation",
                                                             arguments="{}"))])

    class Fake:
        class chat:
            @staticmethod
            def complete(**kw):
                return NS(choices=[NS(message=msg)])
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(settings, "mistral_api_key", "x")
    monkeypatch.setattr(llm, "_client", Fake)
    assert llm.chat_tools("investigation", [], []).tool_calls[0].name == "finish_investigation"


def test_per_agent_routing(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setenv("LLM_ROUTE_DIGEST", "groq:openai/gpt-oss-20b")
    monkeypatch.setenv("LLM_ROUTE_CHECKIN_CLARIFY", "groq")
    monkeypatch.delenv("LLM_ROUTE_INVESTIGATION", raising=False)
    assert llm.route("digest") == ("groq", "openai/gpt-oss-20b")
    assert llm.route("checkin_clarify") == ("groq", settings.groq_model)
    assert llm.route("investigation") == ("openrouter", settings.openrouter_model)
