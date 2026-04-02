"""Analytics API routes."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta
from typing import Iterator, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select

from database.connection import get_db_context
from database.models import QueryAnalytics
from web.dependencies import require_admin
from web.models.schemas import AnalyticsSummary, QueryLogEntry
from web.services.guild_context import resolve_guild_uuid, target_discord_guild_id

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    guild_id: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(require_admin),
):
    target_gid = target_discord_guild_id(current_user, guild_id)
    with get_db_context() as session:
        internal_id = resolve_guild_uuid(session, target_gid)
        since = datetime.utcnow() - timedelta(days=days)

        total = (
            session.execute(
                select(func.count(QueryAnalytics.id))
                .where(QueryAnalytics.guild_id == internal_id)
                .where(QueryAnalytics.created_at >= since)
            ).scalar()
            or 0
        )

        type_rows = session.execute(
            select(QueryAnalytics.response_type, func.count(QueryAnalytics.id))
            .where(QueryAnalytics.guild_id == internal_id)
            .where(QueryAnalytics.created_at >= since)
            .group_by(QueryAnalytics.response_type)
        ).all()
        type_breakdown = {row[0]: row[1] for row in type_rows}

        avg_time = (
            session.execute(
                select(func.avg(QueryAnalytics.processing_time_ms))
                .where(QueryAnalytics.guild_id == internal_id)
                .where(QueryAnalytics.created_at >= since)
                .where(QueryAnalytics.processing_time_ms.isnot(None))
            ).scalar()
            or 0
        )

        cost_per_token = 0.00001
        total_tokens = (
            session.execute(
                select(func.coalesce(func.sum(QueryAnalytics.tokens_used), 0))
                .where(QueryAnalytics.guild_id == internal_id)
                .where(QueryAnalytics.created_at >= since)
            ).scalar()
            or 0
        )
        cost_total = float(total_tokens) * cost_per_token

        successful = sum(
            type_breakdown.get(k, 0)
            for k in ("knowledge_base", "semantic_search", "keyword_match")
        )
        failed = type_breakdown.get("error", 0)

        return AnalyticsSummary(
            total_queries=int(total),
            successful_queries=int(successful),
            failed_queries=int(failed),
            average_response_time_ms=float(avg_time),
            cost_total=cost_total,
            top_keywords=[],
            response_type_breakdown=type_breakdown,
        )


@router.get("/queries", response_model=List[QueryLogEntry])
async def get_query_logs(
    guild_id: Optional[str] = Query(None),
    response_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_admin),
):
    target_gid = target_discord_guild_id(current_user, guild_id)
    with get_db_context() as session:
        internal_id = resolve_guild_uuid(session, target_gid)
        q = select(QueryAnalytics).where(QueryAnalytics.guild_id == internal_id)
        if response_type:
            q = q.where(QueryAnalytics.response_type == response_type)
        q = q.order_by(desc(QueryAnalytics.created_at)).offset(skip).limit(limit)
        rows = session.execute(q).scalars().all()
        return [
            QueryLogEntry(
                id=str(r.id),
                query=(r.query[:100] if r.query else ""),
                response_type=r.response_type,
                confidence_score=r.confidence_score,
                processing_time_ms=r.processing_time_ms,
                created_at=r.created_at,
            )
            for r in rows
        ]


def _export_rows(
    session, internal_id, since: Optional[datetime]
) -> List[QueryAnalytics]:
    q = select(QueryAnalytics).where(QueryAnalytics.guild_id == internal_id)
    if since:
        q = q.where(QueryAnalytics.created_at >= since)
    q = q.order_by(desc(QueryAnalytics.created_at))
    return list(session.execute(q).scalars().all())


@router.get("/export")
async def export_analytics(
    guild_id: Optional[str] = Query(None),
    format: str = Query("csv", pattern="^(csv|json)$"),
    days: Optional[int] = Query(None, ge=1, le=365),
    current_user: dict = Depends(require_admin),
):
    target_gid = target_discord_guild_id(current_user, guild_id)
    since = datetime.utcnow() - timedelta(days=days) if days else None

    with get_db_context() as session:
        internal_id = resolve_guild_uuid(session, target_gid)
        rows = _export_rows(session, internal_id, since)

    if format == "json":

        def json_iter() -> Iterator[bytes]:
            payload = [
                {
                    "id": str(r.id),
                    "query": r.query,
                    "response_type": r.response_type,
                    "processing_time_ms": r.processing_time_ms,
                    "tokens_used": r.tokens_used,
                    "confidence_score": r.confidence_score,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
            yield json.dumps(payload, default=str).encode("utf-8")

        return StreamingResponse(
            json_iter(),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="analytics_export.json"'
            },
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "query",
            "response_type",
            "processing_time_ms",
            "tokens_used",
            "confidence_score",
            "created_at",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                str(r.id),
                (r.query or "").replace("\n", " ")[:2000],
                r.response_type,
                r.processing_time_ms or "",
                r.tokens_used or "",
                r.confidence_score or "",
                r.created_at.isoformat() if r.created_at else "",
            ]
        )

    data = buf.getvalue().encode("utf-8")

    def csv_bytes() -> Iterator[bytes]:
        yield data

    return StreamingResponse(
        csv_bytes(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="analytics_export.csv"'},
    )
