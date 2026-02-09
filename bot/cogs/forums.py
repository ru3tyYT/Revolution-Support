"""Forum monitoring cog for Discord support bot.

This cog monitors forum channels and threads, providing AI-powered
responses and keyword matching for support queries.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass

import discord
from discord.ext import commands
from database.connection import get_db_context
from database.models import Base, TimestampMixin, Guild, QueryAnalytics, ForumConfig, ForumThread
from keywords.engine import KeywordEngine
from ai.router import AIRouter, ChatCompletionRequest, ChatMessage, RoutingStrategy
from bot.embed_builder import EmbedBuilder, EmbedColors
from cache.redis_client import get_redis_client, rate_limit
from monitoring.logging_config import get_logger, set_guild_context, LogContext

logger = get_logger(__name__)


@dataclass
class ThreadContext:
    """Context for processing a forum thread."""

    thread: discord.Thread
    forum_config: ForumConfig
    guild: Guild
    initial_message: Optional[discord.Message] = None


class Forums(commands.Cog):
    """Forum monitoring and auto-response cog."""

    def __init__(
        self,
        bot: commands.Bot,
        keyword_engine: Optional[KeywordEngine] = None,
        ai_router: Optional[AIRouter] = None,
    ):
        self.bot = bot
        self.keyword_engine = keyword_engine or KeywordEngine()
        self.ai_router = ai_router
        self.redis = get_redis_client()

        # Thread tracking cache (thread_id -> ForumThread)
        self._thread_cache: Dict[str, ForumThread] = {}

        # Rate limiting settings
        self.rate_limit_key_prefix = "forum_response"
        self.rate_limit_max = 10
        self.rate_limit_window = 60

        logger.info("Forums initialized")

    async def cog_load(self):
        """Called when the cog is loaded."""
        logger.info("Forums loaded")

    async def cog_unload(self):
        """Called when the cog is unloaded."""
        logger.info("Forums unloaded")

    # =========================================================================
    # Event Listeners
    # =========================================================================

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        """Handle new forum thread creation.

        Args:
            thread: The newly created thread.
        """
        with LogContext(guild=thread.guild.id if thread.guild else None):
            logger.info(f"Thread created: {thread.name} (ID: {thread.id})")

            try:
                # Check if this is a forum thread
                if not isinstance(thread.parent, discord.ForumChannel):
                    return

                # Get forum configuration
                forum_config = await self._get_forum_config(thread.guild.id, thread.parent.id)
                if not forum_config or not forum_config.is_active:
                    logger.debug(f"Forum not configured or inactive: {thread.parent.id}")
                    return

                # Check if thread should be monitored
                if not self.should_monitor_thread(forum_config, thread):
                    logger.debug(f"Thread excluded by tags: {thread.name}")
                    return

                # Fetch initial message
                initial_message = None
                async for message in thread.history(limit=1, oldest_first=True):
                    initial_message = message
                    break

                if not initial_message:
                    logger.warning(f"No initial message found in thread: {thread.name}")
                    return

                # Track thread in database
                db_thread = await self._track_thread(forum_config, thread, initial_message)

                # Send welcome response if enabled
                if forum_config.auto_respond:
                    await self.send_welcome_response(thread, forum_config, db_thread)

                # Update guild stats
                await self._update_forum_stats(forum_config)

            except Exception as e:
                logger.exception(f"Error handling thread creation: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle messages in forum threads.

        Args:
            message: The message that was sent.
        """
        # Ignore bot messages
        if message.author.bot:
            return

        # Only process messages in threads
        if not isinstance(message.channel, discord.Thread):
            return

        thread = message.channel

        # Only process forum threads
        if not isinstance(thread.parent, discord.ForumChannel):
            return

        with LogContext(guild=message.guild.id if message.guild else None, user=message.author.id):
            try:
                await self.process_forum_message(message)
            except Exception as e:
                logger.exception(f"Error processing forum message: {e}")

    # =========================================================================
    # Core Functionality
    # =========================================================================

    def should_monitor_thread(self, forum_config: ForumConfig, thread: discord.Thread) -> bool:
        """Check if a thread should be monitored based on configuration.

        Args:
            forum_config: The forum configuration.
            thread: The Discord thread.

        Returns:
            True if the thread should be monitored.
        """
        # Get thread tags
        thread_tags = []
        if hasattr(thread, "applied_tags") and thread.applied_tags:
            thread_tags = [tag.name.lower() for tag in thread.applied_tags]

        # Check required tags
        if forum_config.require_tags and forum_config.include_tags:
            if not any(tag in thread_tags for tag in forum_config.include_tags):
                logger.debug(f"Thread missing required tags: {thread.name}")
                return False

        # Check excluded tags
        if forum_config.exclude_tags:
            if any(tag in thread_tags for tag in forum_config.exclude_tags):
                logger.debug(f"Thread has excluded tags: {thread.name}")
                return False

        # Check include tags (if specified and not requiring all)
        if forum_config.include_tags and not forum_config.require_tags:
            # Thread can pass with no tags or matching tags
            pass

        return True

    async def process_forum_message(self, message: discord.Message):
        """Process a message in a forum thread.

        Args:
            message: The message to process.
        """
        thread = message.channel

        # Get forum configuration
        forum_config = await self._get_forum_config(message.guild.id, thread.parent.id)
        if not forum_config or not forum_config.is_active:
            return

        # Get tracked thread
        db_thread = await self._get_tracked_thread(str(thread.id))
        if not db_thread:
            # Thread not tracked yet, create tracking
            db_thread = await self._track_thread(forum_config, thread, message)

        # Check response limits
        if db_thread.response_count >= forum_config.max_responses_per_thread:
            logger.debug(f"Thread response limit reached: {thread.name}")
            return

        # Update message count
        db_thread.total_messages += 1

        # Check rate limiting
        rate_key = f"{self.rate_limit_key_prefix}:{thread.id}"
        if self.redis:
            try:
                current = await self.redis.get(rate_key)
                if current and int(current) >= self.rate_limit_max:
                    logger.debug(f"Rate limit reached for thread: {thread.name}")
                    return
            except Exception as e:
                logger.warning(f"Rate limit check failed: {e}")

        # Process message content
        content = message.content
        if not content.strip():
            return

        response_embed = None
        response_type = None
        confidence = None

        # Try keyword matching first if enabled
        if forum_config.use_keywords_first:
            match_result = self.keyword_engine.process_message(content, include_intent=False)

            if match_result.matches:
                # Use keyword response
                best_match = match_result.matches[0]
                response_embed = EmbedBuilder.keyword_response(
                    keyword=best_match.keyword,
                    responses=best_match.response_text,
                    category=best_match.category.value
                    if hasattr(best_match.category, "value")
                    else str(best_match.category),
                    confidence=best_match.confidence,
                )
                response_type = "keyword_match"
                confidence = best_match.confidence
                logger.info(f"Keyword match found: {best_match.keyword}")

        # If no keyword match or keywords disabled, use AI
        if response_embed is None and self.ai_router and forum_config.auto_respond:
            try:
                response_embed = await self.get_ai_response(thread, message, forum_config)
                if response_embed:
                    response_type = "ai_response"
                    confidence = 0.85  # AI confidence estimate
                    logger.info(f"AI response generated for thread: {thread.name}")
            except Exception as e:
                logger.exception(f"Failed to generate AI response: {e}")

        # Send response if we have one
        if response_embed:
            try:
                await message.channel.send(embed=response_embed)

                # Update tracking
                db_thread.response_count += 1
                db_thread.last_response_at = datetime.utcnow()

                # Calculate first response time if first response
                if db_thread.response_count == 1 and db_thread.created_at:
                    first_response_ms = int(
                        (datetime.utcnow() - db_thread.created_at).total_seconds() * 1000
                    )
                    db_thread.first_response_time_ms = first_response_ms

                # Update rate limit counter
                if self.redis:
                    try:
                        count = await self.redis.incr(rate_key)
                        if count == 1:
                            await self.redis.expire(rate_key, self.rate_limit_window)
                    except Exception as e:
                        logger.warning(f"Rate limit increment failed: {e}")

                # Track analytics
                await self._track_analytics(
                    guild_id=str(message.guild.id),
                    query=content,
                    response_type=response_type,
                    confidence=confidence,
                    channel_id=str(thread.id),
                    user_id=str(message.author.id),
                )

                # Save thread updates
                with get_db_context() as db:
                    db.add(db_thread)
                    db.commit()

                logger.info(f"Response sent to thread: {thread.name}")

            except Exception as e:
                logger.exception(f"Failed to send response: {e}")

    async def get_ai_response(
        self,
        thread: discord.Thread,
        message: discord.Message,
        forum_config: ForumConfig,
    ) -> Optional[discord.Embed]:
        """Generate an AI response for a forum message.

        Args:
            thread: The forum thread.
            message: The message to respond to.
            forum_config: The forum configuration.

        Returns:
            Discord embed with AI response, or None if failed.
        """
        if not self.ai_router:
            logger.warning("AI router not configured")
            return None

        # Build context from thread history
        context_messages = []
        try:
            async for msg in thread.history(limit=10, oldest_first=True):
                if msg.author.bot:
                    continue
                role = "assistant" if msg.author.id == self.bot.user.id else "user"
                context_messages.append(ChatMessage(role=role, content=msg.content))
        except Exception as e:
            logger.warning(f"Failed to fetch thread history: {e}")

        # Add system prompt
        system_prompt = (
            "You are a helpful support assistant. Provide clear, concise answers "
            "to user questions. Be friendly and professional. If you don't know "
            "something, say so honestly."
        )

        messages = [
            ChatMessage(role="system", content=system_prompt),
            *context_messages,
        ]

        # If no context, just use current message
        if not context_messages:
            messages.append(ChatMessage(role="user", content=message.content))

        # Create request
        temperature = forum_config.ai_temperature / 10.0  # Convert 0-10 to 0-1
        request = ChatCompletionRequest(
            messages=messages,
            temperature=temperature,
            max_tokens=1000,
        )

        try:
            # Get AI response
            start_time = asyncio.get_event_loop().time()
            response = await self.ai_router.chat_completion(
                request,
                strategy=RoutingStrategy.BALANCED,
            )
            elapsed_time = asyncio.get_event_loop().time() - start_time

            # Build embed
            embed = EmbedBuilder.ai_response(
                response_text=response.content,
                model=response.model,
                cost=response.usage.cost if hasattr(response.usage, "cost") else None,
                tokens_used=response.usage.total_tokens,
                response_time=elapsed_time,
                title="Support Response",
            )

            return embed

        except Exception as e:
            logger.exception(f"AI response generation failed: {e}")
            return None

    async def send_welcome_response(
        self,
        thread: discord.Thread,
        forum_config: ForumConfig,
        db_thread: ForumThread,
    ):
        """Send initial welcome/help message to a new thread.

        Args:
            thread: The Discord thread.
            forum_config: The forum configuration.
            db_thread: The tracked thread database model.
        """
        # Check if we should send welcome message
        if not forum_config.auto_respond:
            return

        # Check rate limiting for welcome messages
        rate_key = f"{self.rate_limit_key_prefix}:welcome:{thread.id}"
        if self.redis:
            try:
                current = await self.redis.get(rate_key)
                if current:
                    logger.debug(f"Welcome message already sent for thread: {thread.name}")
                    return
            except Exception as e:
                logger.warning(f"Welcome rate limit check failed: {e}")

        # Build welcome message
        if forum_config.welcome_message_template:
            welcome_text = forum_config.welcome_message_template
        else:
            welcome_text = (
                f"Hello! I've noticed your post in **{thread.parent.name}**. "
                "I'll do my best to help you with your question. "
                "Feel free to provide more details if needed!"
            )

        # Try AI welcome if configured
        if self.ai_router and db_thread.initial_message_id:
            try:
                # Fetch initial message for context
                initial_message = None
                async for msg in thread.history(limit=1, oldest_first=True):
                    initial_message = msg
                    break

                if initial_message:
                    ai_embed = await self.get_ai_response(thread, initial_message, forum_config)
                    if ai_embed:
                        await thread.send(embed=ai_embed)

                        # Update tracking
                        db_thread.response_count += 1
                        db_thread.last_response_at = datetime.utcnow()

                        # Mark welcome sent
                        if self.redis:
                            await self.redis.set(rate_key, "1", expire=3600)

                        logger.info(f"AI welcome sent to thread: {thread.name}")
                        return
            except Exception as e:
                logger.warning(f"Failed to generate AI welcome: {e}")

        # Send standard welcome
        embed = EmbedBuilder.info_embed(
            title="Welcome to Support",
            description=welcome_text,
            color=EmbedColors.INFO,
        )

        try:
            await thread.send(embed=embed)

            # Update tracking
            db_thread.response_count += 1
            db_thread.last_response_at = datetime.utcnow()

            # Mark welcome sent
            if self.redis:
                await self.redis.set(rate_key, "1", expire=3600)

            logger.info(f"Welcome sent to thread: {thread.name}")

        except Exception as e:
            logger.exception(f"Failed to send welcome message: {e}")

    # =========================================================================
    # Database Operations
    # =========================================================================

    async def _get_forum_config(
        self, guild_id: int, forum_channel_id: int
    ) -> Optional[ForumConfig]:
        """Get forum configuration from database.

        Args:
            guild_id: The Discord guild ID.
            forum_channel_id: The forum channel ID.

        Returns:
            ForumConfig or None if not found.
        """
        try:
            with get_db_context() as db:
                # Get guild first
                guild = db.query(Guild).filter(Guild.discord_id == str(guild_id)).first()
                if not guild:
                    return None

                # Get forum config
                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild.id,
                        ForumConfig.forum_channel_id == str(forum_channel_id),
                    )
                    .first()
                )

                return config
        except Exception as e:
            logger.exception(f"Failed to get forum config: {e}")
            return None

    async def _get_tracked_thread(self, thread_id: str) -> Optional[ForumThread]:
        """Get tracked thread from cache or database.

        Args:
            thread_id: The Discord thread ID.

        Returns:
            ForumThread or None if not found.
        """
        # Check cache first
        if thread_id in self._thread_cache:
            return self._thread_cache[thread_id]

        try:
            with get_db_context() as db:
                thread = db.query(ForumThread).filter(ForumThread.thread_id == thread_id).first()

                if thread:
                    self._thread_cache[thread_id] = thread

                return thread
        except Exception as e:
            logger.exception(f"Failed to get tracked thread: {e}")
            return None

    async def _track_thread(
        self,
        forum_config: ForumConfig,
        thread: discord.Thread,
        initial_message: discord.Message,
    ) -> ForumThread:
        """Track a new forum thread in the database.

        Args:
            forum_config: The forum configuration.
            thread: The Discord thread.
            initial_message: The initial message in the thread.

        Returns:
            The created ForumThread model.
        """
        try:
            with get_db_context() as db:
                # Extract tags
                tags = []
                if hasattr(thread, "applied_tags") and thread.applied_tags:
                    tags = [tag.name for tag in thread.applied_tags]

                # Create thread record
                db_thread = ForumThread(
                    id=uuid.uuid4(),
                    forum_config_id=forum_config.id,
                    thread_id=str(thread.id),
                    guild_id=str(thread.guild.id),
                    channel_id=str(thread.parent_id),
                    owner_id=str(thread.owner_id),
                    title=thread.name,
                    initial_message_id=str(initial_message.id),
                    tags=tags,
                    total_messages=1,
                )

                db.add(db_thread)
                db.commit()
                db.refresh(db_thread)

                # Update cache
                self._thread_cache[str(thread.id)] = db_thread

                logger.info(f"Thread tracked: {thread.name} (ID: {thread.id})")

                return db_thread
        except Exception as e:
            logger.exception(f"Failed to track thread: {e}")
            raise

    async def _update_forum_stats(self, forum_config: ForumConfig):
        """Update forum statistics.

        Args:
            forum_config: The forum configuration to update.
        """
        try:
            with get_db_context() as db:
                forum_config.threads_created += 1
                db.add(forum_config)
                db.commit()
        except Exception as e:
            logger.exception(f"Failed to update forum stats: {e}")

    async def _track_analytics(
        self,
        guild_id: str,
        query: str,
        response_type: str,
        confidence: Optional[float],
        channel_id: str,
        user_id: str,
    ):
        """Track analytics for a response.

        Args:
            guild_id: The Discord guild ID.
            query: The user query.
            response_type: Type of response (keyword_match, ai_response, etc.)
            confidence: Confidence score.
            channel_id: The channel/thread ID.
            user_id: The user ID.
        """
        try:
            with get_db_context() as db:
                # Get guild
                guild = db.query(Guild).filter(Guild.discord_id == guild_id).first()
                if not guild:
                    return

                # Create analytics record
                analytics = QueryAnalytics(
                    id=uuid.uuid4(),
                    guild_id=guild.id,
                    query=query,
                    response=None,  # Not storing full response
                    response_type=response_type,
                    confidence_score=confidence,
                    channel_id=channel_id,
                    user_id=user_id,
                )

                db.add(analytics)
                db.commit()
        except Exception as e:
            logger.exception(f"Failed to track analytics: {e}")

    # =========================================================================
    # Commands
    # =========================================================================

    @commands.group(name="forum", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def forum_group(self, ctx: commands.Context):
        """Forum management commands."""
        embed = EmbedBuilder.info_embed(
            title="Forum Management",
            description="Use `!forum monitor <channel>` to monitor a forum channel.",
            fields=[
                {
                    "name": "Commands",
                    "value": "• `monitor <channel>` - Start monitoring\n• `unmonitor <channel>` - Stop monitoring\n• `stats` - Show forum stats",
                    "inline": False,
                },
            ],
            color=EmbedColors.INFO,
        )
        await ctx.send(embed=embed)

    @forum_group.command(name="monitor")
    @commands.has_permissions(manage_guild=True)
    async def forum_monitor(self, ctx: commands.Context, channel: discord.ForumChannel):
        """Start monitoring a forum channel.

        Args:
            ctx: The command context.
            channel: The forum channel to monitor.
        """
        try:
            with get_db_context() as db:
                # Get or create guild
                guild = db.query(Guild).filter(Guild.discord_id == str(ctx.guild.id)).first()
                if not guild:
                    guild = Guild(
                        id=uuid.uuid4(),
                        discord_id=str(ctx.guild.id),
                        name=ctx.guild.name,
                    )
                    db.add(guild)
                    db.flush()

                # Check if already monitoring
                existing = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if existing:
                    existing.is_active = True
                    db.add(existing)
                    db.commit()

                    embed = EmbedBuilder.success_embed(
                        f"Forum monitoring reactivated for **{channel.name}**"
                    )
                else:
                    # Create new config
                    config = ForumConfig(
                        id=uuid.uuid4(),
                        guild_id=guild.id,
                        forum_channel_id=str(channel.id),
                        is_active=True,
                        auto_respond=True,
                    )
                    db.add(config)
                    db.commit()

                    embed = EmbedBuilder.success_embed(
                        f"Now monitoring forum channel **{channel.name}**"
                    )

                await ctx.send(embed=embed)
                logger.info(f"Forum monitoring enabled for {channel.name} in {ctx.guild.name}")

        except Exception as e:
            logger.exception(f"Failed to enable forum monitoring: {e}")
            embed = EmbedBuilder.error_embed(
                f"Failed to enable monitoring: {str(e)}", title="Error"
            )
            await ctx.send(embed=embed)

    @forum_group.command(name="unmonitor")
    @commands.has_permissions(manage_guild=True)
    async def forum_unmonitor(self, ctx: commands.Context, channel: discord.ForumChannel):
        """Stop monitoring a forum channel.

        Args:
            ctx: The command context.
            channel: The forum channel to stop monitoring.
        """
        try:
            with get_db_context() as db:
                guild = db.query(Guild).filter(Guild.discord_id == str(ctx.guild.id)).first()
                if not guild:
                    await ctx.send(embed=EmbedBuilder.error_embed("Guild not configured"))
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if config:
                    config.is_active = False
                    db.add(config)
                    db.commit()

                    embed = EmbedBuilder.success_embed(
                        f"Stopped monitoring forum channel **{channel.name}**"
                    )
                else:
                    embed = EmbedBuilder.warning_embed(
                        f"Forum channel **{channel.name}** was not being monitored"
                    )

                await ctx.send(embed=embed)
                logger.info(f"Forum monitoring disabled for {channel.name} in {ctx.guild.name}")

        except Exception as e:
            logger.exception(f"Failed to disable forum monitoring: {e}")
            embed = EmbedBuilder.error_embed(
                f"Failed to disable monitoring: {str(e)}", title="Error"
            )
            await ctx.send(embed=embed)

    @forum_group.command(name="stats")
    @commands.has_permissions(manage_guild=True)
    async def forum_stats(self, ctx: commands.Context):
        """Show forum monitoring statistics.

        Args:
            ctx: The command context.
        """
        try:
            with get_db_context() as db:
                guild = db.query(Guild).filter(Guild.discord_id == str(ctx.guild.id)).first()
                if not guild:
                    await ctx.send(embed=EmbedBuilder.error_embed("Guild not configured"))
                    return

                configs = db.query(ForumConfig).filter(ForumConfig.guild_id == guild.id).all()

                if not configs:
                    await ctx.send(
                        embed=EmbedBuilder.info_embed(
                            title="Forum Statistics",
                            description="No forum channels are being monitored.",
                            color=EmbedColors.INFO,
                        )
                    )
                    return

                fields = []
                for config in configs:
                    channel = self.bot.get_channel(int(config.forum_channel_id))
                    channel_name = channel.name if channel else "Unknown"

                    field_value = (
                        f"**Status:** {'Active' if config.is_active else 'Inactive'}\n"
                        f"**Threads Created:** {config.threads_created:,}\n"
                        f"**Responses Sent:** {config.responses_sent:,}\n"
                        f"**Auto-Respond:** {'Enabled' if config.auto_respond else 'Disabled'}"
                    )

                    fields.append(
                        {
                            "name": f"📋 {channel_name}",
                            "value": field_value,
                            "inline": False,
                        }
                    )

                embed = EmbedBuilder.info_embed(
                    title="Forum Statistics",
                    description=f"Monitoring {len(configs)} forum channel(s)",
                    fields=fields,
                    color=EmbedColors.STATS,
                )

                await ctx.send(embed=embed)

        except Exception as e:
            logger.exception(f"Failed to get forum stats: {e}")
            embed = EmbedBuilder.error_embed(f"Failed to get statistics: {str(e)}", title="Error")
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(Forums(bot, ai_router=bot.ai_router))
