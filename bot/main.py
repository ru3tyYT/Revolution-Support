"""
Main entry point for the Discord Support Bot.
Uses AutoShardedBot for scalability with clustering support.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands

from ai.router import AIRouter

from .config import Config
from .shard_manager import ShardManager


# Configure logging
def setup_logging() -> logging.Logger:
    """Set up logging configuration."""
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "bot.log", encoding="utf-8"),
        ],
    )

    # Reduce noise from discord library
    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.WARNING)

    return logging.getLogger(__name__)


logger = setup_logging()


class SupportBot(commands.AutoShardedBot):
    """Main bot class with clustering support."""

    def __init__(self) -> None:
        """Initialize the bot with configuration."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(Config.COMMAND_PREFIX),
            intents=intents,
            case_insensitive=True,
            max_messages=10000,
            help_command=None,  # Custom help command can be added later
        )

        self.start_time: float = 0.0
        self.shard_manager: ShardManager | None = None
        self.ai_router = AIRouter()

    def initialize_ai_providers(self) -> None:
        """Initialize AI providers based on environment configuration."""
        providers_registered: list[str] = []

        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.ai_router.register_openai(openai_key)
            providers_registered.append("openai")

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.ai_router.register_anthropic(anthropic_key)
            providers_registered.append("anthropic")

        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self.ai_router.register_groq(groq_key)
            providers_registered.append("groq")

        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            self.ai_router.register_openrouter(openrouter_key)
            providers_registered.append("openrouter")

        ollama_cloud_key = os.getenv("OLLAMA_CLOUD_KEY")
        ollama_cloud_base_url = os.getenv("OLLAMA_CLOUD_BASE_URL")
        ollama_cloud_model = os.getenv("OLLAMA_CLOUD_MODEL")
        ollama_base_url = os.getenv("OLLAMA_BASE_URL")
        ollama_default_model = os.getenv("OLLAMA_MODEL")

        if ollama_cloud_key or ollama_cloud_base_url:
            self.ai_router.register_ollama(
                use_cloud=True,
                cloud_api_key=ollama_cloud_key,
                api_base=ollama_cloud_base_url,
                default_model=ollama_cloud_model or ollama_default_model,
            )
            providers_registered.append("ollama")
        elif ollama_base_url or ollama_default_model:
            self.ai_router.register_ollama(
                api_base=ollama_base_url,
                default_model=ollama_default_model,
            )
            providers_registered.append("ollama")

        if providers_registered:
            logger.info(
                "AI providers registered: %s",
                ", ".join(providers_registered),
            )
        else:
            logger.info("No AI providers registered; missing API keys")

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        logger.info("Setting up bot...")

        self.initialize_ai_providers()

        # Initialize shard manager if clustering is enabled
        if Config.CLUSTER_ENABLED:
            self.shard_manager = ShardManager(self)
            await self.shard_manager.initialize()

        # Load cogs/extensions here
        await self.load_extensions()

    async def load_extensions(self) -> None:
        """Load all bot extensions/cogs."""
        extensions = [
            "bot.cogs.research",
            "bot.cogs.knowledge",
            "bot.cogs.forums",
            "bot.cogs.forum_commands",
        ]

        for extension in extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")

        logger.info("Extensions loaded")

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        import time

        self.start_time = time.time()

        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Serving {len(set(self.get_all_members()))} members")
        logger.info(f"Shard count: {self.shard_count}")

        if self.shard_ids:
            logger.info(f"Shard IDs in this cluster: {self.shard_ids}")

        # Set bot presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{Config.COMMAND_PREFIX}help | {len(self.guilds)} servers",
            )
        )

    async def on_shard_ready(self, shard_id: int) -> None:
        """Called when a shard becomes ready."""
        logger.info(f"Shard {shard_id} is ready")

    async def on_shard_connect(self, shard_id: int) -> None:
        """Called when a shard connects."""
        logger.info(f"Shard {shard_id} connected")

    async def on_shard_disconnect(self, shard_id: int) -> None:
        """Called when a shard disconnects."""
        logger.warning(f"Shard {shard_id} disconnected")

    async def on_resumed(self) -> None:
        """Called when the bot resumes connection."""
        logger.info("Session resumed")

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Handle errors in event methods."""
        logger.exception(f"Error in {event_method}: ", exc_info=True)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.", delete_after=10)
            return

        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I don't have permission to do that.", delete_after=10)
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}", delete_after=10)
            return

        # Log unknown errors
        logger.exception(f"Command error in {ctx.command}: ", exc_info=error)

        if Config.DEBUG:
            await ctx.send(f"An error occurred: ```{error}```", delete_after=30)
        else:
            await ctx.send(
                "An error occurred while processing your command. Please try again later.",
                delete_after=10,
            )


def main() -> int:
    """Main entry point."""
    try:
        # Validate configuration
        Config.validate()

        logger.info("Starting Discord Support Bot...")
        logger.info(f"Version: 1.0.0")
        logger.info(f"Python: {sys.version}")
        logger.info(f"Discord.py: {discord.__version__}")

        bot = SupportBot()

        # Run the bot
        bot.run(Config.DISCORD_TOKEN, log_handler=None)

        return 0

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        return 0

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
