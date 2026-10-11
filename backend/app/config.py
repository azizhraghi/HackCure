"""Runtime configuration (environment variables, demo timeouts), shared by D2 and D3.

Values are read once at import; tests override attributes on `settings` directly.
D3 code uses the lowercase fields; D2 code (app/ai, app/api/v1) uses the UPPERCASE names and
get_chat_llm()/get_embeddings(), which go through the same keys, LLM_MODE and LLM_ROUTE_D2.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

PROVIDERS = ("groq", "openrouter", "mistral")


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


def _key(name: str) -> str:
    """API key from the environment; template placeholders such as 'your-groq-api-key' count as unset."""
    value = os.getenv(name, "").strip()
    return "" if value.lower().startswith("your-") else value


@dataclass
class Settings:
    mistral_api_key: str = field(default_factory=lambda: _key("MISTRAL_API_KEY"))
    mistral_model: str = field(default_factory=lambda: os.getenv("MISTRAL_MODEL", "mistral-medium-latest"))
    # mistral | groq | openrouter (the last two use the OpenAI-compatible API) | auto (first with a key)
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "auto").strip().lower())
    groq_api_key: str = field(default_factory=lambda: _key("GROQ_API_KEY"))
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))
    openrouter_api_key: str = field(default_factory=lambda: _key("OPENROUTER_API_KEY"))
    openrouter_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "poolside/laguna-s-2.1:free"))
    # stub = canned outputs, no network | live = the provider | off = every LLM call fails (demo "LLM down")
    llm_mode: str = field(default_factory=lambda: os.getenv(
        "LLM_MODE", "live" if any(_key(k) for k in ("MISTRAL_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY")) else "stub"))
    llm_timeout_s: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_S", "25")))
    # Minimum gap between Mistral calls (the free tier allows about 1 request/second).
    llm_min_interval_s: float = field(default_factory=lambda: float(os.getenv("LLM_MIN_INTERVAL_S", "1.1")))
    # Max total time one call may spend waiting out provider rate limits ("try again in Xs").
    llm_rate_wait_max_s: float = field(default_factory=lambda: float(os.getenv("LLM_RATE_WAIT_MAX_S", "60")))

    # --- SurgiGuard API (.NET + MongoDB): source of truth for ESP32 telemetry, medications and family alerts.
    # The AI backend READS telemetry/medications from it and PUSHES its alerts to it (POST /api/alerts/trigger).
    surgiguard_api_url: str = field(default_factory=lambda: os.getenv("SURGIGUARD_API_URL", "http://localhost:8080").rstrip("/"))
    surgiguard_agents_key: str = field(default_factory=lambda: os.getenv("SURGIGUARD_AGENTS_KEY", "dev-agents-key"))
    surgiguard_iot_key: str = field(default_factory=lambda: os.getenv("SURGIGUARD_IOT_KEY", "dev-iot-key"))
    # "off" = standalone AI backend (seed data only) | "on" = link to the SurgiGuard API
    surgiguard_link: str = field(default_factory=lambda: os.getenv("SURGIGUARD_LINK", "on").strip().lower())
    # Which SurgiGuard API patient is the demo patient "sarah": a Mongo id, or "auto" = the patient that owns ESP32_DEVICE_ID.
    surgiguard_patient_id: str = field(default_factory=lambda: os.getenv("SURGIGUARD_PATIENT_ID", "auto").strip())
    esp32_device_id: str = field(default_factory=lambda: os.getenv("ESP32_DEVICE_ID", "ESP32_001").strip())
    # One AI observation per metric per window (the ESP32 publishes about once per second).
    esp32_window_s: int = field(default_factory=lambda: int(os.getenv("ESP32_WINDOW_S", "15")))
    esp32_poll_s: int = field(default_factory=lambda: int(os.getenv("ESP32_POLL_S", "3")))

    db_url: str = field(default_factory=lambda: os.getenv("DB_URL", "sqlite:///./surgiguard.db"))

    # Demo timeouts (seconds). Real deployments would use much longer values.
    ack_timeout_s: int = field(default_factory=lambda: int(os.getenv("ACK_TIMEOUT_S", "60")))
    investigation_timeout_s: int = field(default_factory=lambda: int(os.getenv("INVESTIGATION_TIMEOUT_S", "120")))
    request_timeout_s: int = field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_S", "90")))

    scheduler_enabled: bool = field(default_factory=lambda: _bool("SCHEDULER_ENABLED", True))
    sweep_interval_s: int = field(default_factory=lambda: int(os.getenv("SWEEP_INTERVAL_S", "5")))
    # Agents (investigation, digest) run in a worker thread so API calls return fast.
    # Tests set this to True to run them inline and deterministically.
    run_agents_inline: bool = field(default_factory=lambda: _bool("RUN_AGENTS_INLINE", False))

    max_tool_calls: int = 8
    max_patient_requests: int = 2

    # D2 RAG assistant (vectorstore + semantic chunking)
    vectorstore_path: str = field(default_factory=lambda: os.getenv("VECTORSTORE_PATH", "./data/vectorstore"))
    semantic_chunk_threshold: float = field(default_factory=lambda: float(os.getenv("SEMANTIC_CHUNK_THRESHOLD", "0.72")))
    max_chunk_chars: int = field(default_factory=lambda: int(os.getenv("MAX_CHUNK_CHARS", "500")))
    min_chunk_chars: int = field(default_factory=lambda: int(os.getenv("MIN_CHUNK_CHARS", "60")))
    pain_warning_eva_threshold: int = 7

    def __post_init__(self):
        if self.llm_provider not in PROVIDERS:  # "auto" or unknown: first provider that has a key
            self.llm_provider = next((p for p in PROVIDERS if getattr(self, f"{p}_api_key")), "mistral")

    # ---- D2 names (UPPERCASE), same values
    @property
    def LLM_PROVIDER(self) -> str: return self.llm_provider
    @property
    def MISTRAL_API_KEY(self) -> str: return self.mistral_api_key
    @property
    def MISTRAL_MODEL(self) -> str: return self.mistral_model
    @property
    def GROQ_API_KEY(self) -> str: return self.groq_api_key
    @property
    def GROQ_MODEL(self) -> str: return self.groq_model
    @property
    def VECTORSTORE_PATH(self) -> str: return self.vectorstore_path
    @property
    def SEMANTIC_CHUNK_SIMILARITY_THRESHOLD(self) -> float: return self.semantic_chunk_threshold
    @property
    def MAX_CHUNK_CHARS(self) -> int: return self.max_chunk_chars
    @property
    def MIN_CHUNK_CHARS(self) -> int: return self.min_chunk_chars
    @property
    def PAIN_WARNING_EVA_THRESHOLD(self) -> int: return self.pain_warning_eva_threshold


settings = Settings()

DEMO_PATIENT_ID = "sarah"


# ------------------------------------------------------------------ D2 LangChain adapters

D2_DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"  # own free-tier quota (D1 and the agents use gpt-oss-120b)


def d2_route() -> tuple[str, str]:
    """(provider, model) for the D2 LangChain graphs: LLM_ROUTE_D2 if set, else Groq (gpt-oss-20b),
    else Mistral, else LLM_PROVIDER."""
    from .llm import route
    if os.getenv("LLM_ROUTE_D2", "").strip():
        return route("d2")
    if settings.groq_api_key:
        return "groq", D2_DEFAULT_GROQ_MODEL
    if settings.mistral_api_key:
        return "mistral", settings.mistral_model
    return route("d2")


def get_active_provider() -> str:
    """Provider for the D2 LangChain graphs; 'offline' when LLM_MODE is stub/off or no key is configured
    (tests and offline demos never reach the network)."""
    if settings.llm_mode != "live":
        return "offline"
    provider, _ = d2_route()
    return provider if getattr(settings, f"{provider}_api_key", "") else "offline"


def get_chat_llm(temperature: float = 0.1, model: Optional[str] = None, max_tokens: Optional[int] = None):
    """Chat model for D2 (Groq, OpenRouter, Mistral, or an offline fake)."""
    provider = get_active_provider()
    if provider != "offline":
        model = model or d2_route()[1]
    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(groq_api_key=settings.groq_api_key, model=model, temperature=temperature,
                        max_tokens=max_tokens, reasoning_effort="low" if "gpt-oss" in model else None)
    if provider == "mistral":
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(mistral_api_key=settings.mistral_api_key, model=model, temperature=temperature,
                             max_tokens=max_tokens)
    if provider == "openrouter":
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(api_key=settings.openrouter_api_key, base_url="https://openrouter.ai/api/v1",
                              model=model, temperature=temperature, max_tokens=max_tokens)
        except ImportError:
            pass
    from langchain_community.chat_models import FakeListChatModel
    return FakeListChatModel(responses=[
        "Je suis l'assistant SurgiGuard AI (mode hors-ligne). Configurez une clé Groq, OpenRouter ou Mistral "
        "dans backend/.env et LLM_MODE=live."])


def get_embeddings():
    """Mistral embeddings when a Mistral key is set (live mode), else deterministic FakeEmbeddings."""
    if settings.llm_mode == "live" and settings.mistral_api_key:
        from langchain_mistralai import MistralAIEmbeddings
        return MistralAIEmbeddings(mistral_api_key=settings.mistral_api_key)
    from langchain_core.embeddings import FakeEmbeddings
    return FakeEmbeddings(size=1024)
