"""Data analysis tools for research tasks.

Provides analysis capabilities for search results, documents, and diagnostic data.
"""

import logging
import re
from collections import Counter
from typing import Any

import requests

logger = logging.getLogger(__name__)


class ResearchAnalyzer:
    """Analyzer for research data and results."""

    def __init__(self):
        """Initialize the analyzer."""
        self.stopwords = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "dare",
            "ought",
            "used",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "and",
            "but",
            "or",
            "yet",
            "so",
        }

    def rank_search_results(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Rank search results by relevance to query.

        Args:
            query: Search query
            results: Search results to rank

        Returns:
            Ranked results with scores
        """
        query_terms = set(query.lower().split())
        scored_results = []

        for result in results:
            score = self._calculate_relevance_score(result, query_terms)
            result["relevance_score"] = score
            scored_results.append(result)

        # Sort by relevance score descending
        scored_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Update rank positions
        for i, result in enumerate(scored_results, 1):
            result["final_rank"] = i

        return scored_results

    def _calculate_relevance_score(
        self,
        result: dict[str, Any],
        query_terms: set[str],
    ) -> float:
        """Calculate relevance score for a result."""
        score = 0.0

        # Base score from original source rank
        original_rank = result.get("rank", 100)
        score += max(0, 1.0 - (original_rank - 1) * 0.1)

        # Title matching
        title = result.get("title", "").lower()
        title_terms = set(title.split())
        title_matches = len(query_terms & title_terms)
        score += title_matches * 0.5

        # Snippet matching
        snippet = result.get("snippet", "").lower()
        snippet_terms = set(snippet.split())
        snippet_matches = len(query_terms & snippet_terms)
        score += snippet_matches * 0.2

        # Exact phrase match bonus
        query_lower = " ".join(query_terms)
        if query_lower in title:
            score += 1.0
        if query_lower in snippet:
            score += 0.5

        # Domain authority
        url = result.get("url", "")
        score += self._get_domain_authority_score(url)

        return round(score, 3)

    def _get_domain_authority_score(self, url: str) -> float:
        """Get authority score based on domain."""
        authority_domains = {
            "stackoverflow.com": 0.4,
            "github.com": 0.35,
            "docs.python.org": 0.35,
            "discord.com": 0.4,
            "support.discord.com": 0.45,
            "docs.discord.com": 0.4,
            "python.org": 0.35,
            "pypi.org": 0.3,
            "readthedocs.io": 0.25,
            "medium.com": 0.15,
            "dev.to": 0.2,
        }

        url_lower = url.lower()
        for domain, score in authority_domains.items():
            if domain in url_lower:
                return score

        return 0.0

    def summarize(self, content: str, max_length: int = 500) -> dict[str, Any]:
        """Generate a summary of document content.

        Args:
            content: Document content to summarize
            max_length: Maximum summary length

        Returns:
            Summary data
        """
        if not content:
            return {"summary": "", "length": 0, "method": "none"}

        # Simple extractive summarization
        sentences = re.split(r"(?<=[.!?])\s+", content)

        if len(sentences) <= 3:
            summary = content[:max_length]
        else:
            # Score sentences by keyword density
            word_freq = Counter(
                w.lower()
                for w in re.findall(r"\b\w+\b", content)
                if w.lower() not in self.stopwords and len(w) > 3
            )

            sentence_scores = []
            for sent in sentences:
                score = sum(
                    word_freq.get(word.lower(), 0)
                    for word in re.findall(r"\b\w+\b", sent)
                )
                sentence_scores.append((sent, score))

            # Select top sentences
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            top_sentences = [s[0] for s in sentence_scores[:3]]

            # Maintain original order
            top_sentences.sort(key=lambda s: sentences.index(s))

            summary = " ".join(top_sentences)
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(" ", 1)[0] + "..."

        return {
            "summary": summary,
            "length": len(summary),
            "original_length": len(content),
            "method": "extractive",
            "sentences_extracted": min(3, len(sentences)),
        }

    def analyze_sentiment(self, content: str) -> dict[str, Any]:
        """Analyze sentiment of content.

        Args:
            content: Text to analyze

        Returns:
            Sentiment analysis results
        """
        if not content:
            return {"sentiment": "neutral", "score": 0.0}

        # Simple lexicon-based sentiment analysis
        positive_words = {
            "good",
            "great",
            "excellent",
            "amazing",
            "awesome",
            "fantastic",
            "wonderful",
            "perfect",
            "best",
            "love",
            "happy",
            "satisfied",
            "helpful",
            "easy",
            "simple",
            "fast",
            "quick",
            "reliable",
            "recommended",
            "works",
            "working",
            "solved",
            "fixed",
            "thanks",
        }

        negative_words = {
            "bad",
            "terrible",
            "awful",
            "horrible",
            "worst",
            "hate",
            "angry",
            "frustrated",
            "disappointed",
            "annoying",
            "difficult",
            "hard",
            "complicated",
            "slow",
            "broken",
            "error",
            "bug",
            "issue",
            "problem",
            "fail",
            "failed",
            "not working",
            "useless",
        }

        content_lower = content.lower()
        words = re.findall(r"\b\w+\b", content_lower)

        positive_count = sum(1 for w in words if w in positive_words)
        negative_count = sum(1 for w in words if w in negative_words)

        # Check for negations
        negations = ["not", "no", "never", "without", "don't", "doesn't", "didn't"]
        for neg in negations:
            for pos in positive_words:
                if f"{neg} {pos}" in content_lower:
                    positive_count -= 1
                    negative_count += 1

        total = positive_count + negative_count

        if total == 0:
            sentiment = "neutral"
            score = 0.0
        else:
            score = (positive_count - negative_count) / total
            if score > 0.2:
                sentiment = "positive"
            elif score < -0.2:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": round(score, 3),
            "positive_words": positive_count,
            "negative_words": negative_count,
            "confidence": min(abs(score) * 2, 1.0),
        }

    def extract_entities(self, content: str) -> dict[str, list[str]]:
        """Extract named entities from content.

        Args:
            content: Text to analyze

        Returns:
            Dictionary of entity types and values
        """
        if not content:
            return {
                "organizations": [],
                "people": [],
                "locations": [],
                "technologies": [],
            }

        # Simple pattern-based entity extraction
        entities = {
            "organizations": [],
            "people": [],
            "locations": [],
            "technologies": [],
        }

        # Technology patterns
        tech_patterns = [
            r"\bPython\s+\d+\.?\d*\b",
            r"\bDiscord\.py\b",
            r"\bPostgreSQL\b",
            r"\bRedis\b",
            r"\bCelery\b",
            r"\bDocker\b",
            r"\bKubernetes\b",
            r"\bAWS\b",
            r"\bAzure\b",
            r"\bGCP\b",
        ]

        for pattern in tech_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            entities["technologies"].extend(matches)

        # Remove duplicates while preserving order
        for key in entities:
            entities[key] = list(dict.fromkeys(entities[key]))

        return entities

    def extract_keywords(self, content: str, top_n: int = 10) -> list[dict[str, Any]]:
        """Extract keywords from content.

        Args:
            content: Text to analyze
            top_n: Number of top keywords to return

        Returns:
            List of keywords with scores
        """
        if not content:
            return []

        words = re.findall(r"\b\w+\b", content.lower())

        # Filter stopwords and short words
        filtered_words = [w for w in words if w not in self.stopwords and len(w) > 3]

        # Count word frequencies
        word_freq = Counter(filtered_words)

        # Get top keywords
        keywords = [
            {"word": word, "frequency": freq, "score": round(freq / len(words), 4)}
            for word, freq in word_freq.most_common(top_n)
        ]

        return keywords

    def score_criterion(
        self,
        item: dict[str, Any],
        criterion: str,
        context: str,
    ) -> float:
        """Score an item against a comparison criterion.

        Args:
            item: Item to score
            criterion: Criterion name
            context: Comparison context

        Returns:
            Score from 0.0 to 1.0
        """
        score = 0.5  # Default neutral score

        # Get item attributes
        attributes = item.get("attributes", {})
        criterion_lower = criterion.lower()

        # Check if item has this criterion as an attribute
        if criterion_lower in attributes:
            value = attributes[criterion_lower]

            # Boolean values
            if isinstance(value, bool):
                score = 1.0 if value else 0.0

            # Numeric values (normalize to 0-1)
            elif isinstance(value, (int, float)):
                # Assume higher is better, clamp to 0-1
                score = min(max(value / 100.0, 0.0), 1.0)

            # String values - check for positive indicators
            elif isinstance(value, str):
                value_lower = value.lower()
                positive_indicators = ["yes", "true", "excellent", "good", "high"]
                negative_indicators = ["no", "false", "poor", "low", "none"]

                if any(p in value_lower for p in positive_indicators):
                    score = 0.9
                elif any(n in value_lower for n in negative_indicators):
                    score = 0.1

        # Context-based adjustments
        context_lower = context.lower()
        item_name = item.get("name", "").lower()

        # Boost score if item name appears positively in context
        if item_name in context_lower:
            # Check surrounding context for positive words
            context_words = context_lower.split()
            try:
                idx = context_words.index(item_name.split()[0])
                surrounding = context_words[
                    max(0, idx - 5) : min(len(context_words), idx + 5)
                ]
                positive_words = ["best", "recommended", "top", "great", "excellent"]
                if any(p in surrounding for p in positive_words):
                    score = min(score + 0.2, 1.0)
            except ValueError:
                pass

        return round(score, 2)

    def diagnose_issue(
        self,
        problem: str,
        symptoms: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Diagnose an issue based on problem and symptoms.

        Args:
            problem: Problem description
            symptoms: List of symptoms
            context: Additional context

        Returns:
            Diagnosis with steps and recommendations
        """
        steps = []
        severity = "medium"
        eta = "15-30 minutes"

        # Analyze problem keywords
        problem_lower = problem.lower()
        all_text = problem_lower + " " + " ".join(s.lower() for s in symptoms)

        # Determine severity
        critical_keywords = [
            "crash",
            "error",
            "broken",
            "not working",
            "failure",
            "urgent",
        ]
        if any(kw in all_text for kw in critical_keywords):
            severity = "high"
            eta = "5-15 minutes"

        simple_keywords = ["how to", "question", "help with", "guidance"]
        if any(kw in all_text for kw in simple_keywords):
            severity = "low"
            eta = "5-10 minutes"

        # Generate troubleshooting steps based on context
        steps.append(
            {
                "step": 1,
                "action": "Verify the issue",
                "description": "Confirm the problem and gather all relevant information including error messages.",
            }
        )

        # Add specific steps based on problem type
        if "login" in all_text or "sign in" in all_text:
            steps.append(
                {
                    "step": 2,
                    "action": "Check credentials",
                    "description": "Verify username/password and check for caps lock. Try password reset if needed.",
                }
            )
            steps.append(
                {
                    "step": 3,
                    "action": "Clear browser cache",
                    "description": "Clear cookies and cache, then try logging in again.",
                }
            )

        elif "error" in all_text or "exception" in all_text:
            steps.append(
                {
                    "step": 2,
                    "action": "Check error logs",
                    "description": "Review application logs for detailed error messages and stack traces.",
                }
            )
            steps.append(
                {
                    "step": 3,
                    "action": "Verify configuration",
                    "description": "Check that all configuration values are correct and services are accessible.",
                }
            )

        elif "slow" in all_text or "performance" in all_text:
            steps.append(
                {
                    "step": 2,
                    "action": "Check resource usage",
                    "description": "Monitor CPU, memory, and disk usage to identify bottlenecks.",
                }
            )
            steps.append(
                {
                    "step": 3,
                    "action": "Review recent changes",
                    "description": "Check for recent deployments or configuration changes that might cause issues.",
                }
            )

        else:
            steps.append(
                {
                    "step": 2,
                    "action": "Review documentation",
                    "description": "Check knowledge base and documentation for similar issues and solutions.",
                }
            )
            steps.append(
                {
                    "step": 3,
                    "action": "Test basic functionality",
                    "description": "Try the simplest case to isolate the problem area.",
                }
            )

        # Add final escalation step
        steps.append(
            {
                "step": len(steps) + 1,
                "action": "Escalate if unresolved",
                "description": "If the issue persists after these steps, escalate to senior support or development team.",
            }
        )

        return {
            "severity": severity,
            "steps": steps,
            "eta": eta,
            "recommendations": [
                "Document all steps taken for future reference",
                "Keep user informed of progress throughout the process",
            ],
        }
