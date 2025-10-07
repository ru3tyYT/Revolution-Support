import os
import logging
import discord
from discord import app_commands, Embed, ButtonStyle
from discord.ui import View, Button
from dotenv import load_dotenv

from modules.ai_client import AIClient
from modules.thread_manager import ThreadManager
from modules import fix_store, prompts, utils

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("bot")

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPPORT_ROLE_ID = os.getenv("SUPPORT_ROLE_ID")
BACKUP_WEBHOOK_URL = os.getenv("BACKUP_WEBHOOK_URL")

# Allowed role IDs for using bot commands
ALLOWED_ROLE_IDS = [
    1324169948444102848,
    1407811396426534974,
    1327057500242972702,
    1419402709043384521,
    1373900702207836291,
    1422106035337826315,
    1405246916760961125
]

# Validate required env vars
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is required in .env file")

def has_allowed_role(interaction: discord.Interaction) -> bool:
    """Check if user has any of the allowed roles"""
    if not interaction.user.roles:
        return False
    user_role_ids = [role.id for role in interaction.user.roles]
    return any(role_id in ALLOWED_ROLE_IDS for role_id in user_role_ids)

class SupportBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.ai_client = AIClient(api_key=GEMINI_API_KEY, max_concurrency=2)
        self.thread_manager = ThreadManager(self, self.ai_client)

    async def setup_hook(self):
        await self.ai_client.init_session()
        # Start background task for inactivity watcher
        self.loop.create_task(self.thread_manager.inactivity_watcher())
        # Sync commands
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {GUILD_ID}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")

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
    logger.info(f'Logged in as {client.user} (ID: {client.user.id})')
    logger.info(f'Connected to {len(client.guilds)} guild(s)')
    logger.info('------')

@client.event
async def on_thread_create(thread: discord.Thread):
    """Auto-post welcome message when a new thread is created"""
    await client.thread_manager.handle_new_thread(thread)

@client.event
async def on_interaction(interaction: discord.Interaction):
    """Handle button interactions"""
    if interaction.type != discord.InteractionType.component:
        return
    
    custom_id = interaction.data.get("custom_id", "")
    
    # Handle "Generate AI Fix" button
    if custom_id == "generate_fix":
        await handle_generate_fix_button(interaction)
    
    # Handle "Solved" button
    elif custom_id.startswith("mark_solved:"):
        thread_id = int(custom_id.split(":")[1])
        await interaction.response.send_message("✅ Thread marked as solved!", ephemeral=False)
        try:
            # Find "Resolved" tag
            if isinstance(interaction.channel, discord.Thread):
                parent_channel = interaction.channel.parent
                resolved_tag = None
                
                # Look for a tag named "Resolved" (case-insensitive)
                if hasattr(parent_channel, 'available_tags'):
                    for tag in parent_channel.available_tags:
                        if tag.name.lower() == "resolved":
                            resolved_tag = tag
                            break
                
                # Apply the tag and lock the thread (don't archive)
                if resolved_tag:
                    await interaction.channel.edit(
                        applied_tags=[resolved_tag],
                        locked=True
                    )
                else:
                    # If no "Resolved" tag exists, just lock
                    await interaction.channel.edit(locked=True)
        except Exception as e:
            logger.error(f"Failed to lock/tag thread: {e}")
    
    # Handle "Unsolved" button
    elif custom_id.startswith("mark_unsolved:"):
        await interaction.response.send_message("❌ Thread marked as unsolved. A support member will assist you.", ephemeral=False)
        if SUPPORT_ROLE_ID:
            try:
                await interaction.channel.send(f"<@&{SUPPORT_ROLE_ID}> This thread needs attention.")
            except Exception as e:
                logger.error(f"Failed to ping support role: {e}")

async def handle_generate_fix_button(interaction: discord.Interaction):
    """Handle the Generate AI Fix button click"""
    await interaction.response.defer(ephemeral=False)
    
    try:
        # Collect thread messages
        messages = []
        async for msg in interaction.channel.history(limit=100):
            if not msg.author.bot:
                messages.append(f"{msg.author.name}: {msg.content}")
        
        if not messages:
            await interaction.followup.send("⚠️ No messages found in this thread.", ephemeral=True)
            return
        
        messages.reverse()  # Chronological order
        thread_text = "\n".join(messages)
        
        # Check for attachments/logs
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
                        except Exception as e:
                            logger.error(f"Failed to read attachment: {e}")
            if log_excerpt:
                break
        
        # Get similar fixes for context
        thread_title = interaction.channel.name
        similar_fixes = fix_store.get_similar_fixes(thread_title, k=3)
        
        # Build AI prompt
        prompt = prompts.build_troubleshoot_prompt(
            title=thread_title,
            messages_text=thread_text[:3000],  # Limit length
            log_excerpt=log_excerpt[:1000] if log_excerpt else None,
            few_shot_examples=similar_fixes
        )
        
        # Generate AI response
        ai_response = await client.ai_client.generate_fix(prompt)
        
        # Extract confidence
        confidence = utils.confidence_heuristic(ai_response)
        
        # Save fix to database
        fix_store.add_fix(
            source="ai_button",
            thread_id=str(interaction.channel_id),
            thread_name=thread_title,
            problem_summary=thread_title,
            fix_text=ai_response,
            confidence=confidence
        )
        
        # Send response
        embed = Embed(
            title="🤖 AI-Generated Solution",
            description=ai_response[:4000],  # Discord embed limit
            color=0x00FF00
        )
        embed.set_footer(text=f"Confidence: {confidence:.0%} | Thread: {thread_title}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.exception("Error in handle_generate_fix_button")
        await interaction.followup.send(f"⚠️ Error generating fix: {str(e)}", ephemeral=True)

# ==================== SLASH COMMANDS ====================

@client.tree.command(name="fix", description="Manually add a fix to the knowledge base")
@app_commands.describe(
    problem="Brief description of the problem",
    solution="The solution or fix",
    confidence="Confidence level (0.0 to 1.0)"
)
async def fix_command(
    interaction: discord.Interaction,
    problem: str,
    solution: str,
    confidence: float = 0.8
):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        thread_id = str(interaction.channel_id) if interaction.channel else None
        thread_name = interaction.channel.name if interaction.channel else None
        
        entry = fix_store.add_fix(
            source="manual",
            thread_id=thread_id,
            thread_name=thread_name,
            problem_summary=problem,
            fix_text=solution,
            confidence=max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
        )
        
        embed = Embed(
            title="✅ Fix Saved",
            description=f"**Problem:** {problem}\n**Solution:** {solution[:200]}...",
            color=0x00FF00
        )
        embed.add_field(name="ID", value=entry["id"][:8], inline=True)
        embed.add_field(name="Confidence", value=f"{confidence:.0%}", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.exception("Error in fix_command")
        await interaction.followup.send(f"⚠️ Error saving fix: {str(e)}", ephemeral=True)

@client.tree.command(name="analyze", description="Analyze the current thread and generate a fix")
async def analyze_command(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        return
    
    if not interaction.channel:
        await interaction.response.send_message("⚠️ This command must be used in a thread.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=False)
    
    try:
        # Collect messages
        messages = []
        async for msg in interaction.channel.history(limit=100):
            if not msg.author.bot:
                messages.append(f"{msg.author.name}: {msg.content}")
        
        if not messages:
            await interaction.followup.send("⚠️ No messages to analyze.", ephemeral=True)
            return
        
        messages.reverse()
        thread_text = "\n".join(messages)
        
        # Build prompt
        prompt = prompts.build_summary_prompt(thread_text[:4000])
        
        # Generate AI analysis
        ai_response = await client.ai_client.generate_fix(prompt)
        confidence = utils.confidence_heuristic(ai_response)
        
        # Save to database
        fix_store.add_fix(
            source="analyze_command",
            thread_id=str(interaction.channel_id),
            thread_name=interaction.channel.name,
            problem_summary=f"Analysis: {interaction.channel.name}",
            fix_text=ai_response,
            confidence=confidence
        )
        
        # Send response
        embed = Embed(
            title="📊 Thread Analysis",
            description=ai_response[:4000],
            color=0x3498db
        )
        embed.set_footer(text=f"Confidence: {confidence:.0%}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.exception("Error in analyze_command")
        await interaction.followup.send(f"⚠️ Error analyzing thread: {str(e)}", ephemeral=True)

@client.tree.command(name="search", description="Search the fix database")
@app_commands.describe(query="Search term or problem description")
async def search_command(interaction: discord.Interaction, query: str):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        results = fix_store.get_similar_fixes(query, k=5)
        
        if not results:
            await interaction.followup.send(f"❌ No fixes found for: `{query}`", ephemeral=True)
            return
        
        embed = Embed(
            title=f"🔍 Search Results for: {query}",
            description=f"Found {len(results)} similar fix(es)",
            color=0xe67e22
        )
        
        for i, fix in enumerate(results[:5], 1):
            problem = fix.get("problem_summary", "Unknown")[:100]
            solution = fix.get("fix", "No solution")[:200]
            confidence = fix.get("confidence", 0.5)
            
            embed.add_field(
                name=f"{i}. {problem}",
                value=f"{solution}...\n*Confidence: {confidence:.0%}*",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.exception("Error in search_command")
        await interaction.followup.send(f"⚠️ Error searching: {str(e)}", ephemeral=True)

@client.tree.command(name="say", description="Send a message as the bot")
@app_commands.describe(
    message="The message to send",
    ai_enhance="Use AI to rewrite and enhance the message"
)
async def say_command(
    interaction: discord.Interaction,
    message: str,
    ai_enhance: bool = False
):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        final_message = message
        
        if ai_enhance:
            prompt = f"Rewrite this message to be more clear, professional, and well-formatted:\n\n{message}"
            final_message = await client.ai_client.generate_fix(prompt)
        
        # Send the message as an embed
        embed = Embed(
            description=final_message,
            color=0x5865F2  # Discord blurple color
        )
        
        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ Message sent!", ephemeral=True)
        
    except Exception as e:
        logger.exception("Error in say_command")
        await interaction.followup.send(f"⚠️ Error sending message: {str(e)}", ephemeral=True)

@client.tree.command(name="backup", description="Backup all fixes to a webhook")
async def backup_command(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        return
    
    if not BACKUP_WEBHOOK_URL:
        await interaction.response.send_message("⚠️ Backup webhook not configured.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        fixes = fix_store.load_fixes()
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Split into chunks if too large
            import json
            data = json.dumps(fixes, indent=2)
            
            if len(data) > 1900:
                # Send as file
                import io
                file = discord.File(io.BytesIO(data.encode()), filename="fixes_backup.json")
                webhook = discord.Webhook.from_url(BACKUP_WEBHOOK_URL, session=session)
                await webhook.send(
                    content=f"📦 Backup - {len(fixes)} fixes",
                    file=file
                )
            else:
                webhook = discord.Webhook.from_url(BACKUP_WEBHOOK_URL, session=session)
                await webhook.send(f"```json\n{data}\n```")
        
        await interaction.followup.send(f"✅ Backed up {len(fixes)} fixes!", ephemeral=True)
        
    except Exception as e:
        logger.exception("Error in backup_command")
        await interaction.followup.send(f"⚠️ Backup failed: {str(e)}", ephemeral=True)

@client.tree.command(name="reload", description="Reload bot commands (Admin only)")
async def reload_command(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        return
    
    # Check if user has administrator permission
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("⚠️ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            # Clear old commands first
            client.tree.clear_commands(guild=guild)
            await client.tree.sync(guild=guild)
            # Now sync new ones
            client.tree.copy_global_to(guild=guild)
            await client.tree.sync(guild=guild)
            await interaction.followup.send("✅ Commands cleared and reloaded for this guild!", ephemeral=True)
        else:
            # Clear global commands
            client.tree.clear_commands(guild=None)
            await client.tree.sync()
            await interaction.followup.send("✅ Commands cleared and reloaded globally!", ephemeral=True)
    except Exception as e:
        logger.exception("Error in reload_command")
        await interaction.followup.send(f"⚠️ Reload failed: {str(e)}", ephemeral=True)

@client.tree.command(name="stats", description="Show bot statistics")
async def stats_command(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        fixes = fix_store.load_fixes()
        
        # Calculate stats
        total_fixes = len(fixes)
        ai_fixes = sum(1 for f in fixes if f.get("source") in ["ai_button", "analyze_command"])
        manual_fixes = sum(1 for f in fixes if f.get("source") == "manual")
        
        # Handle None confidence values
        confidences = [f.get("confidence") or 0 for f in fixes]
        avg_confidence = sum(confidences) / total_fixes if total_fixes > 0 else 0
        
        embed = Embed(
            title="📊 Bot Statistics",
            color=0x3498db
        )
        embed.add_field(name="Total Fixes", value=str(total_fixes), inline=True)
        embed.add_field(name="AI Generated", value=str(ai_fixes), inline=True)
        embed.add_field(name="Manual Fixes", value=str(manual_fixes), inline=True)
        embed.add_field(name="Avg Confidence", value=f"{avg_confidence:.0%}", inline=True)
        embed.add_field(name="Guilds", value=str(len(client.guilds)), inline=True)
        embed.add_field(name="Uptime", value="Active", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.exception("Error in stats_command")
        await interaction.followup.send(f"⚠️ Error getting stats: {str(e)}", ephemeral=True)

@client.tree.command(name="mark_for_review", description="Mark this thread for review by the original poster")
async def mark_for_review_command(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        return
    
    # Check if used in a thread
    if not isinstance(interaction.channel, discord.Thread):
        await interaction.response.send_message("⚠️ This command can only be used in threads.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=False)
    
    try:
        thread = interaction.channel
        thread_owner = thread.owner
        
        if not thread_owner:
            await interaction.followup.send("⚠️ Could not find the thread owner.", ephemeral=True)
            return
        
        # Create the solved/unsolved buttons
        view = View()
        view.add_item(Button(style=ButtonStyle.success, label="Solved ✅", custom_id=f"mark_solved:{thread.id}"))
        view.add_item(Button(style=ButtonStyle.danger, label="Unsolved ❌", custom_id=f"mark_unsolved:{thread.id}"))
        
        # Send message pinging the thread owner
        await thread.send(
            f"{thread_owner.mention} Please mark this thread as solved or unsolved:",
            view=view
        )
        
        await interaction.followup.send("✅ Review buttons posted and thread owner pinged!", ephemeral=False)
        
    except Exception as e:
        logger.exception("Error in mark_for_review_command")
        await interaction.followup.send(f"⚠️ Error posting review buttons: {str(e)}", ephemeral=True)

@client.tree.command(name="ask", description="Ask the AI a question")
@app_commands.describe(question="Your question for the AI")
async def ask_command(interaction: discord.Interaction, question: str):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("⚠️ You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=False)
    
    try:
        # Simple conversational prompt
        prompt = f"Answer this question clearly and helpfully:\n\n{question}"
        
        # Get AI response
        ai_response = await client.ai_client.generate_fix(prompt)
        
        # Send response as embed
        embed = Embed(
            title="💬 AI Response",
            description=ai_response[:4000],  # Discord embed limit
            color=0x5865F2
        )
        embed.set_footer(text=f"Question: {question[:100]}...")
        
        await interaction.followup.send(embed=embed, ephemeral=False)
        
    except Exception as e:
        logger.exception("Error in ask_command")
        await interaction.followup.send(f"⚠️ Error asking AI: {str(e)}", ephemeral=True)

# ==================== RUN BOT ====================

if __name__ == "__main__":
    try:
        client.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception("Fatal error running bot")
