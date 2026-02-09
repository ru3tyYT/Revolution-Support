"""Forum configuration commands cog for the Discord support bot.

Provides commands to configure and manage forum channel monitoring,
including auto-responses, tag filtering, and statistics tracking.
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Optional, List

from ..embed_builder import EmbedBuilder, EmbedColors


class ForumCommands(commands.Cog):
    """Forum configuration and management commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    forum_group = app_commands.Group(name="forum", description="Configure forum channel monitoring")

    def _format_bool(self, value: bool) -> str:
        """Format boolean value with emoji."""
        return "✅ Yes" if value else "❌ No"

    def _format_tags(self, tags: List[str]) -> str:
        """Format tag list for display."""
        if not tags:
            return "None"
        return ", ".join(f"`{tag}`" for tag in tags[:10]) + (
            f" (+{len(tags) - 10} more)" if len(tags) > 10 else ""
        )

    def _success_embed(self, title: str, description: str) -> discord.Embed:
        """Create a success embed."""
        return EmbedBuilder._create_base_embed(
            title=f"✅ {title}",
            description=description,
            color=EmbedColors.SUCCESS,
        )

    def _error_embed(self, title: str, description: str) -> discord.Embed:
        """Create an error embed."""
        return EmbedBuilder._create_base_embed(
            title=f"❌ {title}",
            description=description,
            color=EmbedColors.ERROR,
        )

    def _info_embed(self, title: str, description: str) -> discord.Embed:
        """Create an info embed."""
        return EmbedBuilder._create_base_embed(
            title=f"ℹ️ {title}",
            description=description,
            color=EmbedColors.INFO,
        )

    @forum_group.command(name="setup", description="Configure a forum for monitoring")
    @app_commands.describe(
        channel="The forum channel to monitor",
        auto_respond="Enable automatic AI responses (default: True)",
        welcome_message="Custom welcome message for new threads",
        ai_model="AI model to use for responses (default: gpt-4)",
        response_delay="Delay in seconds before responding (default: 5)",
        max_responses="Maximum AI responses per thread (default: 3)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
        auto_respond: Optional[bool] = True,
        welcome_message: Optional[str] = None,
        ai_model: Optional[str] = "gpt-4",
        response_delay: Optional[app_commands.Range[int, 0, 300]] = 5,
        max_responses: Optional[app_commands.Range[int, 1, 50]] = 3,
    ):
        """Configure a forum channel for monitoring with AI responses."""
        try:
            # Check permissions
            bot_member = interaction.guild.me
            forum_perms = channel.permissions_for(bot_member)

            missing_perms = []
            if not forum_perms.view_channel:
                missing_perms.append("View Channel")
            if not forum_perms.send_messages:
                missing_perms.append("Send Messages")
            if not forum_perms.read_message_history:
                missing_perms.append("Read Message History")
            if not forum_perms.create_public_threads:
                missing_perms.append("Create Public Threads")

            if missing_perms:
                embed = self._error_embed(
                    "Missing Permissions",
                    f"I need the following permissions in {channel.mention}:\n"
                    + "\n".join(f"• {perm}" for perm in missing_perms),
                )
                embed.add_field(
                    name="How to Fix",
                    value="Update my role permissions or channel-specific permissions "
                    "to grant these permissions.",
                    inline=False,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Create or update ForumConfig
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                # Get or create guild record
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )

                if not guild_record:
                    guild_record = Guild(
                        discord_id=str(interaction.guild_id),
                        name=interaction.guild.name,
                    )
                    db.add(guild_record)
                    db.flush()

                # Check if config already exists
                existing_config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if existing_config:
                    # Update existing config
                    existing_config.is_active = True
                    existing_config.auto_respond = auto_respond
                    existing_config.welcome_message = welcome_message
                    existing_config.ai_model = ai_model
                    existing_config.response_delay_seconds = response_delay
                    existing_config.max_responses_per_thread = max_responses
                    existing_config.forum_name = channel.name

                    db.commit()

                    embed = self._success_embed(
                        "Forum Configuration Updated",
                        f"Configuration for {channel.mention} has been updated successfully.",
                    )
                else:
                    # Create new config
                    new_config = ForumConfig(
                        guild_id=guild_record.id,
                        forum_channel_id=str(channel.id),
                        forum_name=channel.name,
                        is_active=True,
                        auto_respond=auto_respond,
                        welcome_message=welcome_message,
                        ai_model=ai_model,
                        response_delay_seconds=response_delay,
                        max_responses_per_thread=max_responses,
                    )
                    db.add(new_config)
                    db.commit()

                    embed = self._success_embed(
                        "Forum Configuration Created",
                        f"{channel.mention} is now configured for monitoring.",
                    )

                # Add configuration summary
                EmbedBuilder._add_field_safely(
                    embed,
                    name="Configuration Summary",
                    value=f"**Channel:** {channel.mention}\n"
                    f"**Auto Respond:** {self._format_bool(auto_respond)}\n"
                    f"**AI Model:** `{ai_model}`\n"
                    f"**Response Delay:** `{response_delay}s`\n"
                    f"**Max Responses:** `{max_responses}`",
                    inline=False,
                )

                if welcome_message:
                    EmbedBuilder._add_field_safely(
                        embed,
                        name="Welcome Message",
                        value=f"```{welcome_message[:500]}{'...' if len(welcome_message) > 500 else ''}```",
                        inline=False,
                    )

                embed.set_footer(text=f"Configured by {interaction.user}")
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "Configuration Error", f"Failed to configure forum: {str(e)}"
                ),
                ephemeral=True,
            )

    edit_group = app_commands.Group(
        name="edit", description="Edit forum configuration", parent=forum_group
    )

    @edit_group.command(name="auto_respond", description="Enable or disable automatic AI responses")
    @app_commands.describe(channel="The forum channel", enabled="Enable automatic responses")
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_edit_auto_respond(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
        enabled: bool,
    ):
        """Toggle automatic AI responses for a forum."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if not config:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Not Found",
                            f"No configuration found for {channel.mention}. Use `/forum setup` first.",
                        ),
                        ephemeral=True,
                    )
                    return

                config.auto_respond = enabled
                db.commit()

                status = "enabled" if enabled else "disabled"
                embed = self._success_embed(
                    "Setting Updated",
                    f"Automatic AI responses have been **{status}** for {channel.mention}.",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to update setting: {str(e)}"),
                ephemeral=True,
            )

    @edit_group.command(
        name="welcome_message", description="Set the welcome message for new threads"
    )
    @app_commands.describe(
        channel="The forum channel", message="Welcome message (leave empty to remove)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_edit_welcome_message(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
        message: Optional[str] = None,
    ):
        """Set or remove the welcome message for new threads."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if not config:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Not Found",
                            f"No configuration found for {channel.mention}. Use `/forum setup` first.",
                        ),
                        ephemeral=True,
                    )
                    return

                config.welcome_message = message if message else None
                db.commit()

                if message:
                    embed = self._success_embed(
                        "Welcome Message Updated",
                        f"Welcome message for {channel.mention} has been updated.",
                    )
                    EmbedBuilder._add_field_safely(
                        embed,
                        name="Message",
                        value=f"```{message[:500]}{'...' if len(message) > 500 else ''}```",
                        inline=False,
                    )
                else:
                    embed = self._success_embed(
                        "Welcome Message Removed",
                        f"Welcome message for {channel.mention} has been removed.",
                    )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to update welcome message: {str(e)}"),
                ephemeral=True,
            )

    @edit_group.command(name="ai_model", description="Change the AI model for responses")
    @app_commands.describe(channel="The forum channel", model="AI model to use")
    @app_commands.choices(
        model=[
            app_commands.Choice(name="GPT-4", value="gpt-4"),
            app_commands.Choice(name="GPT-4 Turbo", value="gpt-4-turbo"),
            app_commands.Choice(name="GPT-3.5 Turbo", value="gpt-3.5-turbo"),
            app_commands.Choice(name="Claude 3 Opus", value="claude-3-opus"),
            app_commands.Choice(name="Claude 3 Sonnet", value="claude-3-sonnet"),
            app_commands.Choice(name="Claude 3 Haiku", value="claude-3-haiku"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_edit_ai_model(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
        model: app_commands.Choice[str],
    ):
        """Change the AI model used for forum responses."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if not config:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Not Found",
                            f"No configuration found for {channel.mention}. Use `/forum setup` first.",
                        ),
                        ephemeral=True,
                    )
                    return

                config.ai_model = model.value
                db.commit()

                embed = self._success_embed(
                    "AI Model Updated",
                    f"AI model for {channel.mention} changed to **{model.name}**.",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to update AI model: {str(e)}"),
                ephemeral=True,
            )

    @edit_group.command(name="response_delay", description="Set the response delay in seconds")
    @app_commands.describe(
        channel="The forum channel", seconds="Delay before responding (0-300 seconds)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_edit_response_delay(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
        seconds: app_commands.Range[int, 0, 300],
    ):
        """Set the delay before AI responds to new threads."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if not config:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Not Found",
                            f"No configuration found for {channel.mention}. Use `/forum setup` first.",
                        ),
                        ephemeral=True,
                    )
                    return

                config.response_delay_seconds = seconds
                db.commit()

                embed = self._success_embed(
                    "Response Delay Updated",
                    f"Response delay for {channel.mention} set to **{seconds} seconds**.",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to update response delay: {str(e)}"),
                ephemeral=True,
            )

    @edit_group.command(name="max_responses", description="Set the maximum AI responses per thread")
    @app_commands.describe(channel="The forum channel", count="Maximum responses (1-50)")
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_edit_max_responses(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
        count: app_commands.Range[int, 1, 50],
    ):
        """Set the maximum number of AI responses per thread."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if not config:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Not Found",
                            f"No configuration found for {channel.mention}. Use `/forum setup` first.",
                        ),
                        ephemeral=True,
                    )
                    return

                config.max_responses_per_thread = count
                db.commit()

                embed = self._success_embed(
                    "Max Responses Updated",
                    f"Maximum AI responses for {channel.mention} set to **{count}**.",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to update max responses: {str(e)}"),
                ephemeral=True,
            )

    @edit_group.command(name="include_tags", description="Set tags to monitor (comma-separated)")
    @app_commands.describe(
        channel="The forum channel",
        tags="Comma-separated list of tags to monitor (leave empty to monitor all)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_edit_include_tags(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
        tags: Optional[str] = None,
    ):
        """Set which tags to monitor. Leave empty to monitor all threads."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if not config:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Not Found",
                            f"No configuration found for {channel.mention}. Use `/forum setup` first.",
                        ),
                        ephemeral=True,
                    )
                    return

                if tags:
                    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                    config.tags_to_monitor = tag_list
                else:
                    config.tags_to_monitor = []

                db.commit()

                embed = self._success_embed(
                    "Include Tags Updated",
                    f"Tags to monitor for {channel.mention} have been updated.",
                )

                if config.tags_to_monitor:
                    EmbedBuilder._add_field_safely(
                        embed,
                        name="Monitored Tags",
                        value=self._format_tags(config.tags_to_monitor),
                        inline=False,
                    )
                else:
                    EmbedBuilder._add_field_safely(
                        embed, name="Monitored Tags", value="All tags (no filtering)", inline=False
                    )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to update tags: {str(e)}"),
                ephemeral=True,
            )

    @edit_group.command(name="exclude_tags", description="Set tags to exclude (comma-separated)")
    @app_commands.describe(
        channel="The forum channel", tags="Comma-separated list of tags to exclude"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_edit_exclude_tags(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
        tags: str,
    ):
        """Set which tags to exclude from monitoring."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if not config:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Not Found",
                            f"No configuration found for {channel.mention}. Use `/forum setup` first.",
                        ),
                        ephemeral=True,
                    )
                    return

                tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                config.exclude_tags = tag_list
                db.commit()

                embed = self._success_embed(
                    "Exclude Tags Updated",
                    f"Excluded tags for {channel.mention} have been updated.",
                )
                EmbedBuilder._add_field_safely(
                    embed,
                    name="Excluded Tags",
                    value=self._format_tags(config.exclude_tags) if config.exclude_tags else "None",
                    inline=False,
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to update exclude tags: {str(e)}"),
                ephemeral=True,
            )

    @forum_group.command(name="disable", description="Disable monitoring for a forum")
    @app_commands.describe(channel="The forum channel to disable")
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_disable(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
    ):
        """Disable monitoring for a forum channel (soft delete)."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if not config:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Not Found", f"No configuration found for {channel.mention}."
                        ),
                        ephemeral=True,
                    )
                    return

                if not config.is_active:
                    await interaction.response.send_message(
                        embed=self._info_embed(
                            "Already Disabled", f"{channel.mention} is already disabled."
                        ),
                        ephemeral=True,
                    )
                    return

                config.is_active = False
                db.commit()

                embed = EmbedBuilder._create_base_embed(
                    title="Forum Monitoring Disabled",
                    description=f"Monitoring for {channel.mention} has been disabled.",
                    color=EmbedColors.WARNING,
                )
                EmbedBuilder._add_field_safely(
                    embed,
                    name="What This Means",
                    value="• AI will no longer respond to new threads\n"
                    "• Existing threads are unaffected\n"
                    "• Configuration is preserved\n"
                    "• Use `/forum enable` to re-enable",
                    inline=False,
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to disable forum: {str(e)}"),
                ephemeral=True,
            )

    @forum_group.command(name="enable", description="Re-enable monitoring for a forum")
    @app_commands.describe(channel="The forum channel to enable")
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_enable(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
    ):
        """Re-enable monitoring for a previously disabled forum channel."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if not config:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Not Found",
                            f"No configuration found for {channel.mention}. Use `/forum setup` first.",
                        ),
                        ephemeral=True,
                    )
                    return

                if config.is_active:
                    await interaction.response.send_message(
                        embed=self._info_embed(
                            "Already Enabled", f"{channel.mention} is already enabled."
                        ),
                        ephemeral=True,
                    )
                    return

                # Verify permissions before re-enabling
                bot_member = interaction.guild.me
                forum_perms = channel.permissions_for(bot_member)

                missing_perms = []
                if not forum_perms.view_channel:
                    missing_perms.append("View Channel")
                if not forum_perms.send_messages:
                    missing_perms.append("Send Messages")

                if missing_perms:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Missing Permissions",
                            f"Cannot enable: I need the following permissions in {channel.mention}:\n"
                            + "\n".join(f"• {perm}" for perm in missing_perms),
                        ),
                        ephemeral=True,
                    )
                    return

                config.is_active = True
                config.forum_name = channel.name  # Update name in case it changed
                db.commit()

                embed = self._success_embed(
                    "Forum Monitoring Enabled",
                    f"Monitoring for {channel.mention} has been re-enabled.",
                )
                EmbedBuilder._add_field_safely(
                    embed,
                    name="Current Configuration",
                    value=f"**Auto Respond:** {self._format_bool(config.auto_respond)}\n"
                    f"**AI Model:** `{config.ai_model or 'Default'}`\n"
                    f"**Response Delay:** `{config.response_delay_seconds}s`\n"
                    f"**Max Responses:** `{config.max_responses_per_thread}`",
                    inline=False,
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to enable forum: {str(e)}"),
                ephemeral=True,
            )

    @forum_group.command(name="status", description="Show current forum configuration")
    @app_commands.describe(channel="The forum channel to check")
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_status(
        self,
        interaction: discord.Interaction,
        channel: discord.ForumChannel,
    ):
        """Display the current configuration for a forum channel."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild, ForumThread

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                config = (
                    db.query(ForumConfig)
                    .filter(
                        ForumConfig.guild_id == guild_record.id,
                        ForumConfig.forum_channel_id == str(channel.id),
                    )
                    .first()
                )

                if not config:
                    await interaction.response.send_message(
                        embed=self._error_embed(
                            "Not Found",
                            f"No configuration found for {channel.mention}. Use `/forum setup` to configure.",
                        ),
                        ephemeral=True,
                    )
                    return

                # Get thread statistics
                thread_count = (
                    db.query(ForumThread).filter(ForumThread.forum_config_id == config.id).count()
                )
                response_count = (
                    db.query(ForumThread)
                    .filter(
                        ForumThread.forum_config_id == config.id, ForumThread.ai_response_count > 0
                    )
                    .count()
                )

                status_emoji = "🟢" if config.is_active else "🔴"
                embed = EmbedBuilder._create_base_embed(
                    title=f"{status_emoji} Forum Configuration",
                    description=f"Configuration for {channel.mention}",
                    color=EmbedColors.INFO if config.is_active else EmbedColors.WARNING,
                )

                # Configuration settings
                config_value = (
                    f"**Status:** {'Active' if config.is_active else 'Disabled'}\n"
                    f"**Auto Respond:** {self._format_bool(config.auto_respond)}\n"
                    f"**AI Model:** `{config.ai_model or 'Default'}`\n"
                    f"**Response Delay:** `{config.response_delay_seconds}s`\n"
                    f"**Max Responses:** `{config.max_responses_per_thread}`"
                )
                EmbedBuilder._add_field_safely(
                    embed, name="Settings", value=config_value, inline=False
                )

                # Tag filtering
                include_tags = (
                    self._format_tags(config.tags_to_monitor)
                    if config.tags_to_monitor
                    else "All tags"
                )
                exclude_tags = (
                    self._format_tags(config.exclude_tags) if config.exclude_tags else "None"
                )
                EmbedBuilder._add_field_safely(
                    embed, name="Include Tags", value=include_tags, inline=True
                )
                EmbedBuilder._add_field_safely(
                    embed, name="Exclude Tags", value=exclude_tags, inline=True
                )

                # Welcome message
                if config.welcome_message:
                    EmbedBuilder._add_field_safely(
                        embed,
                        name="Welcome Message",
                        value=f"```{config.welcome_message[:200]}{'...' if len(config.welcome_message) > 200 else ''}```",
                        inline=False,
                    )

                # Statistics
                stats_value = (
                    f"**Total Threads:** {thread_count}\n**AI Responses:** {response_count}"
                )
                EmbedBuilder._add_field_safely(
                    embed, name="Statistics", value=stats_value, inline=False
                )

                embed.set_footer(
                    text=f"Created: {config.created_at.strftime('%Y-%m-%d')} | Updated: {config.updated_at.strftime('%Y-%m-%d')}"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to retrieve status: {str(e)}"),
                ephemeral=True,
            )

    @forum_group.command(name="list", description="List all monitored forums in this guild")
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_list(self, interaction: discord.Interaction):
        """List all configured forum channels for this guild."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                configs = (
                    db.query(ForumConfig).filter(ForumConfig.guild_id == guild_record.id).all()
                )

                if not configs:
                    await interaction.response.send_message(
                        embed=self._info_embed(
                            "No Forums Configured",
                            "No forums are currently configured for this server. Use `/forum setup` to add one.",
                        ),
                        ephemeral=True,
                    )
                    return

                embed = EmbedBuilder._create_base_embed(
                    title="📋 Configured Forums",
                    description=f"Forum configurations for **{interaction.guild.name}**",
                    color=EmbedColors.INFO,
                )

                for config in configs:
                    status = "🟢 Active" if config.is_active else "🔴 Disabled"
                    channel = interaction.guild.get_channel(int(config.forum_channel_id))
                    channel_mention = (
                        channel.mention if channel else f"`{config.forum_name}` (deleted)"
                    )

                    value = f"**Status:** {status}\n**Auto Respond:** {self._format_bool(config.auto_respond)}\n**Model:** `{config.ai_model or 'Default'}`"
                    EmbedBuilder._add_field_safely(
                        embed, name=channel_mention, value=value, inline=True
                    )

                embed.set_footer(text=f"Total: {len(configs)} forum(s)")
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to list forums: {str(e)}"),
                ephemeral=True,
            )

    @forum_group.command(name="stats", description="Show forum statistics")
    @app_commands.describe(channel="The forum channel (leave empty for all forums)")
    @app_commands.checks.has_permissions(administrator=True)
    async def forum_stats(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.ForumChannel] = None,
    ):
        """Show statistics for forum monitoring."""
        try:
            from database.connection import get_db_context
            from database.models import ForumConfig, Guild, ForumThread
            from sqlalchemy import func

            with get_db_context() as db:
                guild_record = (
                    db.query(Guild).filter(Guild.discord_id == str(interaction.guild_id)).first()
                )
                if not guild_record:
                    await interaction.response.send_message(
                        embed=self._error_embed("Not Found", "Guild configuration not found."),
                        ephemeral=True,
                    )
                    return

                if channel:
                    # Stats for specific forum
                    config = (
                        db.query(ForumConfig)
                        .filter(
                            ForumConfig.guild_id == guild_record.id,
                            ForumConfig.forum_channel_id == str(channel.id),
                        )
                        .first()
                    )

                    if not config:
                        await interaction.response.send_message(
                            embed=self._error_embed(
                                "Not Found", f"No configuration found for {channel.mention}."
                            ),
                            ephemeral=True,
                        )
                        return

                    # Get statistics
                    threads = db.query(ForumThread).filter(ForumThread.forum_config_id == config.id)
                    total_threads = threads.count()
                    total_responses = (
                        threads.with_entities(func.sum(ForumThread.ai_response_count)).scalar() or 0
                    )
                    resolved_threads = threads.filter(ForumThread.was_resolved == True).count()
                    closed_threads = threads.filter(ForumThread.is_closed == True).count()

                    # Calculate resolution rate
                    resolution_rate = (
                        (resolved_threads / total_threads * 100) if total_threads > 0 else 0
                    )

                    embed = EmbedBuilder._create_base_embed(
                        title="📊 Forum Statistics",
                        description=f"Statistics for {channel.mention}",
                        color=EmbedColors.STATS,
                    )

                    EmbedBuilder._add_field_safely(
                        embed, name="Total Threads", value=str(total_threads), inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="AI Responses", value=str(total_responses), inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="Resolution Rate", value=f"{resolution_rate:.1f}%", inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="Resolved", value=str(resolved_threads), inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="Closed", value=str(closed_threads), inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="Active", value=str(total_threads - closed_threads), inline=True
                    )

                else:
                    # Stats for all forums in guild
                    configs = (
                        db.query(ForumConfig).filter(ForumConfig.guild_id == guild_record.id).all()
                    )

                    if not configs:
                        await interaction.response.send_message(
                            embed=self._info_embed(
                                "No Data", "No forums are configured for this server."
                            ),
                            ephemeral=True,
                        )
                        return

                    total_threads = 0
                    total_responses = 0
                    total_resolved = 0
                    total_closed = 0

                    for config in configs:
                        threads = db.query(ForumThread).filter(
                            ForumThread.forum_config_id == config.id
                        )
                        total_threads += threads.count()
                        total_responses += (
                            threads.with_entities(func.sum(ForumThread.ai_response_count)).scalar()
                            or 0
                        )
                        total_resolved += threads.filter(ForumThread.was_resolved == True).count()
                        total_closed += threads.filter(ForumThread.is_closed == True).count()

                    resolution_rate = (
                        (total_resolved / total_threads * 100) if total_threads > 0 else 0
                    )

                    embed = EmbedBuilder._create_base_embed(
                        title="📊 Guild Forum Statistics",
                        description=f"Combined statistics for **{interaction.guild.name}**",
                        color=EmbedColors.STATS,
                    )

                    EmbedBuilder._add_field_safely(
                        embed, name="Total Threads", value=str(total_threads), inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="Total AI Responses", value=str(total_responses), inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="Resolution Rate", value=f"{resolution_rate:.1f}%", inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="Resolved", value=str(total_resolved), inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="Closed", value=str(total_closed), inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="Active", value=str(total_threads - total_closed), inline=True
                    )
                    EmbedBuilder._add_field_safely(
                        embed, name="Monitored Forums", value=str(len(configs)), inline=True
                    )

                embed.set_footer(text="Statistics are updated in real-time")
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"Failed to retrieve statistics: {str(e)}"),
                ephemeral=True,
            )

    # Error handlers
    @forum_setup.error
    @forum_edit_auto_respond.error
    @forum_edit_welcome_message.error
    @forum_edit_ai_model.error
    @forum_edit_response_delay.error
    @forum_edit_max_responses.error
    @forum_edit_include_tags.error
    @forum_edit_exclude_tags.error
    @forum_disable.error
    @forum_enable.error
    @forum_status.error
    @forum_list.error
    @forum_stats.error
    async def forum_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """Handle permission errors for forum commands."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=self._error_embed(
                    "Permission Denied",
                    "You need **Administrator** permission to use forum commands.",
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=self._error_embed("Error", f"An error occurred: {str(error)}"),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Add the ForumCommands cog to the bot."""
    await bot.add_cog(ForumCommands(bot))
