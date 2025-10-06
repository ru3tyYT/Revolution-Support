# modules/thread_manager.py
"""
Thread manager: posts welcome, handles inactivity watcher, interactions delegated from bot.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from discord import Embed, ButtonStyle
from discord.ui import View, Button
from modules import prompts, fix_store, ai_client
import logging

logger = logging.getLogger("thread_manager")

INACTIVITY_HOURS = 12
CHECK_INTERVAL_SECONDS = 60 * 30  # 30 minutes

class ThreadManager:
    def __init__(self, bot, ai_client):
        self.bot = bot
        self.ai_client = ai_client
        self._posted_inactivity = {}  # thread_id -> timestamp

    async def inactivity_watcher(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = datetime.now(timezone.utc)
                for guild in self.bot.guilds:
                    for ch in guild.channels:
                        if getattr(ch, "is_forum", lambda: False)():
                            for thread in getattr(ch, "threads", []):
                                last = thread.last_message
                                if not last: continue
                                inactivity = now - last.created_at
                                if inactivity > timedelta(hours=INACTIVITY_HOURS) and not thread.locked:
                                    last_post = self._posted_inactivity.get(thread.id)
                                    if not last_post or (now - last_post) > timedelta(hours=INACTIVITY_HOURS):
                                        await self.post_inactivity_buttons(thread)
                                        self._posted_inactivity[thread.id] = now
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            except Exception:
                logger.exception("Error in inactivity_watcher")
                await asyncio.sleep(60)

    async def post_inactivity_buttons(self, thread):
        v = View()
        v.add_item(Button(style=ButtonStyle.success, label="Solved ✅", custom_id=f"mark_solved:{thread.id}"))
        v.add_item(Button(style=ButtonStyle.danger, label="Unsolved ❌", custom_id=f"mark_unsolved:{thread.id}"))
        try:
            await thread.send("Mark this thread as solved or unsolved:", view=v)
        except Exception:
            logger.exception("Failed posting inactivity buttons")

    async def handle_new_thread(self, thread):
        try:
            v = View()
            v.add_item(Button(label="Generate AI Fix", style=ButtonStyle.primary, custom_id="generate_fix"))
            embed = Embed(title="Welcome!", description="Describe your issue and click the button to generate AI support suggestions.", color=0x00FF00)
            await thread.send(embed=embed, view=v)
        except Exception:
            logger.exception("Error in handle_new_thread")

    async def handle_interaction(self, interaction, session):
        # this is mostly handled in bot.py, but kept here for extensibility
        # we forward to bot-level handlers - currently not used
        pass

    async def handle_say_command(self, interaction, message, ai_mode, session):
        await interaction.response.defer(ephemeral=True)
        final = message
        if ai_mode:
            final = await self.ai_client.generate_fix(f"Enhance this message for clarity and professionalism:\n{message}")
        embed = Embed(title="Bot Message", description=final, color=0x00FFFF)
        await interaction.followup.send(embed=embed)
