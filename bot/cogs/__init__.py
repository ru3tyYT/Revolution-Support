"""Cog package initialization."""

from .stats import Stats
from .settings import Settings
from .ping import Ping
from .disable import Disable
from .admin import Admin
from .knowledge import KnowledgeCog
from .forums import Forums
from .forum_commands import ForumCommands

__all__ = [
    "Stats",
    "Settings",
    "Ping",
    "Disable",
    "Admin",
    "KnowledgeCog",
    "Forums",
    "ForumCommands",
]
