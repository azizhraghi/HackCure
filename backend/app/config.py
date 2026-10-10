import os
from typing import Optional
from dotenv import load_dotenv

from langchain_core.embeddings import FakeEmbeddings
from langchain_community.chat_models import FakeListChatModel

load_dotenv()


class Settings:
    """
    Centralized configuration for SurgiGuard AI Backend.
    Supports modular provider selection between Mistral and Groq.
    """
    # Active Provider: "auto", "mistral", or "groq"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto").lower()

    # Mistral AI
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

    # Groq (Ultra-fast inference)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    # Vectorstore & RAG Parameters
    VECTORSTORE_PATH: str = os.getenv("VECTORSTORE_PATH", "./data/vectorstore")
    SEMANTIC_CHUNK_SIMILARITY_THRESHOLD: float = float(os.getenv("SEMANTIC_CHUNK_THRESHOLD", "0.72"))
    MAX_CHUNK_CHARS: int = int(os.getenv("MAX_CHUNK_CHARS", "500"))
    MIN_CHUNK_CHARS: int = int(os.getenv("MIN_CHUNK_CHARS", "60"))

    # Clinical Red-Flag Thresholds
    PAIN_WARNING_EVA_THRESHOLD: int = 7


settings = Settings()


def get_active_provider() -> str:
    """Resolves whether to use Groq, Mistral, or Mock based on configured keys."""
    if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
        return "groq"
    if settings.LLM_PROVIDER == "mistral" and settings.MISTRAL_API_KEY:
        return "mistral"

    # Auto-detection
    if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your-groq-api-key":
        return "groq"
    if settings.MISTRAL_API_KEY and settings.MISTRAL_API_KEY not in ("", "your-mistral-api-key"):
        return "mistral"

    return "offline"


def get_chat_llm(temperature: float = 0.1, model: Optional[str] = None):
    """
    Returns configured Chat LLM (Groq, Mistral, or offline fallback).
    """
    provider = get_active_provider()

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model=model or settings.GROQ_MODEL,
            temperature=temperature
        )

    if provider == "mistral":
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(
            mistral_api_key=settings.MISTRAL_API_KEY,
            model=model or settings.MISTRAL_MODEL,
            temperature=temperature
        )

    # Offline / Test fallback
    return FakeListChatModel(responses=[
        "Je suis l'assistant SurgiGuard AI (mode hors-ligne). Veuillez configurer votre clé d'API Mistral ou Groq dans le fichier .env."
    ])


def get_embeddings():
    """
    Returns Mistral embeddings if configured, or deterministic FakeEmbeddings.
    """
    if settings.MISTRAL_API_KEY and settings.MISTRAL_API_KEY not in ("", "your-mistral-api-key"):
        from langchain_mistralai import MistralAIEmbeddings
        return MistralAIEmbeddings(mistral_api_key=settings.MISTRAL_API_KEY)

    return FakeEmbeddings(size=1024)
