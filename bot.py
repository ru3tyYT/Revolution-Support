# bot.py
"""
Main entrypoint for AI Support Bot.
Run: python3 bot.py
"""
import os
import asyncio
import logging
from dotenv import load_dotenv

import discord
from discord import app_commands, Embed, ButtonStyle
from discord.ui import View, Button

# local modules
from modules.ai_client import AIClient
from modules.fix_store import load_fixes, save_fixes, add_fix, get_similar_fixes
from modules.thread_manager import ThreadManager
from modules.prompts import build_troubleshoot_prompt, build_enhance_prompt, build_summary_prompt
from modules.utils import sanitize_logs, extract_key_log_lines, confidence_heuristic

load_dotenv()

# env values (use .env or environment variables)
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")  # optional
SUPPORT_ROLE_ID = int(os.getenv("SUPPORT_ROLE_ID", "0") or 0)
BACKUP_WEBHOOK_URL = os.getenv("BACKUP_WEBHOOK_URL")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0") or 0)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("supportbot")

# fixes store loaded into memory (writes occur via functions)
fixes = load_fixes()

# Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

class SupportBot(discord.Client):
    def __init__(self, *, intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.ai = None              # will be AIClient instance (set in setup_hook)
        self.thread_manager = None  # ThreadManager instance
        self.session = None         # aiohttp session (set in setup_hook)

    async def setup_hook(self):
        # create aiohttp session and ai client here (inside event loop)
        self.ai = AIClient(api_key=GEMINI_API_KEY, max_concurrency=2)
        await self.ai.init_session()

        # Create thread manager (passes references needed)
        self.thread_manager = ThreadManager(bot=self, ai_client=self.ai)

        # Register slash commands to guild (dev) or globally
        if GUILD_ID:
            await self.tree.sync(guild=discord.Object(id=int(GUILD_ID)))
            logger.info("Commands synced to guild %s", GUILD_ID)
        else:
            await self.tree.sync()
            logger.info("Commands synced globally")

        # Start background inactivity watcher
        self.bg_task = asyncio.create_task(self.thread_manager.inactivity_watcher())

    async def close(self):
        # Graceful shutdown
        try:
            if self.ai:
                await self.ai.close_session()
        except Exception:
            logger.exception("Error closing AI session")
        await super().close()

    # helper: collect thread messages as text
    async def collect_thread_text(self, thread, limit=50):
        lines = []
        async for m in thread.history(limit=limit, oldest_first=True):
            author = getattr(m.author, "display_name", str(m.author))
            content = m.content or ""
            lines.append(f"{author}: {content}")
        return "\n".join(lines)

# instantiate bot
client = SupportBot(intents=intents)

# ---------------- Events ----------------
@client.event
async def on_ready():
    logger.info("Logged in as %s (id=%s)", client.user, client.user.id)

@client.event
async def on_thread_create(thread):
    # handle forum thread create -> send welcome embed + Generate button
    try:
        await asyncio.sleep(1.5)  # small delay to avoid race conditions
        view = View()
        view.add_item(Button(label="Generate AI Support Fix", style=ButtonStyle.primary, custom_id="generate_fix"))
        embed = Embed(
            title="Welcome to Support!",
            description="Thanks for opening a support thread. Click the button below to generate an AI suggested fix from this thread's messages and logs.",
            color=0x00FF00,
        )
        await thread.send(embed=embed, view=view)
    except Exception:
        logger.exception("Error in on_thread_create")

@client.event
async def on_interaction(interaction: discord.Interaction):
    """
    Central handler for button interactions (component interactions).
    Handles:
      - generate_fix
      - mark_solved:<thread_id>
      - mark_unsolved:<thread_id>
    """
    try:
        if interaction.type != discord.InteractionType.component:
            return

        cid = interaction.data.get("custom_id")
        if cid == "generate_fix":
            # Defer quickly to avoid 3s timeout
            await interaction.response.defer(ephemeral=False)

            thread = interaction.channel
            # gather messages and attachments
            messages_text = await client.collect_thread_text(thread, limit=50)

            # find logs in attachments (take first .log/.txt found)
            log_excerpt = None
            async for msg in thread.history(limit=50):
                for att in msg.attachments:
                    if att.filename.lower().endswith((".log", ".txt")):
                        data = await att.read()
                        text = data.decode(errors="ignore")
                        text = sanitize_logs(text)
                        log_excerpt = extract_key_log_lines(text, max_lines=300)
                        break
                if log_excerpt:
                    break

            # build prompt with a few-shot of similar fixes (simple substring match)
            similar = get_similar_fixes(thread.name, k=3)
            few_shot = similar if similar else None
            prompt = build_troubleshoot_prompt(thread.name, messages_text, log_excerpt, few_shot_examples=few_shot)

            # Call AI
            try:
                ai_raw = await client.ai.generate_fix(prompt)
                # ai_raw expected to be text - handle simple shapes
                ai_text = ai_raw or "⚠️ AI returned no content."
            except Exception:
                logger.exception("AI call failed")
                ai_text = "⚠️ AI generation failed."

            # post embed with result
            embed = Embed(title="AI Suggested Fix", description=ai_text, color=0x00FFFF)
            await interaction.followup.send(embed=embed)

            # compute confidence heuristic
            conf = confidence_heuristic(ai_text)

            # save to fixes.json
            entry = add_fix(
                source="ai_button",
                thread_id=str(thread.id),
                thread_name=thread.name,
                problem_summary=(ai_text[:200] if ai_text else ""),
                fix_text=ai_text,
                confidence=conf,
                language=None,
                tags=[]
            )
            logger.info("Saved AI fix id=%s for thread=%s", entry["id"], thread.id)

        elif cid and cid.startswith("mark_solved"):
            # only thread owner or admin can mark solved
            thread = interaction.channel
            user = interaction.user
            allowed = (user.id == getattr(thread, "owner_id", None)) or user.guild_permissions.administrator
            if not allowed:
                await interaction.response.send_message("Only the thread author or admins can mark solved.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                await thread.edit(locked=True)
                # Optionally summarize final fix via AI and save
                messages_text = await client.collect_thread_text(thread, limit=100)
                prompt = build_summary_prompt(messages_text)
                try:
                    summary = await client.ai.generate_fix(prompt)
                except Exception:
                    summary = None
                # Save summary as solved entry if summary provided
                if summary:
                    add_fix(
                        source="solved_action",
                        thread_id=str(thread.id),
                        thread_name=thread.name,
                        problem_summary=(summary[:200]),
                        fix_text=summary,
                        confidence=None,
                        language=None,
                        tags=[]
                    )
                await interaction.followup.send("Thread locked and marked solved ✅", ephemeral=False)
            except Exception:
                logger.exception("Failed marking solved")
                await interaction.followup.send("Failed to mark solved.", ephemeral=True)

        elif cid and cid.startswith("mark_unsolved"):
            thread = interaction.channel
            user = interaction.user
            allowed = (user.id == getattr(thread, "owner_id", None)) or user.guild_permissions.administrator
            if not allowed:
                await interaction.response.send_message("Only the thread author or admins can mark unsolved.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=False)
            # unlock and ping support role
            try:
                await thread.edit(locked=False)
                if SUPPORT_ROLE_ID:
                    await interaction.followup.send(f"<@&{SUPPORT_ROLE_ID}> Thread marked as unsolved and needs review.", ephemeral=False)
                else:
                    await interaction.followup.send("Thread marked as unsolved.", ephemeral=False)
            except Exception:
                logger.exception("Failed marking unsolved")
                await interaction.followup.send("Failed to mark unsolved.", ephemeral=True)

    except Exception:
        logger.exception("Error in on_interaction")

# ---------------- Slash Commands ----------------

# /say - admin-only
@client.tree.command(name="say", description="Admin: post an embed (AI-enhance optional)")
@app_commands.describe(message="Message body", ai_mode="Enhance with AI")
async def say(interaction: discord.Interaction, message: str, ai_mode: bool = False):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    final = message
    if ai_mode:
        try:
            prompt = build_enhance_prompt(message, "")
            final = await client.ai.generate_fix(prompt)
        except Exception:
            logger.exception("AI enhance failed")
    embed = Embed(title="Bot Message", description=final, color=0x00FFFF)
    await interaction.followup.send(embed=embed, ephemeral=False)

# /fix - manual fix entry (admin)
@client.tree.command(name="fix", description="Add a manual fix to the knowledge base")
@app_commands.describe(problem="Problem summary", solution="Solution text", ai_mode="Let AI improve solution")
async def fix_cmd(interaction: discord.Interaction, problem: str, solution: str, ai_mode: bool = False):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    final_solution = solution
    if ai_mode:
        try:
            prompt = build_enhance_prompt(problem, solution)
            final_solution = await client.ai.generate_fix(prompt)
        except Exception:
            logger.exception("AI enhancement failed")
    entry = add_fix(
        source="manual",
        thread_id=None,
        thread_name=None,
        problem_summary=problem,
        fix_text=final_solution,
        confidence=None,
        language=None,
        tags=[]
    )
    await interaction.followup.send(f"Manual fix saved (id: {entry['id']}).", ephemeral=True)

# /analyze - summarize a thread and optionally save
@client.tree.command(name="analyze", description="Analyze a thread and optionally save a fix")
@app_commands.describe(thread_id="ID of thread to analyze", save="Save summary to fixes.json")
async def analyze(interaction: discord.Interaction, thread_id: str, save: bool = True):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        th = await client.fetch_channel(int(thread_id))
    except Exception:
        await interaction.followup.send("Thread not found.", ephemeral=True)
        return
    messages_text = await client.collect_thread_text(th, limit=200)
    prompt = build_summary_prompt(messages_text)
    try:
        summary = await client.ai.generate_fix(prompt)
    except Exception:
        logger.exception("AI summarize failed")
        summary = "AI summarization failed."
    if save:
        entry = add_fix(
            source="analyze",
            thread_id=str(th.id),
            thread_name=th.name,
            problem_summary=summary[:200],
            fix_text=summary,
            confidence=None,
            language=None,
            tags=[]
        )
        await interaction.followup.send(f"Thread analyzed and saved (id: {entry['id']}).", ephemeral=True)
    else:
        await interaction.followup.send(f"Summary:\n{summary}", ephemeral=True)

# /backup - send fixes.json to backup webhook (admin)
@client.tree.command(name="backup", description="Send fixes.json to backup webhook")
async def backup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    if not BACKUP_WEBHOOK_URL:
        await interaction.followup.send("No BACKUP_WEBHOOK_URL configured.", ephemeral=True)
        return
    import aiohttp, json
    try:
        data = load_fixes()
        async with aiohttp.ClientSession() as session:
            # send as embed (truncate if too long)
            payload = {"content": "Backup of fixes.json", "embeds": [{"title": "fixes.json snapshot", "description": json.dumps(data)[:3900]}]}
            await session.post(BACKUP_WEBHOOK_URL, json=payload, timeout=30)
        await interaction.followup.send("Backup sent to webhook.", ephemeral=True)
    except Exception:
        logger.exception("Backup failed")
        await interaction.followup.send("Backup failed.", ephemeral=True)

# -------------- run --------------
if __name__ == "__main__":
    # simple guard
    if not TOKEN:
        logger.error("DISCORD_TOKEN not set in environment.")
        raise SystemExit("Missing DISCORD_TOKEN")
    client.run(TOKEN)
