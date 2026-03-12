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
