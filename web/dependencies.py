"""FastAPI dependencies for authentication and database."""
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional

from .config import get_web_config
from .exceptions import UnauthorizedException, ForbiddenException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Validate JWT and return user data."""
    if not token:
        raise UnauthorizedException()
    
    config = get_web_config()
    
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        user_data = payload.get("user")
        if not user_data:
            raise UnauthorizedException("Invalid token")
        return user_data
    except JWTError:
        raise UnauthorizedException("Invalid token")

async def get_current_user_optional(token: str = Depends(oauth2_scheme)) -> Optional[dict]:
    """Get user if authenticated, None otherwise."""
    try:
        return await get_current_user(token)
    except UnauthorizedException:
        return None

async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin privileges."""
    if not current_user.get("is_admin"):
        raise ForbiddenException("Admin privileges required")
    return current_user
