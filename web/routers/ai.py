"""AI /ask API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from database.connection import get_db_context
from web.dependencies import get_current_user
from web.exceptions import BadRequestException
from web.models.schemas import AskRequest, AskResponse
from web.services.guild_context import resolve_guild_uuid, target_discord_guild_id

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask_ai(
    request: AskRequest,
    current_user: dict = Depends(get_current_user),
):
    q = (request.question or "").strip()
    if len(q) < 3:
        raise BadRequestException("Question must be at least 3 characters")

    target_gid = target_discord_guild_id(current_user, request.guild_id)

    from knowledge.rag import RAGSystem

    with get_db_context() as session:
        internal_id = resolve_guild_uuid(session, target_gid)
        rag = RAGSystem(session)
        results = await rag.retrieve(query=q, guild_id=internal_id, top_k=5)

    if not results:
        return AskResponse(
            answer="I don't have specific information about that in the knowledge base. Please contact support.",
            confidence=0.3,
            sources=[],
            response_type="ai_fallback",
        )

    from ai.providers.base import ChatCompletionRequest, ChatMessage
    from ai.router import RoutingStrategy

    from web.services.ai_router_service import get_web_ai_router

    context = "\n\n".join(f"[{r.title}]\n{r.content}" for r in results)
    prompt = (
        "Based on the following context, answer the question concisely.\n\n"
        f"Context:\n{context}\n\nQuestion: {q}\n\nAnswer:"
    )

    ai_router = get_web_ai_router()
    if not ai_router.providers:
        return AskResponse(
            answer=results[0].content[:2000],
            confidence=0.75,
            sources=list({r.title for r in results}),
            response_type="knowledge_base",
        )

    try:
        cc_req = ChatCompletionRequest(
            messages=[
                ChatMessage(
                    role="system",
                    content="You are a helpful support assistant. Use only the given context when possible.",
                ),
                ChatMessage(role="user", content=prompt),
            ],
            temperature=0.5,
            max_tokens=1024,
        )
        cc_resp = await ai_router.chat_completion(
            cc_req, strategy=RoutingStrategy.BALANCED
        )
        return AskResponse(
            answer=cc_resp.content or "Sorry, I could not generate an answer.",
            confidence=0.8,
            sources=list({r.title for r in results}),
            response_type="knowledge_base",
        )
    except Exception:
        return AskResponse(
            answer=results[0].content[:2000],
            confidence=0.75,
            sources=list({r.title for r in results}),
            response_type="knowledge_base",
        )
