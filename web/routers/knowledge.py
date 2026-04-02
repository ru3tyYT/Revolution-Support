"""Knowledge base API routes."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import joinedload

from database.connection import get_db_context
from database.models import KnowledgeDoc
from web.dependencies import get_current_user, require_admin
from web.exceptions import ForbiddenException, NotFoundException
from web.models.schemas import KnowledgeDocResponse, KnowledgeSearchResult
from web.services.guild_context import (
    ensure_admin_for_discord_guild,
    resolve_guild_uuid,
    target_discord_guild_id,
)

router = APIRouter()


@router.get("/documents", response_model=List[KnowledgeDocResponse])
async def list_documents(
    guild_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin),
):
    target_gid = target_discord_guild_id(current_user, guild_id)
    with get_db_context() as session:
        internal_id = resolve_guild_uuid(session, target_gid)
        docs = (
            session.execute(
                select(KnowledgeDoc)
                .where(KnowledgeDoc.guild_id == internal_id)
                .where(KnowledgeDoc.is_deleted == False)
                .order_by(desc(KnowledgeDoc.created_at))
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [
            KnowledgeDocResponse(
                id=str(doc.id),
                title=doc.title,
                source=doc.source,
                doc_type=doc.doc_type,
                created_at=doc.created_at,
                is_processed=doc.is_processed,
            )
            for doc in docs
        ]


@router.get("/search", response_model=List[KnowledgeSearchResult])
async def search_knowledge(
    query: str = Query(..., min_length=1, max_length=500),
    guild_id: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(require_admin),
):
    target_gid = target_discord_guild_id(current_user, guild_id)
    from knowledge.rag import RAGSystem

    with get_db_context() as session:
        internal_id = resolve_guild_uuid(session, target_gid)
        rag = RAGSystem(session)
        results = await rag.retrieve(query=query, guild_id=internal_id, top_k=limit)
        return [
            KnowledgeSearchResult(
                id=r.document_id,
                title=r.title,
                content=r.content[:500],
                score=float(r.rerank_score if r.rerank_score is not None else r.similarity),
            )
            for r in results
        ]


def _parse_doc_id(doc_id: str) -> UUID:
    try:
        return UUID(doc_id)
    except ValueError as e:
        raise NotFoundException("Document not found") from e


@router.get("/documents/{doc_id}", response_model=KnowledgeDocResponse)
async def get_document(
    doc_id: str,
    current_user: dict = Depends(require_admin),
):
    uid = _parse_doc_id(doc_id)
    with get_db_context() as session:
        doc = session.execute(
            select(KnowledgeDoc)
            .options(joinedload(KnowledgeDoc.guild))
            .where(KnowledgeDoc.id == uid)
        ).scalar_one_or_none()
        if not doc or doc.is_deleted:
            raise NotFoundException("Document not found")
        discord_gid = doc.guild.discord_id
        ensure_admin_for_discord_guild(current_user, discord_gid)
        return KnowledgeDocResponse(
            id=str(doc.id),
            title=doc.title,
            source=doc.source,
            doc_type=doc.doc_type,
            created_at=doc.created_at,
            is_processed=doc.is_processed,
        )


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: dict = Depends(require_admin),
):
    uid = _parse_doc_id(doc_id)
    with get_db_context() as session:
        doc = session.execute(
            select(KnowledgeDoc)
            .options(joinedload(KnowledgeDoc.guild))
            .where(KnowledgeDoc.id == uid)
        ).scalar_one_or_none()
        if not doc or doc.is_deleted:
            raise NotFoundException("Document not found")
        ensure_admin_for_discord_guild(current_user, doc.guild.discord_id)
        doc.is_deleted = True
        session.commit()
        return {"message": "Document deleted"}
