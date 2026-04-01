# PLAN_01: Backend Setup - FastAPI Project Structure

## Overview
Create the FastAPI backend foundation with proper project structure, dependencies, and configuration.

## Prerequisites
- Python 3.11+
- Existing `supportbot` project at `/Users/masonliang/supportbot`

## Task 1.1: Add Dependencies
Add to `requirements.txt`:
```python
# Web Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Authentication
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# Form handling
python-multipart>=0.0.6

# HTTP client (for Discord OAuth)
httpx>=0.26.0
```

Run: `pip install -r requirements.txt`

## Task 1.2: Create Web Module Structure
Create the following directory structure:
```
web/
├── __init__.py
├── main.py              # FastAPI app entry point
├── config.py            # Web-specific config
├── dependencies.py      # Auth dependencies, DB session
├── exceptions.py        # Custom exceptions
├── constants.py         # Constants (scopes, etc.)
├── routers/
│   ├── __init__.py
│   ├── auth.py          # OAuth2 endpoints
│   ├── ai.py            # /api/ask
│   ├── knowledge.py     # /api/knowledge/*
│   ├── analytics.py    # /api/analytics/*
│   ├── guilds.py       # /api/guilds/*
│   └── tickets.py     # /api/tickets/*
├── services/
│   ├── __init__.py
│   ├── auth_service.py
│   └── oauth_service.py
└── models/
    ├── __init__.py
    ├── schemas.py      # Pydantic request/response models
    └── token.py       # JWT schemas
```

## Task 1.3: Create web/config.py
```python
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
```

## Task 1.4: Create web/constants.py
```python
"""Constants for OAuth and API."""

# Discord OAuth scopes
DISCORD_SCOPES = {
    "identify": "View your account information",
    "guilds": "View your Discord servers",
    "guilds.members.read": "View members in servers",
    "email": "View your email (if verified)",
}

# Required scopes for this app (guilds.members.read: member permission API)
REQUIRED_DISCORD_SCOPES = ["identify", "guilds", "guilds.members.read"]

# Token type
TOKEN_TYPE = "bearer"

# API routes
API_PREFIX = "/api"
AUTH_PREFIX = "/api/auth"
WEB_PREFIX = "/web"
```

## Task 1.5: Create web/exceptions.py
```python
"""Custom exceptions for the web app."""
from fastapi import HTTPException, status

class WebException(HTTPException):
    """Base web exception."""
    pass

class UnauthorizedException(WebException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class ForbiddenException(WebException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class NotFoundException(WebException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class BadRequestException(WebException):
    def __init__(self, detail: str = "Invalid request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
```

## Task 1.6: Create web/models/schemas.py
```python
"""Pydantic schemas for API requests/responses."""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    discord_id: str
    username: str
    avatar: Optional[str] = None

# User schemas
class DiscordUser(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar: Optional[str] = None
    global_name: Optional[str] = None

class UserResponse(BaseModel):
    discord_id: str
    username: str
    avatar: Optional[str] = None
    guilds: List[dict]  # Simplified guild data

class AdminCheck(BaseModel):
    is_admin: bool
    admin_guilds: List[dict]

# Guild schemas
class GuildSettings(BaseModel):
    id: str
    name: str
    icon: Optional[str]
    is_admin: bool

# Analytics schemas
class AnalyticsSummary(BaseModel):
    total_queries: int
    successful_queries: int
    failed_queries: int
    average_response_time_ms: float
    cost_total: float
    top_keywords: List[dict]
    response_type_breakdown: dict

class QueryLogEntry(BaseModel):
    id: str
    query: str
    response_type: str
    confidence_score: Optional[float]
    processing_time_ms: Optional[int]
    created_at: datetime

# Knowledge schemas
class KnowledgeDocResponse(BaseModel):
    id: str
    title: str
    source: Optional[str]
    doc_type: str
    created_at: datetime
    is_processed: bool

class KnowledgeSearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float

# Ticket schemas  
class TicketResponse(BaseModel):
    id: str
    user_id: str
    guild_id: str
    channel_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: List[dict]

# AI Ask schemas
class AskRequest(BaseModel):
    question: str
    guild_id: Optional[str] = None  # Optional for external API

class AskResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[str] = []
    response_type: str  # keyword_match, semantic_search, knowledge_base, ai_fallback
```

## Task 1.7: Create web/models/token.py
```python
"""JWT token schemas."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TokenPayload(BaseModel):
    """JWT payload structure."""
    sub: str  # Discord user ID
    iat: datetime
    exp: datetime

class RefreshTokenRequest(BaseModel):
    refresh_token: str
```

## Task 1.8: Create web/dependencies.py
```python
"""FastAPI dependencies for authentication and database."""
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import get_web_config
from .exceptions import ForbiddenException, UnauthorizedException

http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> dict:
    """Validate JWT and return user data."""
    if not credentials:
        raise UnauthorizedException()

    token = credentials.credentials
    config = get_web_config()

    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user_data = payload.get("user")
        if not user_data:
            raise UnauthorizedException("Invalid token")
        return user_data
    except JWTError:
        raise UnauthorizedException("Invalid token")


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> Optional[dict]:
    """Get user if authenticated, None otherwise."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except UnauthorizedException:
        return None


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin privileges."""
    if not current_user.get("is_admin"):
        raise ForbiddenException("Admin privileges required")
    return current_user
```

## Task 1.9: Create web/main.py
```python
"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import get_web_config
from .constants import API_PREFIX

# Import routers (will be created in PLAN_03)
# from .routers import auth, ai, knowledge, analytics, guilds, tickets

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    config = get_web_config()
    config.validate()
    yield
    # Shutdown

app = FastAPI(
    title="Discord Support Bot API",
    description="Web API for Discord Support Bot",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
config = get_web_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (will be added in PLAN_03)
# app.include_router(auth.router, prefix=AUTH_PREFIX, tags=["auth"])
# app.include_router(ai.router, prefix=API_PREFIX, tags=["ai"])
# etc.

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Discord Support Bot API",
        "version": "1.0.0",
        "docs": "/docs"
    }
```

## Task 1.10: Create web/__init__.py
```python
"""Web module."""
```

## Task 1.11: Update .env.example
Add to `.env.example`:
```bash
# Web Server
WEB_HOST=0.0.0.0
WEB_PORT=8000
FRONTEND_URL=http://localhost:5173

# Discord OAuth (get from Discord Developer Portal)
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret
DISCORD_REDIRECT_URI=http://localhost:8000/api/auth/callback

# JWT Secret (generate: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=your_32_character_minimum_secret_key

# Admin Guild IDs (comma-separated Discord server IDs)
ADMIN_GUILD_IDS=123456789,987654321
```

## Verification
1. Set minimal OAuth env vars (e.g. `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `SECRET_KEY` with 32+ chars), then run `python -c "from web.main import app; print('OK')"` — should import without errors.
2. Run `python -c "from web.config import WebConfig; WebConfig.validate()"` — should fail gracefully if required env vars are missing.
3. From the **repository root**, run `uvicorn web.main:app --reload --host 0.0.0.0 --port 8000` and open `/docs` after the auth router is registered (PLAN_02).

## Notes
- This creates the foundation only - no actual routes yet
- Routes added in PLAN_03
- Authentication logic added in PLAN_02
