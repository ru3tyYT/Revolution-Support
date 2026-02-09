"""
AI Provider Abstraction Layer for Discord Support Bot
"""

from .providers.base import BaseAIProvider, ModelConfig, ProviderStatus
from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider
from .providers.groq_provider import GroqProvider
from .providers.ollama_provider import OllamaProvider
from .providers.openrouter_provider import OpenRouterProvider
from .router import AIRouter, RoutingDecision, RoutingStrategy
from .embeddings import EmbeddingGenerator

__all__ = [
    # Base
    "BaseAIProvider",
    "ModelConfig",
    "ProviderStatus",
    # Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "GroqProvider",
    "OllamaProvider",
    "OpenRouterProvider",
    # Router
    "AIRouter",
    "RoutingDecision",
    "RoutingStrategy",
    # Embeddings
    "EmbeddingGenerator",
]

__version__ = "1.0.0"
