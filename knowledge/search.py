"""Search utilities for knowledge base.

Provides full-text search, vector similarity search, and hybrid search.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple, Union
from enum import Enum
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_, and_
from pgvector.sqlalchemy import cosine_distance

from database.models import KnowledgeChunk, KnowledgeDoc


class SearchType(Enum):
    """Types of search."""

    VECTOR = "vector"
    FULLTEXT = "fulltext"
    HYBRID = "hybrid"


@dataclass
class SearchConfig:
    """Configuration for search."""

    search_type: SearchType = SearchType.HYBRID
    vector_weight: float = 0.7
    text_weight: float = 0.3
    similarity_threshold: float = 0.7
    top_k: int = 5
    include_inactive: bool = False


@dataclass
class SearchResult:
    """Search result."""

    chunk: KnowledgeChunk
    document: KnowledgeDoc
    vector_score: Optional[float] = None
    text_score: Optional[float] = None
    combined_score: Optional[float] = None


class KnowledgeSearch:
    """Search utilities for knowledge base."""

    def __init__(
        self,
        db: Session,
        embedding_generator=None,
    ):
        """Initialize search.

        Args:
            db: Database session
            embedding_generator: Optional embedding generator for vector search
        """
        self.db = db
        self.embedding_generator = embedding_generator

    def vector_search(
        self,
        query_embedding: List[float],
        guild_id: Union[UUID, str],
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
        exclude_doc_id: Optional[str] = None,
    ) -> List[Tuple[KnowledgeChunk, KnowledgeDoc, float]]:
        """Search using vector similarity.

        Args:
            query_embedding: Query embedding vector
            guild_id: Guild/server ID
            top_k: Number of results
            similarity_threshold: Minimum similarity score
            filters: Optional filters
            exclude_doc_id: Document ID to exclude

        Returns:
            List of (chunk, document, similarity) tuples
        """
        # Build query
        query = (
            self.db.query(
                KnowledgeChunk,
                KnowledgeDoc,
                (1 - cosine_distance(KnowledgeChunk.embedding, query_embedding)).label(
                    "similarity"
                ),
            )
            .join(KnowledgeDoc, KnowledgeChunk.document_id == KnowledgeDoc.id)
            .filter(
                KnowledgeDoc.guild_id == guild_id,
                KnowledgeDoc.is_deleted == False,
            )
        )

        # Apply similarity threshold
        query = query.filter(
            cosine_distance(KnowledgeChunk.embedding, query_embedding)
            <= (1 - similarity_threshold)
        )

        # Exclude document if specified
        if exclude_doc_id:
            query = query.filter(KnowledgeDoc.id != exclude_doc_id)

        # Apply additional filters
        if filters:
            if "doc_type" in filters:
                query = query.filter(KnowledgeDoc.doc_type == filters["doc_type"])
            if "tags" in filters:
                for tag in filters["tags"]:
                    query = query.filter(
                        KnowledgeDoc.json_metadata.contains({"tags": [tag]})
                    )

        # Order by similarity and limit
        results = (
            query.order_by(cosine_distance(KnowledgeChunk.embedding, query_embedding))
            .limit(top_k)
            .all()
        )

        return [(chunk, doc, float(similarity)) for chunk, doc, similarity in results]

    def fulltext_search(
        self,
        query: str,
        guild_id: Union[UUID, str],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[KnowledgeChunk, KnowledgeDoc, float]]:
        """Search using full-text search.

        Args:
            query: Search query
            guild_id: Guild/server ID
            top_k: Number of results
            filters: Optional filters

        Returns:
            List of (chunk, document, score) tuples
        """
        # Normalize query
        search_terms = query.lower().split()

        # Build query
        base_query = (
            self.db.query(KnowledgeChunk, KnowledgeDoc)
            .join(KnowledgeDoc, KnowledgeChunk.document_id == KnowledgeDoc.id)
            .filter(
                KnowledgeDoc.guild_id == guild_id,
                KnowledgeDoc.is_deleted == False,
            )
        )

        # Add text search conditions
        conditions = []
        for term in search_terms:
            conditions.append(
                or_(
                    func.lower(KnowledgeChunk.content).contains(term),
                    func.lower(KnowledgeDoc.title).contains(term),
                )
            )

        if conditions:
            base_query = base_query.filter(and_(*conditions))

        # Apply additional filters
        if filters:
            if "doc_type" in filters:
                base_query = base_query.filter(
                    KnowledgeDoc.doc_type == filters["doc_type"]
                )

        # Get results and calculate scores
        results = base_query.limit(top_k * 2).all()

        scored_results = []
        for chunk, doc in results:
            score = self._calculate_text_score(query, chunk.content, doc.title)
            scored_results.append((chunk, doc, score))

        # Sort by score and limit
        scored_results.sort(key=lambda x: x[2], reverse=True)
        return scored_results[:top_k]

    def _calculate_text_score(
        self,
        query: str,
        content: str,
        title: str,
    ) -> float:
        """Calculate text match score.

        Args:
            query: Search query
            content: Chunk content
            title: Document title

        Returns:
            Match score between 0 and 1
        """
        query_lower = query.lower()
        content_lower = content.lower()
        title_lower = title.lower()

        query_words = set(query_lower.split())

        # Title matches weighted higher
        title_matches = sum(1 for word in query_words if word in title_lower)
        title_score = title_matches / len(query_words) if query_words else 0

        # Content matches
        content_matches = sum(1 for word in query_words if word in content_lower)
        content_score = content_matches / len(query_words) if query_words else 0

        # Exact phrase match
        phrase_score = 1.0 if query_lower in content_lower else 0.0

        # Combine scores
        return title_score * 0.4 + content_score * 0.4 + phrase_score * 0.2

    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        guild_id: Union[UUID, str],
        top_k: int = 5,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[KnowledgeChunk, KnowledgeDoc, float]]:
        """Combine vector and full-text search.

        Args:
            query: Text query
            query_embedding: Query embedding vector
            guild_id: Guild/server ID
            top_k: Number of results
            vector_weight: Weight for vector scores
            text_weight: Weight for text scores
            filters: Optional filters

        Returns:
            List of (chunk, document, combined_score) tuples
        """
        # Get vector results
        vector_results = self.vector_search(
            query_embedding=query_embedding,
            guild_id=guild_id,
            top_k=top_k * 2,
            filters=filters,
        )

        # Get text results
        text_results = self.fulltext_search(
            query=query,
            guild_id=guild_id,
            top_k=top_k * 2,
            filters=filters,
        )

        # Combine and normalize scores
        combined_scores: Dict[str, dict] = {}

        # Add vector scores
        for chunk, doc, score in vector_results:
            key = str(chunk.id)
            combined_scores[key] = {
                "chunk": chunk,
                "doc": doc,
                "vector_score": score,
                "text_score": 0.0,
            }

        # Add text scores
        for chunk, doc, score in text_results:
            key = str(chunk.id)
            if key in combined_scores:
                combined_scores[key]["text_score"] = score
            else:
                combined_scores[key] = {
                    "chunk": chunk,
                    "doc": doc,
                    "vector_score": 0.0,
                    "text_score": score,
                }

        # Calculate combined scores
        results = []
        for item in combined_scores.values():
            combined = (
                item["vector_score"] * vector_weight + item["text_score"] * text_weight
            )
            results.append((item["chunk"], item["doc"], combined))

        # Sort by combined score and limit
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:top_k]

    def search_chunks(
        self,
        query_embedding: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        guild_id: Optional[Union[UUID, str]] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        search_type: SearchType = SearchType.VECTOR,
        filters: Optional[Dict[str, Any]] = None,
        exclude_doc_id: Optional[str] = None,
    ) -> List[Tuple[KnowledgeChunk, KnowledgeDoc, float]]:
        """Unified search interface.

        Args:
            query_embedding: Vector for vector search
            query_text: Text for full-text search
            guild_id: Guild/server ID
            top_k: Number of results
            similarity_threshold: Minimum similarity
            search_type: Type of search to perform
            filters: Optional filters
            exclude_doc_id: Document to exclude

        Returns:
            List of (chunk, document, score) tuples
        """
        if search_type == SearchType.VECTOR:
            if query_embedding is None:
                raise ValueError("query_embedding required for vector search")
            return self.vector_search(
                query_embedding=query_embedding,
                guild_id=guild_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                filters=filters,
                exclude_doc_id=exclude_doc_id,
            )

        elif search_type == SearchType.FULLTEXT:
            if query_text is None:
                raise ValueError("query_text required for fulltext search")
            return self.fulltext_search(
                query=query_text,
                guild_id=guild_id,
                top_k=top_k,
                filters=filters,
            )

        elif search_type == SearchType.HYBRID:
            if query_embedding is None or query_text is None:
                raise ValueError(
                    "Both query_embedding and query_text required for hybrid search"
                )
            return self.hybrid_search(
                query=query_text,
                query_embedding=query_embedding,
                guild_id=guild_id,
                top_k=top_k,
                filters=filters,
            )

        else:
            raise ValueError(f"Unknown search type: {search_type}")

    def search_documents(
        self,
        query: str,
        guild_id: Union[UUID, str],
        top_k: int = 5,
    ) -> List[KnowledgeDoc]:
        """Search for documents by title.

        Args:
            query: Search query
            guild_id: Guild/server ID
            top_k: Number of results

        Returns:
            List of matching documents
        """
        query_lower = query.lower()

        results = (
            self.db.query(KnowledgeDoc)
            .filter(
                KnowledgeDoc.guild_id == guild_id,
                KnowledgeDoc.is_deleted == False,
                func.lower(KnowledgeDoc.title).contains(query_lower),
            )
            .limit(top_k)
            .all()
        )

        return results

    def get_document_chunks(
        self,
        document_id: str,
    ) -> List[KnowledgeChunk]:
        """Get all chunks for a document.

        Args:
            document_id: Document UUID

        Returns:
            List of chunks ordered by index
        """
        return (
            self.db.query(KnowledgeChunk)
            .filter(
                KnowledgeChunk.document_id == document_id,
            )
            .order_by(KnowledgeChunk.chunk_index)
            .all()
        )
