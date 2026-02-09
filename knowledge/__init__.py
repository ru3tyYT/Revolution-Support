"""Knowledge base and RAG system for Discord support bot.

Provides document management, chunking, and retrieval-augmented generation
for intelligent support responses.
"""

from knowledge.rag import RAGSystem, RAGConfig, SearchResult
from knowledge.chunker import TextChunker, ChunkConfig
from knowledge.search import KnowledgeSearch, SearchConfig, SearchType

__all__ = [
    # RAG
    "RAGSystem",
    "RAGConfig",
    "SearchResult",
    # Chunker
    "TextChunker",
    "ChunkConfig",
    # Search
    "KnowledgeSearch",
    "SearchConfig",
    "SearchType",
]

__version__ = "1.0.0"
