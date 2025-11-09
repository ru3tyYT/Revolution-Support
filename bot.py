import os
import logging
import discord
from discord import app_commands, Embed, ButtonStyle
from discord.ui import View, Button
from dotenv import load_dotenv
import asyncio
import re
from io import BytesIO
import time
from datetime import datetime, timezone

from modules.ai_client import AIClient
from modules.thread_manager import ThreadManager
from modules import fix_store, prompts, utils, ocr_handler, trained_responses
import api_usage
import bot_history
import permissions
import bot_state

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("bot")
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPPORT_ROLE_ID = os.getenv("SUPPORT_ROLE_ID")
BACKUP_WEBHOOK_URL = os.getenv("BACKUP_WEBHOOK_URL")
SUPPORT_FORUM_ID = int(os.getenv("SUPPORT_FORUM_ID", "1411119542456811722"))

# Permission System
ADMIN_ROLE_IDS = [1324169948444102848, 1429151393851379842, 1327057500242972702]
STAFF_ROLE_IDS = [1422106035337826315, 1419081648435237036]  # Both can use everything except admin commands

DUCK_FOOTER = "Made with ❤️ by duck"
BOT_START_TIME = time.time()

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is required in .env file")

def strip_markdown_embeds(text: str) -> str:
    """Remove markdown embed syntax from AI responses"""
    text = re.sub(r'```json\s*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'```(.*?)```', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text.strip()

def has_admin_role(interaction: discord.Interaction) -> bool:
    """Check if user has any admin role - FULL ACCESS"""
    if not hasattr(interaction.user, 'roles'):
        return False
    user_role_ids = [role.id for role in interaction.user.roles]
    return any(role_id in ADMIN_ROLE_IDS for role_id in user_role_ids)

def has_staff_role(interaction: discord.Interaction) -> bool:
    """Check if user has any staff role"""
    if not hasattr(interaction.user, 'roles'):
        return False
    user_role_ids = [role.id for role in interaction.user.roles]
    return any(role_id in STAFF_ROLE_IDS for role_id in user_role_ids)

def can_use_command(interaction: discord.Interaction) -> bool:
    """Check if user can use regular commands"""
    return has_admin_role(interaction) or has_staff_role(interaction)

def can_use_admin_only(interaction: discord.Interaction) -> bool:
    """Check if user can use admin-only commands"""
    return has_admin_role(interaction)

def get_uptime() -> str:
    """Get bot uptime as formatted string"""
    uptime_seconds = int(time.time() - BOT_START_TIME)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    else:
        return f"{minutes}m {seconds}s"

class ToggleView(View):
    """Interactive view for toggling bot features"""
    def __init__(self, mode: str):
        super().__init__(timeout=300)
        self.mode = mode
        self.setup_buttons()
    
    def get_feature_display_name(self, feature_name: str) -> str:
        """Convert feature name to display format"""
        display_names = {
            "bot": "BOT",
            "autoresponse": "Auto Response",
            "auto_analyze_solved": "Auto Analyze Solved",
            "ocr": "OCR",
            "ask": "Ask Command",
            "say": "Say Command",
            "stats": "Stats Command",
            "analyze": "Analyze Command",
            "search": "Search Command",
            "fix": "Fix Command",
            "history": "History Command",
            "mark_for_review": "Mark For Review"
        }
        return display_names.get(feature_name, feature_name.replace('_', ' ').title())
    
    def setup_buttons(self):
        features = bot_state.get_all_states()
        
        if self.mode == 'status':
            for feature_name, is_enabled in features.items():
                button = Button(
                    label=self.get_feature_display_name(feature_name),
                    style=ButtonStyle.success if is_enabled else ButtonStyle.danger,
                    custom_id=f"status_{feature_name}",
                    disabled=True
                )
                self.add_item(button)
        else:
            for feature_name, is_enabled in features.items():
                if self.mode == 'enable' and is_enabled:
                    continue
                if self.mode == 'disable' and not is_enabled:
                    continue
                
                button = Button(
                    label=self.get_feature_display_name(feature_name),
                    style=ButtonStyle.success if self.mode == 'enable' else ButtonStyle.danger,
                    custom_id=f"{self.mode}_{feature_name}"
                )
                button.callback = self.create_callback(feature_name)
                self.add_item(button)
    
    def create_callback(self, feature_name: str):
        async def button_callback(interaction: discord.Interaction):
            if not can_use_admin_only(interaction):
                await interaction.response.send_message("⚠️ Only admins can toggle features.", ephemeral=True)
                return
            
            try:
                if self.mode == 'enable':
                    bot_state.enable(feature_name)
                    display_name = self.get_feature_display_name(feature_name)
                    await interaction.response.send_message(f"✅ **{display_name}** has been enabled!", ephemeral=False)
                    bot_history.log_action("enable", interaction.user.name, f"Enabled: {feature_name}", "System")
                else:
                    bot_state.disable(feature_name)
                    display_name = self.get_feature_display_name(feature_name)
                    
                    if feature_name == "bot":
                        await interaction.response.send_message(f"🔴 **{display_name}** has been disabled! Bot is now in kill switch mode.", ephemeral=False)
                    else:
                        await interaction.response.send_message(f"🔴 **{display_name}** has been disabled!", ephemeral=False)
                    
                    bot_history.log_action("disable", interaction.user.name, f"Disabled: {feature_name}", "System")
                
                self.clear_items()
                self.setup_buttons()
                await interaction.message.edit(view=self)
            except Exception as e:
                logger.error(f"Error toggling feature: {e}")
                await interaction.response.send_message(f"⚠️ Error: {str(e)}", ephemeral=True)
        
        return button_callback

class SupportBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.ai_client = AIClient(api_key=GEMINI_API_KEY, max_concurrency=2)
        self.thread_manager = ThreadManager(self, self.ai_client)
        self.daily_task = None

    async def setup_hook(self):
        await self.ai_client.init_session()
        self.loop.create_task(self.thread_manager.inactivity_watcher())
        self.daily_task = self.loop.create_task(self.daily_report_task())
        
        logger.info("Registering slash commands...")
        try:
            if GUILD_ID:
                guild = discord.Object(id=int(GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(f"✅ Synced {len(synced)} commands to guild {GUILD_ID}")
            else:
                synced = await self.tree.sync()
                logger.info(f"✅ Synced {len(synced)} commands globally")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def daily_report_task(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                import datetime
                tomorrow = datetime.datetime.now(datetime.timezone.utc).date() + datetime.timedelta(days=1)
                midnight = datetime.datetime.combine(tomorrow, datetime.time.min, tzinfo=datetime.timezone.utc)
                seconds_until_midnight = (midnight - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
                
                await asyncio.sleep(seconds_until_midnight)
                await self.send_daily_report()
                
            except Exception as e:
                logger.error(f"Error in daily_report_task: {e}")
                await asyncio.sleep(3600)

    async def send_daily_report(self):
        if not BACKUP_WEBHOOK_URL:
            return
        
        try:
            import aiohttp
            from datetime import datetime, timezone
            
            today_stats = api_usage.get_today_stats()
            fixes = fix_store.load_fixes()
            history = bot_history.get_recent_history(20)
            
            embed = Embed(title="📊 Daily Bot Report", color=0x3498db, timestamp=datetime.now(timezone.utc))
            embed.add_field(name="API Requests", value=str(today_stats.get("requests", 0)), inline=True)
            embed.add_field(name="API Cost", value=f"${today_stats.get('cost', 0):.4f}", inline=True)
            embed.add_field(name="Total Fixes", value=str(len(fixes)), inline=True)
            
            action_summary = {}
            for entry in history:
                action = entry.get("action_type", "unknown")
                action_summary[action] = action_summary.get(action, 0) + 1
            
            actions_text = "\n".join([f"• {k}: {v}" for k, v in list(action_summary.items())[:5]])
            embed.add_field(name="Recent Actions", value=actions_text or "None", inline=False)
            embed.set_footer(text=DUCK_FOOTER)
            
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(BACKUP_WEBHOOK_URL, session=session)
                await webhook.send(embed=embed)
            
            logger.info("✅ Daily report sent")
            bot_history.log_action("daily_report", "System", "Daily report sent", "Webhook")
            
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")

    async def close(self):
        if self.daily_task:
            self.daily_task.cancel()
        await self.ai_client.close_session()
        await super().close()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
client = SupportBot(intents=intents)

@client.event
async def on_ready():
    logger.info('='*50)
    logger.info(f'Bot Online: {client.user.name}')
    logger.info(f'Bot ID: {client.user.id}')
    logger.info(f'Guilds: {len(client.guilds)}')
    logger.info('='*50)
    bot_history.log_action("bot_start", "System", "Bot started successfully")

@client.event
async def on_thread_create(thread: discord.Thread):
    await asyncio.sleep(2)
    await client.thread_manager.handle_new_thread(thread)

@client.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    
    custom_id = interaction.data.get("custom_id", "")
    
    if custom_id == "generate_fix":
        await handle_generate_fix_button(interaction)
    elif custom_id.startswith("mark_solved:"):
        await handle_solved_button(interaction)
    elif custom_id.startswith("mark_unsolved:"):
        await handle_unsolved_button(interaction)
    elif custom_id.startswith("feedback_"):
        await handle_feedback_button(interaction)
    elif custom_id == "save_analysis":
        await handle_save_analysis_button(interaction)
    elif custom_id.startswith("save_solved:"):
        await handle_save_solved_analysis_button(interaction)

async def handle_save_analysis_button(interaction: discord.Interaction):
    """Handle save analysis button - ADMIN ONLY"""
    if not has_admin_role(interaction):
        try:
            await interaction.response.send_message("⚠️ Only admins can save analysis to the database.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    try:
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            analysis_text = embed.description
            
            confidence = 0.7
            if embed.footer and embed.footer.text:
                footer_text = embed.footer.text
                if "Confidence:" in footer_text:
                    try:
                        conf_str = footer_text.split("Confidence:")[1].split("%")[0].strip()
                        confidence = float(conf_str) / 100
                    except:
                        pass
            
            thread_name = interaction.channel.name if interaction.channel else "Unknown"
            
            fix_store.add_fix(
                source="analyze_command",
                thread_id=str(interaction.channel_id),
                thread_name=thread_name,
                problem_summary=f"Analysis: {thread_name}",
                fix_text=analysis_text,
                confidence=confidence
            )
            
            await interaction.followup.send("✅ Analysis saved to fixes database!", ephemeral=True)
            
            new_view = View()
            save_button = Button(
                style=ButtonStyle.success,
                label="✅ Saved",
                custom_id="save_analysis",
                disabled=True
            )
            new_view.add_item(save_button)
            await interaction.message.edit(view=new_view)
            
            bot_history.log_action("save_analysis", interaction.user.name, f"Saved analysis for: {thread_name}", str(interaction.channel_id))
        else:
            await interaction.followup.send("⚠️ Could not find analysis text.", ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error saving analysis: {e}")
        await interaction.followup.send(f"⚠️ Error saving: {str(e)}", ephemeral=True)

async def handle_save_solved_analysis_button(interaction: discord.Interaction):
    """Handle save solved analysis button - STAFF ONLY"""
    if not can_use_command(interaction):
        try:
            await interaction.response.send_message("⚠️ Only staff can save analysis to the database.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    try:
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            analysis_text = embed.description
            
            confidence = 0.7
            if embed.footer and embed.footer.text:
                footer_text = embed.footer.text
                if "Confidence:" in footer_text:
                    try:
                        conf_str = footer_text.split("Confidence:")[1].split("%")[0].strip()
                        confidence = float(conf_str) / 100
                    except:
                        pass
            
            thread_name = interaction.channel.name if interaction.channel else "Unknown"
            
            fix_store.add_fix(
                source="solved_auto_analysis",
                thread_id=str(interaction.channel_id),
                thread_name=thread_name,
                problem_summary=f"Solved: {thread_name}",
                fix_text=analysis_text,
                confidence=confidence
            )
            
            await interaction.followup.send("✅ Solved thread analysis saved to fixes database!", ephemeral=True)
            
            new_view = View()
            save_button = Button(
                style=ButtonStyle.success,
                label="✅ Saved to Database",
                custom_id=f"save_solved:{interaction.channel.id}",
                disabled=True
            )
            new_view.add_item(save_button)
            await interaction.message.edit(view=new_view)
            
            bot_history.log_action("save_solved_analysis", interaction.user.name, f"Saved solved analysis for: {thread_name}", str(interaction.channel_id))
        else:
            await interaction.followup.send("⚠️ Could not find analysis text.", ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error saving solved analysis: {e}")
        await interaction.followup.send(f"⚠️ Error saving: {str(e)}", ephemeral=True)

async def handle_generate_fix_button(interaction: discord.Interaction):
    """Handle the AI fix generation button"""
    if not bot_state.is_enabled("bot"):
        try:
            await interaction.response.send_message("⚠️ Bot is currently disabled.", ephemeral=True)
        except:
            pass
        return
    
    is_staff = has_staff_role(interaction) or has_admin_role(interaction)
    is_owner = False
    
    if isinstance(interaction.channel, discord.Thread):
        is_owner = interaction.channel.owner_id == interaction.user.id
    
    if not is_staff and not is_owner:
        try:
            await interaction.response.send_message("⚠️ Only staff or the thread creator can use this button.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=False)
        
        # Show typing indicator
        async def send_with_typing():
            async with interaction.channel.typing():
                messages = []
                async for msg in interaction.channel.history(limit=150):
                    if not msg.author.bot:
                        messages.append(f"{msg.author.name}: {msg.content}")
                
                if not messages:
                    await interaction.followup.send("⚠️ No messages found.", ephemeral=True)
                    return None
                
                messages.reverse()
                thread_text = "\n".join(messages)
                
                ocr_text = None
                if bot_state.is_enabled("ocr"):
                    async for msg in interaction.channel.history(limit=20):
                        if msg.attachments:
                            for att in msg.attachments:
                                if att.content_type and att.content_type.startswith("image/"):
                                    try:
                                        image_data = await att.read()
                                        ocr_result = await ocr_handler.extract_text_from_image(BytesIO(image_data))
                                        if ocr_result:
                                            ocr_text = ocr_result
                                            break
                                    except:
                                        pass
                        if ocr_text:
                            break
                
                log_excerpt = None
                async for msg in interaction.channel.history(limit=50):
                    if msg.attachments:
                        for att in msg.attachments:
                            if att.filename.endswith(('.txt', '.log')):
                                try:
                                    content = await att.read()
                                    text = content.decode('utf-8', errors='ignore')
                                    log_excerpt = utils.extract_key_log_lines(text)
                                    break
                                except:
                                    pass
                    if log_excerpt:
                        break
                
                thread_title = interaction.channel.name
                
                trained_answer = trained_responses.get_trained_response(thread_title, thread_text)
                if trained_answer:
                    return (trained_answer, 0.95, thread_title)
                else:
                    similar_fixes = fix_store.get_similar_fixes(thread_title, k=5)
                    
                    system_context = """You are a technical support expert. Provide clear, actionable solutions.
- Be concise but thorough
- Give step-by-step instructions when needed
- If confidence is low, provide multiple possible solutions
- Always summarize your answer at the end"""
                    
                    prompt = f"""{system_context}

Thread Title: {thread_title}
Thread Messages: {thread_text[:4000]}"""
                    
                    if ocr_text:
                        prompt += f"\n\nText from Images: {ocr_text[:500]}"
                    
                    if log_excerpt:
                        prompt += f"\n\nLog Excerpt: {log_excerpt[:1000]}"
                    
                    if similar_fixes:
                        prompt += "\n\n**Similar Issues from Database:**\n"
                        for i, fix in enumerate(similar_fixes, 1):
                            problem = fix.get("problem_summary", "")[:150]
                            solution = fix.get("fix", "")[:300]
                            prompt += f"\n{i}. Problem: {problem}\n   Solution: {solution}\n"
                    
                    prompt += """

Provide a clear solution. If you're not highly confident, suggest multiple approaches.
Summarize your answer concisely."""
                    
                    ai_response = await client.ai_client.generate_fix(prompt)
                    api_usage.track_request(prompt, ai_response)
                    confidence = utils.confidence_heuristic(ai_response)
                    
                    return (ai_response, confidence, thread_title)
        
        result = await send_with_typing()
        if not result:
            return
        
        ai_response, confidence, thread_title = result
        ai_response = strip_markdown_embeds(ai_response)
        
        fix_store.add_fix(
            source="ai_button",
            thread_id=str(interaction.channel_id),
            thread_name=thread_title,
            problem_summary=thread_title,
            fix_text=ai_response,
            confidence=confidence
        )
        
        embed = Embed(title="🤖 AI-Generated Solution", description=ai_response[:4000], color=0x00FF00)
        embed.set_footer(text=f"Confidence: {confidence:.0%} | {DUCK_FOOTER}")
        
        view = View(timeout=None)
        view.add_item(Button(style=ButtonStyle.success, label="👍 Helpful", custom_id=f"feedback_helpful_{interaction.channel_id}"))
        view.add_item(Button(style=ButtonStyle.danger, label="👎 Not Helpful", custom_id=f"feedback_not_helpful_{interaction.channel_id}"))
        
        await interaction.followup.send(embed=embed, view=view)
        
        try:
            original_message = await interaction.channel.fetch_message(interaction.message.id)
            new_view = View()
            for item in original_message.components[0].children:
                new_button = Button(
                    style=item.style,
                    label=item.label,
                    custom_id=item.custom_id,
                    disabled=True
                )
                new_view.add_item(new_button)
            await original_message.edit(view=new_view)
        except:
            pass
        
        bot_history.log_action("generate_fix_button", interaction.user.name, f"AI fix generated in thread: {thread_title}", str(interaction.channel_id))
    except Exception as e:
        logger.error(f"Error in generate_fix: {e}")
        try:
            await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)
        except:
            pass

async def handle_feedback_button(interaction: discord.Interaction):
    """Handle feedback buttons"""
    try:
        await interaction.response.defer(ephemeral=True)
        
        custom_id = interaction.data.get("custom_id", "")
        feedback_type = "helpful" if "helpful" in custom_id else "not_helpful"
        
        bot_history.log_action("feedback", interaction.user.name, f"Feedback: {feedback_type}", str(interaction.channel_id))
        
        await interaction.followup.send(f"✅ Thank you for your feedback!", ephemeral=True)
        
        try:
            new_view = View()
            for item in interaction.message.components[0].children:
                new_button = Button(
                    style=item.style,
                    label=item.label,
                    custom_id=item.custom_id,
                    disabled=True
                )
                new_view.add_item(new_button)
            await interaction.message.edit(view=new_view)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error in handle_feedback_button: {e}")

async def handle_solved_button(interaction: discord.Interaction):
    is_staff = can_use_command(interaction)
    is_op = False
    
    if isinstance(interaction.channel, discord.Thread):
        is_op = interaction.channel.owner_id == interaction.user.id
    
    if not is_staff and not is_op:
        try:
            await interaction.response.send_message("⚠️ Only staff or the thread creator can mark this as solved.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=False)
    except:
        return
    
    try:
        if isinstance(interaction.channel, discord.Thread):
            parent_channel = interaction.channel.parent
            resolved_tag = None
            
            if hasattr(parent_channel, 'available_tags'):
                for tag in parent_channel.available_tags:
                    if tag.name.lower() == "resolved":
                        resolved_tag = tag
                        break
            
            if resolved_tag:
                await interaction.channel.edit(applied_tags=[resolved_tag], locked=True)
            else:
                await interaction.channel.edit(locked=True)
            
            await interaction.followup.send("✅ Thread marked as solved! Analyzing thread...", ephemeral=False)
            
            if bot_state.is_enabled("auto_analyze_solved"):
                try:
                    messages = []
                    async for msg in interaction.channel.history(limit=150):
                        if not msg.author.bot:
                            messages.append(f"{msg.author.name}: {msg.content}")
                    
                    if messages:
                        messages.reverse()
                        thread_text = "\n".join(messages)
                        thread_title = interaction.channel.name
                        
                        ocr_text = None
                        if bot_state.is_enabled("ocr"):
                            async for msg in interaction.channel.history(limit=20):
                                if msg.attachments:
                                    for att in msg.attachments:
                                        if att.content_type and att.content_type.startswith("image/"):
                                            try:
                                                image_data = await att.read()
                                                ocr_result = await ocr_handler.extract_text_from_image(BytesIO(image_data))
                                                if ocr_result:
                                                    ocr_text = ocr_result
                                                    break
                                            except:
                                                pass
                                if ocr_text:
                                    break
                        
                        system_context = "You are a technical support analyst. Provide concise, accurate summaries. Focus on key information without unnecessary elaboration."
                        
                        prompt = f"""{system_context}

Analyze this SOLVED support thread. Summarize the key points concisely.

Thread Title: {thread_title}
Thread Messages: {thread_text[:4000]}"""
                        
                        if ocr_text:
                            prompt += f"\n\nText from Images: {ocr_text[:500]}"
                        
                        prompt += """

Provide:
1. Brief problem summary (2-3 sentences)
2. Solution that worked (be specific)
3. Key steps taken
4. Confidence percentage

Keep response focused and actionable."""
                        
                        ai_response = await client.ai_client.generate_fix(prompt)
                        api_usage.track_request(prompt, ai_response)
                        ai_response = strip_markdown_embeds(ai_response)
                        
                        confidence = utils.confidence_heuristic(ai_response)
                        
                        embed = Embed(
                            title=f"📊 Auto-Analysis: {thread_title[:80]}",
                            description=ai_response[:4000],
                            color=0x00ff00
                        )
                        embed.set_footer(text=f"Confidence: {confidence:.0%} | {DUCK_FOOTER}")
                        
                        view = View(timeout=None)
                        save_button = Button(
                            style=ButtonStyle.success,
                            label="💾 Save to Database (Staff Only)",
                            custom_id=f"save_solved:{interaction.channel.id}"
                        )
                        view.add_item(save_button)
                        
                        await interaction.channel.send(embed=embed, view=view)
                        bot_history.log_action("auto_analyze_solved", "System", f"Auto-analyzed solved thread: {thread_title}", str(interaction.channel_id))
                except Exception as e:
                    logger.error(f"Error auto-analyzing solved thread: {e}")
            
            bot_history.log_action("mark_solved", interaction.user.name, f"Thread marked as solved: {interaction.channel.name}", str(interaction.channel_id))
    except Exception as e:
        logger.error(f"Failed to lock/tag thread: {e}")

async def handle_unsolved_button(interaction: discord.Interaction):
    is_staff = can_use_command(interaction)
    is_op = False
    
    if isinstance(interaction.channel, discord.Thread):
        is_op = interaction.channel.owner_id == interaction.user.id
    
    if not is_staff and not is_op:
        try:
            await interaction.response.send_message("⚠️ Only staff or the thread creator can mark this as unsolved.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.send_message("❌ Thread marked as unsolved.", ephemeral=False)
    except:
        return
    
    if SUPPORT_ROLE_ID:
        try:
            await interaction.channel.send(f"<@&{SUPPORT_ROLE_ID}> This thread needs attention.")
            bot_history.log_action("mark_unsolved", interaction.user.name, f"Thread marked as unsolved: {interaction.channel.name}", str(interaction.channel_id))
        except:
            pass

@client.tree.command(name="fix", description="Manually add a fix to the knowledge base")
@app_commands.describe(problem="Brief description of the problem", solution="The solution or fix", confidence="Confidence level (0.0 to 1.0)")
async def fix_command(interaction: discord.Interaction, problem: str, solution: str, confidence: float = 0.8):
    if not can_use_command(interaction):
        try:
            await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        except:
            pass
        return
    
    if not bot_state.is_enabled("bot") or not bot_state.is_enabled("fix"):
        try:
            await interaction.response.send_message("⚠️ This command is currently disabled.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    try:
        entry = fix_store.add_fix(
            source="manual",
            thread_id=str(interaction.channel_id) if interaction.channel else None,
            thread_name=interaction.channel.name if interaction.channel else None,
            problem_summary=problem,
            fix_text=solution,
            confidence=max(0.0, min(1.0, confidence))
        )
        
        embed = Embed(title="✅ Fix Saved", description=f"**Problem:** {problem}\n**Solution:** {solution[:200]}...", color=0x00FF00)
        embed.add_field(name="ID", value=entry["id"][:8], inline=True)
        embed.add_field(name="Confidence", value=f"{confidence:.0%}", inline=True)
        embed.set_footer(text=DUCK_FOOTER)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        bot_history.log_action("manual_fix", interaction.user.name, f"Added fix: {problem[:50]}", interaction.channel.name if interaction.channel else "DM")
    except Exception as e:
        logger.error(f"Error in fix_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="analyze", description="Analyze the current thread and generate a fix")
async def analyze_command(interaction: discord.Interaction):
    if not can_use_command(interaction):
        try:
            await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        except:
            pass
        return
    
    if not bot_state.is_enabled("bot") or not bot_state.is_enabled("analyze"):
        try:
            await interaction.response.send_message("⚠️ This command is currently disabled.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=False)
    except:
        return
    
    if not interaction.channel:
        await interaction.followup.send("⚠️ Must be used in a thread.", ephemeral=True)
        return
    
    try:
        messages = []
        async for msg in interaction.channel.history(limit=150):
            if not msg.author.bot:
                messages.append(f"{msg.author.name}: {msg.content}")
        
        if not messages:
            await interaction.followup.send("⚠️ No messages to analyze.", ephemeral=True)
            return
        
        messages.reverse()
        thread_text = "\n".join(messages)
        
        thread_title = interaction.channel.name if hasattr(interaction.channel, 'name') else "Unknown Thread"
        
        ocr_text = None
        if bot_state.is_enabled("ocr"):
            async for msg in interaction.channel.history(limit=20):
                if msg.attachments:
                    for att in msg.attachments:
                        if att.content_type and att.content_type.startswith("image/"):
                            try:
                                image_data = await att.read()
                                ocr_result = await ocr_handler.extract_text_from_image(BytesIO(image_data))
                                if ocr_result:
                                    ocr_text = ocr_result
                                    break
                            except:
                                pass
                if ocr_text:
                    break
        
        system_context = "You are a technical support analyst. Provide concise, accurate summaries. Focus on key information without unnecessary elaboration."
        
        prompt = f"""{system_context}

Analyze this support thread. Summarize the key points.

Thread Title: {thread_title}
Thread Messages: {thread_text[:4000]}"""
        
        if ocr_text:
            prompt += f"\n\nText from Images: {ocr_text[:500]}"
        
        prompt += """

Provide:
1. Brief problem summary (2-3 sentences)
2. Key steps taken by the user
3. Current solution or status
4. Your confidence percentage

Keep response focused and actionable."""
        
        ai_response = await client.ai_client.generate_fix(prompt)
        api_usage.track_request(prompt, ai_response)
        ai_response = strip_markdown_embeds(ai_response)
        
        confidence = utils.confidence_heuristic(ai_response)
        
        embed = Embed(title=f"📊 Thread Analysis: {thread_title[:80]}", description=ai_response[:4000], color=0x3498db)
        embed.set_footer(text=f"Confidence: {confidence:.0%} | {DUCK_FOOTER}")
        
        if has_admin_role(interaction):
            view = View(timeout=300)
            save_button = Button(style=ButtonStyle.success, label="💾 Save to Fixes Database", custom_id="save_analysis")
            view.add_item(save_button)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(embed=embed)
        
        bot_history.log_action("analyze", interaction.user.name, f"Analyzed thread: {thread_title}", str(interaction.channel_id))
    except Exception as e:
        logger.error(f"Error in analyze_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="search", description="Search the fix database")
@app_commands.describe(query="Search term or problem description")
async def search_command(interaction: discord.Interaction, query: str):
    if not can_use_command(interaction):
        try:
            await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        except:
            pass
        return
    
    if not bot_state.is_enabled("bot") or not bot_state.is_enabled("search"):
        try:
            await interaction.response.send_message("⚠️ This command is currently disabled.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    try:
        results = fix_store.get_similar_fixes(query, k=5)
        
        if not results:
            await interaction.followup.send(f"❌ No fixes found for: `{query}`", ephemeral=True)
            return
        
        embed = Embed(title=f"🔍 Search Results for: {query}", description=f"Found {len(results)} similar fix(es)", color=0xe67e22)
        
        for i, fix in enumerate(results[:5], 1):
            problem = fix.get("problem_summary", "Unknown")[:100]
            solution = fix.get("fix", "No solution")[:200]
            confidence = fix.get("confidence", 0.5)
            embed.add_field(name=f"{i}. {problem}", value=f"{solution}...\n*Confidence: {confidence:.0%}*", inline=False)
        
        embed.set_footer(text=DUCK_FOOTER)
        await interaction.followup.send(embed=embed, ephemeral=True)
        bot_history.log_action("search", interaction.user.name, f"Searched for: {query}", interaction.channel.name if interaction.channel else "DM")
    except Exception as e:
        logger.error(f"Error in search_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="say", description="Send a message as the bot")
@app_commands.describe(message="The message to send", ai_enhance="Use AI to rewrite and enhance the message")
async def say_command(interaction: discord.Interaction, message: str, ai_enhance: bool = False):
    if not can_use_command(interaction):
        try:
            await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        except:
            pass
        return
    
    if not bot_state.is_enabled("bot") or not bot_state.is_enabled("say"):
        try:
            await interaction.response.send_message("⚠️ This command is currently disabled.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    try:
        final_message = message
        if ai_enhance:
            system_context = "You are a professional message editor. Rewrite messages to be clear and professional. Keep the core meaning but improve clarity."
            prompt = f"{system_context}\n\nRewrite this message professionally:\n\n{message}\n\nProvide only the rewritten message, nothing else."
            final_message = await client.ai_client.generate_fix(prompt)
            api_usage.track_request(prompt, final_message)
            final_message = strip_markdown_embeds(final_message)
        
        embed = Embed(description=final_message, color=0x5865F2)
        embed.set_footer(text=DUCK_FOOTER)
        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ Message sent!", ephemeral=True)
        bot_history.log_action("say", interaction.user.name, f"Sent message: {message[:50]}...", interaction.channel.name if interaction.channel else "DM")
    except Exception as e:
        logger.error(f"Error in say_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="ask", description="Ask the AI a question")
@app_commands.describe(question="Your question for the AI")
async def ask_command(interaction: discord.Interaction, question: str):
    if not can_use_command(interaction):
        try:
            await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        except:
            pass
        return
    
    if not bot_state.is_enabled("bot") or not bot_state.is_enabled("ask"):
        try:
            await interaction.response.send_message("⚠️ This command is currently disabled.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=False)
    except:
        return
    
    try:
        system_context = "You are a helpful AI assistant. Provide clear, concise, and accurate answers. Summarize your response to focus on key information."
        
        prompt = f"""{system_context}

Question: {question}

Provide a brief, focused answer with key points. Be direct and helpful."""
        
        ai_response = await client.ai_client.generate_fix(prompt)
        api_usage.track_request(prompt, ai_response)
        ai_response = strip_markdown_embeds(ai_response)
        
        embed = Embed(title="💬 AI Response", description=ai_response[:4000], color=0x5865F2)
        embed.set_footer(text=f"Q: {question[:80]}... | {DUCK_FOOTER}")
        
        await interaction.followup.send(embed=embed, ephemeral=False)
        bot_history.log_action("ask", interaction.user.name, f"Asked: {question[:50]}...", interaction.channel.name if interaction.channel else "DM")
    except Exception as e:
        logger.error(f"Error in ask_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="backup", description="Backup all fixes to webhook (Admin only)")
async def backup_command(interaction: discord.Interaction):
    if not can_use_admin_only(interaction):
        try:
            await interaction.response.send_message("⚠️ Only admins can use this command.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    if not BACKUP_WEBHOOK_URL:
        await interaction.followup.send("⚠️ Backup webhook not configured.", ephemeral=True)
        return
    
    try:
        fixes = fix_store.load_fixes()
        import aiohttp, json, io
        
        async with aiohttp.ClientSession() as session:
            data = json.dumps(fixes, indent=2)
            file = discord.File(io.BytesIO(data.encode()), filename="fixes_backup.json")
            webhook = discord.Webhook.from_url(BACKUP_WEBHOOK_URL, session=session)
            await webhook.send(content=f"📦 Backup - {len(fixes)} fixes", file=file, username="Support Bot Backup")
        
        await interaction.followup.send(f"✅ Backed up {len(fixes)} fixes!", ephemeral=True)
        bot_history.log_action("backup", interaction.user.name, f"Backed up {len(fixes)} fixes", "Webhook")
    except Exception as e:
        logger.error(f"Error in backup_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="stats", description="Show bot statistics")
async def stats_command(interaction: discord.Interaction):
    if not can_use_command(interaction):
        try:
            await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        except:
            pass
        return
    
    if not bot_state.is_enabled("bot") or not bot_state.is_enabled("stats"):
        try:
            await interaction.response.send_message("⚠️ This command is currently disabled.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    try:
        fixes = fix_store.load_fixes()
        total_fixes = len(fixes)
        ai_fixes = sum(1 for f in fixes if f.get("source") in ["ai_button", "analyze_command"])
        manual_fixes = sum(1 for f in fixes if f.get("source") == "manual")
        confidences = [f.get("confidence") or 0 for f in fixes]
        avg_confidence = sum(confidences) / total_fixes if total_fixes > 0 else 0
        
        today_stats = api_usage.get_today_stats()
        month_stats = api_usage.get_month_stats()
        estimated_monthly = api_usage.estimate_monthly_cost()
        
        embed = Embed(title="📊 Bot Statistics", color=0x3498db)
        embed.add_field(name="Total Fixes", value=str(total_fixes), inline=True)
        embed.add_field(name="AI Generated", value=str(ai_fixes), inline=True)
        embed.add_field(name="Manual Fixes", value=str(manual_fixes), inline=True)
        embed.add_field(name="Avg Confidence", value=f"{avg_confidence:.0%}", inline=True)
        embed.add_field(name="Guilds", value=str(len(client.guilds)), inline=True)
        embed.add_field(name="Status", value="✅ Active", inline=True)
        
        embed.add_field(name="\u200b", value="**💰 API Usage**", inline=False)
        embed.add_field(name="Requests Today", value=str(today_stats.get("requests", 0)), inline=True)
        embed.add_field(name="Cost Today", value=f"${today_stats.get('cost', 0):.4f}", inline=True)
        embed.add_field(name="Monthly Cost", value=f"${month_stats.get('cost', 0):.4f}", inline=True)
        embed.add_field(name="Est. Monthly", value=f"${estimated_monthly:.2f}", inline=True)
        
        embed.set_footer(text=DUCK_FOOTER)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="mark_for_review", description="Mark this thread for review by the original poster")
async def mark_for_review_command(interaction: discord.Interaction):
    if not can_use_command(interaction):
        try:
            await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        except:
            pass
        return
    
    if not isinstance(interaction.channel, discord.Thread):
        try:
            await interaction.response.send_message("⚠️ This command can only be used in threads.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=False)
    except:
        return
    
    if not bot_state.is_enabled("bot") or not bot_state.is_enabled("mark_for_review"):
        try:
            await interaction.followup.send("⚠️ This command is currently disabled.", ephemeral=True)
        except:
            pass
        return
    
    try:
        thread = interaction.channel
        thread_owner = thread.owner
        
        if not thread_owner:
            await interaction.followup.send("⚠️ Could not find the thread owner.", ephemeral=True)
            return
        
        view = View()
        view.add_item(Button(style=ButtonStyle.success, label="Solved ✅", custom_id=f"mark_solved:{thread.id}"))
        view.add_item(Button(style=ButtonStyle.danger, label="Unsolved ❌", custom_id=f"mark_unsolved:{thread.id}"))
        
        embed = Embed(description=f"{thread_owner.mention} Please mark this thread as solved or unsolved:", color=0x3498db)
        embed.set_footer(text=DUCK_FOOTER)
        
        await thread.send(embed=embed, view=view)
        await interaction.followup.send("✅ Review buttons posted and thread owner pinged!", ephemeral=False)
        bot_history.log_action("mark_for_review", interaction.user.name, f"Marked thread for review: {thread.name}", str(thread.id))
    except Exception as e:
        logger.error(f"Error in mark_for_review_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="history", description="View bot action history")
@app_commands.describe(limit="Number of recent actions to show (max 50)")
async def history_command(interaction: discord.Interaction, limit: int = 20):
    if not can_use_command(interaction):
        try:
            await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    if not bot_state.is_enabled("bot") or not bot_state.is_enabled("history"):
        try:
            await interaction.followup.send("⚠️ This command is currently disabled.", ephemeral=True)
        except:
            pass
        return
    
    try:
        limit = min(max(1, limit), 50)
        history = bot_history.get_recent_history(limit)
        
        if not history:
            await interaction.followup.send("📜 No history found.", ephemeral=True)
            return
        
        embed = Embed(title="📜 Bot Action History", color=0x9b59b6)
        embed.set_footer(text=f"Showing last {len(history)} action(s) | {DUCK_FOOTER}")
        
        action_emoji = {
            "bot_start": "🟢", "manual_fix": "✏️", "analyze": "📊", "search": "🔍",
            "say": "💬", "ask": "❓", "mark_solved": "✅", "mark_unsolved": "❌",
            "generate_fix_button": "🤖", "thread_create": "📝", "mark_for_review": "👀",
            "save_analysis": "💾", "backup": "📦", "reload": "🔄", "enable": "🟢", 
            "disable": "🔴", "feedback": "💭", "maintenance": "🔧"
        }
        
        for entry in history[-limit:]:
            timestamp = entry.get("timestamp", "Unknown")[:19]
            action = entry.get("action_type", "unknown")
            user = entry.get("user", "Unknown")
            details = entry.get("details", "No details")
            channel = entry.get("channel", "N/A")
            
            emoji = action_emoji.get(action, "•")
            value = f"**User:** {user}\n**Details:** {details[:100]}\n**Channel:** {channel}"
            
            embed.add_field(
                name=f"{emoji} {action.replace('_', ' ').title()} - {timestamp}",
                value=value,
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        bot_history.log_action("history", interaction.user.name, f"Viewed history (limit: {limit})", "System")
    except Exception as e:
        logger.error(f"Error in history_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="status", description="View bot status and feature states")
async def status_command(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=False)
    except:
        return
    
    try:
        uptime = get_uptime()
        latency = round(client.latency * 1000)
        
        features = bot_state.get_all_states()
        
        embed = Embed(title="🤖 Bot Status Dashboard", color=0x00ff00, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="⏱️ Uptime", value=uptime, inline=True)
        embed.add_field(name="📡 Latency", value=f"{latency}ms", inline=True)
        embed.add_field(name="🌐 Guilds", value=str(len(client.guilds)), inline=True)
        
        enabled_features = [f"✅ {k.replace('_', ' ').title()}" for k, v in features.items() if v]
        disabled_features = [f"❌ {k.replace('_', ' ').title()}" for k, v in features.items() if not v]
        
        features_text = "\n".join(enabled_features + disabled_features) if (enabled_features or disabled_features) else "No features configured"
        embed.add_field(name="🔧 Features Status", value=features_text, inline=False)
        
        embed.set_footer(text=DUCK_FOOTER)
        
        view = ToggleView(mode='status')
        
        await interaction.followup.send(embed=embed, view=view)
        bot_history.log_action("status", interaction.user.name, "Viewed bot status", "System")
    except Exception as e:
        logger.error(f"Error in status_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="enable", description="Enable bot features (Admin only)")
async def enable_command(interaction: discord.Interaction):
    if not can_use_admin_only(interaction):
        try:
            await interaction.response.send_message("⚠️ Only admins can use this command.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=False)
    except:
        return
    
    try:
        features = bot_state.get_all_states()
        disabled_features = [k for k, v in features.items() if not v]
        
        if not disabled_features:
            await interaction.followup.send("✅ All features are already enabled!", ephemeral=False)
            return
        
        feature_descriptions = {
            "bot": "**BOT** - Master kill switch. Disables ALL features including auto-responses.",
            "autoresponse": "**Auto Response** - Automatic welcome message in new support threads.",
            "auto_analyze_solved": "**Auto Analyze Solved** - Automatically analyze threads when marked as solved.",
            "ocr": "**OCR** - Optical Character Recognition for extracting text from images.",
            "ask": "**Ask Command** - `/ask` - Ask the AI a question.",
            "say": "**Say Command** - `/say` - Send a message as the bot.",
            "stats": "**Stats Command** - `/stats` - View bot statistics and usage.",
            "analyze": "**Analyze Command** - `/analyze` - Analyze current thread and generate fix.",
            "search": "**Search Command** - `/search` - Search the fix database.",
            "fix": "**Fix Command** - `/fix` - Manually add a fix to knowledge base.",
            "history": "**History Command** - `/history` - View bot action history.",
            "mark_for_review": "**Mark For Review** - `/mark_for_review` & 12h inactivity checks."
        }
        
        description = "**📋 Available Features to Enable:**\n\n"
        for feature in disabled_features:
            description += feature_descriptions.get(feature, f"**{feature}**") + "\n"
        
        embed = Embed(
            title="🟢 ENABLE BOT FEATURES",
            description=description,
            color=0x00ff00
        )
        embed.set_footer(text="Click a button below to enable that feature | " + DUCK_FOOTER)
        
        view = ToggleView(mode='enable')
        
        await interaction.followup.send(embed=embed, view=view)
        bot_history.log_action("enable_menu", interaction.user.name, "Opened enable menu", "System")
    except Exception as e:
        logger.error(f"Error in enable_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="disable", description="Disable bot features (Admin only)")
async def disable_command(interaction: discord.Interaction):
    if not can_use_admin_only(interaction):
        try:
            await interaction.response.send_message("⚠️ Only admins can use this command.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=False)
    except:
        return
    
    try:
        features = bot_state.get_all_states()
        enabled_features = [k for k, v in features.items() if v]
        
        if not enabled_features:
            await interaction.followup.send("🔴 All features are already disabled!", ephemeral=False)
            return
        
        feature_descriptions = {
            "bot": "**BOT** ⚠️ KILL SWITCH - Disables ALL features including auto-responses. Bot appears offline.",
            "autoresponse": "**Auto Response** - Automatic welcome message in new support threads.",
            "auto_analyze_solved": "**Auto Analyze Solved** - Automatically analyze threads when marked as solved.",
            "ocr": "**OCR** - Optical Character Recognition for extracting text from images.",
            "ask": "**Ask Command** - `/ask` - Ask the AI a question.",
            "say": "**Say Command** - `/say` - Send a message as the bot.",
            "stats": "**Stats Command** - `/stats` - View bot statistics and usage.",
            "analyze": "**Analyze Command** - `/analyze` - Analyze current thread and generate fix.",
            "search": "**Search Command** - `/search` - Search the fix database.",
            "fix": "**Fix Command** - `/fix` - Manually add a fix to knowledge base.",
            "history": "**History Command** - `/history` - View bot action history.",
            "mark_for_review": "**Mark For Review** - `/mark_for_review` & 12h inactivity checks."
        }
        
        description = "**📋 Currently Enabled Features:**\n\n"
        for feature in enabled_features:
            description += feature_descriptions.get(feature, f"**{feature}**") + "\n"
        
        embed = Embed(
            title="🔴 DISABLE BOT FEATURES",
            description=description + "\n⚠️ **Warning:** Disabling 'BOT' will make the bot appear offline for all commands!",
            color=0xff0000
        )
        embed.set_footer(text="Click a button below to disable that feature | " + DUCK_FOOTER)
        
        view = ToggleView(mode='disable')
        
        await interaction.followup.send(embed=embed, view=view)
        bot_history.log_action("disable_menu", interaction.user.name, "Opened disable menu", "System")
    except Exception as e:
        logger.error(f"Error in disable_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="maintenance", description="Post a maintenance announcement (Admin only)")
@app_commands.describe(message="Maintenance message", duration="Expected duration (e.g. '2 hours')")
async def maintenance_command(interaction: discord.Interaction, message: str, duration: str = "Unknown"):
    if not has_admin_role(interaction):
        try:
            await interaction.response.send_message("⚠️ You need admin permission to use this command.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        embed = Embed(title="🔧 Maintenance Announcement", description=message, color=0xffa500)
        embed.add_field(name="Expected Duration", value=duration, inline=True)
        embed.add_field(name="Status", value="In Progress", inline=True)
        embed.set_footer(text=f"Posted by {interaction.user.name} | {DUCK_FOOTER}")
        
        if BACKUP_WEBHOOK_URL:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(BACKUP_WEBHOOK_URL, session=session)
                await webhook.send(embed=embed, username="Maintenance Bot")
        
        await interaction.followup.send("✅ Maintenance announcement sent to webhook!", ephemeral=True)
        bot_history.log_action("maintenance", interaction.user.name, f"Maintenance: {message[:50]}", "Webhook")
        
    except Exception as e:
        logger.error(f"Error in maintenance_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="reload", description="Reload bot commands (Admin only)")
async def reload_command(interaction: discord.Interaction):
    if not has_admin_role(interaction):
        try:
            await interaction.response.send_message("⚠️ You need admin permission to use this command.", ephemeral=True)
        except:
            pass
        return
    
    try:
        await interaction.response.send_message("🔄 Reloading commands...", ephemeral=True)
    except:
        return
    
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            client.tree.clear_commands(guild=guild)
            await client.tree.sync(guild=guild)
            client.tree.copy_global_to(guild=guild)
            await client.tree.sync(guild=guild)
            await interaction.edit_original_response(content="✅ Commands reloaded!")
        else:
            client.tree.clear_commands(guild=None)
            await client.tree.sync()
            await interaction.edit_original_response(content="✅ Commands reloaded!")
        bot_history.log_action("reload", interaction.user.name, "Reloaded bot commands", "System")
    except Exception as e:
        logger.error(f"Error in reload_command: {e}")
        try:
            await interaction.edit_original_response(content=f"⚠️ Error: {str(e)}")
        except:
            pass

if __name__ == "__main__":
    try:
        client.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot_history.log_action("bot_stop", "System", "Bot stopped by user", "System")
    except Exception as e:
        logger.exception("Fatal error running bot")
        bot_history.log_action("bot_error", "System", f"Fatal error: {str(e)}", "System")
