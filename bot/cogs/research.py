"""Discord cog for research commands.

Provides slash commands for triggering research tasks and managing the queue.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands, tasks

# Absolute imports from research package (top-level project package)
from research.worker import get_task_result, revoke_task, get_queue_status
from research.tasks import (
    web_search,
    api_query,
    database_lookup,
    document_analysis,
    comparison,
    troubleshooting,
)

logger = logging.getLogger(__name__)


class ResearchCog(commands.Cog):
    """Cog for research-related commands."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the research cog."""
        self.bot = bot
        self.active_tasks: dict[str, dict[str, Any]] = {}
        self.task_notifications: dict[str, int] = {}  # task_id -> channel_id

        # Start background task for checking task completion
        self.check_tasks.start()

    def cog_unload(self) -> None:
        """Clean up when cog is unloaded."""
        self.check_tasks.cancel()

    @tasks.loop(seconds=5)
    async def check_tasks(self) -> None:
        """Background task to check for completed research tasks."""
        completed_tasks = []

        for task_id, task_info in list(self.active_tasks.items()):
            try:
                result = get_task_result(task_id)

                if result["status"] in ["SUCCESS", "FAILURE", "REVOKED"]:
                    completed_tasks.append((task_id, result, task_info))

            except Exception as e:
                logger.error(f"Error checking task {task_id}: {e}")

        # Send notifications for completed tasks
        for task_id, result, task_info in completed_tasks:
            await self._send_task_completion(task_id, result, task_info)
            del self.active_tasks[task_id]
            if task_id in self.task_notifications:
                del self.task_notifications[task_id]

    @check_tasks.before_loop
    async def before_check_tasks(self) -> None:
        """Wait for bot to be ready before starting task checks."""
        await self.bot.wait_until_ready()

    async def _send_task_completion(
        self,
        task_id: str,
        result: dict[str, Any],
        task_info: dict[str, Any],
    ) -> None:
        """Send notification when a task completes.

        Args:
            task_id: The task ID
            result: Task result data
            task_info: Task metadata
        """
        channel_id = self.task_notifications.get(task_id)
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        user = self.bot.get_user(task_info.get("user_id"))
        user_mention = user.mention if user else "Unknown User"

        # Create completion embed
        if result["status"] == "SUCCESS":
            embed = self._create_result_embed(task_info, result["result"])
            content = f"{user_mention} Your research task is complete!"
        else:
            embed = discord.Embed(
                title="❌ Research Failed",
                description=f"Task ID: `{task_id}`",
                color=discord.Color.red(),
            )
            embed.add_field(
                name="Error",
                value=result.get("error", "Unknown error"),
                inline=False,
            )
            content = f"{user_mention} Your research task failed."

        try:
            await channel.send(content=content, embed=embed)
        except Exception as e:
            logger.error(f"Failed to send task completion: {e}")

    def _create_result_embed(
        self,
        task_info: dict[str, Any],
        result: dict[str, Any],
    ) -> discord.Embed:
        """Create an embed for research results.

        Args:
            task_info: Task metadata
            result: Research result data

        Returns:
            Discord embed
        """
        task_type = result.get("task_type", "unknown")

        # Color based on task type
        colors = {
            "web_search": discord.Color.blue(),
            "api_query": discord.Color.green(),
            "database_lookup": discord.Color.purple(),
            "document_analysis": discord.Color.orange(),
            "comparison": discord.Color.gold(),
            "troubleshooting": discord.Color.red(),
        }
        color = colors.get(task_type, discord.Color.default())

        embed = discord.Embed(
            title=f"🔍 Research Results: {task_type.replace('_', ' ').title()}",
            color=color,
            timestamp=datetime.utcnow(),
        )

        # Add fields based on task type
        if task_type == "web_search":
            embed.add_field(
                name="Query",
                value=result.get("query", "N/A"),
                inline=False,
            )
            embed.add_field(
                name="Total Results",
                value=str(result.get("total_results", 0)),
                inline=True,
            )

            # Add top results
            results = result.get("results", [])[:5]
            if results:
                results_text = ""
                for i, r in enumerate(results, 1):
                    title = r.get("title", "Untitled")[:50]
                    url = r.get("url", "")
                    results_text += f"{i}. [{title}]({url})\n"
                embed.add_field(
                    name="Top Results",
                    value=results_text or "No results",
                    inline=False,
                )

        elif task_type == "api_query":
            embed.add_field(
                name="Endpoint",
                value=result.get("endpoint", "N/A"),
                inline=False,
            )
            embed.add_field(
                name="Status Code",
                value=str(result.get("status_code", "N/A")),
                inline=True,
            )
            embed.add_field(
                name="Method",
                value=result.get("method", "GET"),
                inline=True,
            )

            data = result.get("data", {})
            if isinstance(data, dict) and len(str(data)) < 1000:
                embed.add_field(
                    name="Response Data",
                    value=f"```json\n{str(data)[:900]}\n```",
                    inline=False,
                )

        elif task_type == "database_lookup":
            embed.add_field(
                name="Query Type",
                value=result.get("query_type", "N/A"),
                inline=True,
            )
            embed.add_field(
                name="Total Results",
                value=str(result.get("total_results", 0)),
                inline=True,
            )

        elif task_type == "document_analysis":
            embed.add_field(
                name="Analysis Type",
                value=result.get("analysis_type", "N/A"),
                inline=True,
            )
            embed.add_field(
                name="Content Length",
                value=str(result.get("content_length", 0)),
                inline=True,
            )

            analysis_result = result.get("result", {})
            if "summary" in analysis_result:
                summary = analysis_result["summary"][:500]
                embed.add_field(
                    name="Summary",
                    value=summary or "No summary available",
                    inline=False,
                )
            elif "sentiment" in analysis_result:
                embed.add_field(
                    name="Sentiment",
                    value=f"{analysis_result['sentiment']} ({analysis_result.get('score', 0)})",
                    inline=True,
                )

        elif task_type == "comparison":
            embed.add_field(
                name="Items Compared",
                value=str(result.get("items_compared", 0)),
                inline=True,
            )

            rankings = result.get("rankings", [])
            if rankings:
                rankings_text = ""
                for r in rankings[:5]:
                    rank = r.get("rank", 0)
                    name = r.get("name", "Unknown")
                    score = r.get("overall_score", 0)
                    rankings_text += f"{rank}. {name} ({score})\n"
                embed.add_field(
                    name="Rankings",
                    value=rankings_text or "No rankings",
                    inline=False,
                )

            recommendation = result.get("recommendation")
            if recommendation:
                embed.add_field(
                    name="🏆 Recommendation",
                    value=recommendation.get("name", "None"),
                    inline=False,
                )

        elif task_type == "troubleshooting":
            embed.add_field(
                name="Problem",
                value=result.get("problem", "N/A")[:100],
                inline=False,
            )
            embed.add_field(
                name="Severity",
                value=result.get("severity", "unknown").upper(),
                inline=True,
            )
            embed.add_field(
                name="Estimated Time",
                value=result.get("estimated_resolution_time", "unknown"),
                inline=True,
            )

            steps = result.get("troubleshooting_steps", [])
            if steps:
                steps_text = ""
                for step in steps[:5]:
                    step_num = step.get("step", 0)
                    action = step.get("action", "")
                    steps_text += f"{step_num}. {action}\n"
                embed.add_field(
                    name="Troubleshooting Steps",
                    value=steps_text or "No steps",
                    inline=False,
                )

        # Add footer with task info
        embed.set_footer(text=f"Task ID: {task_info.get('task_id', 'unknown')}")

        return embed

    @app_commands.command(name="research", description="Trigger a research task")
    @app_commands.describe(
        query="The research query or topic",
        task_type="Type of research to perform",
    )
    @app_commands.choices(
        task_type=[
            app_commands.Choice(name="Web Search", value="web_search"),
            app_commands.Choice(name="Database Lookup", value="database_lookup"),
            app_commands.Choice(name="Troubleshooting", value="troubleshooting"),
        ]
    )
    async def research(
        self,
        interaction: discord.Interaction,
        query: str,
        task_type: app_commands.Choice[str],
    ) -> None:
        """Trigger a research task.

        Args:
            interaction: Discord interaction
            query: Research query
            task_type: Type of research task
        """
        await interaction.response.defer(thinking=True)

        try:
            # Submit task based on type
            if task_type.value == "web_search":
                task = web_search.delay(query=query, max_results=10)
            elif task_type.value == "database_lookup":
                task = database_lookup.delay(
                    query_type="knowledge",
                    filters={"search": query},
                    limit=20,
                )
            elif task_type.value == "troubleshooting":
                task = troubleshooting.delay(
                    problem=query,
                    symptoms=[query],
                )
            else:
                await interaction.followup.send(
                    "❌ Unknown task type.",
                    ephemeral=True,
                )
                return

            # Track task
            self.active_tasks[task.id] = {
                "task_id": task.id,
                "user_id": interaction.user.id,
                "channel_id": interaction.channel_id,
                "guild_id": interaction.guild_id,
                "query": query,
                "task_type": task_type.value,
                "created_at": datetime.utcnow().isoformat(),
            }
            self.task_notifications[task.id] = interaction.channel_id

            # Create confirmation embed
            embed = discord.Embed(
                title="🔍 Research Task Started",
                description=f"Your research task has been queued.",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Query", value=query, inline=False)
            embed.add_field(
                name="Task Type",
                value=task_type.name,
                inline=True,
            )
            embed.add_field(
                name="Task ID",
                value=f"`{task.id}`",
                inline=True,
            )
            embed.add_field(
                name="Status",
                value="⏳ Queued",
                inline=True,
            )
            embed.set_footer(text="Use /research status to check progress")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to start research task: {e}")
            await interaction.followup.send(
                f"❌ Failed to start research task: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(
        name="research_status",
        description="Check the status of a research task",
    )
    @app_commands.describe(task_id="The task ID to check")
    async def research_status(
        self,
        interaction: discord.Interaction,
        task_id: str,
    ) -> None:
        """Check the status of a research task.

        Args:
            interaction: Discord interaction
            task_id: Task ID to check
        """
        await interaction.response.defer(thinking=True)

        try:
            result = get_task_result(task_id)

            # Status emojis
            status_emojis = {
                "PENDING": "⏳",
                "STARTED": "🔄",
                "PROGRESS": "📊",
                "SUCCESS": "✅",
                "FAILURE": "❌",
                "REVOKED": "🚫",
                "RETRY": "🔄",
            }

            status = result["status"]
            emoji = status_emojis.get(status, "❓")

            embed = discord.Embed(
                title=f"{emoji} Research Task Status",
                color=self._get_status_color(status),
            )
            embed.add_field(
                name="Task ID",
                value=f"`{task_id}`",
                inline=True,
            )
            embed.add_field(
                name="Status",
                value=status,
                inline=True,
            )

            # Add progress info if available
            if status == "PROGRESS" and result.get("result"):
                progress = result["result"]
                current = progress.get("current", 0)
                total = progress.get("total", 100)
                percent = progress.get("percent", 0)
                message = progress.get("message", "Processing...")

                # Progress bar
                filled = int(percent / 10)
                bar = "█" * filled + "░" * (10 - filled)

                embed.add_field(
                    name="Progress",
                    value=f"{bar} {percent}%",
                    inline=False,
                )
                embed.add_field(
                    name="Current Step",
                    value=message,
                    inline=False,
                )

            # Add error info if failed
            if status == "FAILURE" and result.get("error"):
                embed.add_field(
                    name="Error",
                    value=result["error"][:1000],
                    inline=False,
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            await interaction.followup.send(
                f"❌ Failed to get task status: {str(e)}",
                ephemeral=True,
            )

    def _get_status_color(self, status: str) -> discord.Color:
        """Get color for task status."""
        colors = {
            "PENDING": discord.Color.light_gray(),
            "STARTED": discord.Color.blue(),
            "PROGRESS": discord.Color.yellow(),
            "SUCCESS": discord.Color.green(),
            "FAILURE": discord.Color.red(),
            "REVOKED": discord.Color.dark_red(),
            "RETRY": discord.Color.orange(),
        }
        return colors.get(status, discord.Color.default())

    @app_commands.command(
        name="research_queue",
        description="View the current research task queue",
    )
    async def research_queue(self, interaction: discord.Interaction) -> None:
        """View the current research task queue.

        Args:
            interaction: Discord interaction
        """
        await interaction.response.defer(thinking=True)

        try:
            queue_info = get_queue_status()

            embed = discord.Embed(
                title="📋 Research Queue Status",
                color=discord.Color.blue(),
            )

            # Count tasks in different states
            active_count = 0
            scheduled_count = 0
            reserved_count = 0

            for worker, tasks in queue_info.get("active", {}).items():
                active_count += len(tasks)

            for worker, tasks in queue_info.get("scheduled", {}).items():
                scheduled_count += len(tasks)

            for worker, tasks in queue_info.get("reserved", {}).items():
                reserved_count += len(tasks)

            embed.add_field(
                name="🔄 Active",
                value=str(active_count),
                inline=True,
            )
            embed.add_field(
                name="⏳ Scheduled",
                value=str(scheduled_count),
                inline=True,
            )
            embed.add_field(
                name="📦 Reserved",
                value=str(reserved_count),
                inline=True,
            )

            # Show user's active tasks
            user_tasks = [
                t for t in self.active_tasks.values() if t.get("user_id") == interaction.user.id
            ]

            if user_tasks:
                tasks_text = ""
                for task in user_tasks[:5]:
                    task_id = task.get("task_id", "unknown")[:8]
                    task_type = task.get("task_type", "unknown")
                    tasks_text += f"• `{task_id}...` - {task_type}\n"

                embed.add_field(
                    name="Your Active Tasks",
                    value=tasks_text or "None",
                    inline=False,
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            await interaction.followup.send(
                f"❌ Failed to get queue status: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(
        name="research_cancel",
        description="Cancel a research task",
    )
    @app_commands.describe(task_id="The task ID to cancel")
    async def research_cancel(
        self,
        interaction: discord.Interaction,
        task_id: str,
    ) -> None:
        """Cancel a research task.

        Args:
            interaction: Discord interaction
            task_id: Task ID to cancel
        """
        await interaction.response.defer(thinking=True)

        try:
            # Check if user owns this task
            task_info = self.active_tasks.get(task_id)

            if task_info and task_info.get("user_id") != interaction.user.id:
                # Check if user has admin permissions
                if not interaction.permissions.administrator:
                    await interaction.followup.send(
                        "❌ You can only cancel your own tasks.",
                        ephemeral=True,
                    )
                    return

            # Revoke the task
            success = revoke_task(task_id, terminate=True)

            if success:
                # Remove from tracking
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                if task_id in self.task_notifications:
                    del self.task_notifications[task_id]

                embed = discord.Embed(
                    title="🚫 Task Cancelled",
                    description=f"Task `{task_id}` has been cancelled.",
                    color=discord.Color.orange(),
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "❌ Failed to cancel task. It may have already completed.",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Failed to cancel task: {e}")
            await interaction.followup.send(
                f"❌ Failed to cancel task: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(
        name="research_compare",
        description="Compare multiple options",
    )
    @app_commands.describe(
        items="Comma-separated list of items to compare",
        criteria="Comma-separated comparison criteria",
    )
    async def research_compare(
        self,
        interaction: discord.Interaction,
        items: str,
        criteria: str = "price,features,quality",
    ) -> None:
        """Compare multiple options.

        Args:
            interaction: Discord interaction
            items: Items to compare (comma-separated)
            criteria: Comparison criteria (comma-separated)
        """
        await interaction.response.defer(thinking=True)

        try:
            # Parse items and criteria
            item_list = [item.strip() for item in items.split(",")]
            criteria_list = [c.strip() for c in criteria.split(",")]

            if len(item_list) < 2:
                await interaction.followup.send(
                    "❌ Please provide at least 2 items to compare.",
                    ephemeral=True,
                )
                return

            # Create item dictionaries
            item_dicts = [{"name": item, "attributes": {}} for item in item_list]

            # Submit comparison task
            from research.tasks import comparison

            task = comparison.delay(
                items=item_dicts,
                criteria=criteria_list,
                context="",
            )

            # Track task
            self.active_tasks[task.id] = {
                "task_id": task.id,
                "user_id": interaction.user.id,
                "channel_id": interaction.channel_id,
                "guild_id": interaction.guild_id,
                "query": f"Compare: {items}",
                "task_type": "comparison",
                "created_at": datetime.utcnow().isoformat(),
            }
            self.task_notifications[task.id] = interaction.channel_id

            embed = discord.Embed(
                title="⚖️ Comparison Started",
                description="Your comparison task has been queued.",
                color=discord.Color.gold(),
            )
            embed.add_field(
                name="Items",
                value=", ".join(item_list),
                inline=False,
            )
            embed.add_field(
                name="Criteria",
                value=", ".join(criteria_list),
                inline=False,
            )
            embed.add_field(
                name="Task ID",
                value=f"`{task.id}`",
                inline=True,
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to start comparison: {e}")
            await interaction.followup.send(
                f"❌ Failed to start comparison: {str(e)}",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    """Add the research cog to the bot."""
    await bot.add_cog(ResearchCog(bot))
    logger.info("Research cog loaded")
