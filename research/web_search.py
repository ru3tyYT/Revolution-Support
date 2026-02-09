"""Web search integration for research tasks.

Supports multiple search providers with result ranking and filtering.
"""

import logging
import os
import random
from typing import Any
from urllib.parse import quote_plus, urlparse

import requests

logger = logging.getLogger(__name__)


class WebSearchProvider:
    """Multi-provider web search with result ranking."""

    PROVIDERS = ["duckduckgo", "google", "bing"]

    def __init__(self):
        """Initialize search provider with API keys."""
        self.api_keys = {
            "google": os.getenv("GOOGLE_SEARCH_API_KEY"),
            "bing": os.getenv("BING_SEARCH_API_KEY"),
        }
        self.cx = os.getenv("GOOGLE_SEARCH_CX")  # Custom search engine ID

    def search(
        self,
        query: str,
        provider: str = "auto",
        max_results: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute web search with specified provider.

        Args:
            query: Search query
            provider: Provider name or "auto" for best available
            max_results: Maximum results to return
            filters: Search filters (date, site, etc.)

        Returns:
            List of search results
        """
        filters = filters or {}

        # Determine provider
        if provider == "auto":
            provider = self._select_best_provider()

        # Execute search based on provider
        if provider == "google" and self.api_keys["google"]:
            results = self._search_google(query, max_results, filters)
        elif provider == "bing" and self.api_keys["bing"]:
            results = self._search_bing(query, max_results, filters)
        else:
            results = self._search_duckduckgo(query, max_results, filters)

        return results

    def _select_best_provider(self) -> str:
        """Select the best available search provider."""
        if self.api_keys["google"] and self.cx:
            return "google"
        elif self.api_keys["bing"]:
            return "bing"
        return "duckduckgo"

    def _search_google(
        self,
        query: str,
        max_results: int,
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Search using Google Custom Search API."""
        base_url = "https://www.googleapis.com/customsearch/v1"

        params = {
            "key": self.api_keys["google"],
            "cx": self.cx,
            "q": query,
            "num": min(max_results, 10),  # Google max is 10 per request
        }

        # Apply filters
        if "site" in filters:
            params["q"] = f"site:{filters['site']} {query}"
        if "date_restrict" in filters:
            params["dateRestrict"] = filters["date_restrict"]

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("items", []):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": "google",
                        "rank": len(results) + 1,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return self._search_duckduckgo(query, max_results, filters)

    def _search_bing(
        self,
        query: str,
        max_results: int,
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Search using Bing Search API."""
        base_url = "https://api.bing.microsoft.com/v7.0/search"

        headers = {
            "Ocp-Apim-Subscription-Key": self.api_keys["bing"],
        }

        params = {
            "q": query,
            "count": max_results,
            "responseFilter": "Webpages",
        }

        # Apply filters
        if "site" in filters:
            params["q"] = f"site:{filters['site']} {query}"

        try:
            response = requests.get(
                base_url,
                headers=headers,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("webPages", {}).get("value", []):
                results.append(
                    {
                        "title": item.get("name", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                        "source": "bing",
                        "rank": len(results) + 1,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            return self._search_duckduckgo(query, max_results, filters)

    def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Search using DuckDuckGo (no API key required).

        Note: This uses DuckDuckGo HTML scraping as a fallback.
        For production, consider using duckduckgo-search library.
        """
        try:
            # Try using duckduckgo-search library if available
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = []
                for r in ddgs.text(query, max_results=max_results):
                    results.append(
                        {
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                            "source": "duckduckgo",
                            "rank": len(results) + 1,
                        }
                    )
                return results

        except ImportError:
            logger.warning("duckduckgo-search library not installed, using fallback")
            return self._fallback_search(query, max_results)
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return self._fallback_search(query, max_results)

    def _fallback_search(
        self,
        query: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Fallback search that returns empty results with metadata."""
        logger.warning("Using fallback search - no results available")
        return [
            {
                "title": "Search Unavailable",
                "url": "",
                "snippet": "Web search is currently unavailable. Please configure search API keys or install duckduckgo-search library.",
                "source": "fallback",
                "rank": 1,
            }
        ]

    def rank_results(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Rank search results by relevance.

        Args:
            query: Original search query
            results: Search results to rank

        Returns:
            Ranked results with relevance scores
        """
        query_terms = set(query.lower().split())

        for result in results:
            score = 0.0

            # Base score from original rank
            score += 1.0 / result.get("rank", 1)

            # Content relevance
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()

            for term in query_terms:
                if term in title:
                    score += 0.3
                if term in snippet:
                    score += 0.1

            # Domain authority (simplified)
            url = result.get("url", "")
            domain = urlparse(url).netloc.lower()

            authority_domains = [
                "stackoverflow.com",
                "github.com",
                "docs.python.org",
                "discord.com",
                "support.discord.com",
            ]

            if any(auth in domain for auth in authority_domains):
                score += 0.2

            result["relevance_score"] = round(score, 3)

        # Sort by relevance score
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Update ranks
        for i, result in enumerate(results, 1):
            result["rank"] = i

        return results

    def filter_results(
        self,
        results: list[dict[str, Any]],
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Filter search results based on criteria.

        Args:
            results: Search results to filter
            filters: Filter criteria

        Returns:
            Filtered results
        """
        filtered = results

        # Site filter
        if "site" in filters:
            site = filters["site"].lower()
            filtered = [r for r in filtered if site in r.get("url", "").lower()]

        # Content filter
        if "exclude" in filters:
            exclude_terms = filters["exclude"]
            if isinstance(exclude_terms, str):
                exclude_terms = [exclude_terms]

            for term in exclude_terms:
                term = term.lower()
                filtered = [
                    r
                    for r in filtered
                    if term not in r.get("title", "").lower()
                    and term not in r.get("snippet", "").lower()
                ]

        # Minimum relevance score
        if "min_score" in filters:
            min_score = filters["min_score"]
            filtered = [r for r in filtered if r.get("relevance_score", 0) >= min_score]

        return filtered
