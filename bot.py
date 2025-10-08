import os
import logging
import discord
from discord import app_commands, Embed, ButtonStyle
from discord.ui import View, Button
from dotenv import load_dotenv
import asyncio

from modules.ai_client import AIClient
from modules.thread_manager import ThreadManager
from modules import fix_store, prompts, utils
import api_usage

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

ALLOWED_ROLE_IDS = [
    1324169948444102848, 1407811396426534974, 1327057500242972702,
    1419402709043384521, 1373900702207836291, 1422106035337826315, 1405246916760961125
]

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is required in .env file")

def has_allowed_role(interaction: discord.Interaction) -> bool:
    if not hasattr(interaction.user, 'roles') or not interaction.user.roles:
        return False
    return any(role.id in ALLOWED_ROLE_IDS for role in interaction.user.roles)

class SupportBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.ai_client = AIClient(api_key=GEMINI_API_KEY, max_concurrency=2)
        self.thread_manager = ThreadManager(self, self.ai_client)

    async def setup_hook(self):
        await self.ai_client.init_session()
        self.loop.create_task(self.thread_manager.inactivity_watcher())
        
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

    async def close(self):
        await self.ai_client.close_session()
        await super().close()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
client = SupportBot(intents=intents)

# ==================== EVENTS ====================

@client.event
async def on_ready():
    logger.info('='*50)
    logger.info(f'Bot Online: {client.user.name}')
    logger.info(f'Bot ID: {client.user.id}')
    logger.info(f'Guilds: {len(client.guilds)}')
    logger.info('='*50)

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

async def handle_generate_fix_button(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=False)
    except:
        return
    
    try:
        messages = []
        async for msg in interaction.channel.history(limit=100):
            if not msg.author.bot:
                messages.append(f"{msg.author.name}: {msg.content}")
        
        if not messages:
            await interaction.followup.send("⚠️ No messages found.", ephemeral=True)
            return
        
        messages.reverse()
        thread_text = "\n".join(messages)
        
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
        similar_fixes = fix_store.get_similar_fixes(thread_title, k=3)
        
        prompt = prompts.build_troubleshoot_prompt(
            title=thread_title,
            messages_text=thread_text[:3000],
            log_excerpt=log_excerpt[:1000] if log_excerpt else None,
            few_shot_examples=similar_fixes
        )
        
        ai_response = await client.ai_client.generate_fix(prompt)
        
        # Track API usage
        api_usage.track_request(prompt, ai_response)
        
        confidence = utils.confidence_heuristic(ai_response)
        
        fix_store.add_fix(
            source="ai_button",
            thread_id=str(interaction.channel_id),
            thread_name=thread_title,
            problem_summary=thread_title,
            fix_text=ai_response,
            confidence=confidence
        )
        
        embed = Embed(title="🤖 AI-Generated Solution", description=ai_response[:4000], color=0x00FF00)
        embed.set_footer(text=f"Confidence: {confidence:.0%}")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.error(f"Error in generate_fix: {e}")
        try:
            await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)
        except:
            pass

async def handle_solved_button(interaction: discord.Interaction):
    try:
        await interaction.response.send_message("✅ Thread marked as solved!", ephemeral=False)
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
    except Exception as e:
        logger.error(f"Failed to lock/tag thread: {e}")

async def handle_unsolved_button(interaction: discord.Interaction):
    try:
        await interaction.response.send_message("❌ Thread marked as unsolved.", ephemeral=False)
    except:
        return
    
    if SUPPORT_ROLE_ID:
        try:
            await interaction.channel.send(f"<@&{SUPPORT_ROLE_ID}> This thread needs attention.")
        except:
            pass

# ==================== SLASH COMMANDS ====================

@client.tree.command(name="fix", description="Manually add a fix to the knowledge base")
@app_commands.describe(problem="Brief description of the problem", solution="The solution or fix", confidence="Confidence level (0.0 to 1.0)")
async def fix_command(interaction: discord.Interaction, problem: str, solution: str, confidence: float = 0.8):
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    if not has_allowed_role(interaction):
        await interaction.followup.send("⚠️ You don't have permission.", ephemeral=True)
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
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Error in fix_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="analyze", description="Analyze the current thread and generate a fix")
async def analyze_command(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=False)
    except:
        return
    
    if not has_allowed_role(interaction):
        await interaction.followup.send("⚠️ You don't have permission.", ephemeral=True)
        return
    
    if not interaction.channel:
        await interaction.followup.send("⚠️ Must be used in a thread.", ephemeral=True)
        return
    
    try:
        messages = []
        async for msg in interaction.channel.history(limit=100):
            if not msg.author.bot:
                messages.append(f"{msg.author.name}: {msg.content}")
        
        if not messages:
            await interaction.followup.send("⚠️ No messages to analyze.", ephemeral=True)
            return
        
        messages.reverse()
        thread_text = "\n".join(messages)
        prompt = prompts.build_summary_prompt(thread_text[:4000])
        ai_response = await client.ai_client.generate_fix(prompt)
        
        # Track API usage
        api_usage.track_request(prompt, ai_response)
        
        confidence = utils.confidence_heuristic(ai_response)
        
        # Create embed with analysis
        embed = Embed(title="📊 Thread Analysis", description=ai_response[:4000], color=0x3498db)
        embed.set_footer(text=f"Confidence: {confidence:.0%}")
        
        # Create button to save to fixes
        view = View(timeout=300)
        save_button = Button(style=ButtonStyle.success, label="💾 Save to Fixes Database", custom_id=f"save_analysis")
        
        async def save_callback(button_interaction: discord.Interaction):
            try:
                await button_interaction.response.defer(ephemeral=True)
            except:
                return
            
            try:
                fix_store.add_fix(
                    source="analyze_command",
                    thread_id=str(interaction.channel_id),
                    thread_name=interaction.channel.name,
                    problem_summary=f"Analysis: {interaction.channel.name}",
                    fix_text=ai_response,
                    confidence=confidence
                )
                await button_interaction.followup.send("✅ Analysis saved to fixes database!", ephemeral=True)
                save_button.disabled = True
                save_button.label = "✅ Saved"
                await button_interaction.message.edit(view=view)
            except Exception as e:
                logger.error(f"Error saving analysis: {e}")
                await button_interaction.followup.send(f"⚠️ Error saving: {str(e)}", ephemeral=True)
        
        save_button.callback = save_callback
        view.add_item(save_button)
        
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        logger.error(f"Error in analyze_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="search", description="Search the fix database")
@app_commands.describe(query="Search term or problem description")
async def search_command(interaction: discord.Interaction, query: str):
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    if not has_allowed_role(interaction):
        await interaction.followup.send("⚠️ You don't have permission.", ephemeral=True)
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
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Error in search_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="say", description="Send a message as the bot")
@app_commands.describe(message="The message to send", ai_enhance="Use AI to rewrite and enhance the message")
async def say_command(interaction: discord.Interaction, message: str, ai_enhance: bool = False):
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    if not has_allowed_role(interaction):
        await interaction.followup.send("⚠️ You don't have permission.", ephemeral=True)
        return
    
    try:
        final_message = message
        if ai_enhance:
            prompt = f"Rewrite this message to be more clear, professional, and well-formatted:\n\n{message}"
            final_message = await client.ai_client.generate_fix(prompt)
            # Track API usage
            api_usage.track_request(prompt, final_message)
        
        embed = Embed(description=final_message, color=0x5865F2)
        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ Message sent!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in say_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="backup", description="Backup all fixes to a webhook")
async def backup_command(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    if not has_allowed_role(interaction):
        await interaction.followup.send("⚠️ You don't have permission.", ephemeral=True)
        return
    
    if not BACKUP_WEBHOOK_URL:
        await interaction.followup.send("⚠️ Backup webhook not configured.", ephemeral=True)
        return
    
    try:
        fixes = fix_store.load_fixes()
        import aiohttp, json, io
        
        async with aiohttp.ClientSession() as session:
            data = json.dumps(fixes, indent=2)
            
            if len(data) > 1900:
                file = discord.File(io.BytesIO(data.encode()), filename="fixes_backup.json")
                webhook = discord.Webhook.from_url(BACKUP_WEBHOOK_URL, session=session)
                await webhook.send(content=f"📦 Backup - {len(fixes)} fixes", file=file)
            else:
                webhook = discord.Webhook.from_url(BACKUP_WEBHOOK_URL, session=session)
                await webhook.send(f"```json\n{data}\n```")
        
        await interaction.followup.send(f"✅ Backed up {len(fixes)} fixes!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in backup_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="reload", description="Reload bot commands (Admin only)")
async def reload_command(interaction: discord.Interaction):
    if not has_allowed_role(interaction) or not interaction.user.guild_permissions.administrator:
        try:
            await interaction.response.send_message("⚠️ You don't have permission.", ephemeral=True)
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
    except Exception as e:
        logger.error(f"Error in reload_command: {e}")
        try:
            await interaction.edit_original_response(content=f"⚠️ Error: {str(e)}")
        except:
            pass

@client.tree.command(name="stats", description="Show bot statistics")
async def stats_command(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    if not has_allowed_role(interaction):
        await interaction.followup.send("⚠️ You don't have permission.", ephemeral=True)
        return
    
    try:
        # Get fix stats
        fixes = fix_store.load_fixes()
        total_fixes = len(fixes)
        ai_fixes = sum(1 for f in fixes if f.get("source") in ["ai_button", "analyze_command"])
        manual_fixes = sum(1 for f in fixes if f.get("source") == "manual")
        confidences = [f.get("confidence") or 0 for f in fixes]
        avg_confidence = sum(confidences) / total_fixes if total_fixes > 0 else 0
        
        # Get API usage stats
        today_stats = api_usage.get_today_stats()
        month_stats = api_usage.get_month_stats()
        estimated_monthly = api_usage.estimate_monthly_cost()
        
        embed = Embed(title="📊 Bot Statistics", color=0x3498db)
        
        # Fix stats
        embed.add_field(name="Total Fixes", value=str(total_fixes), inline=True)
        embed.add_field(name="AI Generated", value=str(ai_fixes), inline=True)
        embed.add_field(name="Manual Fixes", value=str(manual_fixes), inline=True)
        embed.add_field(name="Avg Confidence", value=f"{avg_confidence:.0%}", inline=True)
        embed.add_field(name="Guilds", value=str(len(client.guilds)), inline=True)
        embed.add_field(name="Uptime", value="Active", inline=True)
        
        # API usage stats
        embed.add_field(name="\u200b", value="**💰 API Usage**", inline=False)
        embed.add_field(name="Requests Today", value=str(today_stats.get("requests", 0)), inline=True)
        embed.add_field(name="Cost Today", value=f"${today_stats.get('cost', 0):.4f}", inline=True)
        embed.add_field(name="Monthly Cost", value=f"${month_stats.get('cost', 0):.4f}", inline=True)
        embed.add_field(name="Est. Monthly", value=f"${estimated_monthly:.2f}", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="mark_for_review", description="Mark this thread for review by the original poster")
async def mark_for_review_command(interaction: discord.Interaction):
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
    
    if not has_allowed_role(interaction):
        await interaction.followup.send("⚠️ You don't have permission.", ephemeral=True)
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
        
        await thread.send(f"{thread_owner.mention} Please mark this thread as solved or unsolved:", view=view)
        await interaction.followup.send("✅ Review buttons posted and thread owner pinged!", ephemeral=False)
    except Exception as e:
        logger.error(f"Error in mark_for_review_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

@client.tree.command(name="ask", description="Ask the AI a question")
@app_commands.describe(question="Your question for the AI")
async def ask_command(interaction: discord.Interaction, question: str):
    try:
        await interaction.response.defer(ephemeral=False)
    except:
        return
    
    if not has_allowed_role(interaction):
        await interaction.followup.send("⚠️ You don't have permission.", ephemeral=True)
        return
    
    try:
        prompt = f"Answer this question clearly and helpfully:\n\n{question}"
        ai_response = await client.ai_client.generate_fix(prompt)
        
        # Track API usage
        api_usage.track_request(prompt, ai_response)
        
        embed = Embed(title="💬 AI Response", description=ai_response[:4000], color=0x5865F2)
        embed.set_footer(text=f"Question: {question[:100]}...")
        
        await interaction.followup.send(embed=embed, ephemeral=False)
    except Exception as e:
        logger.error(f"Error in ask_command: {e}")
        await interaction.followup.send(f"⚠️ Error: {str(e)}", ephemeral=True)

# ==================== RUN BOT ====================

if __name__ == "__main__":
    try:
        client.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception("Fatal error running bot")
