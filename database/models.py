"""SQLAlchemy models for Discord support bot.

This module defines all database models including multi-tenant support,
vector embeddings, and analytics tracking.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Index,
    UniqueConstraint,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, declarative_base, validates
from pgvector.sqlalchemy import Vector

from database.connection import Base


class TimestampMixin:
    """Mixin for timestamp fields."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)


class Guild(Base, TimestampMixin):
    """Discord server/guild configuration.

    Stores settings and configuration for each Discord server.
    """

    __tablename__ = "guilds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discord_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)

    # Configuration
    support_channel_id = Column(String(20), nullable=True)
    log_channel_id = Column(String(20), nullable=True)
    auto_respond = Column(Boolean, default=True, nullable=False)
    confidence_threshold = Column(Float, default=0.7, nullable=False)

    # Multi-tenancy settings
    max_knowledge_docs = Column(Integer, default=100, nullable=False)
    max_keywords = Column(Integer, default=500, nullable=False)

    # Metadata
    settings = Column(JSONB, default=dict, nullable=False)

    # Relationships
    keywords = relationship("Keyword", back_populates="guild")
    knowledge_docs = relationship("KnowledgeDoc", back_populates="guild")
    conversations = relationship("Conversation", back_populates="guild")
    analytics = relationship("QueryAnalytics", back_populates="guild")
    forum_configs = relationship("ForumConfig", back_populates="guild")

    __table_args__ = (Index("ix_guilds_discord_id", "discord_id"),)

    def __repr__(self) -> str:
        return f"<Guild(id={self.id}, discord_id={self.discord_id}, name={self.name})>"


class Keyword(Base, TimestampMixin, SoftDeleteMixin):
    """Trigger patterns with categories for keyword matching.

    Stores keywords and phrases that trigger bot responses.
    """

    __tablename__ = "keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guilds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Keyword data
    pattern = Column(String(500), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    response_template = Column(Text, nullable=False)

    # Matching configuration
    match_type = Column(
        String(20),
        default="contains",
        nullable=False,
        comment="exact, contains, regex, or semantic",
    )
    priority = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    metadata = Column(JSONB, default=dict, nullable=False)
    tags = Column(ARRAY(String), default=list, nullable=False)

    # Relationships
    guild = relationship("Guild", back_populates="keywords")
    embeddings = relationship(
        "KeywordEmbedding", back_populates="keyword", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_keywords_guild_pattern", "guild_id", "pattern"),
        Index("ix_keywords_category_active", "category", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Keyword(id={self.id}, pattern={self.pattern}, category={self.category})>"


class KeywordEmbedding(Base, TimestampMixin):
    """Vector embeddings for keyword semantic search.

    Stores 1536-dimensional embeddings for semantic matching.
    """

    __tablename__ = "keyword_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword_id = Column(
        UUID(as_uuid=True),
        ForeignKey("keywords.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Embedding
    embedding = Column(Vector(1536), nullable=False)
    model = Column(String(100), default="text-embedding-ada-002", nullable=False)

    # Relationships
    keyword = relationship("Keyword", back_populates="embeddings")

    __table_args__ = (
        Index(
            "ix_keyword_embeddings_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
        ),
    )

    def __repr__(self) -> str:
        return f"<KeywordEmbedding(id={self.id}, keyword_id={self.keyword_id})>"


class KnowledgeDoc(Base, TimestampMixin, SoftDeleteMixin):
    """Knowledge base documents.

    Stores documents that can be chunked and searched.
    """

    __tablename__ = "knowledge_docs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guilds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Document info
    title = Column(String(500), nullable=False)
    source = Column(String(200), nullable=True)
    doc_type = Column(
        String(50), default="text", nullable=False, comment="text, markdown, html, pdf"
    )

    # Content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)

    # Processing
    chunk_count = Column(Integer, default=0, nullable=False)
    is_processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Metadata
    metadata = Column(JSONB, default=dict, nullable=False)

    # Relationships
    guild = relationship("Guild", back_populates="knowledge_docs")
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_knowledge_docs_guild_title", "guild_id", "title"),
        Index("ix_knowledge_docs_type_processed", "doc_type", "is_processed"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeDoc(id={self.id}, title={self.title}, type={self.doc_type})>"


class KnowledgeChunk(Base, TimestampMixin):
    """Document chunks with vector embeddings.

    Stores chunks of knowledge documents with embeddings for similarity search.
    """

    __tablename__ = "knowledge_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_docs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Chunk data
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    # Embedding
    embedding = Column(Vector(1536), nullable=False)
    model = Column(String(100), default="text-embedding-ada-002", nullable=False)

    # Metadata
    token_count = Column(Integer, nullable=True)
    metadata = Column(JSONB, default=dict, nullable=False)

    # Relationships
    document = relationship("KnowledgeDoc", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunk_index"),
        Index(
            "ix_knowledge_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
        ),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeChunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"


class Conversation(Base, TimestampMixin):
    """Multi-turn conversation context.

    Stores conversation history for maintaining context.
    """

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guilds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Discord identifiers
    channel_id = Column(String(20), nullable=False, index=True)
    user_id = Column(String(20), nullable=False, index=True)

    # Conversation data
    session_id = Column(String(100), nullable=False, index=True)
    messages = Column(JSONB, default=list, nullable=False)

    # Context
    context_summary = Column(Text, nullable=True)
    relevant_docs = Column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)

    # Metadata
    metadata = Column(JSONB, default=dict, nullable=False)

    # Relationships
    guild = relationship("Guild", back_populates="conversations")

    __table_args__ = (
        Index("ix_conversations_guild_channel_user", "guild_id", "channel_id", "user_id"),
        Index("ix_conversations_session_active", "session_id", "is_active"),
        Index("ix_conversations_last_activity", "last_activity_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, session_id={self.session_id}, user_id={self.user_id})>"


class QueryAnalytics(Base, TimestampMixin):
    """Analytics tracking for queries and responses.

    Stores analytics data for monitoring and improving the bot.
    """

    __tablename__ = "query_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guilds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Query info
    query = Column(Text, nullable=False)
    query_embedding = Column(Vector(1536), nullable=True)

    # Response info
    response = Column(Text, nullable=True)
    response_type = Column(
        String(50),
        nullable=False,
        comment="keyword_match, semantic_search, knowledge_base, fallback",
    )

    # Performance
    processing_time_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)

    # Source tracking
    source_keyword_id = Column(
        UUID(as_uuid=True),
        ForeignKey("keywords.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_doc_ids = Column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)

    # Quality metrics
    confidence_score = Column(Float, nullable=True)
    user_rating = Column(Integer, nullable=True)
    was_helpful = Column(Boolean, nullable=True)

    # Discord context
    channel_id = Column(String(20), nullable=True)
    user_id = Column(String(20), nullable=True)

    # Metadata
    metadata = Column(JSONB, default=dict, nullable=False)

    # Relationships
    guild = relationship("Guild", back_populates="analytics")
    source_keyword = relationship("Keyword")

    __table_args__ = (
        Index("ix_analytics_guild_response_type", "guild_id", "response_type"),
        Index("ix_analytics_created_at", "created_at"),
        Index("ix_analytics_confidence", "confidence_score"),
        Index(
            "ix_analytics_query_embedding",
            "query_embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
        ),
    )

    def __repr__(self) -> str:
        return f"<QueryAnalytics(id={self.id}, response_type={self.response_type}, confidence={self.confidence_score})>"


class APIKey(Base, TimestampMixin):
    """API key management for external services.

    Supports key rotation and multiple service integrations.
    API keys are automatically encrypted before storage and decrypted on retrieval.
    """

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Key identification
    service_name = Column(String(50), nullable=False, index=True)
    key_name = Column(String(100), nullable=False)

    # Key data (encrypted in production)
    # The api_key column stores the encrypted value with "ENC::" prefix
    _api_key = Column("api_key", String(500), nullable=False)

    # Rotation management
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0, nullable=False)

    # Rate limiting
    rate_limit_per_minute = Column(Integer, nullable=True)

    # Metadata
    metadata = Column(JSONB, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint("service_name", "key_name", name="uq_api_key_service_name"),
        Index("ix_api_keys_service_active", "service_name", "is_active"),
        Index("ix_api_keys_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, service={self.service_name}, name={self.key_name})>"

    @property
    def api_key(self) -> str:
        """Get the decrypted API key.

        Automatically decrypts the stored value when accessed.
        Maintains backward compatibility with legacy plaintext keys.

        Returns:
            The decrypted API key value.

        Raises:
            EncryptionError: If decryption fails (e.g., wrong encryption key).
        """
        if not self._api_key:
            return self._api_key

        try:
            from bot.utils.encryption import decrypt_value

            return decrypt_value(self._api_key)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"Failed to decrypt API key {self.service_name}/{self.key_name}: {e}"
            )
            raise

    @api_key.setter
    def api_key(self, value: str) -> None:
        """Set the API key (automatically encrypts).

        Args:
            value: The plaintext API key to encrypt and store.
        """
        if not value:
            self._api_key = value
            return

        try:
            from bot.utils.encryption import encrypt_value

            self._api_key = encrypt_value(value)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"Failed to encrypt API key {self.service_name}/{self.key_name}: {e}"
            )
            raise

    def get_key_value(self) -> str:
        """Get the decrypted API key value (convenience method).

        This is an alias for the api_key property.

        Returns:
            The decrypted API key.
        """
        return self.api_key

    def set_key_value(self, value: str) -> None:
        """Set the API key value (convenience method).

        This is an alias for the api_key setter.

        Args:
            value: The plaintext API key.
        """
        self.api_key = value

    def is_encrypted(self) -> bool:
        """Check if the stored API key is encrypted.

        Returns:
            True if the key is encrypted, False if it's plaintext (legacy).
        """
        from bot.utils.encryption import is_encrypted

        return is_encrypted(self._api_key)

    def rotate_key(self, new_key: str) -> None:
        """Rotate the API key to a new value.

        Args:
            new_key: The new API key value.
        """
        self.api_key = new_key
        self.updated_at = datetime.utcnow()


class ForumConfig(Base, TimestampMixin):
    """Configuration for monitored Discord forums.

    Stores settings for forum channels that the bot monitors and responds to.
    """

    __tablename__ = "forum_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guilds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Forum identification
    forum_channel_id = Column(String(20), nullable=False, index=True)
    forum_name = Column(String(100), nullable=False)

    # Response configuration
    is_active = Column(Boolean, default=True, nullable=False)
    auto_respond = Column(Boolean, default=True, nullable=False)
    welcome_message = Column(Text, nullable=True)
    ai_model = Column(String(50), nullable=True)
    response_delay_seconds = Column(Integer, default=0, nullable=False)

    # Tag filtering
    tags_to_monitor = Column(ARRAY(String), default=list, nullable=False)
    exclude_tags = Column(ARRAY(String), default=list, nullable=False)

    # Response limits
    max_responses_per_thread = Column(Integer, default=10, nullable=False)

    # Relationships
    guild = relationship("Guild", back_populates="forum_configs")
    threads = relationship(
        "ForumThread", back_populates="forum_config", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_forum_configs_guild_active", "guild_id", "is_active"),
        Index("ix_forum_configs_channel", "forum_channel_id"),
        UniqueConstraint("guild_id", "forum_channel_id", name="uq_forum_config_guild_channel"),
    )

    def __repr__(self) -> str:
        return (
            f"<ForumConfig(id={self.id}, forum_name={self.forum_name}, is_active={self.is_active})>"
        )


class ForumThread(Base, TimestampMixin):
    """Tracks AI responses to forum posts.

    Stores information about forum threads and AI interaction history.
    """

    __tablename__ = "forum_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forum_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("forum_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Thread identification
    thread_id = Column(String(20), nullable=False, index=True)
    thread_name = Column(String(100), nullable=False)
    author_id = Column(String(20), nullable=False, index=True)

    # Content
    initial_message = Column(Text, nullable=False)

    # AI interaction tracking
    ai_response_count = Column(Integer, default=0, nullable=False)
    last_ai_response_at = Column(DateTime, nullable=True)

    # Status
    is_closed = Column(Boolean, default=False, nullable=False)
    was_resolved = Column(Boolean, nullable=True)

    # Relationships
    forum_config = relationship("ForumConfig", back_populates="threads")

    __table_args__ = (
        Index("ix_forum_threads_config", "forum_config_id"),
        Index("ix_forum_threads_author", "author_id"),
        Index("ix_forum_threads_closed_resolved", "is_closed", "was_resolved"),
        Index("ix_forum_threads_last_response", "last_ai_response_at"),
    )

    def __repr__(self) -> str:
        return f"<ForumThread(id={self.id}, thread_name={self.thread_name}, ai_responses={self.ai_response_count})>"
