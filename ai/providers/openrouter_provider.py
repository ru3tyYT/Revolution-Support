"""
OpenRouter Provider Implementation - API Aggregation Service
"""

import json
from typing import AsyncGenerator, Dict, List, Optional, Any
import aiohttp
import logging

from .base import (
    BaseAIProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ModelConfig,
    UsageInfo,
    ProviderStatus,
)

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseAIProvider):
    """
    OpenRouter API provider - aggregates access to multiple providers
    Provides unified interface to OpenAI, Anthropic, Google, Meta, etc.
    """

    DEFAULT_MODELS = {
        # OpenAI models via OpenRouter
        "openai/gpt-4o": ModelConfig(
            id="openai/gpt-4o",
            name="GPT-4o (via OpenRouter)",
            provider="openrouter",
            max_tokens=4096,
            context_window=128000,
            cost_per_input_token=5.00 / 1_000_000,
            cost_per_output_token=15.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="fast",
            description="OpenAI GPT-4o via OpenRouter",
        ),
        "openai/gpt-4o-mini": ModelConfig(
            id="openai/gpt-4o-mini",
            name="GPT-4o Mini (via OpenRouter)",
            provider="openrouter",
            max_tokens=4096,
            context_window=128000,
            cost_per_input_token=0.15 / 1_000_000,
            cost_per_output_token=0.60 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="fast",
            description="OpenAI GPT-4o Mini via OpenRouter",
        ),
        # Anthropic models
        "anthropic/claude-3.5-sonnet": ModelConfig(
            id="anthropic/claude-3.5-sonnet",
            name="Claude 3.5 Sonnet (via OpenRouter)",
            provider="openrouter",
            max_tokens=8192,
            context_window=200000,
            cost_per_input_token=3.00 / 1_000_000,
            cost_per_output_token=15.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="fast",
            description="Anthropic Claude 3.5 Sonnet via OpenRouter",
        ),
        "anthropic/claude-3.5-haiku": ModelConfig(
            id="anthropic/claude-3.5-haiku",
            name="Claude 3.5 Haiku (via OpenRouter)",
            provider="openrouter",
            max_tokens=4096,
            context_window=200000,
            cost_per_input_token=1.00 / 1_000_000,
            cost_per_output_token=5.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="fast",
            description="Anthropic Claude 3.5 Haiku via OpenRouter",
        ),
        "anthropic/claude-3-opus": ModelConfig(
            id="anthropic/claude-3-opus",
            name="Claude 3 Opus (via OpenRouter)",
            provider="openrouter",
            max_tokens=4096,
            context_window=200000,
            cost_per_input_token=15.00 / 1_000_000,
            cost_per_output_token=75.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="standard",
            description="Anthropic Claude 3 Opus via OpenRouter",
        ),
        # Google models
        "google/gemini-2.0-flash": ModelConfig(
            id="google/gemini-2.0-flash",
            name="Gemini 2.0 Flash (via OpenRouter)",
            provider="openrouter",
            max_tokens=8192,
            context_window=1000000,
            cost_per_input_token=0.10 / 1_000_000,
            cost_per_output_token=0.40 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="fast",
            description="Google Gemini 2.0 Flash via OpenRouter",
        ),
        "google/gemini-2.0-pro": ModelConfig(
            id="google/gemini-2.0-pro",
            name="Gemini 2.0 Pro (via OpenRouter)",
            provider="openrouter",
            max_tokens=8192,
            context_window=2000000,
            cost_per_input_token=3.50 / 1_000_000,
            cost_per_output_token=10.50 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="standard",
            description="Google Gemini 2.0 Pro via OpenRouter",
        ),
        # Meta models
        "meta-llama/llama-3.3-70b-instruct": ModelConfig(
            id="meta-llama/llama-3.3-70b-instruct",
            name="Llama 3.3 70B (via OpenRouter)",
            provider="openrouter",
            max_tokens=131072,
            context_window=128000,
            cost_per_input_token=0.59 / 1_000_000,
            cost_per_output_token=0.79 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            latency_tier="standard",
            description="Meta Llama 3.3 70B via OpenRouter",
        ),
        "meta-llama/llama-3.1-8b-instruct": ModelConfig(
            id="meta-llama/llama-3.1-8b-instruct",
            name="Llama 3.1 8B (via OpenRouter)",
            provider="openrouter",
            max_tokens=8192,
            context_window=128000,
            cost_per_input_token=0.18 / 1_000_000,
            cost_per_output_token=0.18 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            latency_tier="fast",
            description="Meta Llama 3.1 8B via OpenRouter",
        ),
        # Mistral models
        "mistralai/mistral-large": ModelConfig(
            id="mistralai/mistral-large",
            name="Mistral Large (via OpenRouter)",
            provider="openrouter",
            max_tokens=8192,
            context_window=128000,
            cost_per_input_token=2.00 / 1_000_000,
            cost_per_output_token=6.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            latency_tier="standard",
            description="Mistral Large via OpenRouter",
        ),
        # Free/discounted models on OpenRouter
        "meta-llama/llama-3.1-8b-instruct:free": ModelConfig(
            id="meta-llama/llama-3.1-8b-instruct:free",
            name="Llama 3.1 8B (Free Tier)",
            provider="openrouter",
            max_tokens=8192,
            context_window=128000,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="fast",
            description="Free tier - Llama 3.1 8B via OpenRouter",
        ),
        "google/gemini-2.0-flash:free": ModelConfig(
            id="google/gemini-2.0-flash:free",
            name="Gemini 2.0 Flash (Free Tier)",
            provider="openrouter",
            max_tokens=8192,
            context_window=1000000,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            is_free=True,
            latency_tier="fast",
            description="Free tier - Gemini 2.0 Flash via OpenRouter",
        ),
    }

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://openrouter.ai/api/v1",
        http_referer: Optional[str] = None,
        x_title: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize OpenRouter provider

        Args:
            api_key: OpenRouter API key
            api_base: OpenRouter API base URL
            http_referer: Your site URL for OpenRouter rankings
            x_title: Your app name for OpenRouter rankings
        """
        super().__init__(
            api_key=api_key,
            api_base=api_base,
            name="openrouter",
            rate_limit_requests=60,
            rate_limit_tokens=200000,
            **kwargs,
        )
        self.http_referer = http_referer
        self.x_title = x_title
        self._models = self.DEFAULT_MODELS.copy()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.http_referer or "https://discord-bot.local",
                "X-Title": self.x_title or "Discord Support Bot",
            }

            self._session = aiohttp.ClientSession(
                headers=headers, timeout=aiohttp.ClientTimeout(total=120)
            )
        return self._session

    def _format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """Format messages for OpenRouter API (OpenAI-compatible)"""
        formatted = []
        for msg in messages:
            message_dict: Dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                message_dict["name"] = msg.name
            if msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            formatted.append(message_dict)
        return formatted

    async def _make_request(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Make request to OpenRouter API"""
        session = await self._get_session()

        payload = {
            "model": request.model or "openai/gpt-4o-mini",
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "stream": False,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        if request.response_format:
            payload["response_format"] = request.response_format

        if request.tools:
            payload["tools"] = request.tools

        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice

        # Add OpenRouter-specific routing options
        payload["transforms"] = ["middle-out"]  # Handle long contexts better

        url = f"{self.api_base}/chat/completions"

        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()

                # Check for rate limit
                if response.status == 429:
                    retry_after = response.headers.get("retry-after", "60")
                    raise Exception(
                        f"OpenRouter rate limit exceeded. Retry after {retry_after}s: {error_text}"
                    )

                # Check for invalid model
                if response.status == 404 and "model" in error_text.lower():
                    raise Exception(
                        f"Model not available on OpenRouter: {request.model}"
                    )

                raise Exception(f"OpenRouter API error {response.status}: {error_text}")

            data = await response.json()

            # Extract usage
            usage_data = data.get("usage", {})
            usage = UsageInfo(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            # Calculate cost
            model_id = data.get("model", request.model or "openai/gpt-4o-mini")

            # Get pricing from response if available
            pricing = data.get("pricing", {})
            if pricing:
                usage.cost = usage.prompt_tokens * float(
                    pricing.get("prompt", 0)
                ) + usage.completion_tokens * float(pricing.get("completion", 0))
            else:
                usage.cost = self.estimate_cost(
                    model_id, usage.prompt_tokens, usage.completion_tokens
                )

            # Extract content
            choice = data["choices"][0]
            message = choice.get("message", {})

            return ChatCompletionResponse(
                id=data.get("id", ""),
                model=model_id,
                content=message.get("content", ""),
                usage=usage,
                finish_reason=choice.get("finish_reason", "stop"),
                tool_calls=message.get("tool_calls"),
            )

    async def _stream_request(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """Make streaming request to OpenRouter API"""
        session = await self._get_session()

        payload = {
            "model": request.model or "openai/gpt-4o-mini",
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "stream": True,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        payload["transforms"] = ["middle-out"]

        url = f"{self.api_base}/chat/completions"

        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"OpenRouter API error {response.status}: {error_text}")

            async for line in response.content:
                line = line.decode("utf-8").strip()

                if not line or line == "data: [DONE]":
                    continue

                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    def get_available_models(self) -> List[ModelConfig]:
        """Get list of available models"""
        return list(self._models.values())

    async def fetch_available_models(self) -> List[Dict[str, Any]]:
        """Fetch current list of available models from OpenRouter"""
        try:
            session = await self._get_session()
            url = f"{self.api_base}/models"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                return []
        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
            return []

    def get_free_models(self) -> List[ModelConfig]:
        """Get free tier models"""
        return [m for m in self._models.values() if m.is_free]

    def get_models_by_provider(self, provider_name: str) -> List[ModelConfig]:
        """Get models from a specific provider"""
        return [
            m for m in self._models.values() if m.id.startswith(f"{provider_name}/")
        ]

    async def health_check(self) -> bool:
        """Check OpenRouter API health"""
        try:
            if not self.api_key:
                return False

            session = await self._get_session()
            url = f"{self.api_base}/models"

            async with session.get(url) as response:
                if response.status == 200:
                    self.status = ProviderStatus.HEALTHY
                    return True
                return False
        except Exception as e:
            logger.error(f"OpenRouter health check failed: {e}")
            self.status = ProviderStatus.ERROR
            return False

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
