"""Research subagent system for Discord support bot.

Provides Celery-based async research capabilities with web search,
API queries, database lookups, document analysis, comparison, and troubleshooting.
"""

from .worker import celery_app, get_task_result
from .tasks import (
    web_search,
    api_query,
    database_lookup,
    document_analysis,
    comparison,
    troubleshooting,
)
from .analyzer import ResearchAnalyzer
from .web_search import WebSearchProvider

__all__ = [
    "celery_app",
    "get_task_result",
    "web_search",
    "api_query",
    "database_lookup",
    "document_analysis",
    "comparison",
    "troubleshooting",
    "ResearchAnalyzer",
    "WebSearchProvider",
]
