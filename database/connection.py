"""Database connection and session management.

Provides SQLAlchemy engine setup with connection pooling, session management,
and async support for PostgreSQL with pgvector extension.
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/discord_support_bot"
)

# Pool configuration
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,  # Verify connections before use
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
)


# Enable pgvector extension on connect
@event.listens_for(engine, "connect")
def enable_pgvector(dbapi_conn, connection_record):
    """Enable pgvector extension on each connection."""
    with dbapi_conn.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get a database session.

    Usage:
        db = next(get_db())
        try:
            # use db
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Usage:
        with get_db_context() as db:
            # use db
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
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

    Base.metadata.create_all(bind=engine)


def close_db() -> None:
    """Close database connections."""
    engine.dispose()
