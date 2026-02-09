"""Retrieval-Augmented Generation (RAG) system.

Provides document retrieval, context assembly, and re-ranking for AI responses.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import numpy as np

from sqlalchemy.orm import Session
from sqlalchemy import text, func

from knowledge.search import KnowledgeSearch, SearchType
from ai.embeddings import get_embedding_generator, EmbeddingGenerator
from database.models import KnowledgeChunk, KnowledgeDoc


@dataclass
class RAGConfig:
    """Configuration for RAG system."""

    top_k: int = 5
    similarity_threshold: float = 0.7
    max_context_tokens: int = 3000
    include_metadata: bool = True
    rerank_results: bool = True
    rerank_top_k: int = 3
    context_format: str = "qa"  # qa, bullet, paragraph


@dataclass
class SearchResult:
    """A search result with context."""

    chunk_id: str
    document_id: str
    title: str
    content: str
    similarity: float
    rerank_score: Optional[float] = None
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGContext:
    """Assembled context for AI prompts."""

    query: str
    results: List[SearchResult]
    context_text: str
    total_tokens: int
    sources: List[Dict[str, Any]]
    search_time_ms: int


class RAGSystem:
    """Retrieval-Augmented Generation system."""

    def __init__(
        self,
        db: Session,
        config: Optional[RAGConfig] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
    ):
        """Initialize the RAG system.

        Args:
            db: Database session
            config: RAG configuration
            embedding_generator: Embedding generator instance
        """
        self.db = db
        self.config = config or RAGConfig()
        self.embedding_generator = embedding_generator or get_embedding_generator()
        self.search_engine = KnowledgeSearch(db, embedding_generator)

    async def retrieve(
        self,
        query: str,
        guild_id: int,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Retrieve relevant documents for a query.

        Args:
            query: User query
            guild_id: Guild/server ID
            top_k: Number of results to retrieve
            filters: Optional filters (doc_type, tags, etc.)

        Returns:
            List of search results
        """
        top_k = top_k or self.config.top_k

        # Generate query embedding
        query_embedding = await self.embedding_generator.generate(query)

        # Perform vector search
        results = self.search_engine.search_chunks(
            query_embedding=query_embedding,
            guild_id=guild_id,
            top_k=top_k * 2,  # Retrieve more for re-ranking
            similarity_threshold=self.config.similarity_threshold,
            filters=filters,
        )

        # Convert to SearchResult objects
        search_results = []
        for result in results:
            chunk, doc, similarity = result
            search_results.append(
                SearchResult(
                    chunk_id=str(chunk.id),
                    document_id=str(doc.id),
                    title=doc.title,
                    content=chunk.content,
                    similarity=similarity,
                    chunk_index=chunk.chunk_index,
                    metadata=doc.metadata or {},
                )
            )

        # Re-rank if enabled
        if self.config.rerank_results and len(search_results) > 1:
            search_results = self._rerank_results(query, search_results)
            search_results = search_results[: self.config.rerank_top_k]
        else:
            search_results = search_results[:top_k]

        return search_results

    def _rerank_results(
        self,
        query: str,
        results: List[SearchResult],
    ) -> List[SearchResult]:
        """Re-rank results using additional signals.

        Args:
            query: Original query
            results: Initial search results

        Returns:
            Re-ranked results
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_results = []
        for result in results:
            score = result.similarity
            content_lower = result.content.lower()

            # Keyword matching boost
            keyword_matches = sum(1 for word in query_words if word in content_lower)
            keyword_score = keyword_matches / len(query_words) if query_words else 0

            # Position boost (earlier chunks may have more context)
            position_score = 1.0 / (1 + result.chunk_index * 0.1)

            # Recency boost (if available)
            recency_score = 1.0
            if "updated_at" in result.metadata:
                try:
                    updated = datetime.fromisoformat(result.metadata["updated_at"])
                    days_old = (datetime.utcnow() - updated).days
                    recency_score = max(0.5, 1.0 - days_old / 365)
                except:
                    pass

            # Combine scores
            combined_score = (
                score * 0.5
                + keyword_score * 0.25
                + position_score * 0.15
                + recency_score * 0.1
            )

            result.rerank_score = combined_score
            scored_results.append((combined_score, result))

        # Sort by combined score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in scored_results]

    async def assemble_context(
        self,
        query: str,
        guild_id: int,
        top_k: Optional[int] = None,
    ) -> RAGContext:
        """Assemble context for AI prompts.

        Args:
            query: User query
            guild_id: Guild/server ID
            top_k: Number of results to include

        Returns:
            Assembled RAG context
        """
        import time

        start_time = time.time()

        # Retrieve results
        results = await self.retrieve(query, guild_id, top_k)

        if not results:
            return RAGContext(
                query=query,
                results=[],
                context_text="",
                total_tokens=0,
                sources=[],
                search_time_ms=int((time.time() - start_time) * 1000),
            )

        # Build context text
        context_parts = []
        total_tokens = 0
        sources = []

        for i, result in enumerate(results, 1):
            part = self._format_result(result, i)
            part_tokens = len(part.split())  # Approximate

            if total_tokens + part_tokens > self.config.max_context_tokens:
                break

            context_parts.append(part)
            total_tokens += part_tokens

            sources.append(
                {
                    "id": result.document_id,
                    "title": result.title,
                    "similarity": result.similarity,
                    "rerank_score": result.rerank_score,
                }
            )

        context_text = "\n\n".join(context_parts)

        return RAGContext(
            query=query,
            results=results,
            context_text=context_text,
            total_tokens=total_tokens,
            sources=sources,
            search_time_ms=int((time.time() - start_time) * 1000),
        )

    def _format_result(self, result: SearchResult, index: int) -> str:
        """Format a search result for context.

        Args:
            result: Search result
            index: Result index

        Returns:
            Formatted context string
        """
        if self.config.context_format == "qa":
            return f"[{index}] {result.title}:\n{result.content}"
        elif self.config.context_format == "bullet":
            return f"• {result.title}: {result.content}"
        elif self.config.context_format == "paragraph":
            return f"According to {result.title}: {result.content}"
        else:
            return result.content

    def create_prompt(
        self,
        query: str,
        context: RAGContext,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Create a prompt with retrieved context.

        Args:
            query: User query
            context: RAG context
            system_prompt: Optional system prompt

        Returns:
            Complete prompt for AI
        """
        if system_prompt is None:
            system_prompt = (
                "You are a helpful support assistant. Answer the user's question "
                "using the provided context. If the context doesn't contain the answer, "
                "say so clearly. Cite sources using the [number] format."
            )

        prompt = f"""{system_prompt}

Context:
{context.context_text}

User Question: {query}

Answer:"""

        return prompt

    async def query(
        self,
        query: str,
        guild_id: int,
        ai_router: Optional[Any] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Full RAG query pipeline.

        Args:
            query: User query
            guild_id: Guild/server ID
            ai_router: AI router for generating response
            system_prompt: Optional system prompt

        Returns:
            Dictionary with response and metadata
        """
        # Assemble context
        context = await self.assemble_context(query, guild_id)

        if not context.results:
            return {
                "response": "I couldn't find any relevant information to answer your question.",
                "sources": [],
                "search_time_ms": context.search_time_ms,
                "has_results": False,
            }

        # Create prompt
        prompt = self.create_prompt(query, context, system_prompt)

        # Generate response if AI router provided
        response_text = None
        if ai_router:
            try:
                response = await ai_router.generate(prompt)
                response_text = response.get("content", "Error generating response")
            except Exception as e:
                response_text = f"Error: {str(e)}"

        return {
            "response": response_text,
            "prompt": prompt,
            "sources": context.sources,
            "context": context.context_text,
            "search_time_ms": context.search_time_ms,
            "has_results": True,
            "total_tokens": context.total_tokens,
        }

    def get_related_documents(
        self,
        document_id: str,
        guild_id: int,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find documents related to a given document.

        Args:
            document_id: Document UUID
            guild_id: Guild/server ID
            top_k: Number of related documents

        Returns:
            List of related documents with similarity scores
        """
        # Get embedding for the document's first chunk
        chunk = (
            self.db.query(KnowledgeChunk)
            .filter(KnowledgeChunk.document_id == document_id)
            .first()
        )

        if not chunk:
            return []

        # Find similar chunks from different documents
        results = self.search_engine.search_chunks(
            query_embedding=chunk.embedding,
            guild_id=guild_id,
            top_k=top_k + 1,
            exclude_doc_id=document_id,
        )

        related = []
        seen_docs = set()

        for chunk_result, doc, similarity in results:
            if str(doc.id) != document_id and str(doc.id) not in seen_docs:
                seen_docs.add(str(doc.id))
                related.append(
                    {
                        "id": str(doc.id),
                        "title": doc.title,
                        "similarity": similarity,
                    }
                )

                if len(related) >= top_k:
                    break

        return related
