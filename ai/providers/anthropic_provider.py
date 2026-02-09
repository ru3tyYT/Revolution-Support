"""
Anthropic/Claude Provider Implementation
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


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API provider implementation"""

    DEFAULT_MODELS = {
        "claude-3-5-sonnet-20241022": ModelConfig(
            id="claude-3-5-sonnet-20241022",
            name="Claude 3.5 Sonnet",
            provider="anthropic",
            max_tokens=8192,
            context_window=200000,
            cost_per_input_token=3.00 / 1_000_000,
            cost_per_output_token=15.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="fast",
            description="Most intelligent Claude model",
        ),
        "claude-3-5-haiku-20241022": ModelConfig(
            id="claude-3-5-haiku-20241022",
            name="Claude 3.5 Haiku",
            provider="anthropic",
            max_tokens=4096,
            context_window=200000,
            cost_per_input_token=0.80 / 1_000_000,
            cost_per_output_token=4.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="fast",
            description="Fastest Claude model",
        ),
        "claude-3-opus-20240229": ModelConfig(
            id="claude-3-opus-20240229",
            name="Claude 3 Opus",
            provider="anthropic",
            max_tokens=4096,
            context_window=200000,
            cost_per_input_token=15.00 / 1_000_000,
            cost_per_output_token=75.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="standard",
            description="Most powerful Claude model for complex tasks",
        ),
        "claude-3-sonnet-20240229": ModelConfig(
            id="claude-3-sonnet-20240229",
            name="Claude 3 Sonnet",
            provider="anthropic",
            max_tokens=4096,
            context_window=200000,
            cost_per_input_token=3.00 / 1_000_000,
            cost_per_output_token=15.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="standard",
            description="Balanced performance and cost",
        ),
        "claude-3-haiku-20240307": ModelConfig(
            id="claude-3-haiku-20240307",
            name="Claude 3 Haiku",
            provider="anthropic",
            max_tokens=4096,
            context_window=200000,
            cost_per_input_token=0.25 / 1_000_000,
            cost_per_output_token=1.25 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="fast",
            description="Fastest and most cost-effective",
        ),
    }

    def __init__(
        self, api_key: str, api_base: str = "https://api.anthropic.com/v1", **kwargs
    ):
        super().__init__(
            api_key=api_key,
            api_base=api_base,
            name="anthropic",
            rate_limit_requests=50,
            rate_limit_tokens=100000,
            **kwargs,
        )
        self._models = self.DEFAULT_MODELS.copy()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                timeout=aiohttp.ClientTimeout(total=120),
            )
        return self._session

    def _format_messages(self, messages: List[ChatMessage]) -> tuple:
        """
        Format messages for Anthropic API
        Returns (system_prompt, formatted_messages)
        """
        formatted = []
        system_prompt = None

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
                continue

            # Anthropic uses 'user' and 'assistant' only
            role = msg.role if msg.role in ["user", "assistant"] else "user"

            message_dict = {"role": role, "content": msg.content}
            formatted.append(message_dict)

        return system_prompt, formatted

    async def _make_request(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Make request to Anthropic API"""
        session = await self._get_session()

        system_prompt, messages = self._format_messages(request.messages)

        payload: Dict[str, Any] = {
            "model": request.model or "claude-3-5-sonnet-20241022",
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if request.temperature is not None:
            payload["temperature"] = request.temperature

        url = f"{self.api_base}/messages"

        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Anthropic API error {response.status}: {error_text}")

            data = await response.json()

            # Extract usage
            usage_data = data.get("usage", {})
            usage = UsageInfo(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("input_tokens", 0)
                + usage_data.get("output_tokens", 0),
            )

            # Calculate cost
            model_id = data.get("model", request.model or "claude-3-5-sonnet-20241022")
            usage.cost = self.estimate_cost(
                model_id, usage.prompt_tokens, usage.completion_tokens
            )

            # Extract content
            content_blocks = data.get("content", [])
            content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    content += block.get("text", "")

            return ChatCompletionResponse(
                id=data.get("id", ""),
                model=model_id,
                content=content,
                usage=usage,
                finish_reason=data.get("stop_reason", "end_turn"),
                tool_calls=None,  # Tool use not yet implemented
            )

    async def _stream_request(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """Make streaming request to Anthropic API"""
        session = await self._get_session()

        system_prompt, messages = self._format_messages(request.messages)

        payload: Dict[str, Any] = {
            "model": request.model or "claude-3-5-sonnet-20241022",
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
            "stream": True,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if request.temperature is not None:
            payload["temperature"] = request.temperature

        url = f"{self.api_base}/messages"

        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Anthropic API error {response.status}: {error_text}")

            async for line in response.content:
                line = line.decode("utf-8").strip()

                if not line or line.startswith(":"):
                    continue

                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        event_type = data.get("type")

                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
                    except json.JSONDecodeError:
                        continue

    def get_available_models(self) -> List[ModelConfig]:
        """Get list of available models"""
        return list(self._models.values())

    async def health_check(self) -> bool:
        """Check Anthropic API health"""
        try:
            if not self.api_key:
                return False

            # Make a minimal request to check health
            session = await self._get_session()
            url = f"{self.api_base}/models"

            async with session.get(url) as response:
                if response.status == 200:
                    self.status = ProviderStatus.HEALTHY
                    return True
                return False
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            self.status = ProviderStatus.ERROR
            return False

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
