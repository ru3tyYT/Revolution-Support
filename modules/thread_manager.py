# modules/thread_manager.py
"""
Thread manager: posts welcome, handles inactivity watcher, interactions delegated from bot.
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from discord import Embed, ButtonStyle
from discord.ui import View, Button
from modules import prompts, fix_store, ai_client
import bot_state
import bot_history
import logging
logger = logging.getLogger("thread_manager")

INACTIVITY_HOURS = 12
CHECK_INTERVAL_SECONDS = 60 * 30  # Check every 30 minutes
SUPPORT_FORUM_ID = int(os.getenv("SUPPORT_FORUM_ID", "1411119542456811722"))
DUCK_FOOTER = "Made with ❤️ by duck"

class ThreadManager:
    def __init__(self, bot, ai_client):
        self.bot = bot
        self.ai_client = ai_client
        self._posted_inactivity = {}  # thread_id -> timestamp of last inactivity post

    async def inactivity_watcher(self):
        """Check for inactive threads every 30 minutes and post review buttons"""
        await self.bot.wait_until_ready()
        logger.info("Inactivity watcher started")
        
        while not self.bot.is_closed():
            try:
                if not bot_state.is_enabled("bot") or not bot_state.is_enabled("mark_for_review"):
                    await asyncio.sleep(CHECK_INTERVAL_SECONDS)
                    continue
                
                now = datetime.now(timezone.utc)
                threads_checked = 0
                threads_marked = 0
                
                for guild in self.bot.guilds:
                    for channel in guild.channels:
                        # Check if this is a forum channel
                        if hasattr(channel, 'type') and str(channel.type) == 'forum':
                            # Only check the support forum
                            if channel.id != SUPPORT_FORUM_ID:
                                continue
                            
                            # Get active threads
                            try:
                                async for thread in channel.archived_threads(limit=100):
                                    threads_checked += 1
                                    result = await self.check_thread_inactivity(thread, now)
                                    if result:
                                        threads_marked += 1
                                        # Add delay between posts to avoid rate limits
                                        await asyncio.sleep(2)
                                    
                                for thread in channel.threads:
                                    threads_checked += 1
                                    result = await self.check_thread_inactivity(thread, now)
                                    if result:
                                        threads_marked += 1
                                        # Add delay between posts to avoid rate limits
                                        await asyncio.sleep(2)
                            except Exception as e:
                                logger.error(f"Error checking threads in {channel.name}: {e}")
                
                if threads_marked > 0:
                    logger.info(f"Marked {threads_marked} threads for review out of {threads_checked} checked")
                
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
            except Exception as e:
                logger.exception(f"Error in inactivity_watcher: {e}")
                await asyncio.sleep(60)

    async def check_thread_inactivity(self, thread, now):
        """Check if a thread is inactive and post review buttons if needed"""
        try:
            # Skip if thread is locked or archived
            if thread.locked or thread.archived:
                return False
            
            # Check if thread has a "resolved" tag
            if hasattr(thread, 'applied_tags'):
                for tag in thread.applied_tags:
                    if tag.name.lower() in ['resolved', 'solved', 'closed']:
                        return False
            
            # Get the last message
            try:
                last_message = None
                async for msg in thread.history(limit=1):
                    last_message = msg
                    break
                
                if not last_message:
                    return False
                
                # Calculate inactivity time
                inactivity = now - last_message.created_at
                
                # Check if thread has been inactive for more than INACTIVITY_HOURS
                if inactivity > timedelta(hours=INACTIVITY_HOURS):
                    # Check if we've already posted recently (don't spam)
                    last_post = self._posted_inactivity.get(thread.id)
                    if last_post:
                        time_since_last_post = now - last_post
                        if time_since_last_post < timedelta(hours=INACTIVITY_HOURS):
                            return False  # Already posted recently
                    
                    # Post the review buttons
                    await self.post_inactivity_buttons(thread)
                    self._posted_inactivity[thread.id] = now
                    return True
            except Exception as e:
                logger.error(f"Error checking thread history for {thread.name}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error in check_thread_inactivity: {e}")
            return False

    async def post_inactivity_buttons(self, thread):
        """Post review buttons to an inactive thread"""
        try:
            # Get thread owner - handle cases where owner might be None
            thread_owner = thread.owner
            
            # Try to fetch owner if not immediately available
            if not thread_owner and thread.owner_id:
                try:
                    thread_owner = await thread.guild.fetch_member(thread.owner_id)
                except:
                    pass
            
            if not thread_owner:
                logger.warning(f"Could not find owner for thread: {thread.name} (ID: {thread.id}, Owner ID: {thread.owner_id})")
                # Still post buttons but without mentioning owner
                view = View(timeout=None)
                view.add_item(Button(
                    style=ButtonStyle.success,
                    label="Solved ✅",
                    custom_id=f"mark_solved:{thread.id}"
                ))
                view.add_item(Button(
                    style=ButtonStyle.danger,
                    label="Unsolved ❌",
                    custom_id=f"mark_unsolved:{thread.id}"
                ))
                
                embed = Embed(
                    title="⏰ Inactivity Check",
                    description=f"This thread has been inactive for 12 hours.\n\nIs this issue resolved? Please let us know:",
                    color=0xffa500
                )
                embed.set_footer(text=DUCK_FOOTER)
                
                await thread.send(embed=embed, view=view)
                logger.info(f"Posted inactivity buttons to thread (no owner mention): {thread.name} (ID: {thread.id})")
                bot_history.log_action("inactivity_check", "System", f"Posted review buttons in: {thread.name} (owner not found)", str(thread.id))
                return
            
            view = View(timeout=None)
            view.add_item(Button(
                style=ButtonStyle.success,
                label="Solved ✅",
                custom_id=f"mark_solved:{thread.id}"
            ))
            view.add_item(Button(
                style=ButtonStyle.danger,
                label="Unsolved ❌",
                custom_id=f"mark_unsolved:{thread.id}"
            ))
            
            embed = Embed(
                title="⏰ Inactivity Check",
                description=f"This thread has been inactive for 12 hours.\n\nIs your issue resolved? Please let us know:",
                color=0xffa500
            )
            embed.set_footer(text=DUCK_FOOTER)
            
            # ACTUALLY PING the user with content parameter
            await thread.send(content=f"{thread_owner.mention}", embed=embed, view=view)
            logger.info(f"Posted inactivity buttons to thread: {thread.name} (ID: {thread.id})")
            bot_history.log_action("inactivity_check", "System", f"Posted review buttons in: {thread.name}", str(thread.id))
            
        except Exception as e:
            logger.exception(f"Failed posting inactivity buttons to {thread.name}: {e}")

    async def handle_new_thread(self, thread):
        """Handle new thread creation - post welcome message"""
        try:
            # Check if autoresponse is enabled
            if not bot_state.is_enabled("autoresponse"):
                return
            
            # Only auto-respond in the specific support forum
            if thread.parent_id != SUPPORT_FORUM_ID:
                return
            
            view = View(timeout=None)
            view.add_item(Button(
                label="Generate AI Fix",
                style=ButtonStyle.primary,
                custom_id="generate_fix"
            ))
            
            embed = Embed(
                title="👋 Welcome to Support!",
                description="Please describe your issue in detail. When ready, click the button below to generate AI support suggestions.\n\n**Tips for better help:**\n• Include error messages\n• Attach relevant screenshots/logs\n• Describe what you've already tried",
                color=0x00FF00
            )
            embed.set_footer(text=DUCK_FOOTER)
            
            await thread.send(embed=embed, view=view)
            logger.info(f"Posted welcome message in new thread: {thread.name}")
            bot_history.log_action("thread_create", "System", f"Welcome message posted: {thread.name}", str(thread.id))
            
        except Exception as e:
            logger.exception(f"Error in handle_new_thread: {e}")
