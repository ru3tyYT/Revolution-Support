"""Structured JSON logging configuration for Discord support bot.

This module provides centralized logging with structured JSON output,
request tracking, and context injection for guild and shard information.
"""

import json
import logging
import logging.handlers
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

# Context variables for request tracking
request_id: ContextVar[str] = ContextVar("request_id", default="")
guild_id: ContextVar[Optional[int]] = ContextVar("guild_id", default=None)
shard_id: ContextVar[Optional[int]] = ContextVar("shard_id", default=None)
user_id: ContextVar[Optional[int]] = ContextVar("user_id", default=None)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON string representation of the log record.
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            },
        }

        # Add context information
        if request_id.get():
            log_data["request_id"] = request_id.get()
        if guild_id.get():
            log_data["guild_id"] = guild_id.get()
        if shard_id.get() is not None:
            log_data["shard_id"] = shard_id.get()
        if user_id.get():
            log_data["user_id"] = user_id.get()

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "asctime",
                "request_id",
                "guild_id",
                "shard_id",
                "user_id",
            ):
                log_data[key] = value

        return json.dumps(log_data, default=str)


class ContextFilter(logging.Filter):
    """Filter that injects context information into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Inject context into log record.

        Args:
            record: The log record to filter.

        Returns:
            True to include the record.
        """
        record.request_id = request_id.get()
        record.guild_id = guild_id.get()
        record.shard_id = shard_id.get()
        record.user_id = user_id.get()
        return True


def setup_logging(
    level: str = "INFO",
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """Set up logging configuration.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
        log_dir: Directory for log files.
        max_bytes: Maximum size of log file before rotation.
        backup_count: Number of backup files to keep.
        enable_console: Whether to log to console.
        enable_file: Whether to log to file.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create log directory if needed
    if enable_file:
        os.makedirs(log_dir, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = JSONFormatter()
    context_filter = ContextFilter()

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(context_filter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if enable_file:
        log_file = os.path.join(log_dir, "discord-bot.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)

        # Error log file
        error_log_file = os.path.join(log_dir, "discord-bot-error.log")
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(context_filter)
        root_logger.addHandler(error_handler)

    logging.info("Logging configured", extra={"log_level": level})


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name, typically __name__.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


def set_request_id(req_id: Optional[str] = None) -> str:
    """Set the request ID for the current context.

    Args:
        req_id: Request ID to set. If None, generates a new UUID.

    Returns:
        The request ID that was set.
    """
    new_id = req_id or str(uuid.uuid4())
    request_id.set(new_id)
    return new_id


def set_guild_context(
    guild: Optional[int] = None,
    shard: Optional[int] = None,
    user: Optional[int] = None,
) -> None:
    """Set guild/shard context for the current execution.

    Args:
        guild: Guild ID.
        shard: Shard ID.
        user: User ID.
    """
    if guild is not None:
        guild_id.set(guild)
    if shard is not None:
        shard_id.set(shard)
    if user is not None:
        user_id.set(user)


def clear_context() -> None:
    """Clear all context variables."""
    request_id.set("")
    guild_id.set(None)
    shard_id.set(None)
    user_id.set(None)


class LogContext:
    """Context manager for setting log context."""

    def __init__(
        self,
        request: Optional[str] = None,
        guild: Optional[int] = None,
        shard: Optional[int] = None,
        user: Optional[int] = None,
    ):
        """Initialize log context.

        Args:
            request: Request ID. If None, generates new UUID.
            guild: Guild ID.
            shard: Shard ID.
            user: User ID.
        """
        self.request = request or str(uuid.uuid4())
        self.guild = guild
        self.shard = shard
        self.user = user
        self.token: Any = None

    def __enter__(self) -> "LogContext":
        """Enter context and set variables."""
        self.request_token = request_id.set(self.request)
        if self.guild is not None:
            self.guild_token = guild_id.set(self.guild)
        if self.shard is not None:
            self.shard_token = shard_id.set(self.shard)
        if self.user is not None:
            self.user_token = user_id.set(self.user)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and reset variables."""
        request_id.reset(self.request_token)
        if self.guild is not None:
            guild_id.reset(self.guild_token)
        if self.shard is not None:
            shard_id.reset(self.shard_token)
        if self.user is not None:
            user_id.reset(self.user_token)
