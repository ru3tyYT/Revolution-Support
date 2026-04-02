"""Lazily configured AIRouter for the web API (mirrors bot provider registration)."""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.router import AIRouter

logger = logging.getLogger(__name__)


@lru_cache
def get_web_ai_router() -> AIRouter:
    from ai.router import AIRouter

    router = AIRouter()

    if os.getenv("OPENAI_API_KEY"):
        router.register_openai(os.environ["OPENAI_API_KEY"])
    if os.getenv("ANTHROPIC_API_KEY"):
        router.register_anthropic(os.environ["ANTHROPIC_API_KEY"])
    if os.getenv("GROQ_API_KEY"):
        router.register_groq(os.environ["GROQ_API_KEY"])
    if os.getenv("OPENROUTER_API_KEY"):
        router.register_openrouter(os.environ["OPENROUTER_API_KEY"])

    ollama_cloud_key = os.getenv("OLLAMA_CLOUD_KEY")
    ollama_cloud_base_url = os.getenv("OLLAMA_CLOUD_BASE_URL")
    ollama_cloud_model = os.getenv("OLLAMA_CLOUD_MODEL")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL")
    ollama_default_model = os.getenv("OLLAMA_MODEL")

    if ollama_cloud_key or ollama_cloud_base_url:
        router.register_ollama(
            use_cloud=True,
            cloud_api_key=ollama_cloud_key,
            api_base=ollama_cloud_base_url,
            default_model=ollama_cloud_model or ollama_default_model,
        )
    elif ollama_base_url or ollama_default_model:
        router.register_ollama(
            api_base=ollama_base_url,
            default_model=ollama_default_model,
        )

    if not router.providers:
        logger.warning(
            "No AI providers registered for web API; /api/ai/ask will use KB-only fallback"
        )

    return router
