"""Ping command cog for the Discord support bot."""

import discord
from discord import app_commands
from discord.ext import commands
import platform
import psutil
from datetime import datetime

from ..embed_builder import (
    EmbedBuilder,
    success_embed,
    error_embed,
    info_embed,
)


class Ping(commands.Cog):
    """Ping and latency check commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ping", description="Check bot latency and connection status"
    )
    async def ping(self, interaction: discord.Interaction):
        """Check bot latency and connection status."""
        try:
            start_time = datetime.utcnow()
            await interaction.response.defer(thinking=True)

            api_latency = self.bot.latency * 1000

            message_latency = (datetime.utcnow() - start_time).total_seconds() * 1000

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()

            if api_latency < 100:
                status_emoji = "🟢"
                color = "success"
            elif api_latency < 200:
                status_emoji = "🟡"
                color = "warning"
            else:
                status_emoji = "🔴"
                color = "error"

            embed = (
                EmbedBuilder()
                .set_title(f"{status_emoji} Pong!")
                .set_description("Bot connection and performance status")
                .set_color(color)
                .set_timestamp()
            )

            embed.add_field(
                name="📡 WebSocket Latency", value=f"{api_latency:.2f}ms", inline=True
            )
            embed.add_field(
                name="💬 Message Latency", value=f"{message_latency:.2f}ms", inline=True
            )
            embed.add_field(
                name="🌐 API Latency", value=f"{api_latency:.2f}ms", inline=True
            )

            embed.add_field(
                name="💻 System",
                value=f"```\nCPU: {cpu_percent:.1f}%\nRAM: {memory.percent:.1f}%\n```",
                inline=False,
            )

            shard_info = f"Shard {interaction.guild.shard_id if interaction.guild and hasattr(interaction.guild, 'shard_id') else 0}/{self.bot.shard_count or 1}"
            embed.set_footer(
                text=f"{shard_info} | {platform.system()} {platform.release()}"
            )

            await interaction.followup.send(embed=embed.build())

        except Exception as e:
            await interaction.followup.send(
                embed=error_embed("Error", f"Failed to check ping: {str(e)}"),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Add the Ping cog to the bot."""
    await bot.add_cog(Ping(bot))
