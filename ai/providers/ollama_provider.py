"""
Ollama Provider Implementation - Cloud API + Local Support
Supports FREE models: Kimi K2.5, Gemini 3 Pro, Flash via Ollama Cloud
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


class OllamaProvider(BaseAIProvider):
    """
    Ollama Provider - supports both:
    1. Ollama Cloud API (FREE tier with Kimi K2.5, Gemini models)
    2. Local Ollama instance (self-hosted)
    """

    # Ollama Cloud free tier models
    CLOUD_FREE_MODELS = {
        "kimi-k2.5": ModelConfig(
            id="kimi-k2.5",
            name="Kimi K2.5",
            provider="ollama",
            max_tokens=8192,
            context_window=256000,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            is_free=True,
            latency_tier="standard",
            description="FREE - Moonshot AI's Kimi K2.5 model via Ollama Cloud",
        ),
        "gemini-2.0-flash": ModelConfig(
            id="gemini-2.0-flash",
            name="Gemini 2.0 Flash",
            provider="ollama",
            max_tokens=8192,
            context_window=1000000,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            is_free=True,
            latency_tier="fast",
            description="FREE - Google's fast multimodal model via Ollama Cloud",
        ),
        "gemini-2.0-pro": ModelConfig(
            id="gemini-2.0-pro",
            name="Gemini 2.0 Pro",
            provider="ollama",
            max_tokens=8192,
            context_window=2000000,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=True,
            is_free=True,
            latency_tier="standard",
            description="FREE - Google's most capable model via Ollama Cloud",
        ),
    }

    # Popular local models
    LOCAL_MODELS = {
        "llama3.2": ModelConfig(
            id="llama3.2",
            name="Llama 3.2",
            provider="ollama",
            max_tokens=4096,
            context_window=128000,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="standard",
            description="Local - Meta's Llama 3.2 model",
        ),
        "llama3.3": ModelConfig(
            id="llama3.3",
            name="Llama 3.3",
            provider="ollama",
            max_tokens=4096,
            context_window=128000,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="standard",
            description="Local - Meta's Llama 3.3 70B model",
        ),
        "mistral": ModelConfig(
            id="mistral",
            name="Mistral",
            provider="ollama",
            max_tokens=4096,
            context_window=32768,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="standard",
            description="Local - Mistral 7B model",
        ),
        "mixtral": ModelConfig(
            id="mixtral",
            name="Mixtral",
            provider="ollama",
            max_tokens=4096,
            context_window=32768,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="standard",
            description="Local - Mixtral 8x7B MoE model",
        ),
        "codellama": ModelConfig(
            id="codellama",
            name="CodeLlama",
            provider="ollama",
            max_tokens=4096,
            context_window=16384,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="standard",
            description="Local - Code-specialized Llama model",
        ),
        "phi4": ModelConfig(
            id="phi4",
            name="Phi-4",
            provider="ollama",
            max_tokens=4096,
            context_window=16384,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="standard",
            description="Local - Microsoft's Phi-4 model",
        ),
        "qwen2.5": ModelConfig(
            id="qwen2.5",
            name="Qwen 2.5",
            provider="ollama",
            max_tokens=4096,
            context_window=131072,
            cost_per_input_token=0.0,
            cost_per_output_token=0.0,
            supports_streaming=True,
            supports_json_mode=True,
            supports_vision=False,
            is_free=True,
            latency_tier="standard",
            description="Local - Alibaba's Qwen 2.5 model",
        ),
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "http://localhost:11434",
        use_cloud: bool = False,
        cloud_api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize Ollama provider

        Args:
            api_key: Not used for local Ollama (optional)
            api_base: Base URL for Ollama API (default: localhost:11434)
            use_cloud: Whether to use Ollama Cloud API
            cloud_api_key: API key for Ollama Cloud
        """
        self.use_cloud = use_cloud
        self.default_model = default_model

        if use_cloud:
            # Ollama Cloud uses different endpoint and requires API key
            api_base = api_base or "https://api.ollama.ai/v1"
            api_key = cloud_api_key
            rate_limit_requests = 30  # Free tier
            rate_limit_tokens = 100000
        else:
            # Local Ollama has no rate limits
            rate_limit_requests = 1000
            rate_limit_tokens = 1000000

        super().__init__(
            api_key=api_key or "",
            api_base=api_base,
            name="ollama",
            rate_limit_requests=rate_limit_requests,
            rate_limit_tokens=rate_limit_tokens,
            **kwargs,
        )

        # Combine models based on mode
        self._models = {}
        if use_cloud:
            self._models.update(self.CLOUD_FREE_MODELS)
        else:
            self._models.update(self.LOCAL_MODELS)

        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}

            if self.use_cloud and self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            timeout = 300 if not self.use_cloud else 120  # Local can be slower

            self._session = aiohttp.ClientSession(
                headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
            )
        return self._session

    def _format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """Format messages for Ollama API"""
        formatted = []
        for msg in messages:
            # Ollama uses standard roles
            if msg.role in ["system", "user", "assistant"]:
                formatted.append({"role": msg.role, "content": msg.content})
            elif msg.role == "tool":
                # Map tool to user for Ollama
                formatted.append({"role": "user", "content": f"Tool result: {msg.content}"})
        return formatted

    async def _make_request(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Make request to Ollama API"""
        session = await self._get_session()

        # Get default model based on mode
        if self.default_model:
            default_model = self.default_model
        elif self.use_cloud:
            default_model = "kimi-k2.5"
        else:
            default_model = "llama3.2"

        model = request.model or default_model

        payload = {
            "model": model,
            "messages": self._format_messages(request.messages),
            "stream": False,
            "options": {"temperature": request.temperature},
        }

        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        if self.use_cloud:
            # Ollama Cloud uses chat completions endpoint
            url = f"{self.api_base}/chat/completions"
        else:
            # Local Ollama uses /api/chat
            url = f"{self.api_base}/api/chat"

        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Ollama API error {response.status}: {error_text}")

            data = await response.json()

            # Extract content
            if self.use_cloud:
                # Cloud API returns OpenAI-compatible format
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                finish_reason = choice.get("finish_reason", "stop")

                # Extract usage (cloud API provides this)
                usage_data = data.get("usage", {})
                usage = UsageInfo(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0),
                )
            else:
                # Local Ollama returns different format
                message = data.get("message", {})
                content = message.get("content", "")
                finish_reason = "stop"

                # Estimate tokens for local (no usage info provided)
                prompt_text = " ".join([m.content for m in request.messages])
                estimated_input = len(prompt_text.split())
                estimated_output = len(content.split())

                usage = UsageInfo(
                    prompt_tokens=estimated_input,
                    completion_tokens=estimated_output,
                    total_tokens=estimated_input + estimated_output,
                )

            return ChatCompletionResponse(
                id=data.get("id", f"ollama-{model}"),
                model=model,
                content=content,
                usage=usage,
                finish_reason=finish_reason,
                tool_calls=None,
            )

    async def _stream_request(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        """Make streaming request to Ollama API"""
        session = await self._get_session()

        if self.default_model:
            default_model = self.default_model
        elif self.use_cloud:
            default_model = "kimi-k2.5"
        else:
            default_model = "llama3.2"

        model = request.model or default_model

        payload = {
            "model": model,
            "messages": self._format_messages(request.messages),
            "stream": True,
            "options": {"temperature": request.temperature},
        }

        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        if self.use_cloud:
            url = f"{self.api_base}/chat/completions"
        else:
            url = f"{self.api_base}/api/chat"

        async with session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Ollama API error {response.status}: {error_text}")

            async for line in response.content:
                line = line.decode("utf-8").strip()

                if not line:
                    continue

                try:
                    if self.use_cloud:
                        # Cloud API returns SSE format
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    else:
                        # Local Ollama returns NDJSON
                        data = json.loads(line)
                        message = data.get("message", {})
                        content = message.get("content", "")
                        if content:
                            yield content
                except json.JSONDecodeError:
                    continue

    def get_available_models(self) -> List[ModelConfig]:
        """Get list of available models"""
        return list(self._models.values())

    async def list_local_models(self) -> List[Dict[str, Any]]:
        """List all models available on local Ollama instance"""
        if self.use_cloud:
            return []

        try:
            session = await self._get_session()
            url = f"{self.api_base}/api/tags"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("models", [])
                return []
        except Exception as e:
            logger.error(f"Failed to list local Ollama models: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model to local Ollama instance"""
        if self.use_cloud:
            logger.warning("Cannot pull models in cloud mode")
            return False

        try:
            session = await self._get_session()
            url = f"{self.api_base}/api/pull"

            payload = {"name": model_name, "stream": False}

            async with session.post(url, json=payload) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    async def health_check(self) -> bool:
        """Check Ollama API health"""
        try:
            session = await self._get_session()

            if self.use_cloud:
                # Check cloud API
                url = f"{self.api_base}/models"
                async with session.get(url) as response:
                    if response.status == 200:
                        self.status = ProviderStatus.HEALTHY
                        return True
            else:
                # Check local instance
                url = f"{self.api_base}/api/tags"
                async with session.get(url) as response:
                    if response.status == 200:
                        self.status = ProviderStatus.HEALTHY
                        return True

            self.status = ProviderStatus.OFFLINE
            return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            self.status = ProviderStatus.OFFLINE
            return False

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def is_cloud(self) -> bool:
        """Check if using cloud mode"""
        return self.use_cloud

    def get_free_cloud_models(self) -> List[ModelConfig]:
        """Get free cloud models"""
        if not self.use_cloud:
            return []
        return list(self.CLOUD_FREE_MODELS.values())
