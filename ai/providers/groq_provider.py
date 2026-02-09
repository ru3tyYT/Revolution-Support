"""
Groq Provider Implementation with Free Tier Support
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


class GroqProvider(BaseAIProvider):
    """Groq API provider implementation - offers free tier with rate limits"""

    DEFAULT_MODELS = {
        # Free tier models
        "llama-3.1-8b-instant": ModelConfig(
            id="llama-3.1-8b-instant",
            name="Llama 3.1 8B Instant",
            provider="groq",
            max_tokens=8192,
            context_window=128000,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="fast",
            description="Free tier - Fast inference on Groq hardware",
        ),
        "llama-3.2-1b-preview": ModelConfig(
            id="llama-3.2-1b-preview",
            name="Llama 3.2 1B Preview",
            provider="groq",
            max_tokens=8192,
            context_window=128000,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="fast",
            description="Free tier - Very fast, lightweight model",
        ),
        "llama-3.2-3b-preview": ModelConfig(
            id="llama-3.2-3b-preview",
            name="Llama 3.2 3B Preview",
            provider="groq",
            max_tokens=8192,
            context_window=128000,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="fast",
            description="Free tier - Fast with good quality",
        ),
        "llama-3.3-70b-versatile": ModelConfig(
            id="llama-3.3-70b-versatile",
            name="Llama 3.3 70B Versatile",
            provider="groq",
            max_tokens=32768,
            context_window=128000,
            cost_per_input_token=0.59 / 1_000_000,
            cost_per_output_token=0.79 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=False,
            latency_tier="fast",
            description="Paid - Powerful 70B model with fast inference",
        ),
        "mixtral-8x7b-32768": ModelConfig(
            id="mixtral-8x7b-32768",
            name="Mixtral 8x7B",
            provider="groq",
            max_tokens=32768,
            context_window=32768,
            cost_per_input_token=0.24 / 1_000_000,
            cost_per_output_token=0.24 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=False,
            latency_tier="fast",
            description="Paid - MoE architecture model",
        ),
        "gemma-7b-it": ModelConfig(
            id="gemma-7b-it",
            name="Gemma 7B",
            provider="groq",
            max_tokens=8192,
            context_window=8192,
            cost_per_input_token=0.07 / 1_000_000,
            cost_per_output_token=0.07 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=False,
            latency_tier="fast",
            description="Paid - Google's lightweight model",
        ),
        "gemma2-9b-it": ModelConfig(
            id="gemma2-9b-it",
            name="Gemma 2 9B",
            provider="groq",
            max_tokens=8192,
            context_window=8192,
            cost_per_input_token=0.20 / 1_000_000,
            cost_per_output_token=0.20 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=False,
            latency_tier="fast",
            description="Paid - Google's updated model",
        ),
        # Paid models
        "llama-3.1-70b-versatile": ModelConfig(
            id="llama-3.1-70b-versatile",
            name="Llama 3.1 70B Versatile",
            provider="groq",
            max_tokens=32768,
            context_window=128000,
            cost_per_input_token=0.59 / 1_000_000,
            cost_per_output_token=0.79 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=False,
            latency_tier="fast",
            description="Paid - Llama 3.1 70B on Groq",
        ),
    }

    # Groq free tier rate limits (as of 2024)
    FREE_TIER_RPM = 20  # Requests per minute
    FREE_TIER_TPM = 20000  # Tokens per minute
    FREE_TIER_RPD = 14400  # Requests per day

    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.groq.com/openai/v1",
        use_free_tier: bool = True,
        **kwargs,
    ):
        # Use stricter rate limits for free tier
        if use_free_tier:
            rate_limit_requests = self.FREE_TIER_RPM
            rate_limit_tokens = self.FREE_TIER_TPM
        else:
            rate_limit_requests = 100
            rate_limit_tokens = 100000

        super().__init__(
            api_key=api_key,
            api_base=api_base,
            name="groq",
            rate_limit_requests=rate_limit_requests,
            rate_limit_tokens=rate_limit_tokens,
            **kwargs,
        )
        self.use_free_tier = use_free_tier
        self._models = self.DEFAULT_MODELS.copy()
        self._session: Optional[aiohttp.ClientSession] = None
        self._daily_request_count = 0
        self._last_reset = 0.0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=60),  # Groq is fast!
            )
        return self._session

    def _format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """Format messages for Groq API (OpenAI-compatible)"""
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

    async def _check_free_tier_limits(self):
        """Check free tier daily limits"""
        if not self.use_free_tier:
            return

        import time

        now = time.time()

        # Reset daily counter if a day has passed
        if now - self._last_reset > 86400:  # 24 hours
            self._daily_request_count = 0
            self._last_reset = now

        if self._daily_request_count >= self.FREE_TIER_RPD:
            raise Exception("Free tier daily request limit reached (14400/day)")

    async def _make_request(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Make request to Groq API"""
        await self._check_free_tier_limits()

        session = await self._get_session()

        payload = {
            "model": request.model or "llama-3.1-8b-instant",
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "stream": False,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        if request.response_format:
            payload["response_format"] = request.response_format

        url = f"{self.api_base}/chat/completions"

        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()

                # Check for rate limit error
                if response.status == 429:
                    retry_after = response.headers.get("retry-after", "60")
                    raise Exception(
                        f"Groq rate limit exceeded. Retry after {retry_after}s: {error_text}"
                    )

                raise Exception(f"Groq API error {response.status}: {error_text}")

            data = await response.json()

            # Track free tier usage
            if self.use_free_tier:
                self._daily_request_count += 1

            # Extract usage
            usage_data = data.get("usage", {})
            usage = UsageInfo(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            # Calculate cost (free tier = $0)
            model_id = data.get("model", request.model or "llama-3.1-8b-instant")
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
        """Make streaming request to Groq API"""
        await self._check_free_tier_limits()

        session = await self._get_session()

        payload = {
            "model": request.model or "llama-3.1-8b-instant",
            "messages": self._format_messages(request.messages),
            "temperature": request.temperature,
            "stream": True,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        url = f"{self.api_base}/chat/completions"

        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Groq API error {response.status}: {error_text}")

            if self.use_free_tier:
                self._daily_request_count += 1

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
        if self.use_free_tier:
            # Return only free models for free tier
            return [m for m in self._models.values() if m.is_free]
        return list(self._models.values())

    def get_free_models(self) -> List[ModelConfig]:
        """Get only free tier models"""
        return [m for m in self._models.values() if m.is_free]

    def get_paid_models(self) -> List[ModelConfig]:
        """Get only paid models"""
        return [m for m in self._models.values() if not m.is_free]

    async def health_check(self) -> bool:
        """Check Groq API health"""
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
            logger.error(f"Groq health check failed: {e}")
            self.status = ProviderStatus.ERROR
            return False

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def get_free_tier_usage(self) -> Dict[str, Any]:
        """Get free tier usage statistics"""
        import time

        return {
            "daily_requests_used": self._daily_request_count,
            "daily_requests_limit": self.FREE_TIER_RPD,
            "daily_requests_remaining": self.FREE_TIER_RPD - self._daily_request_count,
            "resets_in_hours": 24 - (time.time() - self._last_reset) / 3600
            if self._last_reset > 0
            else 24,
        }
