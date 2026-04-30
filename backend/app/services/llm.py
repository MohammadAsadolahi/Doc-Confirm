"""Shared LLM service – single source of truth for model construction."""
from __future__ import annotations

from langchain_openai import ChatOpenAI
from app.config import get_settings


def get_llm(temperature: float = 0, **kwargs) -> ChatOpenAI:
    """Return a ChatOpenAI instance configured from the root .env."""
    s = get_settings()
    return ChatOpenAI(
        model=s.openai_model,
        api_key=s.openai_api_key,
        base_url=s.openai_base_url,
        temperature=temperature,
        **kwargs,
    )
