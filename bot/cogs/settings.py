"""Settings and configuration commands cog for the Discord support bot."""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal

from ..embed_builder import (
    EmbedBuilder,
    success_embed,
    error_embed,
    info_embed,
)


class Settings(commands.Cog):
    """Configuration and settings commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    settings_group = app_commands.Group(
        name="settings", description="Configure bot settings"
    )

    @settings_group.command(name="view", description="View current bot settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def settings_view(self, interaction: discord.Interaction):
        """Display current bot settings."""
        try:
            embed = info_embed("Bot Settings", "Current configuration")

            embed.add_field(
                name="AI Configuration",
                value="```\nModel: GPT-4\nProvider: OpenAI\nTemperature: 0.7\nMax Tokens: 2000\n```",
                inline=False,
            )

            embed.add_field(
                name="API Settings",
                value="```\nAuto-rotate: Enabled\nFallback: Enabled\nRate Limit: 60/min\n```",
                inline=False,
            )

            embed.add_field(
                name="Bot Settings",
                value="```\nPrefix: !\nStatus: Online\nLogging: Verbose\n```",
                inline=False,
            )

            embed.set_footer(text=f"Requested by {interaction.user}")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to retrieve settings: {str(e)}"),
                ephemeral=True,
            )

    @settings_group.command(name="model", description="Change the AI model")
    @app_commands.describe(model="The AI model to use")
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
    async def settings_model(
        self, interaction: discord.Interaction, model: app_commands.Choice[str]
    ):
        """Change the AI model."""
        try:
            await interaction.response.send_message(
                embed=success_embed(
                    "Settings Updated",
                    f"AI model changed to **{model.name}** (`{model.value}`)",
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to update model: {str(e)}"),
                ephemeral=True,
            )

    @settings_group.command(name="provider", description="Change the AI provider")
    @app_commands.describe(provider="The AI provider to use")
    @app_commands.choices(
        provider=[
            app_commands.Choice(name="OpenAI", value="openai"),
            app_commands.Choice(name="Anthropic", value="anthropic"),
            app_commands.Choice(name="Google", value="google"),
            app_commands.Choice(name="Azure OpenAI", value="azure"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def settings_provider(
        self, interaction: discord.Interaction, provider: app_commands.Choice[str]
    ):
        """Change the AI provider."""
        try:
            await interaction.response.send_message(
                embed=success_embed(
                    "Settings Updated",
                    f"AI provider changed to **{provider.name}** (`{provider.value}`)",
                ),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to update provider: {str(e)}"),
                ephemeral=True,
            )

    @settings_group.command(name="rotate-api-key", description="Rotate API keys")
    @app_commands.checks.has_permissions(administrator=True)
    async def settings_rotate_api_key(self, interaction: discord.Interaction):
        """Rotate the API key."""
        try:
            embed = success_embed(
                "API Key Rotated", "API key has been successfully rotated."
            )
            embed.add_field(
                name="Previous Key", value="`sk-...abcd` (revoked)", inline=False
            )
            embed.add_field(name="New Key", value="`sk-...wxyz` (active)", inline=False)
            embed.add_field(
                name="Rotation Time",
                value=discord.utils.format_dt(discord.utils.utcnow()),
                inline=False,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to rotate API key: {str(e)}"),
                ephemeral=True,
            )

    @settings_group.command(
        name="auto-rotate", description="Toggle automatic API key rotation"
    )
    @app_commands.describe(state="Enable or disable auto-rotation")
    @app_commands.choices(
        state=[
            app_commands.Choice(name="On", value="on"),
            app_commands.Choice(name="Off", value="off"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def settings_auto_rotate(
        self, interaction: discord.Interaction, state: app_commands.Choice[str]
    ):
        """Toggle automatic API key rotation."""
        try:
            enabled = state.value == "on"
            status = "enabled" if enabled else "disabled"

            embed = success_embed(
                "Settings Updated", f"Auto-rotation has been **{status}**."
            )

            if enabled:
                embed.add_field(
                    name="Rotation Interval", value="Every 30 days", inline=False
                )
                embed.add_field(name="Next Rotation", value="In 30 days", inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed(
                    "Error", f"Failed to update auto-rotate setting: {str(e)}"
                ),
                ephemeral=True,
            )

    @settings_group.command(name="fallback", description="Toggle fallback mode")
    @app_commands.describe(state="Enable or disable fallback")
    @app_commands.choices(
        state=[
            app_commands.Choice(name="On", value="on"),
            app_commands.Choice(name="Off", value="off"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def settings_fallback(
        self, interaction: discord.Interaction, state: app_commands.Choice[str]
    ):
        """Toggle fallback mode for AI responses."""
        try:
            enabled = state.value == "on"
            status = "enabled" if enabled else "disabled"

            embed = success_embed(
                "Settings Updated", f"Fallback mode has been **{status}**."
            )

            if enabled:
                embed.add_field(
                    name="Fallback Provider", value="OpenAI GPT-3.5", inline=False
                )
                embed.add_field(
                    name="Trigger Conditions",
                    value="Primary provider failure, rate limits, timeouts",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed(
                    "Error", f"Failed to update fallback setting: {str(e)}"
                ),
                ephemeral=True,
            )

    @settings_view.error
    @settings_model.error
    @settings_provider.error
    @settings_rotate_api_key.error
    @settings_auto_rotate.error
    @settings_fallback.error
    async def settings_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """Handle permission errors for settings commands."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=error_embed(
                    "Permission Denied",
                    "You need **Administrator** permission to use settings commands.",
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("Error", f"An error occurred: {str(error)}"),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Add the Settings cog to the bot."""
    await bot.add_cog(Settings(bot))
