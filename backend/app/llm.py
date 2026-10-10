"""Single entry point for every LLM call (Mistral).

Modes (settings.llm_mode):
  live  - Mistral chat completions (tool calling / JSON mode), timeout + one retry
  stub  - canned, deterministic outputs registered per agent (tests, offline demo)
  off   - every call raises LLMUnavailable (demo "the LLM is down")

Callers must treat LLMUnavailable as normal and fall back to rules/templates.
"""

import json
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from .config import settings

log = logging.getLogger("surgiguard.llm")


class LLMUnavailable(Exception):
    """Network / auth / quota / timeout / disabled. The caller falls back."""


class LLMBadOutput(LLMUnavailable):
    """The model answered but not in the required shape."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Reply:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    mode: str = "stub"
    ms: int = 0

    @property
    def message(self) -> dict:
        """Assistant message to append to the conversation history (Mistral format)."""
        msg: dict[str, Any] = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            msg["tool_calls"] = [{"id": tc.id, "type": "function",
                                  "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}}
                                 for tc in self.tool_calls]
        return msg


def tool_message(call: ToolCall, result: Any) -> dict:
    return {"role": "tool", "name": call.name, "tool_call_id": call.id,
            "content": json.dumps(result, default=str)}


def new_call_id() -> str:
    return uuid.uuid4().hex[:9]  # Mistral expects 9-char alphanumeric ids


# ------------------------------------------------------------------ stubs

_stubs: dict[str, Callable[[list[dict], dict], Any]] = {}


def stub(agent: str):
    """Register the canned behaviour of an agent: fn(messages, context) -> Reply | dict."""
    def deco(fn):
        _stubs[agent] = fn
        return fn
    return deco


def mode() -> str:
    return settings.llm_mode


# ------------------------------------------------------------------ public API

def chat_tools(agent: str, messages: list[dict], tools: list[dict], context: dict | None = None,
               tool_choice: str = "auto") -> Reply:
    """One step of a tool-calling loop."""
    m = mode()
    if m == "off":
        raise LLMUnavailable("LLM disabled (LLM_MODE=off)")
    if m == "stub":
        out = _stub(agent, messages, context)
        out.mode = "stub"
        return out
    t0 = time.perf_counter()
    res = _complete(agent, messages=messages, tools=tools, tool_choice=tool_choice, parallel_tool_calls=False)
    msg = res.choices[0].message
    calls = []
    for tc in msg.tool_calls or []:
        args = tc.function.arguments
        if isinstance(args, str):
            try:
                args = json.loads(args or "{}")
            except json.JSONDecodeError:
                args = {"_unparseable": args}
        # Some models prefix the name ("functions.x", "name=functions.x"); keep the bare tool name.
        name = re.sub(r"^(name=)?(functions\.)?", "", (tc.function.name or "").strip())
        calls.append(ToolCall(id=tc.id or new_call_id(), name=name, arguments=args or {}))
    return Reply(content=_text(msg.content), tool_calls=calls, mode="live", ms=int((time.perf_counter() - t0) * 1000))


def chat_text(agent: str, messages: list[dict], context: dict | None = None) -> str:
    """Plain conversational reply (Recovery Assistant chat)."""
    m = mode()
    if m == "off":
        raise LLMUnavailable("LLM disabled (LLM_MODE=off)")
    if m == "stub":
        return _stub(agent, messages, context)
    text = _text(_complete(agent, messages=messages).choices[0].message.content)
    if not text:
        raise LLMBadOutput("empty reply from model")
    return text


def chat_json(agent: str, messages: list[dict], context: dict | None = None, max_tokens: int | None = None) -> dict:
    """Structured output: returns a parsed JSON object (validate it with Pydantic in the caller)."""
    m = mode()
    if m == "off":
        raise LLMUnavailable("LLM disabled (LLM_MODE=off)")
    if m == "stub":
        return _stub(agent, messages, context)
    last_err = None
    for _ in range(2):
        extra = {"max_tokens": max_tokens} if max_tokens else {}
        res = _complete(agent, messages=messages, response_format={"type": "json_object"}, **extra)
        raw = _text(res.choices[0].message.content)
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
            last_err = "not a JSON object"
        except json.JSONDecodeError as e:
            last_err = str(e)
    raise LLMBadOutput(f"invalid JSON from model: {last_err}")


# ------------------------------------------------------------------ internals

def _stub(agent: str, messages: list[dict], context: dict | None):
    fn = _stubs.get(agent)
    if fn is None:
        raise LLMUnavailable(f"no stub registered for {agent}")
    return fn(messages, context or {})


_client = None


def _mistral():
    global _client
    if not settings.mistral_api_key:
        raise LLMUnavailable("MISTRAL_API_KEY is not set")
    if _client is None:
        from mistralai.client import Mistral
        _client = Mistral(api_key=settings.mistral_api_key)
    return _client


_pace_lock = threading.Lock()
_last_call = 0.0


def _pace() -> None:
    """Space out calls (free tiers allow ~1 request/s). Shared by all agent threads."""
    global _last_call
    with _pace_lock:
        wait = settings.llm_min_interval_s - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _retryable(e: Exception) -> bool:
    status = getattr(e, "status_code", None)
    if status == 400 and "tool_use_failed" in str(e):  # Groq: model produced a malformed tool call; resample
        return True
    return status is None or status == 429 or status >= 500  # network/timeout, rate limit, server error


class ProviderError(Exception):
    def __init__(self, status_code: int, body: str, retry_after: float | None = None):
        super().__init__(f"HTTP {status_code}: {body[:300]}")
        self.status_code = status_code
        self.retry_after = retry_after


def _retry_after(headers, body: str) -> float | None:
    """Groq says how long to wait: a retry-after header or 'Please try again in 6.8s' / '1m2.5s'."""
    try:
        if headers.get("retry-after"):
            return float(headers["retry-after"])
    except ValueError:
        pass
    m_ = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", body)
    return (int(m_.group(1) or 0) * 60 + float(m_.group(2))) if m_ else None


OPENAI_COMPATIBLE = {  # provider -> (endpoint, key setting, model setting)
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "groq_api_key", "groq_model"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "openrouter_api_key", "openrouter_model"),
}


def route(agent: str) -> tuple[str, str]:
    """(provider, model) for an agent. LLM_ROUTE_<AGENT>=provider:model spreads agents over providers/models
    so one free-tier quota is not shared by everything; otherwise LLM_PROVIDER and its model."""
    import os
    spec = os.getenv(f"LLM_ROUTE_{agent.upper()}", "").strip()
    if spec:
        provider, _, model = spec.partition(":")
        provider = provider.strip().lower()
        return provider, model.strip() or getattr(settings, f"{provider}_model", "")
    provider = settings.llm_provider
    return provider, getattr(settings, f"{provider}_model", settings.mistral_model)


def _openai_complete(provider: str, model: str, **kwargs):
    """Groq / OpenRouter (OpenAI-compatible), returned in the same shape as the Mistral SDK response."""
    import httpx
    from types import SimpleNamespace as NS
    url, key_attr, _ = OPENAI_COMPATIBLE[provider]
    key = getattr(settings, key_attr)
    if not key:
        raise LLMUnavailable(f"{key_attr.upper()} is not set")
    # Groq counts max_tokens against the per-minute token limit up front, so keep it modest there.
    body = {"model": model, "temperature": 0.2, "max_tokens": 1000 if provider == "groq" else 2000, **kwargs}
    if body.get("tool_choice") == "any":  # Mistral's "must call a tool" == OpenAI's "required"
        body["tool_choice"] = "required"
    if provider == "groq" and model.startswith("openai/gpt-oss"):
        body["reasoning_effort"] = "low"  # hidden reasoning tokens count against the per-minute token limit
    r = httpx.post(url, json=body, timeout=settings.llm_timeout_s,
                   headers={"Authorization": f"Bearer {key}", "X-Title": "SurgiGuard AI (hackathon demo)"})
    if r.status_code != 200:
        raise ProviderError(r.status_code, r.text, _retry_after(r.headers, r.text))
    data = r.json()
    if "choices" not in data:  # OpenRouter can return 200 with an upstream error object
        err = data.get("error", {})
        raise ProviderError(int(err.get("code") or 502), str(err)[:300])
    msg = data["choices"][0]["message"]
    calls = [NS(id=tc.get("id"), function=NS(name=tc["function"]["name"], arguments=tc["function"]["arguments"]))
             for tc in msg.get("tool_calls") or []]
    return NS(choices=[NS(message=NS(content=msg.get("content"), tool_calls=calls))])


def _complete(agent: str, **kwargs):
    provider, model = route(agent)
    compat = provider in OPENAI_COMPATIBLE
    if not compat and provider != "mistral":
        raise LLMUnavailable(f"unknown LLM provider {provider!r}")
    client = None if compat else _mistral()
    last: Exception | None = None
    attempt, rate_waited = 0, 0.0
    while True:
        attempt += 1
        _pace()
        try:
            if compat:
                return _openai_complete(provider, model, **kwargs)
            return client.chat.complete(model=model, temperature=0.2, timeout_ms=int(settings.llm_timeout_s * 1000),
                                        **{"max_tokens": 1500, **kwargs})
        except LLMUnavailable:
            raise
        except Exception as e:
            last = e
            log.warning("%s/%s call failed (attempt %d): %s", provider, model, attempt, e)
            if not _retryable(e):  # 400/401/403/422: retrying cannot help
                break
            hint = getattr(e, "retry_after", None)
            if hint is not None:  # the provider said how long to wait: follow it within a total budget
                wait = hint + 0.5
                if rate_waited + wait > settings.llm_rate_wait_max_s:
                    break
                rate_waited += wait
            else:
                if attempt >= 5:
                    break
                wait = 1.5 * attempt
            time.sleep(wait)
    raise LLMUnavailable(f"{provider}/{model} unavailable: {last}")


def _text(content) -> str:
    if isinstance(content, list):  # content chunks
        content = "".join(getattr(c, "text", "") for c in content)
    return (content or "").strip()

from . import llm_stubs  # noqa: E402,F401  (registers the stub-mode behaviours)
