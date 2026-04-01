"""Pydantic schemas for API requests/responses."""
from typing import List, Optional

from pydantic import BaseModel, Field
from datetime import datetime

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    discord_id: str
    username: str
    avatar: Optional[str] = None

# User schemas
class DiscordUser(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar: Optional[str] = None
    global_name: Optional[str] = None

class UserResponse(BaseModel):
    discord_id: str
    username: str
    avatar: Optional[str] = None
    guilds: List[dict]  # Simplified guild data

class AdminCheck(BaseModel):
    is_admin: bool
    admin_guilds: List[dict]

# Guild schemas
class GuildSettings(BaseModel):
    id: str
    name: str
    icon: Optional[str]
    is_admin: bool

# Analytics schemas
class AnalyticsSummary(BaseModel):
    total_queries: int
    successful_queries: int
    failed_queries: int
    average_response_time_ms: float
    cost_total: float
    top_keywords: List[dict]
    response_type_breakdown: dict

class QueryLogEntry(BaseModel):
    id: str
    query: str
    response_type: str
    confidence_score: Optional[float]
    processing_time_ms: Optional[int]
    created_at: datetime

# Knowledge schemas
class KnowledgeDocResponse(BaseModel):
    id: str
    title: str
    source: Optional[str]
    doc_type: str
    created_at: datetime
    is_processed: bool

class KnowledgeSearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float

# Ticket schemas  
class TicketResponse(BaseModel):
    id: str
    user_id: str
    guild_id: str
    channel_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: List[dict]

# AI Ask schemas
class AskRequest(BaseModel):
    question: str
    guild_id: Optional[str] = None  # Optional for external API

class AskResponse(BaseModel):
    answer: str
    confidence: float
    sources: List[str] = Field(default_factory=list)
    response_type: str  # keyword_match, semantic_search, knowledge_base, ai_fallback
