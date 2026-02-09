"""
Discord Embed Builder Utility

Comprehensive embed builder for Discord bot responses.
All bot responses use embeds (never plain text).
"""

import discord
from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from enum import IntEnum


class EmbedColors(IntEnum):
    """Predefined colors for different response types."""

    PRIMARY = 0x5865F2  # Discord blurple
    SUCCESS = 0x57F287  # Green
    WARNING = 0xFEE75C  # Yellow
    ERROR = 0xED4245  # Red
    INFO = 0xEB459E  # Pink/magenta
    AI = 0x00D4AA  # Teal for AI responses
    KEYWORD = 0x3498DB  # Blue for keyword triggers
    STATS = 0x9B59B6  # Purple for statistics
    RESEARCH = 0x1ABC9C  # Cyan for research
    SETTINGS = 0x95A5A6  # Gray for settings


class EmbedBuilder:
    """Static methods for building Discord embeds."""

    # Embed limits
    MAX_TITLE_LENGTH = 256
    MAX_DESCRIPTION_LENGTH = 4096
    MAX_FIELD_NAME_LENGTH = 256
    MAX_FIELD_VALUE_LENGTH = 1024
    MAX_FIELDS = 25
    MAX_FOOTER_LENGTH = 2048
    MAX_AUTHOR_NAME_LENGTH = 256

    @staticmethod
    def _truncate(text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to fit within embed limits."""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    def _create_base_embed(
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: int = EmbedColors.PRIMARY,
        url: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> discord.Embed:
        """Create a base embed with common settings."""
        embed = discord.Embed(
            title=EmbedBuilder._truncate(title, EmbedBuilder.MAX_TITLE_LENGTH)
            if title
            else None,
            description=EmbedBuilder._truncate(
                description, EmbedBuilder.MAX_DESCRIPTION_LENGTH
            )
            if description
            else None,
            color=color,
            url=url,
            timestamp=timestamp or datetime.utcnow(),
        )
        return embed

    @staticmethod
    def _add_field_safely(
        embed: discord.Embed, name: str, value: str, inline: bool = False
    ) -> None:
        """Add a field to embed, respecting limits."""
        if len(embed.fields) >= EmbedBuilder.MAX_FIELDS:
            return

        safe_name = EmbedBuilder._truncate(name, EmbedBuilder.MAX_FIELD_NAME_LENGTH)
        safe_value = EmbedBuilder._truncate(value, EmbedBuilder.MAX_FIELD_VALUE_LENGTH)

        embed.add_field(name=safe_name, value=safe_value, inline=inline)

    @staticmethod
    def ai_response(
        response_text: str,
        model: str,
        cost: Optional[float] = None,
        tokens_used: Optional[int] = None,
        response_time: Optional[float] = None,
        title: str = "Support Response",
    ) -> discord.Embed:
        """
        Create an embed for AI-generated responses.

        Args:
            response_text: The AI response content
            model: Name of the AI model used
            cost: Cost of the API call (optional)
            tokens_used: Number of tokens used (optional)
            response_time: Response generation time in seconds (optional)
            title: Embed title
        """
        embed = EmbedBuilder._create_base_embed(title=title, color=EmbedColors.AI)

        # Add response text as main content
        embed.description = EmbedBuilder._truncate(
            response_text, EmbedBuilder.MAX_DESCRIPTION_LENGTH
        )

        # Add model info field
        model_info = f"**Model:** {model}"
        if response_time:
            model_info += f"\n**Time:** {response_time:.2f}s"
        if tokens_used:
            model_info += f"\n**Tokens:** {tokens_used:,}"

        EmbedBuilder._add_field_safely(
            embed, name="AI Details", value=model_info, inline=True
        )

        # Add cost info if provided
        if cost is not None:
            EmbedBuilder._add_field_safely(
                embed, name="Cost", value=f"${cost:.6f}", inline=True
            )

        embed.set_footer(text="Powered by AI")
        return embed

    @staticmethod
    def keyword_response(
        keyword: str,
        responses: Union[str, List[str]],
        category: Optional[str] = None,
        confidence: Optional[float] = None,
        title: str = "Keyword Match",
    ) -> discord.Embed:
        """
        Create an embed for keyword trigger responses.

        Args:
            keyword: The matched keyword
            responses: Response text or list of responses
            category: Keyword category (optional)
            confidence: Match confidence score (optional)
            title: Embed title
        """
        embed = EmbedBuilder._create_base_embed(title=title, color=EmbedColors.KEYWORD)

        # Handle multiple responses
        if isinstance(responses, list):
            if len(responses) == 1:
                embed.description = EmbedBuilder._truncate(
                    responses[0], EmbedBuilder.MAX_DESCRIPTION_LENGTH
                )
            else:
                embed.description = (
                    f"Found {len(responses)} responses for keyword **{keyword}**:"
                )
                for i, response in enumerate(responses[:10], 1):  # Limit to 10
                    EmbedBuilder._add_field_safely(
                        embed, name=f"Response {i}", value=response, inline=False
                    )
        else:
            embed.description = EmbedBuilder._truncate(
                responses, EmbedBuilder.MAX_DESCRIPTION_LENGTH
            )

        # Add keyword details
        keyword_info = f"**Keyword:** {keyword}"
        if category:
            keyword_info += f"\n**Category:** {category}"
        if confidence:
            keyword_info += f"\n**Confidence:** {confidence:.1%}"

        EmbedBuilder._add_field_safely(
            embed, name="Match Details", value=keyword_info, inline=True
        )

        embed.set_footer(text="Auto-response triggered")
        return embed

    @staticmethod
    def error_embed(
        error_message: str,
        error_code: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        title: str = "Error",
    ) -> discord.Embed:
        """
        Create an error embed.

        Args:
            error_message: Description of the error
            error_code: Error code or identifier
            suggestions: List of suggestions to fix the error
            title: Embed title
        """
        embed = EmbedBuilder._create_base_embed(
            title=f"❌ {title}",
            description=EmbedBuilder._truncate(
                error_message, EmbedBuilder.MAX_DESCRIPTION_LENGTH
            ),
            color=EmbedColors.ERROR,
        )

        if error_code:
            EmbedBuilder._add_field_safely(
                embed, name="Error Code", value=f"`{error_code}`", inline=True
            )

        if suggestions:
            suggestions_text = "\n".join(f"• {s}" for s in suggestions)
            EmbedBuilder._add_field_safely(
                embed, name="Suggestions", value=suggestions_text, inline=False
            )

        embed.set_footer(text="Please try again or contact support")
        return embed

    @staticmethod
    def stats_embed(
        guild_stats: Dict[str, Any],
        global_stats: Optional[Dict[str, Any]] = None,
        title: str = "Bot Statistics",
    ) -> discord.Embed:
        """
        Create a statistics display embed.

        Args:
            guild_stats: Statistics for current guild
            global_stats: Global bot statistics (optional)
            title: Embed title
        """
        embed = EmbedBuilder._create_base_embed(
            title=f"📊 {title}", color=EmbedColors.STATS
        )

        # Guild stats
        guild_fields = []
        if "messages_processed" in guild_stats:
            guild_fields.append(f"Messages: {guild_stats['messages_processed']:,}")
        if "ai_responses" in guild_stats:
            guild_fields.append(f"AI Responses: {guild_stats['ai_responses']:,}")
        if "keyword_triggers" in guild_stats:
            guild_fields.append(f"Keywords: {guild_stats['keyword_triggers']:,}")
        if "unique_users" in guild_stats:
            guild_fields.append(f"Active Users: {guild_stats['unique_users']:,}")

        if guild_fields:
            EmbedBuilder._add_field_safely(
                embed, name="📍 This Server", value="\n".join(guild_fields), inline=True
            )

        # Global stats
        if global_stats:
            global_fields = []
            if "total_guilds" in global_stats:
                global_fields.append(f"Servers: {global_stats['total_guilds']:,}")
            if "total_messages" in global_stats:
                global_fields.append(f"Messages: {global_stats['total_messages']:,}")
            if "total_ai_calls" in global_stats:
                global_fields.append(f"AI Calls: {global_stats['total_ai_calls']:,}")
            if "uptime" in global_stats:
                global_fields.append(f"Uptime: {global_stats['uptime']}")

            if global_fields:
                EmbedBuilder._add_field_safely(
                    embed, name="🌍 Global", value="\n".join(global_fields), inline=True
                )

        embed.set_footer(text="Stats are updated in real-time")
        return embed

    @staticmethod
    def info_embed(
        title: str,
        description: str,
        fields: Optional[List[Dict[str, Any]]] = None,
        thumbnail_url: Optional[str] = None,
        image_url: Optional[str] = None,
        color: int = EmbedColors.INFO,
    ) -> discord.Embed:
        """
        Create a general information embed.

        Args:
            title: Embed title
            description: Main description
            fields: List of field dicts with 'name', 'value', 'inline' keys
            thumbnail_url: URL for thumbnail image
            image_url: URL for main image
            color: Embed color
        """
        embed = EmbedBuilder._create_base_embed(
            title=title,
            description=EmbedBuilder._truncate(
                description, EmbedBuilder.MAX_DESCRIPTION_LENGTH
            ),
            color=color,
        )

        if fields:
            for field in fields:
                EmbedBuilder._add_field_safely(
                    embed,
                    name=field.get("name", "\u200b"),
                    value=field.get("value", "\u200b"),
                    inline=field.get("inline", False),
                )

        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        if image_url:
            embed.set_image(url=image_url)

        return embed

    @staticmethod
    def research_embed(
        query: str,
        results: List[Dict[str, Any]],
        total_results: Optional[int] = None,
        search_time: Optional[float] = None,
        sources: Optional[List[str]] = None,
    ) -> discord.Embed:
        """
        Create a research results embed.

        Args:
            query: The research query
            results: List of result dicts with 'title', 'content', 'source', 'url'
            total_results: Total number of results found
            search_time: Search execution time in seconds
            sources: List of sources searched
        """
        embed = EmbedBuilder._create_base_embed(
            title="🔍 Research Results",
            description=f"**Query:** {query}",
            color=EmbedColors.RESEARCH,
        )

        # Add metadata
        metadata = []
        if total_results:
            metadata.append(f"Results: {total_results}")
        if search_time:
            metadata.append(f"Search time: {search_time:.2f}s")

        if metadata:
            embed.description += f"\n*{' | '.join(metadata)}*"

        # Add results
        for i, result in enumerate(results[:5], 1):  # Limit to 5 results
            title = result.get("title", f"Result {i}")
            content = EmbedBuilder._truncate(result.get("content", "No content"), 500)
            source = result.get("source", "Unknown")
            url = result.get("url", "")

            field_value = content
            if url:
                field_value += f"\n[Read more]({url})"
            field_value += f"\n*Source: {source}*"

            EmbedBuilder._add_field_safely(
                embed, name=f"{i}. {title}", value=field_value, inline=False
            )

        # Add sources footer
        if sources:
            sources_text = " | ".join(sources[:5])  # Limit sources
            embed.set_footer(text=f"Sources: {sources_text}")

        return embed

    @staticmethod
    def help_embed(
        commands: Dict[str, Any],
        prefix: str = "/",
        title: str = "Bot Help",
        description: Optional[str] = None,
        categories: Optional[Dict[str, str]] = None,
    ) -> discord.Embed:
        """
        Create a command help embed.

        Args:
            commands: Dict of command info with 'description', 'usage', 'examples'
            prefix: Command prefix
            title: Embed title
            description: Custom description
            categories: Dict mapping command names to category names
        """
        if description is None:
            description = (
                f"Use `{prefix}command` or slash commands to interact with the bot."
            )

        embed = EmbedBuilder._create_base_embed(
            title=f"📖 {title}", description=description, color=EmbedColors.INFO
        )

        # Group commands by category
        if categories:
            grouped = {}
            for cmd_name, cmd_info in commands.items():
                category = categories.get(cmd_name, "General")
                if category not in grouped:
                    grouped[category] = []
                grouped[category].append((cmd_name, cmd_info))

            for category, cmds in grouped.items():
                field_value = ""
                for cmd_name, cmd_info in cmds:
                    desc = cmd_info.get("description", "No description")
                    field_value += f"\n`{prefix}{cmd_name}` - {desc}"

                EmbedBuilder._add_field_safely(
                    embed, name=category, value=field_value, inline=False
                )
        else:
            # Add all commands in one field
            field_value = ""
            for cmd_name, cmd_info in commands.items():
                desc = cmd_info.get("description", "No description")
                usage = cmd_info.get("usage", "")
                if usage:
                    field_value += f"\n`{prefix}{cmd_name} {usage}` - {desc}"
                else:
                    field_value += f"\n`{prefix}{cmd_name}` - {desc}"

            EmbedBuilder._add_field_safely(
                embed, name="Available Commands", value=field_value, inline=False
            )

        embed.set_footer(text="For detailed help on a command, use /help <command>")
        return embed

    @staticmethod
    def settings_embed(
        settings: Dict[str, Any], guild_name: str, editable: bool = True
    ) -> discord.Embed:
        """
        Create a settings display embed.

        Args:
            settings: Dict of setting categories and their values
            guild_name: Name of the guild
            editable: Whether settings can be edited
        """
        embed = EmbedBuilder._create_base_embed(
            title="⚙️ Bot Settings",
            description=f"Settings for **{guild_name}**",
            color=EmbedColors.SETTINGS,
        )

        for category, values in settings.items():
            field_lines = []

            if isinstance(values, dict):
                for key, value in values.items():
                    # Format value based on type
                    if isinstance(value, bool):
                        formatted = "✅ Enabled" if value else "❌ Disabled"
                    elif isinstance(value, list):
                        if value:
                            formatted = ", ".join(str(v) for v in value[:5])
                            if len(value) > 5:
                                formatted += f" (+{len(value) - 5} more)"
                        else:
                            formatted = "None"
                    elif isinstance(value, str):
                        formatted = value if value else "Not set"
                    else:
                        formatted = str(value)

                    field_lines.append(f"**{key}:** {formatted}")
            else:
                field_lines.append(str(values))

            field_value = "\n".join(field_lines) if field_lines else "No settings"

            EmbedBuilder._add_field_safely(
                embed, name=category, value=field_value, inline=False
            )

        if editable:
            embed.set_footer(text="Use /settings to modify these values")
        else:
            embed.set_footer(text="Settings are read-only")

        return embed

    @staticmethod
    def success_embed(message: str, title: str = "Success") -> discord.Embed:
        """Create a simple success embed."""
        return EmbedBuilder._create_base_embed(
            title=f"✅ {title}", description=message, color=EmbedColors.SUCCESS
        )

    @staticmethod
    def warning_embed(message: str, title: str = "Warning") -> discord.Embed:
        """Create a warning embed."""
        return EmbedBuilder._create_base_embed(
            title=f"⚠️ {title}", description=message, color=EmbedColors.WARNING
        )

    @staticmethod
    def loading_embed(message: str = "Processing your request...") -> discord.Embed:
        """Create a loading/processing embed."""
        return EmbedBuilder._create_base_embed(
            title="⏳ Please Wait", description=message, color=EmbedColors.PRIMARY
        )


def get_embed_color(color_name: str) -> int:
    """
    Get embed color by name.

    Args:
        color_name: Name of the color

    Returns:
        Integer color value
    """
    color_map = {
        "primary": EmbedColors.PRIMARY,
        "success": EmbedColors.SUCCESS,
        "warning": EmbedColors.WARNING,
        "error": EmbedColors.ERROR,
        "info": EmbedColors.INFO,
        "ai": EmbedColors.AI,
        "keyword": EmbedColors.KEYWORD,
        "stats": EmbedColors.STATS,
        "research": EmbedColors.RESEARCH,
        "settings": EmbedColors.SETTINGS,
    }
    return color_map.get(color_name.lower(), EmbedColors.PRIMARY)
