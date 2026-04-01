"""Authentication routes.

OAuth `state` is not verified server-side yet; use Redis or signed state in production.
"""
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from ..config import get_web_config
from ..dependencies import get_current_user
from ..exceptions import BadRequestException
from ..models.schemas import AdminCheck, UserResponse
from ..services.auth_service import get_auth_service
from ..services.oauth_service import get_oauth_service

router = APIRouter()


@router.get("/login")
async def login():
    """Redirect to Discord OAuth."""
    auth_service = get_auth_service()
    state = auth_service.create_state()
    auth_url = get_oauth_service().get_authorization_url(state)
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(code: Optional[str] = None, state: Optional[str] = None):
    """OAuth callback - exchange code for token."""
    _ = state  # reserved for future CSRF validation (Redis / signed state)
    if not code:
        raise BadRequestException("Missing authorization code")

    auth_service = get_auth_service()

    try:
        user_data = await auth_service.authenticate_discord_user(code)
    except Exception as e:
        raise BadRequestException(f"Authentication failed: {str(e)}") from e

    token, _ = auth_service.create_access_token(user_data)

    config = get_web_config()
    redirect_url = f"{config.FRONTEND_URL}/auth/callback?{urlencode({'token': token})}"
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
