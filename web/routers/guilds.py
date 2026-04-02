"""Guild management API routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from database.connection import get_db_context
from database.models import Guild
from web.dependencies import require_admin
from web.exceptions import NotFoundException
from web.models.schemas import GuildSettings
from web.services.guild_context import ensure_admin_for_discord_guild

router = APIRouter()


class GuildSettingsUpdate(BaseModel):
    auto_respond: Optional[bool] = None
    confidence_threshold: Optional[float] = None
    support_channel_id: Optional[str] = None
    log_channel_id: Optional[str] = None


@router.get("", response_model=list[GuildSettings])
async def list_guilds(current_user: dict = Depends(require_admin)):
    admin_guilds = current_user.get("admin_guilds", [])
    with get_db_context() as session:
        out: list[GuildSettings] = []
        for g in admin_guilds:
            gid = str(g["id"])
            row = session.execute(
                select(Guild).where(Guild.discord_id == gid)
            ).scalar_one_or_none()
            if row:
                out.append(
                    GuildSettings(
                        id=gid,
                        name=row.name,
                        icon=g.get("icon"),
                        is_admin=True,
                    )
                )
            else:
                out.append(
                    GuildSettings(
                        id=gid,
                        name=g.get("name", "Unknown"),
                        icon=g.get("icon"),
                        is_admin=True,
                    )
                )
        return out


@router.get("/{guild_id}", response_model=GuildSettings)
async def get_guild_settings(
    guild_id: str,
    current_user: dict = Depends(require_admin),
):
    ensure_admin_for_discord_guild(current_user, guild_id)
    with get_db_context() as session:
        row = session.execute(
            select(Guild).where(Guild.discord_id == str(guild_id))
        ).scalar_one_or_none()
        if not row:
            raise NotFoundException("Guild not found")
        meta = next(
            (g for g in current_user.get("admin_guilds", []) if str(g["id"]) == str(guild_id)),
            {},
        )
        return GuildSettings(
            id=str(guild_id),
            name=row.name,
            icon=meta.get("icon"),
            is_admin=True,
        )


@router.patch("/{guild_id}")
async def update_guild_settings(
    guild_id: str,
    settings: GuildSettingsUpdate,
    current_user: dict = Depends(require_admin),
):
    ensure_admin_for_discord_guild(current_user, guild_id)
    with get_db_context() as session:
        row = session.execute(
            select(Guild).where(Guild.discord_id == str(guild_id))
        ).scalar_one_or_none()
        if not row:
            raise NotFoundException("Guild not found")
        if settings.auto_respond is not None:
            row.auto_respond = settings.auto_respond
        if settings.confidence_threshold is not None:
            row.confidence_threshold = settings.confidence_threshold
        if settings.support_channel_id is not None:
            row.support_channel_id = settings.support_channel_id
        if settings.log_channel_id is not None:
            row.log_channel_id = settings.log_channel_id
        session.commit()
        return {"message": "Settings updated"}
