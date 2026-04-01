"""Authentication service - JWT management."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from ..config import get_web_config
from .oauth_service import get_oauth_service


class AuthService:
    """Handles JWT token creation and validation."""

    def __init__(self):
        self.config = get_web_config()
        self.oauth = get_oauth_service()

    def create_access_token(self, user_data: dict[str, Any]) -> tuple[str, int]:
        """Create JWT access token from user data."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES)
        iat_ts = int(now.timestamp())
        exp_ts = int(expire.timestamp())

        payload = {
            "sub": user_data["id"],
            "user": user_data,
            "iat": iat_ts,
            "exp": exp_ts,
        }

        token = jwt.encode(payload, self.config.SECRET_KEY, algorithm=self.config.ALGORITHM)

        return token, self.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def create_state(self) -> str:
        """Create OAuth state parameter to prevent CSRF."""
        return secrets.token_urlsafe(32)

    async def authenticate_discord_user(self, code: str) -> dict:
        """Full OAuth flow - exchange code for user data."""
        token_data = await self.oauth.exchange_code(code)
        access_token = token_data["access_token"]

        discord_user = await self.oauth.get_user(access_token)
        guilds = await self.oauth.get_user_guilds(access_token)

        admin_guilds = []
        is_admin = False

        for guild in guilds:
            guild_id = int(guild["id"])
            if guild_id in self.config.ADMIN_GUILD_IDS:
                is_admin_in_guild = await self.oauth.check_admin_in_guild(
                    access_token, guild_id
                )
                if is_admin_in_guild:
                    admin_guilds.append(
                        {
                            "id": guild["id"],
                            "name": guild["name"],
                            "icon": guild.get("icon"),
                        }
                    )
                    is_admin = True

        return {
            "id": discord_user["id"],
            "username": discord_user["username"],
            "global_name": discord_user.get("global_name"),
            "avatar": discord_user.get("avatar"),
            "discriminator": discord_user["discriminator"],
            "guilds": [
                {
                    "id": g["id"],
                    "name": g["name"],
                    "icon": g.get("icon"),
                }
                for g in guilds
            ],
            "is_admin": is_admin,
            "admin_guilds": admin_guilds,
        }


def get_auth_service() -> AuthService:
    return AuthService()
