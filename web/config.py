"""Web configuration - separate from bot config."""
import os
from functools import lru_cache

class WebConfig:
    """FastAPI web server configuration."""
    
    # Server
    HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("WEB_PORT", "8000"))
    
    # Frontend URL (for CORS)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # Discord OAuth
    DISCORD_CLIENT_ID: str = os.getenv("DISCORD_CLIENT_ID", "")
    DISCORD_CLIENT_SECRET: str = os.getenv("DISCORD_CLIENT_SECRET", "")
    DISCORD_REDIRECT_URI: str = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8000/api/auth/callback")
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")  # Must be 32+ chars
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Discord Guild IDs where bot is used (for admin checks)
    ADMIN_GUILD_IDS: list[int] = [
        int(gid) for gid in os.getenv("ADMIN_GUILD_IDS", "").split(",") if gid
    ]
    
    @classmethod
    def validate(cls) -> None:
        """Validate required config."""
        if not cls.DISCORD_CLIENT_ID:
            raise ValueError("DISCORD_CLIENT_ID is required")
        if not cls.DISCORD_CLIENT_SECRET:
            raise ValueError("DISCORD_CLIENT_SECRET is required")
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be 32+ characters")

@lru_cache
def get_web_config() -> WebConfig:
    return WebConfig()
