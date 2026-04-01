# PLAN_02: Discord OAuth2 Authentication

## Overview
Implement Discord OAuth2 flow for user authentication in the web portal.

## Prerequisites
- PLAN_01 completed (web module exists)
- Discord Application created at https://discord.com/developers/applications

## Task 2.1: Create web/services/oauth_service.py
```python
"""Discord OAuth2 service."""
import httpx
from urllib.parse import urlencode
from typing import Optional

from ..config import get_web_config
from ..constants import REQUIRED_DISCORD_SCOPES

class DiscordOAuthError(Exception):
    """OAuth error."""
    pass

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
        """Check if user is admin in a specific guild."""
        # Note: This requires the bot to be in the guild and have proper intents
        # For simplicity, we'll check if user has manage_server permission
        # In production, use bot's API to check member permissions
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/users/@me/guilds/{guild_id}/member",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                return False
            
            member = response.json()
            # Check for admin permissions (permission integer 0x8 = Administrator)
            permissions = int(member.get("permissions", 0))
            return (permissions & 0x8) == 0x8


def get_oauth_service() -> OAuthService:
    return OAuthService()
```

## Task 2.2: Create web/services/auth_service.py
```python
"""Authentication service - JWT management."""
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
import secrets

from ..config import get_web_config
from ..models.schemas import UserResponse, AdminCheck
from .oauth_service import get_oauth_service

class AuthService:
    """Handles JWT token creation and validation."""
    
    def __init__(self):
        self.config = get_web_config()
        self.oauth = get_oauth_service()
    
    def create_access_token(self, user_data: dict) -> tuple[str, int]:
        """Create JWT access token from user data."""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "sub": user_data["id"],
            "user": user_data,
            "iat": now,
            "exp": expire,
        }
        
        token = jwt.encode(
            payload, 
            self.config.SECRET_KEY, 
            algorithm=self.config.ALGORITHM
        )
        
        return token, self.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    def create_state(self) -> str:
        """Create OAuth state parameter to prevent CSRF."""
        return secrets.token_urlsafe(32)
    
    async def authenticate_discord_user(self, code: str) -> dict:
        """Full OAuth flow - exchange code for user data."""
        # Exchange code for token
        token_data = await self.oauth.exchange_code(code)
        access_token = token_data["access_token"]
        
        # Get user info
        discord_user = await self.oauth.get_user(access_token)
        guilds = await self.oauth.get_user_guilds(access_token)
        
        # Check admin status in configured guilds
        admin_guilds = []
        is_admin = False
        
        for guild in guilds:
            guild_id = int(guild["id"])
            if guild_id in self.config.ADMIN_GUILD_IDS:
                is_admin_in_guild = await self.oauth.check_admin_in_guild(
                    access_token, guild_id
                )
                if is_admin_in_guild:
                    admin_guilds.append({
                        "id": guild["id"],
                        "name": guild["name"],
                        "icon": guild.get("icon"),
                    })
                    is_admin = True
        
        # Build user data
        user_data = {
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
        
        return user_data


def get_auth_service() -> AuthService:
    return AuthService()
```

## Task 2.3: Create web/routers/auth.py
```python
"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import secrets

from ..dependencies import get_current_user, require_admin
from ..services.auth_service import get_auth_service
from ..services.oauth_service import get_oauth_service
from ..models.schemas import Token, UserResponse, AdminCheck
from ..exceptions import BadRequestException, UnauthorizedException
from ..config import get_web_config
from ..constants import AUTH_PREFIX

router = APIRouter()

@router.get("/login")
async def login():
    """Redirect to Discord OAuth."""
    config = get_web_config()
    auth_service = get_auth_service()
    
    state = auth_service.create_state()
    # In production, store state in Redis with short expiry for verification
    # For simplicity, we'll include it in the redirect
    
    auth_url = get_oauth_service().get_authorization_url(state)
    return RedirectResponse(auth_url)

@router.get("/callback")
async def callback(code: str, state: str):
    """OAuth callback - exchange code for token."""
    if not code:
        raise BadRequestException("Missing authorization code")
    
    auth_service = get_auth_service()
    
    try:
        user_data = await auth_service.authenticate_discord_user(code)
    except Exception as e:
        raise BadRequestException(f"Authentication failed: {str(e)}")
    
    # Create JWT
    token, expires_in = auth_service.create_access_token(user_data)
    
    # Redirect to frontend with token
    config = get_web_config()
    redirect_url = f"{config.FRONTEND_URL}/auth/callback?token={token}"
    
    return RedirectResponse(redirect_url)

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserResponse(
        discord_id=current_user["id"],
        username=current_user["username"],
        avatar=current_user.get("avatar"),
        guilds=current_user.get("guilds", []),
    )

@router.get("/admin-check", response_model=AdminCheck)
async def check_admin(current_user: dict = Depends(get_current_user)):
    """Check if user is admin in any configured guild."""
    return AdminCheck(
        is_admin=current_user.get("is_admin", False),
        admin_guilds=current_user.get("admin_guilds", []),
    )

@router.post("/logout")
async def logout():
    """Logout - frontend should discard token."""
    return {"message": "Logged out successfully"}
```

## Task 2.4: Update web/main.py to include auth router
Add to the imports and router registration:
```python
from .routers.auth import router as auth_router

# In app definition, add:
app.include_router(auth_router, prefix=AUTH_PREFIX, tags=["Authentication"])
```

## Task 2.5: Test OAuth Flow (Manual Verification)
1. Set up `.env` with Discord OAuth credentials from Developer Portal (OAuth2 redirect must match `DISCORD_REDIRECT_URI`; scopes include `identify`, `guilds`, `guilds.members.read`).
2. Optionally start the bot: `python -m bot`
3. From the **repository root**, start the web server: `uvicorn web.main:app --reload --host 0.0.0.0 --port 8000`
4. Visit `http://localhost:8000/api/auth/login`
5. Should redirect to Discord, authorize, then redirect back with token

## Task 2.6: Discord Developer Portal Setup Instructions
Add to docs or provide user with:
1. Go to https://discord.com/developers/applications
2. Create new application
3. Go to OAuth2 tab
4. Add redirect: `http://localhost:8000/api/auth/callback`
5. Copy Client ID and Client Secret to `.env`
6. Generate a secret key: `python -c "import secrets; print(secrets.token_hex(32))"`

## Verification
1. OAuth login redirects to Discord
2. After authorization, redirects to frontend with token
3. `/api/auth/me` returns user data with correct guild info
4. `/api/auth/admin-check` correctly identifies admins

## Notes
- State parameter should be validated against stored value in production (Redis); current implementation accepts `state` but does not verify it yet.
- Token should be stored securely on frontend (httpOnly cookie preferred)
- Admin check uses Discord's API directly - could be cached
- Request OAuth scopes `identify`, `guilds`, and `guilds.members.read` so `GET /users/@me/guilds/{guild.id}/member` works for permission checks.
