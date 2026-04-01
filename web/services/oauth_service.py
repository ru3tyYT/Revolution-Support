"""Discord OAuth2 service."""
import httpx
from urllib.parse import urlencode

from ..config import get_web_config
from ..constants import REQUIRED_DISCORD_SCOPES


class DiscordOAuthError(Exception):
    """OAuth error."""


class OAuthService:
    """Discord OAuth2 service."""

    def __init__(self):
        self.config = get_web_config()
        self.base_url = "https://discord.com/api"

    def get_authorization_url(self, state: str) -> str:
        """Generate Discord OAuth authorization URL."""
        params = {
            "client_id": self.config.DISCORD_CLIENT_ID,
            "redirect_uri": self.config.DISCORD_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(REQUIRED_DISCORD_SCOPES),
            "state": state,
        }
        return f"{self.base_url}/oauth2/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/oauth2/token",
                data={
                    "client_id": self.config.DISCORD_CLIENT_ID,
                    "client_secret": self.config.DISCORD_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.config.DISCORD_REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise DiscordOAuthError(f"Token exchange failed: {response.text}")

            return response.json()

    async def get_user(self, access_token: str) -> dict:
        """Fetch current user's Discord data."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                raise DiscordOAuthError(f"Failed to get user: {response.text}")

            return response.json()

    async def get_user_guilds(self, access_token: str) -> list:
        """Fetch user's Discord guilds (servers)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                raise DiscordOAuthError(f"Failed to get guilds: {response.text}")

            return response.json()

    async def check_admin_in_guild(self, access_token: str, guild_id: int) -> bool:
        """Check if user has Administrator in a specific guild (OAuth member endpoint)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/@me/guilds/{guild_id}/member",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                return False

            member = response.json()
            raw = member.get("permissions", 0)
            permissions = int(raw) if raw is not None else 0
            return (permissions & 0x8) == 0x8


def get_oauth_service() -> OAuthService:
    return OAuthService()
