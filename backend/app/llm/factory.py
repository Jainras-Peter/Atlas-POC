"""LLM factory — pick Groq or Gemini from ACTIVE_PROVIDER / ACTIVE_MODEL."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.llm.gemini import get_gemini_llm
from app.llm.groq import get_groq_llm


def get_llm(temperature: float = 0) -> Any:
    """Return a LangChain chat model for the configured provider."""
    provider = settings.provider
    if provider == "groq":
        return get_groq_llm(temperature=temperature)
    if provider == "gemini":
        return get_gemini_llm(temperature=temperature)
    raise RuntimeError(
        f"Unsupported ACTIVE_PROVIDER={provider!r}. Use 'groq' or 'gemini'."
    )
