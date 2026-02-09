"""
OpenAI/GPT Provider Implementation
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
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider implementation"""

    DEFAULT_MODELS = {
        "gpt-4o": ModelConfig(
            id="gpt-4o",
            name="GPT-4o",
            provider="openai",
            max_tokens=4096,
            context_window=128000,
            cost_per_input_token=2.50 / 1_000_000,
            cost_per_output_token=10.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="fast",
            description="Most capable multimodal model",
        ),
        "gpt-4o-mini": ModelConfig(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            provider="openai",
            max_tokens=4096,
            context_window=128000,
            cost_per_input_token=0.15 / 1_000_000,
            cost_per_output_token=0.60 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="fast",
            description="Fast and affordable for most tasks",
        ),
        "gpt-4-turbo": ModelConfig(
            id="gpt-4-turbo",
            name="GPT-4 Turbo",
            provider="openai",
            max_tokens=4096,
            context_window=128000,
            cost_per_input_token=10.00 / 1_000_000,
            cost_per_output_token=30.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            latency_tier="standard",
            description="Previous generation GPT-4",
        ),
        "gpt-3.5-turbo": ModelConfig(
            id="gpt-3.5-turbo",
            name="GPT-3.5 Turbo",
            provider="openai",
            max_tokens=4096,
            context_window=16385,
            cost_per_input_token=0.50 / 1_000_000,
            cost_per_output_token=1.50 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            latency_tier="fast",
            description="Legacy model - use GPT-4o mini instead",
        ),
        "o1": ModelConfig(
            id="o1",
            name="o1",
            provider="openai",
            max_tokens=32768,
            context_window=200000,
            cost_per_input_token=15.00 / 1_000_000,
            cost_per_output_token=60.00 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=False,
            supports_vision=True,
            latency_tier="slow",
            description="Reasoning model for complex tasks",
        ),
        "o1-mini": ModelConfig(
            id="o1-mini",
            name="o1 Mini",
            provider="openai",
            max_tokens=65536,
            context_window=128000,
            cost_per_input_token=1.10 / 1_000_000,
            cost_per_output_token=4.40 / 1_000_000,
            supports_streaming=True,
            supports_json_mode=False,
            supports_vision=True,
            latency_tier="standard",
            description="Faster reasoning model",
        ),
    }

    def __init__(
        self,
        api_key: str,
        organization: Optional[str] = None,
        api_base: str = "https://api.openai.com/v1",
        **kwargs,
    ):
        super().__init__(
            api_key=api_key,
            api_base=api_base,
            name="openai",
            rate_limit_requests=60,
            rate_limit_tokens=150000,
            **kwargs,
        )
        self.organization = organization
        self._models = self.DEFAULT_MODELS.copy()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            if self.organization:
                headers["OpenAI-Organization"] = self.organization

            self._session = aiohttp.ClientSession(
                headers=headers, timeout=aiohttp.ClientTimeout(total=120)
            )
        return self._session

    def _format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """Format messages for OpenAI API"""
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
        """Make request to OpenAI API"""
        session = await self._get_session()

        payload = {
            "model": request.model or "gpt-4o-mini",
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

        url = f"{self.api_base}/chat/completions"

        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"OpenAI API error {response.status}: {error_text}")

            data = await response.json()

            # Extract usage
            usage_data = data.get("usage", {})
            usage = UsageInfo(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            # Calculate cost
            model_id = data.get("model", request.model or "gpt-4o-mini")
            usage.cost = self.estimate_cost(
                model_id.split(":")[0] if ":" in model_id else model_id,
                usage.prompt_tokens,
                usage.completion_tokens,
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
        """Make streaming request to OpenAI API"""
        session = await self._get_session()

        payload = {
            "model": request.model or "gpt-4o-mini",
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
                raise Exception(f"OpenAI API error {response.status}: {error_text}")

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

    async def health_check(self) -> bool:
        """Check OpenAI API health"""
        try:
            if not self.api_key:
                return False

            session = await self._get_session()
            url = f"{self.api_base}/models"

            async with session.get(url) as response:
                if response.status == 200:
                    self.status = (
                        self.__class__.__bases__[0]
                        .__bases__[0]
                        .__subclasses__()[0]
                        .__bases__[0]
                        .HEALTHY
                    )
                    return True
                return False
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            self.status = ProviderStatus.ERROR
            return False

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
