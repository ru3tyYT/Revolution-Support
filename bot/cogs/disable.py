"""Disable/Enable commands cog for the Discord support bot."""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import re
from typing import Optional

from ..embed_builder import (
    EmbedBuilder,
    success_embed,
    error_embed,
    info_embed,
    warning_embed,
)


class Disable(commands.Cog):
    """Disable and enable bot commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.disabled_channels = {}
        self.disabled_ai_channels = {}

    def parse_duration(self, duration_str: Optional[str]) -> Optional[datetime]:
        """Parse duration string and return expiry datetime."""
        if not duration_str:
            return None

        pattern = r"(\d+)\s*(m|min|minute|minutes|h|hr|hour|hours|d|day|days)"
        match = re.match(pattern, duration_str.lower())

        if not match:
            return None

        amount = int(match.group(1))
        unit = match.group(2)

        if unit in ["m", "min", "minute", "minutes"]:
            delta = timedelta(minutes=amount)
        elif unit in ["h", "hr", "hour", "hours"]:
            delta = timedelta(hours=amount)
        elif unit in ["d", "day", "days"]:
            delta = timedelta(days=amount)
        else:
            return None

        return datetime.utcnow() + delta

    @app_commands.command(name="disable", description="Disable the bot in this channel")
    @app_commands.describe(duration="Duration to disable (e.g., '30m', '2h', '1d')")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def disable(
        self, interaction: discord.Interaction, duration: Optional[str] = None
    ):
        """Disable the bot in the current channel."""
        try:
            channel_id = interaction.channel_id

            if channel_id in self.disabled_channels:
                expiry = self.disabled_channels[channel_id]
                if expiry and expiry > datetime.utcnow():
                    remaining = expiry - datetime.utcnow()
                    await interaction.response.send_message(
                        embed=warning_embed(
                            "Already Disabled",
                            f"Bot is already disabled in this channel.\nTime remaining: {remaining.seconds // 60}m {remaining.seconds % 60}s",
                        ),
                        ephemeral=True,
                    )
                    return

            expiry = self.parse_duration(duration)
            self.disabled_channels[channel_id] = expiry

            if expiry:
                expiry_str = discord.utils.format_dt(expiry, style="R")
                embed = success_embed(
                    "Bot Disabled",
                    f"Bot has been disabled in this channel until {expiry_str}",
                )
                embed.add_field(name="Duration", value=duration, inline=True)
                embed.add_field(name="Expires", value=expiry_str, inline=True)
            else:
                embed = success_embed(
                    "Bot Disabled",
                    "Bot has been disabled in this channel indefinitely.\nUse `/enable` to re-enable.",
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to disable bot: {str(e)}"),
                ephemeral=True,
            )

    @app_commands.command(
        name="enable", description="Re-enable the bot in this channel"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def enable(self, interaction: discord.Interaction):
        """Re-enable the bot in the current channel."""
        try:
            channel_id = interaction.channel_id

            was_disabled = channel_id in self.disabled_channels
            ai_was_disabled = channel_id in self.disabled_ai_channels

            if channel_id in self.disabled_channels:
                del self.disabled_channels[channel_id]

            if not was_disabled and not ai_was_disabled:
                await interaction.response.send_message(
                    embed=info_embed(
                        "Already Enabled", "Bot is already enabled in this channel."
                    ),
                    ephemeral=True,
                )
                return

            embed = success_embed(
                "Bot Enabled", "Bot has been re-enabled in this channel."
            )

            if ai_was_disabled:
                embed.add_field(
                    name="Note",
                    value="AI responses are still disabled. Use `/enable-ai` to enable them.",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to enable bot: {str(e)}"),
                ephemeral=True,
            )

    @app_commands.command(
        name="disable-ai", description="Disable AI responses in this channel"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def disable_ai(self, interaction: discord.Interaction):
        """Disable AI responses in the current channel."""
        try:
            channel_id = interaction.channel_id

            if channel_id in self.disabled_ai_channels:
                await interaction.response.send_message(
                    embed=warning_embed(
                        "Already Disabled",
                        "AI responses are already disabled in this channel.",
                    ),
                    ephemeral=True,
                )
                return

            self.disabled_ai_channels[channel_id] = True

            embed = success_embed(
                "AI Disabled",
                "AI responses have been disabled in this channel.\nOther bot commands will still work.",
            )
            embed.add_field(
                name="What's Disabled",
                value="• AI-generated responses\n• Smart suggestions\n• Auto-responses",
                inline=False,
            )
            embed.add_field(
                name="What's Still Available",
                value="• All `/` commands\n• Manual commands\n• Search functionality",
                inline=False,
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to disable AI: {str(e)}"),
                ephemeral=True,
            )

    @app_commands.command(
        name="enable-ai", description="Re-enable AI responses in this channel"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def enable_ai(self, interaction: discord.Interaction):
        """Re-enable AI responses in the current channel."""
        try:
            channel_id = interaction.channel_id

            if channel_id not in self.disabled_ai_channels:
                await interaction.response.send_message(
                    embed=info_embed(
                        "Already Enabled",
                        "AI responses are already enabled in this channel.",
                    ),
                    ephemeral=True,
                )
                return

            del self.disabled_ai_channels[channel_id]

            embed = success_embed(
                "AI Enabled", "AI responses have been re-enabled in this channel."
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to enable AI: {str(e)}"),
                ephemeral=True,
            )

    @disable.error
    @enable.error
    @disable_ai.error
    @enable_ai.error
    async def disable_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """Handle permission errors for disable/enable commands."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=error_embed(
                    "Permission Denied",
                    "You need **Manage Channels** permission to use this command.",
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("Error", f"An error occurred: {str(error)}"),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Add the Disable cog to the bot."""
    await bot.add_cog(Disable(bot))
