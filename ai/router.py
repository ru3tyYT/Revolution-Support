"""
AI Provider Router with Intelligent Routing Logic
Routes requests to the best provider based on context, cost, latency, and availability
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Callable
from enum import Enum
from datetime import datetime
import random

from .providers.base import (
    BaseAIProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelConfig,
    ProviderStatus,
    UsageInfo,
)
from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider
from .providers.groq_provider import GroqProvider
from .providers.ollama_provider import OllamaProvider
from .providers.openrouter_provider import OpenRouterProvider

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Routing strategy options"""

    COST_PRIORITY = "cost_priority"  # Prefer cheaper/free models
    QUALITY_PRIORITY = "quality_priority"  # Prefer best quality models
    LATENCY_PRIORITY = "latency_priority"  # Prefer fastest models
    RELIABILITY_PRIORITY = "reliability_priority"  # Prefer most reliable
    BALANCED = "balanced"  # Balance all factors


@dataclass
class RoutingDecision:
    """Result of routing decision"""

    provider_name: str
    model_id: str
    reason: str
    estimated_cost: float
    estimated_latency_ms: float
    confidence: float  # 0.0 to 1.0


@dataclass
class ProviderInfo:
    """Provider tracking information"""

    provider: BaseAIProvider
    api_keys: List[str] = field(default_factory=list)
    current_key_index: int = 0
    success_count: int = 0
    error_count: int = 0
    last_used: Optional[datetime] = None
    average_latency_ms: float = 0.0
    priority: int = 1  # Higher = preferred


class AIRouter:
    """
    Intelligent AI provider router
    Routes requests to optimal provider based on multiple factors
    """

    # Model quality tiers (subjective ranking)
    QUALITY_TIERS = {
        # Tier 1: Best quality
        "o1": 10,
        "o1-mini": 10,
        "gpt-4o": 9,
        "claude-3-opus": 9,
        "claude-3.5-sonnet": 9,
        "google/gemini-2.0-pro": 9,
        # Tier 2: Very good quality
        "gpt-4o-mini": 8,
        "gpt-4-turbo": 8,
        "claude-3.5-haiku": 8,
        "claude-3-sonnet": 8,
        "claude-3-haiku": 8,
        "google/gemini-2.0-flash": 8,
        "llama-3.3-70b-versatile": 8,
        "llama-3.1-70b-versatile": 8,
        "meta-llama/llama-3.3-70b-instruct": 8,
        "mistral-large": 8,
        "kimi-k2.5": 8,
        # Tier 3: Good quality
        "gpt-3.5-turbo": 7,
        "llama-3.1-8b-instant": 7,
        "llama-3.2-3b-preview": 7,
        "mixtral-8x7b-32768": 7,
        "mixtral": 7,
        "meta-llama/llama-3.1-8b-instruct": 7,
        # Tier 4: Basic quality
        "llama-3.2-1b-preview": 6,
        "llama3.2": 6,
        "gemma-7b-it": 6,
        "gemma2-9b-it": 6,
        "mistral": 6,
    }

    def __init__(
        self,
        default_strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        enable_fallback: bool = True,
        max_fallback_attempts: int = 3,
        cost_budget: Optional[float] = None,  # Max cost per request
    ):
        self.providers: Dict[str, ProviderInfo] = {}
        self.default_strategy = default_strategy
        self.enable_fallback = enable_fallback
        self.max_fallback_attempts = max_fallback_attempts
        self.cost_budget = cost_budget
        self._routing_history: List[RoutingDecision] = []
        self._lock = asyncio.Lock()

    def register_provider(
        self,
        name: str,
        provider: BaseAIProvider,
        api_keys: Optional[List[str]] = None,
        priority: int = 1,
    ):
        """Register a provider with the router"""
        self.providers[name] = ProviderInfo(
            provider=provider,
            api_keys=api_keys or [provider.api_key],
            priority=priority,
        )
        logger.info(f"Registered provider: {name}")

    def register_openai(self, api_key: str, organization: Optional[str] = None, priority: int = 5):
        """Register OpenAI provider"""
        provider = OpenAIProvider(api_key=api_key, organization=organization)
        self.register_provider("openai", provider, priority=priority)

    def register_anthropic(self, api_key: str, priority: int = 5):
        """Register Anthropic provider"""
        provider = AnthropicProvider(api_key=api_key)
        self.register_provider("anthropic", provider, priority=priority)

    def register_groq(
        self,
        api_key: str,
        use_free_tier: bool = True,
        priority: int = 8,  # Higher priority for free tier
    ):
        """Register Groq provider"""
        provider = GroqProvider(api_key=api_key, use_free_tier=use_free_tier)
        self.register_provider("groq", provider, priority=priority)

    def register_ollama(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        use_cloud: bool = False,
        cloud_api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        priority: int = 9,  # Highest for free cloud
    ):
        """Register Ollama provider"""
        if api_base is None:
            api_base = "https://api.ollama.ai/v1" if use_cloud else "http://localhost:11434"
        provider = OllamaProvider(
            api_key=api_key,
            api_base=api_base,
            use_cloud=use_cloud,
            cloud_api_key=cloud_api_key,
            default_model=default_model,
        )
        self.register_provider("ollama", provider, priority=priority)

    def register_openrouter(
        self,
        api_key: str,
        http_referer: Optional[str] = None,
        x_title: Optional[str] = None,
        priority: int = 6,
    ):
        """Register OpenRouter provider"""
        provider = OpenRouterProvider(api_key=api_key, http_referer=http_referer, x_title=x_title)
        self.register_provider("openrouter", provider, priority=priority)

    async def route(
        self,
        request: ChatCompletionRequest,
        strategy: Optional[RoutingStrategy] = None,
        preferred_providers: Optional[List[str]] = None,
        excluded_providers: Optional[Set[str]] = None,
        max_context_length: Optional[int] = None,
        require_vision: bool = False,
    ) -> RoutingDecision:
        """
        Route a request to the best provider

        Args:
            request: The chat completion request
            strategy: Routing strategy (uses default if not specified)
            preferred_providers: List of provider names to prefer
            excluded_providers: Set of provider names to exclude
            max_context_length: Maximum required context window
            require_vision: Whether the model needs vision capabilities

        Returns:
            RoutingDecision with chosen provider and model
        """
        strategy = strategy or self.default_strategy
        excluded = excluded_providers or set()

        # Score all available options
        candidates = []

        for provider_name, provider_info in self.providers.items():
            if provider_name in excluded:
                continue

            if not provider_info.provider.is_healthy():
                continue

            # Get available models for this provider
            models = provider_info.provider.get_available_models()

            for model in models:
                # Filter by requirements
                if max_context_length and model.context_window < max_context_length:
                    continue

                if require_vision and not model.supports_vision:
                    continue

                # Calculate score
                score = self._calculate_score(model, provider_info, strategy, preferred_providers)

                candidates.append(
                    {
                        "provider_name": provider_name,
                        "provider_info": provider_info,
                        "model": model,
                        "score": score,
                    }
                )

        if not candidates:
            raise Exception("No available providers match the requirements")

        # Sort by score (higher is better)
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Select best candidate
        best = candidates[0]

        decision = RoutingDecision(
            provider_name=best["provider_name"],
            model_id=best["model"].id,
            reason=self._generate_reason(best, strategy),
            estimated_cost=best["provider_info"].provider.estimate_cost(
                best["model"].id,
                1000,
                500,  # Rough estimate
            ),
            estimated_latency_ms=best["provider_info"].average_latency_ms
            or (1000 if best["model"].latency_tier == "fast" else 2000),
            confidence=min(1.0, best["score"] / 100),
        )

        # Track decision
        self._routing_history.append(decision)
        if len(self._routing_history) > 1000:
            self._routing_history = self._routing_history[-1000:]

        return decision

    def _calculate_score(
        self,
        model: ModelConfig,
        provider_info: ProviderInfo,
        strategy: RoutingStrategy,
        preferred_providers: Optional[List[str]],
    ) -> float:
        """Calculate routing score for a model"""
        score = 0.0

        # Base priority score
        score += provider_info.priority * 10

        # Preferred provider bonus
        if preferred_providers and provider_info in [
            self.providers.get(p) for p in preferred_providers
        ]:
            score += 50

        # Strategy-specific scoring
        if strategy == RoutingStrategy.COST_PRIORITY:
            if model.is_free:
                score += 100
            else:
                # Lower cost = higher score
                max_cost = 0.01  # $0.01 per 1K tokens
                cost_score = max(0, (max_cost - model.cost_per_input_token) / max_cost * 50)
                score += cost_score

        elif strategy == RoutingStrategy.QUALITY_PRIORITY:
            # Higher quality tier = higher score
            quality = self.QUALITY_TIERS.get(model.id, 5)
            score += quality * 10

            # Prefer larger context windows
            if model.context_window >= 100000:
                score += 20

        elif strategy == RoutingStrategy.LATENCY_PRIORITY:
            if model.latency_tier == "fast":
                score += 100
            elif model.latency_tier == "standard":
                score += 50

        elif strategy == RoutingStrategy.RELIABILITY_PRIORITY:
            # Provider reliability based on success rate
            total_requests = provider_info.success_count + provider_info.error_count
            if total_requests > 0:
                success_rate = provider_info.success_count / total_requests
                score += success_rate * 100

            # Penalize degraded providers
            if provider_info.provider.status == ProviderStatus.DEGRADED:
                score -= 30

        elif strategy == RoutingStrategy.BALANCED:
            # Balanced scoring
            # Quality (30%)
            quality = self.QUALITY_TIERS.get(model.id, 5)
            score += quality * 3

            # Cost (30%) - prefer free, then cheaper
            if model.is_free:
                score += 30
            else:
                max_cost = 0.01
                cost_score = max(0, (max_cost - model.cost_per_input_token) / max_cost * 30)
                score += cost_score

            # Speed (20%)
            if model.latency_tier == "fast":
                score += 20
            elif model.latency_tier == "standard":
                score += 10

            # Reliability (20%)
            total_requests = provider_info.success_count + provider_info.error_count
            if total_requests > 0:
                success_rate = provider_info.success_count / total_requests
                score += success_rate * 20
            else:
                score += 15  # Neutral for new providers

        # Free tier bonus (always preferred if similar quality)
        if model.is_free:
            score += 20

        # Small random factor to prevent always choosing same provider
        score += random.uniform(-2, 2)

        return score

    def _generate_reason(self, candidate: Dict, strategy: RoutingStrategy) -> str:
        """Generate human-readable routing reason"""
        model = candidate["model"]
        provider = candidate["provider_name"]

        reasons = []

        if model.is_free:
            reasons.append("free tier")

        if strategy == RoutingStrategy.COST_PRIORITY:
            reasons.append("cost optimization")
        elif strategy == RoutingStrategy.QUALITY_PRIORITY:
            reasons.append("quality priority")
        elif strategy == RoutingStrategy.LATENCY_PRIORITY:
            reasons.append("low latency")
        elif strategy == RoutingStrategy.RELIABILITY_PRIORITY:
            reasons.append("reliability")

        if model.latency_tier == "fast":
            reasons.append("fast inference")

        quality = self.QUALITY_TIERS.get(model.id, 5)
        if quality >= 8:
            reasons.append("high quality")

        return f"Selected {model.name} via {provider} ({', '.join(reasons)})"

    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        strategy: Optional[RoutingStrategy] = None,
        **routing_kwargs,
    ) -> ChatCompletionResponse:
        """
        Execute chat completion with automatic routing and fallback
        """
        decision = await self.route(request, strategy, **routing_kwargs)

        attempts = 0
        excluded: Set[str] = set()
        last_error: Optional[Exception] = None

        while attempts < self.max_fallback_attempts:
            try:
                provider_info = self.providers[decision.provider_name]

                # Update request with chosen model
                request.model = decision.model_id

                # Rotate API key if multiple keys available
                if len(provider_info.api_keys) > 1:
                    provider_info.current_key_index = (provider_info.current_key_index + 1) % len(
                        provider_info.api_keys
                    )
                    provider_info.provider.api_key = provider_info.api_keys[
                        provider_info.current_key_index
                    ]

                # Execute request
                start_time = asyncio.get_event_loop().time()
                response = await provider_info.provider.chat_completion(request)
                elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000

                # Update provider stats
                provider_info.success_count += 1
                provider_info.last_used = datetime.utcnow()

                # Update average latency
                if provider_info.average_latency_ms == 0:
                    provider_info.average_latency_ms = elapsed_ms
                else:
                    provider_info.average_latency_ms = (
                        provider_info.average_latency_ms * 0.9 + elapsed_ms * 0.1
                    )

                logger.info(
                    f"Request successful via {decision.provider_name}/{decision.model_id} "
                    f"in {elapsed_ms:.0f}ms"
                )

                return response

            except Exception as e:
                last_error = e
                provider_info = self.providers.get(decision.provider_name)
                if provider_info:
                    provider_info.error_count += 1

                logger.warning(f"Request failed via {decision.provider_name}: {e}")

                if not self.enable_fallback:
                    raise

                # Exclude failed provider and retry
                excluded.add(decision.provider_name)
                attempts += 1

                if attempts < self.max_fallback_attempts:
                    logger.info(f"Falling back to alternative provider (attempt {attempts + 1})")
                    try:
                        decision = await self.route(
                            request,
                            strategy,
                            excluded_providers=excluded,
                            **{
                                k: v for k, v in routing_kwargs.items() if k != "excluded_providers"
                            },
                        )
                    except Exception:
                        # No more providers available
                        break

        raise Exception(f"All providers failed after {attempts} attempts. Last error: {last_error}")

    async def get_provider_health(self) -> Dict[str, Any]:
        """Get health status of all providers"""
        health = {}

        for name, info in self.providers.items():
            total_requests = info.success_count + info.error_count
            success_rate = info.success_count / total_requests * 100 if total_requests > 0 else 100

            health[name] = {
                "status": info.provider.status.value,
                "is_healthy": info.provider.is_healthy(),
                "success_rate": f"{success_rate:.1f}%",
                "total_requests": total_requests,
                "avg_latency_ms": f"{info.average_latency_ms:.0f}",
                "models_available": len(info.provider.get_available_models()),
                "last_used": info.last_used.isoformat() if info.last_used else None,
            }

        return health

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        if not self._routing_history:
            return {"total_routes": 0}

        provider_counts: Dict[str, int] = {}
        for decision in self._routing_history:
            provider_counts[decision.provider_name] = (
                provider_counts.get(decision.provider_name, 0) + 1
            )

        return {
            "total_routes": len(self._routing_history),
            "provider_distribution": provider_counts,
            "avg_confidence": sum(d.confidence for d in self._routing_history)
            / len(self._routing_history),
            "avg_estimated_cost": sum(d.estimated_cost for d in self._routing_history)
            / len(self._routing_history),
        }

    async def rotate_api_key(self, provider_name: str):
        """Manually rotate API key for a provider"""
        info = self.providers.get(provider_name)
        if not info or len(info.api_keys) <= 1:
            return

        info.current_key_index = (info.current_key_index + 1) % len(info.api_keys)
        info.provider.api_key = info.api_keys[info.current_key_index]
        logger.info(f"Rotated API key for {provider_name}")

    async def close_all(self):
        """Close all provider connections"""
        for name, info in self.providers.items():
            if hasattr(info.provider, "close"):
                try:
                    await info.provider.close()
                except Exception as e:
                    logger.error(f"Error closing {name}: {e}")
