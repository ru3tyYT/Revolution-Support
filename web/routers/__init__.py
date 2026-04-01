"""API routers."""
from .ai import router as ai_router
from .analytics import router as analytics_router
from .auth import router as auth_router
from .guilds import router as guilds_router
from .knowledge import router as knowledge_router
from .tickets import router as tickets_router

__all__ = [
    "ai_router",
    "analytics_router",
    "auth_router",
    "guilds_router",
    "knowledge_router",
    "tickets_router",
]
