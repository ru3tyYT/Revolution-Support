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
