"""Database layer for Discord support bot.

This package provides SQLAlchemy models and database connection management
for a multi-tenant support bot with vector search capabilities.
"""

from database.connection import Base, engine, SessionLocal, get_db
from database.models import (
    Guild,
    Keyword,
    KeywordEmbedding,
    KnowledgeDoc,
    KnowledgeChunk,
    Conversation,
    QueryAnalytics,
    APIKey,
)

__all__ = [
    # Connection
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    # Models
    "Guild",
    "Keyword",
    "KeywordEmbedding",
    "KnowledgeDoc",
    "KnowledgeChunk",
    "Conversation",
    "QueryAnalytics",
    "APIKey",
]
