"""Single entry point for every LLM call (Mistral).

Modes (settings.llm_mode):
  live  - Mistral chat completions (tool calling / JSON mode), timeout + one retry
  stub  - canned, deterministic outputs registered per agent (tests, offline demo)
  off   - every call raises LLMUnavailable (demo "the LLM is down")

Callers must treat LLMUnavailable as normal and fall back to rules/templates.
"""

import json
import logging
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
    res = _complete(messages=messages, tools=tools, tool_choice=tool_choice, parallel_tool_calls=False)
    msg = res.choices[0].message
    calls = []
    for tc in msg.tool_calls or []:
        args = tc.function.arguments
        if isinstance(args, str):
            try:
                args = json.loads(args or "{}")
            except json.JSONDecodeError:
                args = {"_unparseable": args}
        calls.append(ToolCall(id=tc.id or new_call_id(), name=tc.function.name, arguments=args or {}))
    return Reply(content=_text(msg.content), tool_calls=calls, mode="live", ms=int((time.perf_counter() - t0) * 1000))


def chat_json(agent: str, messages: list[dict], context: dict | None = None) -> dict:
    """Structured output: returns a parsed JSON object (validate it with Pydantic in the caller)."""
    m = mode()
    if m == "off":
        raise LLMUnavailable("LLM disabled (LLM_MODE=off)")
    if m == "stub":
        return _stub(agent, messages, context)
    last_err = None
    for _ in range(2):
        res = _complete(messages=messages, response_format={"type": "json_object"})
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
    return status is None or status == 429 or status >= 500  # network/timeout, rate limit, server error


def _complete(**kwargs):
    client = _mistral()
    last: Exception | None = None
    for attempt in range(3):
        _pace()
        try:
            return client.chat.complete(model=settings.mistral_model, temperature=0.2, max_tokens=1500,
                                        timeout_ms=int(settings.llm_timeout_s * 1000), **kwargs)
        except Exception as e:
            last = e
            log.warning("Mistral call failed (attempt %d): %s", attempt + 1, e)
            if not _retryable(e):  # 400/401/403/422: retrying cannot help (bad key, model not in tier, ...)
                break
            time.sleep(1.5 * (attempt + 1))
    raise LLMUnavailable(f"Mistral unavailable: {last}")


def _text(content) -> str:
    if isinstance(content, list):  # content chunks
        content = "".join(getattr(c, "text", "") for c in content)
    return (content or "").strip()

from . import llm_stubs  # noqa: E402,F401  (registers the stub-mode behaviours)
