"""Resolve Discord guild snowflakes to internal Guild UUIDs for tenant-scoped queries."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Guild
from web.exceptions import ForbiddenException, NotFoundException


def admin_discord_guild_ids(current_user: dict) -> List[str]:
    return [str(g["id"]) for g in current_user.get("admin_guilds", [])]


def ensure_admin_for_discord_guild(current_user: dict, discord_guild_id: str) -> None:
    if str(discord_guild_id) not in admin_discord_guild_ids(current_user):
        raise ForbiddenException("Not admin in this guild")


def resolve_guild_uuid(session: Session, discord_guild_id: str) -> UUID:
    guild = session.execute(
        select(Guild).where(Guild.discord_id == str(discord_guild_id))
    ).scalar_one_or_none()
    if guild is None:
        raise NotFoundException("Guild not found")
    return guild.id


def target_discord_guild_id(current_user: dict, guild_id: Optional[str]) -> str:
    """Discord snowflake from query/path or first guild where user is admin."""
    admin_ids = admin_discord_guild_ids(current_user)
    if guild_id is not None:
        gid = str(guild_id)
        if gid not in admin_ids:
            raise ForbiddenException("Not admin in this guild")
        return gid
    if not admin_ids:
        raise ForbiddenException("No guild access")
    return admin_ids[0]
