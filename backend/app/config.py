"""Runtime configuration (environment variables, demo timeouts).

Values are read once at import; tests override attributes on `settings` directly.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    mistral_api_key: str = field(default_factory=lambda: os.getenv("MISTRAL_API_KEY", ""))
    mistral_model: str = field(default_factory=lambda: os.getenv("MISTRAL_MODEL", "mistral-large-latest"))
    # stub = canned outputs, no network | live = Mistral | off = every LLM call fails (demo "LLM down")
    llm_mode: str = field(default_factory=lambda: os.getenv("LLM_MODE", "live" if os.getenv("MISTRAL_API_KEY") else "stub"))
    llm_timeout_s: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_S", "25")))

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


settings = Settings()

DEMO_PATIENT_ID = "sarah"
