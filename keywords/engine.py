"""Multi-keyword matching engine for Discord support bot."""

import re
import discord
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Set, Tuple
from collections import defaultdict
from difflib import SequenceMatcher
import time

from .categories import Category, CategoryManager
from .classifier import IntentClassifier, IntentClassification
from .analytics import CostAnalytics


@dataclass
class KeywordMatch:
    """Represents a single keyword match."""

    keyword: str
    match_type: str  # 'exact', 'regex', 'fuzzy'
    confidence: float
    category: Category
    response_text: str
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MatchResult:
    """Result of keyword matching for a message."""

    message: str
    matches: List[KeywordMatch]
    categories: List[Category]
    embeds: List[discord.Embed]
    processing_time_ms: float
    total_matches: int
    intent_classification: Optional[IntentClassification] = None


class KeywordEngine:
    """
    Multi-keyword matching engine that finds ALL matching keywords,
    groups them by category, and returns categorized Discord embeds.
    """

    def __init__(
        self,
        fuzzy_threshold: float = 0.8,
        max_fuzzy_matches: int = 3,
        enable_analytics: bool = True,
    ):
        self.fuzzy_threshold = fuzzy_threshold
        self.max_fuzzy_matches = max_fuzzy_matches
        self.enable_analytics = enable_analytics

        # Storage for keywords
        self._exact_keywords: Dict[str, KeywordMatch] = {}
        self._regex_patterns: List[Tuple[re.Pattern, KeywordMatch]] = []
        self._fuzzy_keywords: List[KeywordMatch] = []
        self._category_keywords: Dict[Category, List[KeywordMatch]] = defaultdict(list)

        # Components
        self.category_manager = CategoryManager()
        self.intent_classifier = IntentClassifier()
        self.analytics = CostAnalytics() if enable_analytics else None

        # Response templates
        self._response_templates: Dict[str, str] = {}
        self._pre_match_hooks: List[Callable] = []
        self._post_match_hooks: List[Callable] = []

    def add_keyword(
        self,
        keyword: str,
        response: str,
        category: Category = Category.GENERAL,
        match_type: str = "exact",
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KeywordMatch:
        """
        Add a keyword to the engine.

        Args:
            keyword: The keyword/pattern to match
            response: The response text for this keyword
            category: The category this keyword belongs to
            match_type: 'exact', 'regex', or 'fuzzy'
            priority: Priority for ordering (higher = more important)
            metadata: Additional data for this keyword
        """
        keyword_lower = keyword.lower().strip()

        match = KeywordMatch(
            keyword=keyword_lower,
            match_type=match_type,
            confidence=1.0 if match_type == "exact" else 0.0,
            category=category,
            response_text=response,
            priority=priority,
            metadata=metadata or {},
        )

        if match_type == "exact":
            self._exact_keywords[keyword_lower] = match
        elif match_type == "regex":
            try:
                pattern = re.compile(keyword, re.IGNORECASE)
                self._regex_patterns.append((pattern, match))
            except re.error:
                raise ValueError(f"Invalid regex pattern: {keyword}")
        elif match_type == "fuzzy":
            self._fuzzy_keywords.append(match)
        else:
            raise ValueError(f"Unknown match type: {match_type}")

        # Add to category mapping
        self._category_keywords[category].append(match)

        return match

    def add_keywords_batch(
        self,
        keywords: List[Dict[str, Any]],
    ) -> List[KeywordMatch]:
        """Add multiple keywords at once."""
        matches = []
        for kw_data in keywords:
            match = self.add_keyword(**kw_data)
            matches.append(match)
        return matches

    def remove_keyword(self, keyword: str, match_type: str = "exact") -> bool:
        """Remove a keyword from the engine."""
        keyword_lower = keyword.lower().strip()

        if match_type == "exact" and keyword_lower in self._exact_keywords:
            match = self._exact_keywords.pop(keyword_lower)
            self._category_keywords[match.category].remove(match)
            return True

        return False

    def process_message(
        self,
        message: str,
        include_intent: bool = True,
    ) -> MatchResult:
        """
        Process a user message and find all matching keywords.

        Args:
            message: The user message to process
            include_intent: Whether to include intent classification

        Returns:
            MatchResult containing all matches and generated embeds
        """
        start_time = time.time()

        # Run pre-match hooks
        for hook in self._pre_match_hooks:
            hook(message)

        # Find all matches
        all_matches: List[KeywordMatch] = []
        message_lower = message.lower()

        # 1. Exact matching
        exact_matches = self._find_exact_matches(message_lower)
        all_matches.extend(exact_matches)

        # 2. Regex matching
        regex_matches = self._find_regex_matches(message)
        all_matches.extend(regex_matches)

        # 3. Fuzzy matching (only if no exact matches found or additional context needed)
        if len(all_matches) < self.max_fuzzy_matches:
            fuzzy_matches = self._find_fuzzy_matches(message_lower)
            # Filter out duplicates
            existing_keywords = {m.keyword for m in all_matches}
            for fm in fuzzy_matches:
                if fm.keyword not in existing_keywords:
                    all_matches.append(fm)

        # Sort by priority (higher first)
        all_matches.sort(key=lambda m: m.priority, reverse=True)

        # Limit total matches to prevent spam
        if len(all_matches) > 10:
            all_matches = all_matches[:10]

        # Classify intent if enabled
        intent_result = None
        if include_intent:
            import asyncio

            intent_result = asyncio.run(self.intent_classifier.classify(message))

        # Group by category
        matches_by_category = self._group_by_category(all_matches)

        # Generate embeds
        embeds = self._create_embeds(matches_by_category)

        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000

        # Track analytics
        if self.analytics:
            self.analytics.record_message_processed(processing_time)
            for match in all_matches:
                self.analytics.record_keyword_match(
                    keyword=match.keyword,
                    category=match.category.value,
                    match_type=match.match_type,
                    response_time_ms=processing_time / max(len(all_matches), 1),
                )

        # Run post-match hooks
        for hook in self._post_match_hooks:
            hook(message, all_matches)

        return MatchResult(
            message=message,
            matches=all_matches,
            categories=list(matches_by_category.keys()),
            embeds=embeds,
            processing_time_ms=processing_time,
            total_matches=len(all_matches),
            intent_classification=intent_result,
        )

    def _find_exact_matches(self, message: str) -> List[KeywordMatch]:
        """Find exact keyword matches."""
        matches = []
        words = message.split()

        # Check for exact matches (including multi-word)
        for keyword, match in self._exact_keywords.items():
            if keyword in message:
                # Create a copy with updated confidence
                match_copy = KeywordMatch(
                    keyword=match.keyword,
                    match_type="exact",
                    confidence=1.0,
                    category=match.category,
                    response_text=match.response_text,
                    priority=match.priority,
                    metadata=match.metadata.copy(),
                )
                matches.append(match_copy)

        return matches

    def _find_regex_matches(self, message: str) -> List[KeywordMatch]:
        """Find regex pattern matches."""
        matches = []

        for pattern, match in self._regex_patterns:
            if pattern.search(message):
                match_copy = KeywordMatch(
                    keyword=match.keyword,
                    match_type="regex",
                    confidence=0.95,
                    category=match.category,
                    response_text=match.response_text,
                    priority=match.priority,
                    metadata=match.metadata.copy(),
                )
                matches.append(match_copy)

        return matches

    def _find_fuzzy_matches(self, message: str) -> List[KeywordMatch]:
        """Find fuzzy matches using string similarity."""
        matches = []
        message_words = message.split()

        for match in self._fuzzy_keywords:
            keyword_words = match.keyword.split()
            max_score = 0.0

            # Compare all combinations of words
            for msg_word in message_words:
                for kw_word in keyword_words:
                    similarity = SequenceMatcher(None, msg_word, kw_word).ratio()
                    max_score = max(max_score, similarity)

            # Also check overall similarity
            overall_similarity = SequenceMatcher(None, message, match.keyword).ratio()
            max_score = max(max_score, overall_similarity)

            if max_score >= self.fuzzy_threshold:
                match_copy = KeywordMatch(
                    keyword=match.keyword,
                    match_type="fuzzy",
                    confidence=max_score,
                    category=match.category,
                    response_text=match.response_text,
                    priority=match.priority,
                    metadata={**match.metadata, "fuzzy_score": max_score},
                )
                matches.append(match_copy)

        # Sort by confidence and limit results
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches[: self.max_fuzzy_matches]

    def _group_by_category(
        self,
        matches: List[KeywordMatch],
    ) -> Dict[Category, List[KeywordMatch]]:
        """Group matches by category."""
        grouped = defaultdict(list)
        for match in matches:
            grouped[match.category].append(match)

        # Update category stats
        for category in grouped.keys():
            self.category_manager.update_stats(category, len(grouped[category]))

        return dict(grouped)

    def _create_embeds(
        self,
        matches_by_category: Dict[Category, List[KeywordMatch]],
    ) -> List[discord.Embed]:
        """Create Discord embeds for each category."""
        embeds = []

        # Sort categories by priority
        sorted_categories = self.category_manager.sort_by_priority(
            list(matches_by_category.keys())
        )

        for category in sorted_categories:
            matches = matches_by_category[category]
            config = self.category_manager.get_config(category)

            # Create category header embed
            header_embed = discord.Embed(
                title=f"{config.emoji} {config.name}",
                description=config.description,
                color=config.color,
            )
            header_embed.set_footer(text=f"Found {len(matches)} relevant match(es)")
            embeds.append(header_embed)

            # Create embed for each match
            for match in matches:
                embed = discord.Embed(
                    description=match.response_text,
                    color=config.color,
                )

                # Add match info in footer
                match_info = f"Match: {match.keyword}"
                if match.match_type == "fuzzy":
                    match_info += f" ({match.confidence:.0%} confidence)"
                embed.set_footer(text=match_info)

                embeds.append(embed)

                # Limit embeds per category to prevent spam
                if (
                    len([e for e in embeds if e.color == config.color])
                    > config.max_embeds
                ):
                    overflow_embed = discord.Embed(
                        description=f"*... and {len(matches) - config.max_embeds} more matches*",
                        color=config.color,
                    )
                    embeds.append(overflow_embed)
                    break

        return embeds

    def add_pre_match_hook(self, hook: Callable[[str], None]):
        """Add a hook to run before matching."""
        self._pre_match_hooks.append(hook)

    def add_post_match_hook(self, hook: Callable[[str, List[KeywordMatch]], None]):
        """Add a hook to run after matching."""
        self._post_match_hooks.append(hook)

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        stats = {
            "total_keywords": (
                len(self._exact_keywords)
                + len(self._regex_patterns)
                + len(self._fuzzy_keywords)
            ),
            "exact_keywords": len(self._exact_keywords),
            "regex_patterns": len(self._regex_patterns),
            "fuzzy_keywords": len(self._fuzzy_keywords),
            "categories": {
                cat.value: len(matches)
                for cat, matches in self._category_keywords.items()
            },
        }

        if self.analytics:
            stats["analytics"] = self.analytics.get_session_stats()
            stats["cost_summary"] = self.analytics.get_cost_summary()

        return stats

    def export_keywords(self) -> List[Dict[str, Any]]:
        """Export all keywords as a list."""
        keywords = []

        for match in self._exact_keywords.values():
            keywords.append(
                {
                    "keyword": match.keyword,
                    "response": match.response_text,
                    "category": match.category.value,
                    "match_type": "exact",
                    "priority": match.priority,
                    "metadata": match.metadata,
                }
            )

        for _, match in self._regex_patterns:
            keywords.append(
                {
                    "keyword": match.keyword,
                    "response": match.response_text,
                    "category": match.category.value,
                    "match_type": "regex",
                    "priority": match.priority,
                    "metadata": match.metadata,
                }
            )

        for match in self._fuzzy_keywords:
            keywords.append(
                {
                    "keyword": match.keyword,
                    "response": match.response_text,
                    "category": match.category.value,
                    "match_type": "fuzzy",
                    "priority": match.priority,
                    "metadata": match.metadata,
                }
            )

        return keywords

    def import_keywords(self, keywords: List[Dict[str, Any]]):
        """Import keywords from a list."""
        for kw_data in keywords:
            category_value = kw_data.get("category", "general")
            try:
                category = Category(category_value)
            except ValueError:
                category = Category.GENERAL

            self.add_keyword(
                keyword=kw_data["keyword"],
                response=kw_data["response"],
                category=category,
                match_type=kw_data.get("match_type", "exact"),
                priority=kw_data.get("priority", 0),
                metadata=kw_data.get("metadata", {}),
            )
