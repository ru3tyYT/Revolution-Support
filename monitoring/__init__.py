"""Monitoring and logging system for Discord support bot."""

from .logging_config import get_logger, setup_logging
from .metrics import (
    track_guild_count,
    track_user_count,
    track_ai_request,
    track_ai_cost,
    track_ai_latency,
    track_keyword_match,
    track_cost_savings,
    track_db_connection,
    track_redis_connection,
    get_metrics_handler,
    start_metrics_server,
)

__all__ = [
    "get_logger",
    "setup_logging",
    "track_guild_count",
    "track_user_count",
    "track_ai_request",
    "track_ai_cost",
    "track_ai_latency",
    "track_keyword_match",
    "track_cost_savings",
    "track_db_connection",
    "track_redis_connection",
    "get_metrics_handler",
    "start_metrics_server",
]
