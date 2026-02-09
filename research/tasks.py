"""Research task definitions for the Discord support bot.

Provides async task execution for various research operations:
- Web search integration
- External API queries
- Deep database lookups
- Document analysis
- Option comparison
- Troubleshooting diagnostics
"""

import json
import logging
from typing import Any

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from .worker import celery_app, update_progress
from .web_search import WebSearchProvider
from .analyzer import ResearchAnalyzer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def web_search(
    self,
    query: str,
    provider: str = "auto",
    max_results: int = 10,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform web search for research queries.

    Args:
        query: Search query string
        provider: Search provider (auto, google, bing, duckduckgo)
        max_results: Maximum number of results to return
        filters: Optional search filters (date range, site, etc.)

    Returns:
        Dictionary containing search results and metadata
    """
    try:
        update_progress(self, 0, 100, "Initializing web search...")

        searcher = WebSearchProvider()

        update_progress(self, 25, 100, f"Searching with {provider}...")

        results = searcher.search(
            query=query,
            provider=provider,
            max_results=max_results,
            filters=filters or {},
        )

        update_progress(self, 75, 100, "Processing results...")

        # Analyze and rank results
        analyzer = ResearchAnalyzer()
        ranked_results = analyzer.rank_search_results(query, results)

        update_progress(self, 100, 100, "Search complete")

        return {
            "task_type": "web_search",
            "query": query,
            "provider": provider,
            "total_results": len(results),
            "results": ranked_results[:max_results],
            "metadata": {
                "filters_applied": filters,
                "processing_time": self.request.timelimit,
            },
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"Web search task timed out for query: {query}")
        raise self.retry(exc=Exception("Task timed out"))

    except Exception as exc:
        logger.error(f"Web search failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def api_query(
    self,
    endpoint: str,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Query external APIs for data retrieval.

    Args:
        endpoint: API endpoint URL
        method: HTTP method (GET, POST, PUT, DELETE)
        params: Query parameters
        headers: HTTP headers
        body: Request body for POST/PUT
        timeout: Request timeout in seconds

    Returns:
        API response data
    """
    import requests

    try:
        update_progress(self, 0, 100, f"Preparing {method} request...")

        update_progress(self, 50, 100, "Sending request...")

        response = requests.request(
            method=method.upper(),
            url=endpoint,
            params=params,
            headers=headers,
            json=body,
            timeout=timeout,
        )
        response.raise_for_status()

        update_progress(self, 100, 100, "Request complete")

        # Try to parse as JSON, fallback to text
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"content": response.text}

        return {
            "task_type": "api_query",
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "data": data,
            "headers": dict(response.headers),
        }

    except requests.exceptions.RequestException as exc:
        logger.error(f"API query failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def database_lookup(
    self,
    query_type: str,
    filters: dict[str, Any],
    limit: int = 100,
    include_embeddings: bool = False,
) -> dict[str, Any]:
    """Perform deep database queries for research.

    Args:
        query_type: Type of data to query (tickets, users, knowledge, analytics)
        filters: Query filters and conditions
        limit: Maximum results to return
        include_embeddings: Whether to include vector embeddings

    Returns:
        Query results with metadata
    """
    try:
        update_progress(self, 0, 100, "Connecting to database...")

        from database.connection import get_db_context

        update_progress(self, 30, 100, "Executing query...")

        with get_db_context() as db:
            # Route to appropriate query handler
            if query_type == "tickets":
                results = _query_tickets(db, filters, limit)
            elif query_type == "users":
                results = _query_users(db, filters, limit)
            elif query_type == "knowledge":
                results = _query_knowledge(db, filters, limit, include_embeddings)
            elif query_type == "analytics":
                results = _query_analytics(db, filters, limit)
            else:
                raise ValueError(f"Unknown query_type: {query_type}")

        update_progress(self, 100, 100, "Query complete")

        return {
            "task_type": "database_lookup",
            "query_type": query_type,
            "filters": filters,
            "total_results": len(results),
            "results": results,
        }

    except Exception as exc:
        logger.error(f"Database lookup failed: {exc}")
        raise self.retry(exc=exc)


def _query_tickets(db, filters: dict, limit: int) -> list[dict]:
    """Query support tickets from database."""
    from database.models import Conversation
    from sqlalchemy import desc

    query = db.query(Conversation)

    if "user_id" in filters:
        query = query.filter(Conversation.user_id == filters["user_id"])
    if "guild_id" in filters:
        query = query.filter(Conversation.guild_id == filters["guild_id"])
    if "status" in filters:
        query = query.filter(Conversation.status == filters["status"])
    if "date_from" in filters:
        query = query.filter(Conversation.created_at >= filters["date_from"])
    if "date_to" in filters:
        query = query.filter(Conversation.created_at <= filters["date_to"])

    conversations = query.order_by(desc(Conversation.created_at)).limit(limit).all()

    return [
        {
            "id": conv.id,
            "user_id": conv.user_id,
            "guild_id": conv.guild_id,
            "status": conv.status,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        }
        for conv in conversations
    ]


def _query_users(db, filters: dict, limit: int) -> list[dict]:
    """Query users from database."""
    # Placeholder - implement based on your user model
    return []


def _query_knowledge(
    db, filters: dict, limit: int, include_embeddings: bool
) -> list[dict]:
    """Query knowledge base from database."""
    from database.models import KnowledgeDoc

    query = db.query(KnowledgeDoc)

    if "category" in filters:
        query = query.filter(KnowledgeDoc.category == filters["category"])
    if "search" in filters:
        query = query.filter(KnowledgeDoc.title.ilike(f"%{filters['search']}%"))

    docs = query.limit(limit).all()

    results = []
    for doc in docs:
        doc_data = {
            "id": doc.id,
            "title": doc.title,
            "category": doc.category,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        if include_embeddings and hasattr(doc, "embedding"):
            doc_data["embedding"] = doc.embedding
        results.append(doc_data)

    return results


def _query_analytics(db, filters: dict, limit: int) -> list[dict]:
    """Query analytics data from database."""
    from database.models import QueryAnalytics

    query = db.query(QueryAnalytics)

    if "query_type" in filters:
        query = query.filter(QueryAnalytics.query_type == filters["query_type"])
    if "date_from" in filters:
        query = query.filter(QueryAnalytics.created_at >= filters["date_from"])

    analytics = query.order_by(QueryAnalytics.created_at.desc()).limit(limit).all()

    return [
        {
            "id": a.id,
            "query_type": a.query_type,
            "success": a.success,
            "response_time": a.response_time_ms,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in analytics
    ]


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def document_analysis(
    self,
    document_id: str | None = None,
    document_url: str | None = None,
    content: str | None = None,
    analysis_type: str = "summary",
) -> dict[str, Any]:
    """Analyze documents for insights.

    Args:
        document_id: Internal document ID
        document_url: URL to fetch document from
        content: Direct document content
        analysis_type: Type of analysis (summary, sentiment, entities, keywords)

    Returns:
        Analysis results
    """
    try:
        update_progress(self, 0, 100, "Fetching document...")

        # Get document content
        doc_content = None
        if content:
            doc_content = content
        elif document_id:
            doc_content = _fetch_document_by_id(document_id)
        elif document_url:
            doc_content = _fetch_document_from_url(document_url)

        if not doc_content:
            raise ValueError("No document content available")

        update_progress(self, 30, 100, f"Performing {analysis_type} analysis...")

        # Perform analysis
        analyzer = ResearchAnalyzer()

        if analysis_type == "summary":
            result = analyzer.summarize(doc_content)
        elif analysis_type == "sentiment":
            result = analyzer.analyze_sentiment(doc_content)
        elif analysis_type == "entities":
            result = analyzer.extract_entities(doc_content)
        elif analysis_type == "keywords":
            result = analyzer.extract_keywords(doc_content)
        else:
            raise ValueError(f"Unknown analysis_type: {analysis_type}")

        update_progress(self, 100, 100, "Analysis complete")

        return {
            "task_type": "document_analysis",
            "analysis_type": analysis_type,
            "document_id": document_id,
            "document_url": document_url,
            "content_length": len(doc_content),
            "result": result,
        }

    except Exception as exc:
        logger.error(f"Document analysis failed: {exc}")
        raise self.retry(exc=exc)


def _fetch_document_by_id(document_id: str) -> str:
    """Fetch document from database by ID."""
    from database.connection import get_db_context
    from database.models import KnowledgeDoc

    with get_db_context() as db:
        doc = db.query(KnowledgeDoc).filter(KnowledgeDoc.id == document_id).first()
        if doc:
            return doc.content or ""
    return ""


def _fetch_document_from_url(url: str) -> str:
    """Fetch document from URL."""
    import requests

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def comparison(
    self,
    items: list[dict[str, Any]],
    criteria: list[str],
    context: str = "",
) -> dict[str, Any]:
    """Compare multiple options based on criteria.

    Args:
        items: List of items to compare, each with name and attributes
        criteria: List of comparison criteria/attributes
        context: Additional context for comparison

    Returns:
        Comparison results with rankings and recommendations
    """
    try:
        update_progress(self, 0, 100, "Initializing comparison...")

        if len(items) < 2:
            raise ValueError("At least 2 items required for comparison")

        update_progress(self, 30, 100, "Analyzing items...")

        analyzer = ResearchAnalyzer()

        # Score each item on each criterion
        scores = {}
        for item in items:
            item_name = item.get("name", "Unknown")
            scores[item_name] = {}

            for criterion in criteria:
                score = analyzer.score_criterion(item, criterion, context)
                scores[item_name][criterion] = score

        update_progress(self, 70, 100, "Calculating rankings...")

        # Calculate overall scores and rankings
        rankings = []
        for item_name, item_scores in scores.items():
            avg_score = (
                sum(item_scores.values()) / len(item_scores) if item_scores else 0
            )
            rankings.append(
                {
                    "name": item_name,
                    "overall_score": round(avg_score, 2),
                    "criteria_scores": item_scores,
                }
            )

        # Sort by overall score
        rankings.sort(key=lambda x: x["overall_score"], reverse=True)

        # Add ranking position
        for i, r in enumerate(rankings, 1):
            r["rank"] = i

        update_progress(self, 100, 100, "Comparison complete")

        return {
            "task_type": "comparison",
            "items_compared": len(items),
            "criteria": criteria,
            "rankings": rankings,
            "recommendation": rankings[0] if rankings else None,
            "context": context,
        }

    except Exception as exc:
        logger.error(f"Comparison failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def troubleshooting(
    self,
    problem: str,
    symptoms: list[str],
    context: dict[str, Any] | None = None,
    category: str = "general",
) -> dict[str, Any]:
    """Diagnose issues and provide troubleshooting steps.

    Args:
        problem: Description of the problem
        symptoms: List of observed symptoms
        context: Additional context (system info, error logs, etc.)
        category: Problem category (technical, billing, account, etc.)

    Returns:
        Diagnosis results with steps and recommendations
    """
    try:
        update_progress(self, 0, 100, "Analyzing problem...")

        analyzer = ResearchAnalyzer()

        update_progress(self, 30, 100, "Searching knowledge base...")

        # Search for similar issues in knowledge base
        from database.connection import get_db_context
        from database.models import KnowledgeDoc
        from sqlalchemy import or_

        similar_issues = []
        with get_db_context() as db:
            # Search by keywords from problem and symptoms
            search_terms = problem.split() + symptoms
            query = db.query(KnowledgeDoc)

            conditions = []
            for term in search_terms[:5]:  # Limit to first 5 terms
                conditions.append(KnowledgeDoc.title.ilike(f"%{term}%"))

            if conditions:
                query = query.filter(or_(*conditions))

            similar_issues = query.limit(5).all()

        update_progress(self, 60, 100, "Generating diagnosis...")

        # Generate troubleshooting steps
        diagnosis = analyzer.diagnose_issue(problem, symptoms, context or {})

        update_progress(self, 100, 100, "Diagnosis complete")

        return {
            "task_type": "troubleshooting",
            "problem": problem,
            "symptoms": symptoms,
            "category": category,
            "diagnosis": diagnosis,
            "similar_issues": [
                {
                    "id": issue.id,
                    "title": issue.title,
                    "category": issue.category,
                }
                for issue in similar_issues
            ],
            "troubleshooting_steps": diagnosis.get("steps", []),
            "severity": diagnosis.get("severity", "unknown"),
            "estimated_resolution_time": diagnosis.get("eta", "unknown"),
        }

    except Exception as exc:
        logger.error(f"Troubleshooting failed: {exc}")
        raise self.retry(exc=exc)
