"""Cost analytics and usage tracking for the keyword engine."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os


@dataclass
class UsageStats:
    """Statistics for a single keyword or category."""

    matches: int = 0
    last_matched: Optional[datetime] = None
    first_matched: Optional[datetime] = None
    total_response_time_ms: float = 0.0
    embeds_generated: int = 0

    @property
    def avg_response_time_ms(self) -> float:
        """Calculate average response time."""
        if self.matches == 0:
            return 0.0
        return self.total_response_time_ms / self.matches


@dataclass
class CostMetrics:
    """Cost metrics for different operations."""

    fuzzy_matching_cost: float = 0.0  # Based on computation time
    regex_matching_cost: float = 0.0
    semantic_search_cost: float = 0.0  # pgvector + embedding costs
    ai_classification_cost: float = 0.0  # LLM API costs
    total_cost: float = 0.0

    # Estimated costs per operation (configurable)
    COST_PER_FUZZY_MATCH: float = 0.0001
    COST_PER_REGEX_MATCH: float = 0.00005
    COST_PER_SEMANTIC_SEARCH: float = 0.001
    COST_PER_AI_CLASSIFICATION: float = 0.01


@dataclass
class DailyStats:
    """Daily aggregated statistics."""

    date: str
    total_messages: int = 0
    total_matches: int = 0
    total_embeds: int = 0
    category_matches: Dict[str, int] = field(default_factory=dict)
    keyword_matches: Dict[str, int] = field(default_factory=dict)
    cost_metrics: CostMetrics = field(default_factory=CostMetrics)
    avg_response_time_ms: float = 0.0


class CostAnalytics:
    """Tracks usage statistics and costs for optimization."""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or "analytics_data.json"
        self._keyword_stats: Dict[str, UsageStats] = defaultdict(UsageStats)
        self._category_stats: Dict[str, UsageStats] = defaultdict(UsageStats)
        self._daily_stats: Dict[str, DailyStats] = {}
        self._cost_metrics = CostMetrics()
        self._session_start = datetime.now()
        self._current_day = datetime.now().strftime("%Y-%m-%d")

        # Session metrics
        self._session_messages = 0
        self._session_matches = 0
        self._session_start_time = datetime.now()

        self._load_data()

    def _get_or_create_daily(self, date: Optional[str] = None) -> DailyStats:
        """Get or create daily stats for a date."""
        date = date or datetime.now().strftime("%Y-%m-%d")
        if date not in self._daily_stats:
            self._daily_stats[date] = DailyStats(date=date)
        return self._daily_stats[date]

    def record_message_processed(self, response_time_ms: float):
        """Record that a message was processed."""
        self._session_messages += 1
        daily = self._get_or_create_daily()
        daily.total_messages += 1

        # Update running average
        if daily.total_messages > 0:
            daily.avg_response_time_ms = (
                daily.avg_response_time_ms * (daily.total_messages - 1)
                + response_time_ms
            ) / daily.total_messages

    def record_keyword_match(
        self,
        keyword: str,
        category: str,
        match_type: str,
        response_time_ms: float,
        embeds_count: int = 1,
    ):
        """Record a keyword match with cost tracking."""
        now = datetime.now()

        # Update keyword stats
        stats = self._keyword_stats[keyword]
        stats.matches += 1
        stats.last_matched = now
        if stats.first_matched is None:
            stats.first_matched = now
        stats.total_response_time_ms += response_time_ms
        stats.embeds_generated += embeds_count

        # Update category stats
        cat_stats = self._category_stats[category]
        cat_stats.matches += 1
        cat_stats.last_matched = now
        if cat_stats.first_matched is None:
            cat_stats.first_matched = now
        cat_stats.embeds_generated += embeds_count

        # Update daily stats
        daily = self._get_or_create_daily()
        daily.total_matches += 1
        daily.total_embeds += embeds_count
        daily.keyword_matches[keyword] = daily.keyword_matches.get(keyword, 0) + 1
        daily.category_matches[category] = daily.category_matches.get(category, 0) + 1

        # Update costs based on match type
        self._update_costs(match_type)

        self._session_matches += 1

    def _update_costs(self, match_type: str):
        """Update cost metrics based on operation type."""
        if match_type == "fuzzy":
            self._cost_metrics.fuzzy_matching_cost += (
                self._cost_metrics.COST_PER_FUZZY_MATCH
            )
            self._cost_metrics.total_cost += self._cost_metrics.COST_PER_FUZZY_MATCH
        elif match_type == "regex":
            self._cost_metrics.regex_matching_cost += (
                self._cost_metrics.COST_PER_REGEX_MATCH
            )
            self._cost_metrics.total_cost += self._cost_metrics.COST_PER_REGEX_MATCH
        elif match_type == "semantic":
            self._cost_metrics.semantic_search_cost += (
                self._cost_metrics.COST_PER_SEMANTIC_SEARCH
            )
            self._cost_metrics.total_cost += self._cost_metrics.COST_PER_SEMANTIC_SEARCH
        elif match_type == "ai":
            self._cost_metrics.ai_classification_cost += (
                self._cost_metrics.COST_PER_AI_CLASSIFICATION
            )
            self._cost_metrics.total_cost += (
                self._cost_metrics.COST_PER_AI_CLASSIFICATION
            )

    def record_semantic_search(self):
        """Record a semantic search operation."""
        self._update_costs("semantic")

    def record_ai_classification(self):
        """Record an AI classification operation."""
        self._update_costs("ai")

    def get_top_keywords(self, limit: int = 10) -> List[tuple]:
        """Get most frequently matched keywords."""
        sorted_keywords = sorted(
            self._keyword_stats.items(),
            key=lambda x: x[1].matches,
            reverse=True,
        )
        return sorted_keywords[:limit]

    def get_top_categories(self, limit: int = 10) -> List[tuple]:
        """Get most frequently matched categories."""
        sorted_cats = sorted(
            self._category_stats.items(),
            key=lambda x: x[1].matches,
            reverse=True,
        )
        return sorted_cats[:limit]

    def get_unused_keywords(self, days: int = 30) -> List[str]:
        """Get keywords not matched in the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        unused = []
        for keyword, stats in self._keyword_stats.items():
            if stats.last_matched is None or stats.last_matched < cutoff:
                unused.append(keyword)
        return unused

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary."""
        return {
            "fuzzy_matching": round(self._cost_metrics.fuzzy_matching_cost, 4),
            "regex_matching": round(self._cost_metrics.regex_matching_cost, 4),
            "semantic_search": round(self._cost_metrics.semantic_search_cost, 4),
            "ai_classification": round(self._cost_metrics.ai_classification_cost, 4),
            "total_cost": round(self._cost_metrics.total_cost, 4),
        }

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        session_duration = datetime.now() - self._session_start_time
        return {
            "messages_processed": self._session_messages,
            "matches_found": self._session_matches,
            "match_rate": round(
                self._session_matches / max(self._session_messages, 1) * 100, 2
            ),
            "session_duration_minutes": round(session_duration.total_seconds() / 60, 2),
            "session_start": self._session_start_time.isoformat(),
        }

    def get_daily_stats(self, date: Optional[str] = None) -> Optional[DailyStats]:
        """Get stats for a specific date."""
        date = date or datetime.now().strftime("%Y-%m-%d")
        return self._daily_stats.get(date)

    def get_keyword_stats(self, keyword: str) -> Optional[UsageStats]:
        """Get stats for a specific keyword."""
        return self._keyword_stats.get(keyword)

    def generate_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate a comprehensive report."""
        today = datetime.now()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

        daily_data = []
        total_matches = 0
        total_messages = 0
        total_cost = 0.0

        for date in dates:
            if date in self._daily_stats:
                daily = self._daily_stats[date]
                daily_data.append(
                    {
                        "date": date,
                        "messages": daily.total_messages,
                        "matches": daily.total_matches,
                        "embeds": daily.total_embeds,
                        "match_rate": round(
                            daily.total_matches / max(daily.total_messages, 1) * 100, 2
                        ),
                    }
                )
                total_matches += daily.total_matches
                total_messages += daily.total_messages
                total_cost += daily.cost_metrics.total_cost

        return {
            "period": f"Last {days} days",
            "total_messages": total_messages,
            "total_matches": total_matches,
            "overall_match_rate": round(
                total_matches / max(total_messages, 1) * 100, 2
            ),
            "total_cost": round(total_cost, 4),
            "daily_breakdown": daily_data,
            "top_keywords": [
                {"keyword": k, "matches": v.matches}
                for k, v in self.get_top_keywords(5)
            ],
            "top_categories": [
                {"category": c, "matches": v.matches}
                for c, v in self.get_top_categories(5)
            ],
            "unused_keywords_count": len(self.get_unused_keywords(30)),
        }

    def _load_data(self):
        """Load analytics data from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                # Restore daily stats
                for date, daily_data in data.get("daily", {}).items():
                    daily = DailyStats(
                        date=date,
                        total_messages=daily_data.get("messages", 0),
                        total_matches=daily_data.get("matches", 0),
                        total_embeds=daily_data.get("embeds", 0),
                        category_matches=daily_data.get("categories", {}),
                        keyword_matches=daily_data.get("keywords", {}),
                    )
                    self._daily_stats[date] = daily
            except Exception:
                pass  # Start fresh if loading fails

    def save_data(self):
        """Save analytics data to storage."""
        data = {
            "daily": {
                date: {
                    "messages": daily.total_messages,
                    "matches": daily.total_matches,
                    "embeds": daily.total_embeds,
                    "categories": daily.category_matches,
                    "keywords": daily.keyword_matches,
                }
                for date, daily in self._daily_stats.items()
            },
            "session": self.get_session_stats(),
        }
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def reset_session(self):
        """Reset session statistics."""
        self._session_messages = 0
        self._session_matches = 0
        self._session_start_time = datetime.now()
