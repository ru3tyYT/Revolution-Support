"""Support ticket (conversation) API routes."""
from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import joinedload

from database.connection import get_db_context
from database.models import Conversation
from web.dependencies import get_current_user
from web.exceptions import ForbiddenException, NotFoundException
from web.models.schemas import TicketResponse

router = APIRouter()


def _ticket_from_conv(c: Conversation) -> TicketResponse:
    guild = c.guild
    discord_guild_id = guild.discord_id if guild else str(c.guild_id)
    raw_messages = c.messages if isinstance(c.messages, list) else []
    tail = raw_messages[-10:] if len(raw_messages) > 10 else raw_messages
    return TicketResponse(
        id=str(c.id),
        user_id=c.user_id,
        guild_id=str(discord_guild_id),
        channel_id=c.channel_id,
        status="active" if c.is_active else "closed",
        created_at=c.created_at,
        updated_at=c.last_activity_at,
        messages=tail,
    )


@router.get("", response_model=List[TicketResponse])
async def list_user_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    discord_id = str(current_user["id"])
    with get_db_context() as session:
        rows = (
            session.execute(
                select(Conversation)
                .options(joinedload(Conversation.guild))
                .where(Conversation.user_id == discord_id)
                .order_by(desc(Conversation.last_activity_at))
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .unique()
            .all()
        )
        return [_ticket_from_conv(c) for c in rows]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        uid = UUID(ticket_id)
    except ValueError as e:
        raise NotFoundException("Ticket not found") from e

    discord_id = str(current_user["id"])
    with get_db_context() as session:
        c = session.execute(
            select(Conversation)
            .options(joinedload(Conversation.guild))
            .where(Conversation.id == uid)
        ).scalar_one_or_none()
        if not c:
            raise NotFoundException("Ticket not found")
        if c.user_id != discord_id and not current_user.get("is_admin"):
            raise ForbiddenException("Not authorized")
        full = TicketResponse(
            id=str(c.id),
            user_id=c.user_id,
            guild_id=str(c.guild.discord_id if c.guild else c.guild_id),
            channel_id=c.channel_id,
            status="active" if c.is_active else "closed",
            created_at=c.created_at,
            updated_at=c.last_activity_at,
            messages=c.messages if isinstance(c.messages, list) else [],
        )
        return full
