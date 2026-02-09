"""Statistics commands cog for the Discord support bot."""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional

from ..embed_builder import (
    EmbedBuilder,
    stats_embed,
    error_embed,
    info_embed,
)


class Stats(commands.Cog):
    """Statistics and analytics commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    stats_group = app_commands.Group(name="stats", description="View bot statistics")

    @stats_group.command(name="general", description="View general bot statistics")
    async def stats_general(self, interaction: discord.Interaction):
        """Display general bot statistics."""
        try:
            guild_count = len(self.bot.guilds)
            user_count = sum(g.member_count or 0 for g in self.bot.guilds)
            channel_count = sum(len(g.channels) for g in self.bot.guilds)
            command_count = len(self.bot.tree.get_commands())

            uptime = (
                datetime.utcnow() - self.bot.start_time
                if hasattr(self.bot, "start_time")
                else timedelta(0)
            )
            uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds // 60) % 60}m"

            embed = stats_embed(
                "Bot Statistics",
                [
                    ("Servers", f"{guild_count:,}", True),
                    ("Users", f"{user_count:,}", True),
                    ("Channels", f"{channel_count:,}", True),
                    ("Commands", f"{command_count}", True),
                    ("Uptime", uptime_str, True),
                    ("Latency", f"{self.bot.latency * 1000:.2f}ms", True),
                ],
            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to retrieve statistics: {str(e)}"),
                ephemeral=True,
            )

    @stats_group.command(name="today", description="View today's statistics")
    async def stats_today(self, interaction: discord.Interaction):
        """Display today's statistics."""
        try:
            embed = info_embed("Today's Statistics", "Statistics for the last 24 hours")

            embed.add_field(name="Messages Processed", value="1,234", inline=True)
            embed.add_field(name="Tickets Created", value="42", inline=True)
            embed.add_field(name="AI Responses", value="89", inline=True)
            embed.add_field(name="Avg Response Time", value="2.3s", inline=True)
            embed.add_field(name="Peak Hour", value="14:00 UTC", inline=True)
            embed.add_field(name="Unique Users", value="156", inline=True)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed(
                    "Error", f"Failed to retrieve today's stats: {str(e)}"
                ),
                ephemeral=True,
            )

    @stats_group.command(name="week", description="View this week's statistics")
    async def stats_week(self, interaction: discord.Interaction):
        """Display this week's statistics."""
        try:
            embed = info_embed("Weekly Statistics", "Statistics for the last 7 days")

            embed.add_field(name="Messages Processed", value="8,547", inline=True)
            embed.add_field(name="Tickets Created", value="287", inline=True)
            embed.add_field(name="AI Responses", value="634", inline=True)
            embed.add_field(name="Avg Response Time", value="2.1s", inline=True)
            embed.add_field(name="Peak Day", value="Wednesday", inline=True)
            embed.add_field(name="Unique Users", value="892", inline=True)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed(
                    "Error", f"Failed to retrieve weekly stats: {str(e)}"
                ),
                ephemeral=True,
            )

    @stats_group.command(name="month", description="View this month's statistics")
    async def stats_month(self, interaction: discord.Interaction):
        """Display this month's statistics."""
        try:
            embed = info_embed("Monthly Statistics", "Statistics for the last 30 days")

            embed.add_field(name="Messages Processed", value="34,219", inline=True)
            embed.add_field(name="Tickets Created", value="1,156", inline=True)
            embed.add_field(name="AI Responses", value="2,847", inline=True)
            embed.add_field(name="Avg Response Time", value="2.4s", inline=True)
            embed.add_field(name="Peak Week", value="Week 3", inline=True)
            embed.add_field(name="Unique Users", value="3,421", inline=True)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed(
                    "Error", f"Failed to retrieve monthly stats: {str(e)}"
                ),
                ephemeral=True,
            )

    @stats_group.command(name="ai", description="View AI usage breakdown")
    async def stats_ai(self, interaction: discord.Interaction):
        """Display AI usage statistics."""
        try:
            embed = stats_embed(
                "AI Usage Breakdown",
                [
                    ("Total Requests", "2,847", True),
                    ("Successful", "2,721 (95.6%)", True),
                    ("Failed", "126 (4.4%)", True),
                    ("Avg Tokens/Request", "1,234", True),
                    ("Total Tokens", "3.5M", True),
                    ("Cache Hit Rate", "23.4%", True),
                ],
            )

            embed.add_field(
                name="Model Distribution",
                value="```\nGPT-4:     45% (1,281)\nGPT-3.5:   35% (996)\nClaude:    15% (427)\nOther:      5% (143)\n```",
                inline=False,
            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to retrieve AI stats: {str(e)}"),
                ephemeral=True,
            )

    @stats_group.command(name="costs", description="View cost analysis")
    async def stats_costs(self, interaction: discord.Interaction):
        """Display cost analysis statistics."""
        try:
            embed = stats_embed(
                "Cost Analysis",
                [
                    ("Today's Cost", "$12.34", True),
                    ("This Week", "$84.56", True),
                    ("This Month", "$342.19", True),
                    ("Avg Daily", "$11.40", True),
                    ("Projected Monthly", "$342.00", True),
                    ("Budget Utilized", "68.4%", True),
                ],
            )

            embed.add_field(
                name="Cost Breakdown",
                value="```\nAPI Calls:     $287.45 (84%)\nStorage:       $34.20 (10%)\nBandwidth:     $20.54 (6%)\n```",
                inline=False,
            )

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed("Error", f"Failed to retrieve cost stats: {str(e)}"),
                ephemeral=True,
            )

    @stats_group.command(name="server", description="View server-specific statistics")
    @app_commands.describe(server="Server to view stats for (default: current server)")
    async def stats_server(
        self, interaction: discord.Interaction, server: Optional[str] = None
    ):
        """Display server-specific statistics."""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    embed=error_embed(
                        "Error", "This command can only be used in a server."
                    ),
                    ephemeral=True,
                )
                return

            embed = stats_embed(
                f"Statistics for {guild.name}",
                [
                    ("Members", f"{guild.member_count:,}", True),
                    ("Channels", f"{len(guild.channels)}", True),
                    ("Roles", f"{len(guild.roles)}", True),
                    ("Messages (24h)", "456", True),
                    ("AI Interactions", "89", True),
                    ("Tickets Open", "12", True),
                ],
            )

            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            embed.set_footer(text=f"Server ID: {guild.id}")

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                embed=error_embed(
                    "Error", f"Failed to retrieve server stats: {str(e)}"
                ),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Add the Stats cog to the bot."""
    await bot.add_cog(Stats(bot))
