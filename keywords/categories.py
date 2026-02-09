"""Category management for Discord support bot."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import discord


class Category(Enum):
    """Predefined support categories."""

    GENERAL = "general"
    FAQ = "faq"
    TECHNICAL = "technical"
    BILLING = "billing"
    SUPPORT = "support"
    TROUBLESHOOTING = "troubleshooting"


@dataclass
class CategoryConfig:
    """Configuration for a category."""

    name: str
    color: discord.Color
    priority: int
    description: str
    emoji: str = ""
    max_embeds: int = 5


class CategoryManager:
    """Manages categories and their configurations."""

    # Color mapping for embeds
    CATEGORY_COLORS: Dict[Category, discord.Color] = {
        Category.GENERAL: discord.Color.blue(),
        Category.FAQ: discord.Color.green(),
        Category.TECHNICAL: discord.Color.purple(),
        Category.BILLING: discord.Color.gold(),
        Category.SUPPORT: discord.Color.red(),
        Category.TROUBLESHOOTING: discord.Color.orange(),
    }

    # Priority ordering (lower = higher priority)
    CATEGORY_PRIORITIES: Dict[Category, int] = {
        Category.FAQ: 1,
        Category.BILLING: 2,
        Category.TECHNICAL: 3,
        Category.TROUBLESHOOTING: 4,
        Category.SUPPORT: 5,
        Category.GENERAL: 6,
    }

    # Category descriptions
    CATEGORY_DESCRIPTIONS: Dict[Category, str] = {
        Category.GENERAL: "General questions and information",
        Category.FAQ: "Frequently asked questions",
        Category.TECHNICAL: "Technical issues and configuration",
        Category.BILLING: "Billing and subscription questions",
        Category.SUPPORT: "Support requests and help",
        Category.TROUBLESHOOTING: "Problem diagnosis and solutions",
    }

    # Category emojis
    CATEGORY_EMOJIS: Dict[Category, str] = {
        Category.GENERAL: "💬",
        Category.FAQ: "❓",
        Category.TECHNICAL: "⚙️",
        Category.BILLING: "💳",
        Category.SUPPORT: "🆘",
        Category.TROUBLESHOOTING: "🔧",
    }

    def __init__(self):
        self._categories: Dict[Category, CategoryConfig] = {}
        self._custom_categories: Dict[str, CategoryConfig] = {}
        self._stats: Dict[Category, Dict[str, Any]] = {
            cat: {"matches": 0, "embeds_sent": 0, "last_match": None}
            for cat in Category
        }
        self._init_default_categories()

    def _init_default_categories(self):
        """Initialize default categories."""
        for category in Category:
            self._categories[category] = CategoryConfig(
                name=category.value.title(),
                color=self.CATEGORY_COLORS[category],
                priority=self.CATEGORY_PRIORITIES[category],
                description=self.CATEGORY_DESCRIPTIONS[category],
                emoji=self.CATEGORY_EMOJIS[category],
            )

    def get_config(self, category: Category) -> CategoryConfig:
        """Get configuration for a category."""
        return self._categories.get(category, self._get_default_config(category))

    def _get_default_config(self, category: Category) -> CategoryConfig:
        """Get default config for unknown category."""
        return CategoryConfig(
            name=category.value.title(),
            color=discord.Color.default(),
            priority=99,
            description="",
            emoji="📋",
        )

    def get_color(self, category: Category) -> discord.Color:
        """Get the color for a category."""
        return self.get_config(category).color

    def get_priority(self, category: Category) -> int:
        """Get the priority for a category (lower = higher priority)."""
        return self.get_config(category).priority

    def sort_by_priority(self, categories: List[Category]) -> List[Category]:
        """Sort categories by priority."""
        return sorted(categories, key=lambda c: self.get_priority(c))

    def get_all_categories(self) -> List[Category]:
        """Get all predefined categories."""
        return list(Category)

    def update_stats(self, category: Category, embeds_sent: int = 1):
        """Update category statistics."""
        from datetime import datetime

        self._stats[category]["matches"] += 1
        self._stats[category]["embeds_sent"] += embeds_sent
        self._stats[category]["last_match"] = datetime.now().isoformat()

    def get_stats(self, category: Optional[Category] = None) -> Dict[str, Any]:
        """Get statistics for a category or all categories."""
        if category:
            return self._stats.get(category, {}).copy()
        return {cat.value: stats.copy() for cat, stats in self._stats.items()}

    def create_embed_header(self, category: Category) -> discord.Embed:
        """Create a header embed for a category."""
        config = self.get_config(category)
        embed = discord.Embed(
            title=f"{config.emoji} {config.name}",
            description=config.description,
            color=config.color,
        )
        return embed

    def add_custom_category(
        self,
        name: str,
        color: discord.Color,
        priority: int = 99,
        description: str = "",
        emoji: str = "📋",
    ) -> CategoryConfig:
        """Add a custom category."""
        config = CategoryConfig(
            name=name,
            color=color,
            priority=priority,
            description=description,
            emoji=emoji,
        )
        self._custom_categories[name.lower()] = config
        return config

    def get_custom_category(self, name: str) -> Optional[CategoryConfig]:
        """Get a custom category by name."""
        return self._custom_categories.get(name.lower())
