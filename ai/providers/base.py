"""
Abstract base class for AI providers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Provider operational status"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class ModelConfig:
    """Configuration for an AI model"""

    id: str
    name: str
    provider: str
    max_tokens: int
    context_window: int
    cost_per_input_token: float
    cost_per_output_token: float
    supports_streaming: bool = True
    supports_json_mode: bool = False
    supports_vision: bool = False
    is_free: bool = False
    latency_tier: str = "standard"  # fast, standard, slow
    description: str = ""


@dataclass
class UsageInfo:
    """Usage tracking information"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatMessage:
    """Chat message structure"""

    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ChatCompletionRequest:
    """Request for chat completion"""

    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[str] = None


@dataclass
class ChatCompletionResponse:
    """Response from chat completion"""

    id: str
    model: str
    content: str
    usage: UsageInfo
    finish_reason: str = "stop"
    tool_calls: Optional[List[Dict]] = None


@dataclass
class RateLimitInfo:
    """Rate limit tracking"""

    requests_per_minute: int
    tokens_per_minute: int
    current_requests: int = 0
    current_tokens: int = 0
    last_request_time: float = field(default_factory=time.time)
    backoff_until: float = 0.0


class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""

    def __init__(
        self,
        api_key: str,
        api_base: Optional[str] = None,
        name: str = "base",
        rate_limit_requests: int = 60,
        rate_limit_tokens: int = 100000,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        self.api_key = api_key
        self.api_base = api_base
        self.name = name
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

        self.rate_limit = RateLimitInfo(
            requests_per_minute=rate_limit_requests, tokens_per_minute=rate_limit_tokens
        )
        self.status = ProviderStatus.HEALTHY
        self._usage_history: List[UsageInfo] = []
        self._models: Dict[str, ModelConfig] = {}
        self._lock = asyncio.Lock()

    @abstractmethod
    async def _make_request(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Make actual API request - must be implemented by subclasses"""
        pass

    @abstractmethod
    async def _stream_request(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """Make streaming API request - must be implemented by subclasses"""
        pass

    @abstractmethod
    def get_available_models(self) -> List[ModelConfig]:
        """Get list of available models for this provider"""
        pass

    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """
        Execute chat completion with rate limiting and retry logic
        """
        await self._check_rate_limit()

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                if request.stream:
                    raise ValueError("Use stream_chat for streaming requests")

                response = await self._make_request(request)

                # Calculate latency
                latency_ms = (time.time() - start_time) * 1000
                response.usage.latency_ms = latency_ms

                # Track usage
                await self._track_usage(response.usage)
                self.status = ProviderStatus.HEALTHY

                return response

            except Exception as e:
                error_msg = str(e).lower()

                # Check for rate limit errors
                if (
                    "rate limit" in error_msg
                    or "429" in error_msg
                    or "too many requests" in error_msg
                ):
                    self.status = ProviderStatus.RATE_LIMITED
                    delay = self._calculate_backoff(attempt, error_msg)
                    logger.warning(
                        f"Rate limit hit for {self.name}, backing off for {delay}s"
                    )
                    await asyncio.sleep(delay)
                    continue

                # Check for server errors (5xx) - these are retryable
                if any(code in error_msg for code in ["500", "502", "503", "504"]):
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Server error for {self.name}, retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue

                # Other errors - mark as degraded
                self.status = ProviderStatus.ERROR
                logger.error(f"Error from {self.name}: {e}")

                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

        raise RuntimeError(f"Max retries ({self.max_retries}) exceeded for {self.name}")

    async def stream_chat(
        self, request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """
        Execute streaming chat completion with rate limiting and retry logic
        """
        await self._check_rate_limit()

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                if not request.stream:
                    request.stream = True

                async for chunk in self._stream_request(request):
                    yield chunk

                # Track latency
                latency_ms = (time.time() - start_time) * 1000
                await self._track_usage(UsageInfo(latency_ms=latency_ms))
                self.status = ProviderStatus.HEALTHY

                return

            except Exception as e:
                error_msg = str(e).lower()

                if "rate limit" in error_msg or "429" in error_msg:
                    self.status = ProviderStatus.RATE_LIMITED
                    delay = self._calculate_backoff(attempt, error_msg)
                    logger.warning(
                        f"Rate limit hit for {self.name}, backing off for {delay}s"
                    )
                    await asyncio.sleep(delay)
                    continue

                if any(code in error_msg for code in ["500", "502", "503", "504"]):
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Server error for {self.name}, retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue

                self.status = ProviderStatus.ERROR
                logger.error(f"Error from {self.name}: {e}")

                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise

        raise RuntimeError(f"Max retries ({self.max_retries}) exceeded for {self.name}")

    def _calculate_backoff(self, attempt: int, error_msg: str = "") -> float:
        """Calculate exponential backoff delay"""
        # Check if API provided a retry-after header hint
        import re

        retry_match = re.search(r"retry after (\d+)", error_msg)
        if retry_match:
            return float(retry_match.group(1))

        # Exponential backoff with jitter
        import random

        delay = min(
            self.base_delay * (self.exponential_base**attempt) + random.uniform(0, 1),
            self.max_delay,
        )
        return delay

    async def _check_rate_limit(self):
        """Check and enforce rate limits"""
        async with self._lock:
            now = time.time()

            # Check if in backoff period
            if now < self.rate_limit.backoff_until:
                wait_time = self.rate_limit.backoff_until - now
                logger.warning(f"{self.name} in backoff, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            # Reset counters if more than a minute has passed
            if now - self.rate_limit.last_request_time > 60:
                self.rate_limit.current_requests = 0
                self.rate_limit.current_tokens = 0
                self.rate_limit.last_request_time = now

            # Check limits
            if self.rate_limit.current_requests >= self.rate_limit.requests_per_minute:
                wait_time = 60 - (now - self.rate_limit.last_request_time)
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached for {self.name}, waiting {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                    self.rate_limit.current_requests = 0

            self.rate_limit.current_requests += 1

    async def _track_usage(self, usage: UsageInfo):
        """Track API usage"""
        async with self._lock:
            self._usage_history.append(usage)
            self.rate_limit.current_tokens += usage.total_tokens

            # Keep last 1000 usage records
            if len(self._usage_history) > 1000:
                self._usage_history = self._usage_history[-1000:]

    def get_usage_stats(self, minutes: int = 60) -> Dict[str, Any]:
        """Get usage statistics for the last N minutes"""
        cutoff = datetime.utcnow().timestamp() - (minutes * 60)
        recent_usage = [
            u for u in self._usage_history if u.timestamp.timestamp() > cutoff
        ]

        if not recent_usage:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "avg_latency_ms": 0.0,
            }

        return {
            "total_requests": len(recent_usage),
            "total_tokens": sum(u.total_tokens for u in recent_usage),
            "total_cost": sum(u.cost for u in recent_usage),
            "avg_latency_ms": sum(u.latency_ms for u in recent_usage)
            / len(recent_usage),
        }

    def get_status(self) -> ProviderStatus:
        """Get current provider status"""
        return self.status

    def is_healthy(self) -> bool:
        """Check if provider is healthy"""
        return self.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]

    def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model"""
        return self._models.get(model_id)

    def estimate_cost(
        self, model_id: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost for a request"""
        model = self._models.get(model_id)
        if not model:
            return 0.0

        return (
            input_tokens * model.cost_per_input_token
            + output_tokens * model.cost_per_output_token
        )

    async def health_check(self) -> bool:
        """Perform health check - can be overridden by subclasses"""
        try:
            # Default: check if we have an API key
            if not self.api_key:
                self.status = ProviderStatus.ERROR
                return False
            return True
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            self.status = ProviderStatus.ERROR
            return False
