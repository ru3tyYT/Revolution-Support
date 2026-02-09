"""
Configuration management using environment variables.
Uses python-dotenv for loading .env files.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Configuration class using environment variables."""

    # Discord Bot Configuration
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!")

    # Clustering Configuration
    # Enable clustering for 250k+ users (5 shards per cluster)
    CLUSTER_ENABLED: bool = os.getenv("CLUSTER_ENABLED", "true").lower() == "true"
    SHARDS_PER_CLUSTER: int = int(os.getenv("SHARDS_PER_CLUSTER", "5"))
    TOTAL_SHARDS: int | None = (
        int(os.getenv("TOTAL_SHARDS")) if os.getenv("TOTAL_SHARDS") else None
    )
    CLUSTER_ID: int | None = (
        int(os.getenv("CLUSTER_ID")) if os.getenv("CLUSTER_ID") else None
    )

    # Performance Configuration
    MAX_MESSAGES: int = int(os.getenv("MAX_MESSAGES", "10000"))
    MESSAGE_CACHE_TTL: int = int(os.getenv("MESSAGE_CACHE_TTL", "300"))  # seconds

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///supportbot.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Support System Configuration
    SUPPORT_GUILD_ID: int | None = (
        int(os.getenv("SUPPORT_GUILD_ID")) if os.getenv("SUPPORT_GUILD_ID") else None
    )
    SUPPORT_CHANNEL_ID: int | None = (
        int(os.getenv("SUPPORT_CHANNEL_ID"))
        if os.getenv("SUPPORT_CHANNEL_ID")
        else None
    )
    TICKET_CATEGORY_ID: int | None = (
        int(os.getenv("TICKET_CATEGORY_ID"))
        if os.getenv("TICKET_CATEGORY_ID")
        else None
    )

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_COMMANDS: int = int(os.getenv("RATE_LIMIT_COMMANDS", "5"))  # per minute

    # Webhook/Status Configuration
    STATUS_WEBHOOK: str | None = os.getenv("STATUS_WEBHOOK")
    ERROR_WEBHOOK: str | None = os.getenv("ERROR_WEBHOOK")

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration values."""
        errors = []

        # Required configuration
        if not cls.DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN is required")

        if not cls.DISCORD_TOKEN.startswith(("MTA", "Nz", "ND", "NT")):
            errors.append("DISCORD_TOKEN appears to be invalid")

        # Validate clustering configuration
        if cls.CLUSTER_ENABLED:
            if cls.TOTAL_SHARDS and cls.TOTAL_SHARDS < 1:
                errors.append("TOTAL_SHARDS must be at least 1")

            if cls.SHARDS_PER_CLUSTER < 1:
                errors.append("SHARDS_PER_CLUSTER must be at least 1")

            if cls.CLUSTER_ID is not None and cls.CLUSTER_ID < 0:
                errors.append("CLUSTER_ID must be non-negative")

        # Validate database URL
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")

        if errors:
            print("Configuration errors:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)

    @classmethod
    def get_shard_ids(cls) -> list[int] | None:
        """
        Calculate shard IDs for this cluster.
        Returns None if clustering is disabled.
        """
        if not cls.CLUSTER_ENABLED or cls.CLUSTER_ID is None:
            return None

        start_shard = cls.CLUSTER_ID * cls.SHARDS_PER_CLUSTER
        end_shard = start_shard + cls.SHARDS_PER_CLUSTER

        if cls.TOTAL_SHARDS:
            end_shard = min(end_shard, cls.TOTAL_SHARDS)

        return list(range(start_shard, end_shard))

    @classmethod
    def to_dict(cls) -> dict:
        """Return configuration as a dictionary (for debugging)."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and not callable(getattr(cls, key))
        }
