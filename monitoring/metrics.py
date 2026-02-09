"""Prometheus metrics collection for Discord support bot.

This module provides metrics tracking for Discord guilds, AI requests,
database connections, and custom bot health metrics.
"""

import time
from contextlib import contextmanager
from functools import wraps
from typing import Callable, Generator, Optional, TypeVar

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    start_http_server,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# Discord metrics
DISCORD_GUILDS_TOTAL = Gauge(
    "discord_guilds_total",
    "Total number of guilds the bot is in",
    ["shard_id"],
)

DISCORD_USERS_TOTAL = Gauge(
    "discord_users_total",
    "Total number of users across all guilds",
    ["shard_id"],
)

DISCORD_SHARDS_CONNECTED = Gauge(
    "discord_shards_connected",
    "Number of connected shards",
)

# AI metrics
AI_REQUESTS_TOTAL = Counter(
    "ai_requests_total",
    "Total AI API requests",
    ["provider", "model", "status"],
)

AI_COST_TOTAL = Counter(
    "ai_cost_total",
    "Total AI API cost in USD",
    ["provider", "model"],
)

AI_LATENCY_SECONDS = Histogram(
    "ai_latency_seconds",
    "AI API request latency in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

AI_TOKENS_TOTAL = Counter(
    "ai_tokens_total",
    "Total tokens used in AI requests",
    ["provider", "model", "type"],  # type: prompt or completion
)

# Support metrics
KEYWORD_MATCHES_TOTAL = Counter(
    "keyword_matches_total",
    "Total keyword matches in support requests",
    ["keyword_category", "resolved"],
)

COST_SAVINGS_TOTAL = Counter(
    "cost_savings_total",
    "Total cost savings from keyword matching in USD",
    ["method"],
)

SUPPORT_REQUESTS_TOTAL = Counter(
    "support_requests_total",
    "Total support requests handled",
    ["resolution_type", "escalated"],
)

# Database metrics
DATABASE_CONNECTIONS_ACTIVE = Gauge(
    "database_connections_active",
    "Number of active database connections",
    ["pool"],
)

DATABASE_QUERIES_TOTAL = Counter(
    "database_queries_total",
    "Total database queries executed",
    ["operation", "table"],
)

DATABASE_QUERY_DURATION_SECONDS = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0],
)

# Redis metrics
REDIS_CONNECTIONS_ACTIVE = Gauge(
    "redis_connections_active",
    "Number of active Redis connections",
    ["pool_name"],
)

REDIS_OPERATIONS_TOTAL = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],
)

REDIS_OPERATION_DURATION_SECONDS = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
)

# Bot health metrics
BOT_INFO = Info("discord_bot", "Discord bot information")

BOT_UPTIME_SECONDS = Gauge(
    "bot_uptime_seconds",
    "Bot uptime in seconds",
)

BOT_HEARTBEAT_TIMESTAMP = Gauge(
    "bot_heartbeat_timestamp",
    "Last bot heartbeat timestamp (Unix)",
)

BOT_EVENTS_PROCESSED = Counter(
    "bot_events_processed_total",
    "Total Discord events processed",
    ["event_type"],
)

BOT_COMMANDS_TOTAL = Counter(
    "bot_commands_total",
    "Total bot commands executed",
    ["command", "status"],
)

BOT_ERRORS_TOTAL = Counter(
    "bot_errors_total",
    "Total bot errors",
    ["error_type", "source"],
)

# Rate limiting metrics
RATE_LIMIT_HITS_TOTAL = Counter(
    "rate_limit_hits_total",
    "Total rate limit hits",
    ["endpoint", "user_id"],
)

CACHE_HITS_TOTAL = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"],
)

CACHE_MISSES_TOTAL = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)


F = TypeVar("F", bound=Callable[..., any])


def track_guild_count(count: int, shard_id: Optional[int] = None) -> None:
    """Track total guild count.

    Args:
        count: Number of guilds.
        shard_id: Optional shard ID.
    """
    shard_label = str(shard_id) if shard_id is not None else "all"
    DISCORD_GUILDS_TOTAL.labels(shard_id=shard_label).set(count)


def track_user_count(count: int, shard_id: Optional[int] = None) -> None:
    """Track total user count.

    Args:
        count: Number of users.
        shard_id: Optional shard ID.
    """
    shard_label = str(shard_id) if shard_id is not None else "all"
    DISCORD_USERS_TOTAL.labels(shard_id=shard_label).set(count)


def track_shard_connection(connected: int) -> None:
    """Track number of connected shards.

    Args:
        connected: Number of connected shards.
    """
    DISCORD_SHARDS_CONNECTED.set(connected)


def track_ai_request(
    provider: str,
    model: str,
    status: str = "success",
) -> None:
    """Track AI API request.

    Args:
        provider: AI provider name (e.g., 'openai', 'anthropic').
        model: Model name used.
        status: Request status ('success' or 'error').
    """
    AI_REQUESTS_TOTAL.labels(
        provider=provider,
        model=model,
        status=status,
    ).inc()


def track_ai_cost(provider: str, model: str, cost: float) -> None:
    """Track AI API cost.

    Args:
        provider: AI provider name.
        model: Model name.
        cost: Cost in USD.
    """
    AI_COST_TOTAL.labels(provider=provider, model=model).inc(cost)


def track_ai_latency(provider: str, model: str, duration: float) -> None:
    """Track AI request latency.

    Args:
        provider: AI provider name.
        model: Model name.
        duration: Duration in seconds.
    """
    AI_LATENCY_SECONDS.labels(provider=provider, model=model).observe(duration)


def track_ai_tokens(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    """Track token usage.

    Args:
        provider: AI provider name.
        model: Model name.
        prompt_tokens: Number of prompt tokens.
        completion_tokens: Number of completion tokens.
    """
    AI_TOKENS_TOTAL.labels(
        provider=provider,
        model=model,
        type="prompt",
    ).inc(prompt_tokens)
    AI_TOKENS_TOTAL.labels(
        provider=provider,
        model=model,
        type="completion",
    ).inc(completion_tokens)


def track_keyword_match(category: str, resolved: bool = True) -> None:
    """Track keyword match.

    Args:
        category: Keyword category.
        resolved: Whether the keyword resolved the issue.
    """
    KEYWORD_MATCHES_TOTAL.labels(
        keyword_category=category,
        resolved=str(resolved).lower(),
    ).inc()


def track_cost_savings(method: str, amount: float) -> None:
    """Track cost savings.

    Args:
        method: Method used for savings (e.g., 'keyword_match', 'cache').
        amount: Amount saved in USD.
    """
    COST_SAVINGS_TOTAL.labels(method=method).inc(amount)


def track_support_request(resolution_type: str, escalated: bool = False) -> None:
    """Track support request.

    Args:
        resolution_type: How the request was resolved.
        escalated: Whether the request was escalated.
    """
    SUPPORT_REQUESTS_TOTAL.labels(
        resolution_type=resolution_type,
        escalated=str(escalated).lower(),
    ).inc()


def track_db_connection(pool: str, count: int) -> None:
    """Track active database connections.

    Args:
        pool: Connection pool name.
        count: Number of active connections.
    """
    DATABASE_CONNECTIONS_ACTIVE.labels(pool=pool).set(count)


def track_db_query(operation: str, table: str) -> None:
    """Track database query.

    Args:
        operation: Query operation (SELECT, INSERT, etc.).
        table: Table name.
    """
    DATABASE_QUERIES_TOTAL.labels(operation=operation, table=table).inc()


@contextmanager
def track_db_query_duration(
    operation: str,
    table: str,
) -> Generator[None, None, None]:
    """Context manager to track query duration.

    Args:
        operation: Query operation.
        table: Table name.

    Yields:
        None

    Example:
        with track_db_query_duration("SELECT", "users"):
            cursor.execute("SELECT * FROM users")
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        DATABASE_QUERY_DURATION_SECONDS.labels(
            operation=operation,
            table=table,
        ).observe(duration)


def track_redis_connection(pool_name: str, count: int) -> None:
    """Track active Redis connections.

    Args:
        pool_name: Connection pool name.
        count: Number of active connections.
    """
    REDIS_CONNECTIONS_ACTIVE.labels(pool_name=pool_name).set(count)


def track_redis_operation(operation: str, status: str = "success") -> None:
    """Track Redis operation.

    Args:
        operation: Operation type (GET, SET, etc.).
        status: Operation status.
    """
    REDIS_OPERATIONS_TOTAL.labels(operation=operation, status=status).inc()


@contextmanager
def track_redis_operation_duration(
    operation: str,
) -> Generator[None, None, None]:
    """Context manager to track Redis operation duration.

    Args:
        operation: Operation type.

    Yields:
        None
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        REDIS_OPERATION_DURATION_SECONDS.labels(operation=operation).observe(duration)


def set_bot_info(version: str, environment: str) -> None:
    """Set bot information.

    Args:
        version: Bot version.
        environment: Deployment environment.
    """
    BOT_INFO.info({"version": version, "environment": environment})


def set_bot_uptime(seconds: float) -> None:
    """Set bot uptime.

    Args:
        seconds: Uptime in seconds.
    """
    BOT_UPTIME_SECONDS.set(seconds)


def record_heartbeat() -> None:
    """Record bot heartbeat timestamp."""
    BOT_HEARTBEAT_TIMESTAMP.set_to_current_time()


def track_event(event_type: str) -> None:
    """Track Discord event.

    Args:
        event_type: Type of event (message, reaction, etc.).
    """
    BOT_EVENTS_PROCESSED.labels(event_type=event_type).inc()


def track_command(command: str, status: str = "success") -> None:
    """Track bot command execution.

    Args:
        command: Command name.
        status: Execution status.
    """
    BOT_COMMANDS_TOTAL.labels(command=command, status=status).inc()


def track_error(error_type: str, source: str) -> None:
    """Track bot error.

    Args:
        error_type: Type of error.
        source: Source of error (command, event, etc.).
    """
    BOT_ERRORS_TOTAL.labels(error_type=error_type, source=source).inc()


def track_rate_limit(endpoint: str, user_id: Optional[int] = None) -> None:
    """Track rate limit hit.

    Args:
        endpoint: Endpoint that was rate limited.
        user_id: Optional user ID.
    """
    user_label = str(user_id) if user_id else "global"
    RATE_LIMIT_HITS_TOTAL.labels(endpoint=endpoint, user_id=user_label).inc()


def track_cache_hit(cache_type: str) -> None:
    """Track cache hit.

    Args:
        cache_type: Type of cache (redis, memory, etc.).
    """
    CACHE_HITS_TOTAL.labels(cache_type=cache_type).inc()


def track_cache_miss(cache_type: str) -> None:
    """Track cache miss.

    Args:
        cache_type: Type of cache.
    """
    CACHE_MISSES_TOTAL.labels(cache_type=cache_type).inc()


def timed(metric: Histogram, **labels) -> Callable[[F], F]:
    """Decorator to time function execution.

    Args:
        metric: Histogram metric to observe.
        **labels: Labels for the metric.

    Returns:
        Decorator function.

    Example:
        @timed(AI_LATENCY_SECONDS, provider="openai", model="gpt-4")
        async def make_ai_request():
            pass
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start
                metric.labels(**labels).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                metric.labels(**labels).observe(duration)

        return (
            async_wrapper if callable(getattr(func, "__code__", None)) else sync_wrapper
        )

    return decorator


class MetricsHandler:
    """Handler for serving Prometheus metrics."""

    def __init__(self, port: int = 8000, host: str = "0.0.0.0"):
        """Initialize metrics handler.

        Args:
            port: Port to serve metrics on.
            host: Host to bind to.
        """
        self.port = port
        self.host = host
        self._server = None

    def start(self) -> None:
        """Start the metrics HTTP server."""
        self._server = start_http_server(self.port, self.host)

    def get_metrics(self) -> tuple:
        """Get current metrics in Prometheus format.

        Returns:
            Tuple of (content_type, data).
        """
        return CONTENT_TYPE_LATEST, generate_latest(REGISTRY)


# Global metrics handler instance
_metrics_handler: Optional[MetricsHandler] = None


def get_metrics_handler() -> Optional[MetricsHandler]:
    """Get the global metrics handler.

    Returns:
        MetricsHandler instance or None.
    """
    return _metrics_handler


def start_metrics_server(port: int = 8000, host: str = "0.0.0.0") -> MetricsHandler:
    """Start metrics server.

    Args:
        port: Port to serve metrics on.
        host: Host to bind to.

    Returns:
        MetricsHandler instance.
    """
    global _metrics_handler
    _metrics_handler = MetricsHandler(port=port, host=host)
    _metrics_handler.start()
    return _metrics_handler
