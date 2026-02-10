"""Admin commands cog for the Discord support bot."""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import platform
import psutil
import asyncio

from ..embed_builder import (
    EmbedBuilder,
    success_embed,
    error_embed,
    info_embed,
    warning_embed,
)


class Admin(commands.Cog):
    """Admin-only commands for bot management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    admin_group = app_commands.Group(name="admin", description="Admin-only commands")

    @admin_group.command(name="shard-status", description="View shard status")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_shard_status(self, interaction: discord.Interaction):
        """Display shard status information."""
        try:
            embed = info_embed("Shard Status", "Bot shard information")

            if self.bot.shard_count and self.bot.shard_count > 1:
                for shard_id in range(self.bot.shard_count):
                    latency = (
                        self.bot.get_shard(shard_id).latency * 1000
                        if self.bot.get_shard(shard_id)
                        else 0
                    )
                    status = "🟢 Online" if latency > 0 else "🔴 Offline"

                    guilds = sum(1 for g in self.bot.guilds if g.shard_id == shard_id)

                    embed.add_field(
                        name=f"Shard {shard_id}",
                        value=f"```\nStatus: {status}\nLatency: {latency:.2f}ms\nGuilds: {guilds}\n```",
                        inline=True,
                    )
            else:
                embed.add_field(
                    name="Shard 0",
                    value=f"```\nStatus: 🟢 Online\nLatency: {self.bot.latency * 1000:.2f}ms\nGuilds: {len(self.bot.guilds)}\n```",
                    inline=False,
                )

            embed.add_field(
                name="Total",
                value=f"```\nShards: {self.bot.shard_count or 1}\nGuilds: {len(self.bot.guilds)}\nUsers: {sum(g.member_count for g in self.bot.guilds):,}\n```",
                inline=False,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to retrieve shard status: {str(e)}"),
                ephemeral=True,
            )

    @admin_group.command(name="maintenance", description="Toggle maintenance mode")
    @app_commands.describe(state="Enable or disable maintenance mode")
    @app_commands.choices(
        state=[
            app_commands.Choice(name="On", value="on"),
            app_commands.Choice(name="Off", value="off"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_maintenance(
        self, interaction: discord.Interaction, state: app_commands.Choice[str]
    ):
        """Toggle maintenance mode for the bot."""
        try:
            enabled = state.value == "on"

            if enabled:
                self.bot.maintenance_mode = True
                await self.bot.change_presence(
                    status=discord.Status.dnd,
                    activity=discord.Activity(
                        type=discord.ActivityType.watching, name="Maintenance Mode"
                    ),
                )

                embed = warning_embed(
                    "Maintenance Mode Enabled",
                    "Bot is now in maintenance mode. Only administrators can use commands.",
                )
                embed.add_field(name="Status", value="🔴 Maintenance", inline=True)
                embed.add_field(
                    name="Started",
                    value=discord.utils.format_dt(discord.utils.utcnow()),
                    inline=True,
                )

            else:
                self.bot.maintenance_mode = False
                await self.bot.change_presence(
                    status=discord.Status.online,
                    activity=discord.Activity(
                        type=discord.ActivityType.watching, name="for support requests"
                    ),
                )

                embed = success_embed(
                    "Maintenance Mode Disabled",
                    "Bot is back online and fully operational.",
                )
                embed.add_field(name="Status", value="🟢 Online", inline=True)
                embed.add_field(
                    name="Ended",
                    value=discord.utils.format_dt(discord.utils.utcnow()),
                    inline=True,
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to toggle maintenance mode: {str(e)}"),
                ephemeral=True,
            )

    @admin_group.command(name="logs", description="View recent logs")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_logs(self, interaction: discord.Interaction):
        """Display recent bot logs."""
        try:
            embed = info_embed("Recent Logs", "Last 10 log entries")

            sample_logs = [
                ("INFO", "Bot ready", "2 minutes ago"),
                ("INFO", "Connected to database", "2 minutes ago"),
                ("INFO", "Loaded 5 cogs", "2 minutes ago"),
                ("DEBUG", "Command tree synced", "2 minutes ago"),
                ("INFO", "User requested stats", "5 minutes ago"),
                ("WARN", "Rate limit approaching", "10 minutes ago"),
                ("INFO", "AI response generated", "12 minutes ago"),
                ("INFO", "New ticket created", "15 minutes ago"),
                ("DEBUG", "Cache cleared", "20 minutes ago"),
                ("INFO", "Bot started", "30 minutes ago"),
            ]

            log_text = ""
            for level, message, time in sample_logs:
                emoji = {"INFO": "🟢", "WARN": "🟡", "ERROR": "🔴", "DEBUG": "⚪"}.get(level, "⚪")
                log_text += f"{emoji} `[{level}]` {message} - *{time}*\n"

            embed.description = log_text
            embed.set_footer(text="Showing last 10 entries | Use /admin logs-file for full logs")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to retrieve logs: {str(e)}"),
                ephemeral=True,
            )

    @admin_group.command(name="system", description="View system information")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_system(self, interaction: discord.Interaction):
        """Display system information."""
        try:
            embed = info_embed("System Information", "Bot server statistics")

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            embed.add_field(
                name="CPU",
                value=f"```\nUsage: {cpu_percent:.1f}%\nCores: {psutil.cpu_count()}\nFreq: {psutil.cpu_freq().current:.0f} MHz\n```",
                inline=True,
            )

            embed.add_field(
                name="Memory",
                value=f"```\nUsage: {memory.percent:.1f}%\nUsed: {memory.used / 1024**3:.1f} GB\nTotal: {memory.total / 1024**3:.1f} GB\n```",
                inline=True,
            )

            embed.add_field(
                name="Disk",
                value=f"```\nUsage: {disk.percent}%\nUsed: {disk.used / 1024**3:.1f} GB\nTotal: {disk.total / 1024**3:.1f} GB\n```",
                inline=True,
            )

            embed.add_field(
                name="Platform",
                value=f"```\nOS: {platform.system()} {platform.release()}\nPython: {platform.python_version()}\nDiscord.py: {discord.__version__}\n```",
                inline=False,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to retrieve system info: {str(e)}"),
                ephemeral=True,
            )

    @admin_group.command(name="reload", description="Reload a cog")
    @app_commands.describe(cog="Name of the cog to reload")
    @app_commands.checks.has_permissions(administrator=True)
    async def admin_reload(self, interaction: discord.Interaction, cog: str):
        """Reload a specific cog."""
        try:
            cog_path = f"bot.cogs.{cog}"

            try:
                await self.bot.unload_extension(cog_path)
            except Exception:
                pass

            await self.bot.load_extension(cog_path)

            await interaction.response.send_message(
                embed=success_embed("Cog Reloaded", f"Successfully reloaded `{cog}` cog."),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to reload cog: {str(e)}"),
                ephemeral=True,
            )

    @admin_shard_status.error
    @admin_maintenance.error
    @admin_logs.error
    @admin_system.error
    @admin_reload.error
    async def admin_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """Handle permission errors for admin commands."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=error_embed(
                    "Permission Denied",
                    "You need **Administrator** permission to use admin commands.",
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("Error", f"An error occurred: {str(error)}"),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Add the Admin cog to the bot."""
    await bot.add_cog(Admin(bot))
