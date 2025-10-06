# bot.py -- full-featured AI Support Bot
import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import aiohttp
from dotenv import load_dotenv
import discord
from discord import app_commands, Embed, ButtonStyle
from discord.ui import View, Button

# ---------------- LOAD ENV ----------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
GUILD_ID = os.getenv("GUILD_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPPORT_ROLE_ID = os.getenv("SUPPORT_ROLE_ID")
BACKUP_WEBHOOK_URL = os.getenv("BACKUP_WEBHOOK_URL")
SUPPORT_CHANNEL_ID = os.getenv("SUPPORT_CHANNEL_ID")

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("supportbot")

# ---------------- FIXES STORE ----------------
FIXES_FILE = "fixes.json"

def load_fixes():
    if os.path.exists(FIXES_FILE):
        with open(FIXES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_fixes(fixes):
    tmp = FIXES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(fixes, f, ensure_ascii=False, indent=2)
    os.replace(tmp, FIXES_FILE)

fixes = load_fixes()

# ---------------- PROMPTS ----------------
def build_troubleshoot_prompt(title, messages_text, log_excerpt=None):
    parts = [f"Thread title: {title}", "Messages:", messages_text]
    if log_excerpt:
        parts.append("Attached logs (excerpt):")
        parts.append(log_excerpt)
    user_block = "\n".join(parts)
    prompt = (
        "System: You are an expert support engineer. Output JSON with keys: "
        "\"summary\", \"confidence\" (0-1), \"fixes\" (array of steps), \"files_to_change\" (optional string).\n"
        f"User: {user_block}\n"
        "Task: Identify root cause, list steps to fix, give commands or code where applicable. "
        "Return only JSON."
    )
    return prompt

# ---------------- AI CLIENT ----------------
async def call_gemini(prompt, session: aiohttp.ClientSession):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY}
    async with session.post(url, headers=headers, json=body, timeout=60) as resp:
        try:
            return await resp.json()
        except Exception as e:
            text = await resp.text()
            logger.error("Gemini non-json response: %s", text)
            raise

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True
intents.reactions = True

# ---------------- BOT CLASS ----------------
class SupportBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.session = None
        self._posted_inactivity = {}

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        guild_id = GUILD_ID
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            await self.tree.sync(guild=guild)
            logger.info("Commands synced to guild %s", guild_id)
        else:
            await self.tree.sync()
            logger.info("Commands synced globally")
        self.bg_task = asyncio.create_task(self.inactivity_watcher())

    # ---------------- THREAD TEXT ----------------
    async def collect_thread_text(self, thread, limit=50):
        msgs = [m async for m in thread.history(limit=limit, oldest_first=True)]
        text_lines = [f"{m.author.display_name}: {m.content}" for m in msgs]
        return "\n".join(text_lines)

    # ---------------- INACTIVITY WATCHER ----------------
    async def inactivity_watcher(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                now = datetime.now(timezone.utc)
                for guild in self.guilds:
                    for ch in guild.channels:
                        if getattr(ch, "is_forum", lambda: False)():
                            for thread in ch.threads:
                                last_msg = thread.last_message
                                if not last_msg:
                                    continue
                                inactivity = now - last_msg.created_at
                                if inactivity > timedelta(hours=12) and not thread.locked:
                                    last_posted = self._posted_inactivity.get(thread.id)
                                    if not last_posted or (now - last_posted) > timedelta(hours=12):
                                        solved_btn = Button(style=ButtonStyle.success, label="Solved ✅", custom_id=f"mark_solved:{thread.id}")
                                        unsolved_btn = Button(style=ButtonStyle.danger, label="Unsolved ❌", custom_id=f"mark_unsolved:{thread.id}")
                                        v = View()
                                        v.add_item(solved_btn)
                                        v.add_item(unsolved_btn)
                                        try:
                                            await thread.send("Mark this thread as solved or unsolved:", view=v)
                                            self._posted_inactivity[thread.id] = now
                                        except Exception as e:
                                            logger.exception("Failed to send solved/unsolved buttons for thread %s: %s", thread.id, e)
                await asyncio.sleep(1800)
            except Exception as e:
                logger.exception("Error in inactivity_watcher: %s", e)
                await asyncio.sleep(60)

# ---------------- EVENTS ----------------
client = SupportBot()

@client.event
async def on_ready():
    logger.info("Logged in as %s", client.user)

@client.event
async def on_thread_create(thread):
    try:
        await asyncio.sleep(2)
        embed = Embed(title="Welcome to Support!", description="Thank you for contacting support. Please describe your issue.", color=0x00ff00)
        btn = Button(style=ButtonStyle.primary, label="Generate AI Support Fix", custom_id="generate_fix")
        v = View()
        v.add_item(btn)
        await thread.send(embed=embed, view=v)
    except Exception as e:
        logger.exception("Error in on_thread_create: %s", e)

@client.event
async def on_interaction(interaction: discord.Interaction):
    try:
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id")
        channel = interaction.channel

        # ---------------- GENERATE FIX ----------------
        if cid == "generate_fix":
            await interaction.response.defer(ephemeral=False)
            messages_text = await client.collect_thread_text(channel)
            log_excerpt = None
            for msg in [m async for m in channel.history(limit=50)]:
                for att in msg.attachments:
                    if att.filename.endswith(".log") or att.filename.endswith(".txt"):
                        try:
                            data = await att.read()
                            s = data.decode(errors="ignore")
                            log_excerpt = "\n".join(s.splitlines()[-300:])
                            raise StopIteration
                        except StopIteration:
                            break
            prompt = build_troubleshoot_prompt(channel.name, messages_text, log_excerpt)
            try:
                data = await call_gemini(prompt, client.session)
                ai_text = None
                cand = data.get("candidates")
                if cand and len(cand) > 0:
                    content = cand[0].get("content")
                    if isinstance(content, list):
                        parts = content[0].get("parts")
                        if parts:
                            ai_text = "".join(p.get("text","") for p in parts)
                    elif isinstance(content, dict):
                        parts = content.get("parts")
                        if parts:
                            ai_text = parts[0].get("text")
                    elif isinstance(content, str):
                        ai_text = content
                if not ai_text:
                    ai_text = "⚠️ AI could not generate a fix."
            except Exception:
                ai_text = "⚠️ Error generating AI fix."

            embed = Embed(title="AI Suggested Fix", description=ai_text, color=0x00FFFF)
            await interaction.followup.send(embed=embed)

            entry = {
                "id": str(uuid4()),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "ai_button",
                "thread_id": str(channel.id),
                "thread_name": channel.name,
                "problem_summary": ai_text[:200],
                "fix": ai_text,
                "confidence": None,
                "language": "unknown",
                "tags": [],
                "attachments": [],
                "version": 1
            }
            fixes.append(entry)
            save_fixes(fixes)

        # ---------------- MARK SOLVED ----------------
        elif cid and cid.startswith("mark_solved"):
            user = interaction.user
            allowed = (user.id == getattr(channel, "owner_id", None)) or interaction.user.guild_permissions.administrator
            if not allowed:
                await interaction.response.send_message("Only thread creator or admins can use this.", ephemeral=True)
                return
            try:
                await channel.edit(locked=True)
                await interaction.response.send_message("Thread marked as solved! ✅", ephemeral=False)
            except Exception as e:
                logger.exception("Failed to lock thread: %s", e)
                await interaction.response.send_message("Failed to lock thread.", ephemeral=True)

        # ---------------- MARK UNSOLVED ----------------
        elif cid and cid.startswith("mark_unsolved"):
            await interaction.response.send_message(f"<@&{SUPPORT_ROLE_ID}> Thread marked as unsolved.", ephemeral=False)

    except Exception as e:
        logger.exception("Unhandled interaction error: %s", e)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("An internal error occurred.", ephemeral=True)
        except Exception:
            pass

# ---------------- SLASH COMMANDS ----------------
@client.tree.command(name="say", description="Post a bot embed message")
@app_commands.describe(message="Message body", ai_mode="Let AI enhance message")
async def say(interaction: discord.Interaction, message: str, ai_mode: bool = False):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=False)  # visible to all
    final = message
    if ai_mode:
        prompt = f"Enhance this message for clarity and professionalism:\n{message}"
        try:
            data = await call_gemini(prompt, client.session)
            final = (data.get("candidates") or [{}])[0].get("content") or final
            if isinstance(final, dict):
                final = final.get("parts", [{}])[0].get("text", message)
        except Exception:
            pass
    embed = Embed(title="Bot Message", description=final, color=0x00FFFF)
    await interaction.followup.send(embed=embed)

@client.tree.command(name="fix", description="Add manual fix (admin only)")
@app_commands.describe(problem="Problem", solution="Solution", ai_mode="Enhance with AI")
async def fix_cmd(interaction: discord.Interaction, problem: str, solution: str, ai_mode: bool = False):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    final_solution = solution
    if ai_mode:
        prompt = f"Enhance this support problem and solution:\nProblem: {problem}\nSolution: {solution}"
        try:
            data = await call_gemini(prompt, client.session)
            final_solution = (data.get("candidates") or [{}])[0].get("content") or final_solution
            if isinstance(final_solution, dict):
                final_solution = final_solution.get("parts", [{}])[0].get("text", solution)
        except Exception:
            pass
    entry = {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "manual",
        "thread_id": None,
        "thread_name": None,
        "problem_summary": problem[:200],
        "fix": final_solution,
        "confidence": None,
        "language": "en",
        "tags": [],
        "attachments": [],
        "version": 1
    }
    fixes.append(entry)
    save_fixes(fixes)
    embed = Embed(title="Fix Added", description=f"**Problem:** {problem}\n**Solution:** {final_solution}", color=0x00FFFF)
    await interaction.followup.send(embed=embed, ephemeral=True)

@client.tree.command(name="analyze", description="Analyze thread and save fixes (admin only)")
@app_commands.describe(thread_id="ID of thread to analyze")
async def analyze(interaction: discord.Interaction, thread_id: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Admin only", ephemeral=True)
        return
    try:
        thread = await client.fetch_channel(int(thread_id))
    except Exception:
        await interaction.response.send_message("Thread not found", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    messages_text = await client.collect_thread_text(thread)
    prompt = f"Summarize this forum and suggest fixes if confident:\n{messages_text}"
    try:
        data = await call_gemini(prompt, client.session)
        summary = (data.get("candidates") or [{}])[0].get("content") or "AI could not summarize."
        if isinstance(summary, dict):
            summary = summary.get("parts", [{}])[0].get("text", "")
    except Exception:
        summary = "AI could not summarize due to error."
    entry = {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "analyze",
        "thread_id": str(thread.id),
        "thread_name": thread.name,
        "problem_summary": summary[:200],
        "fix": summary,
        "confidence": None,
        "language": "en",
        "tags": [],
        "attachments": [],
        "version": 1
    }
    fixes.append(entry)
    save_fixes(fixes)
    await interaction.followup.send(f"Thread analyzed and fix saved:\n```{summary}```", ephemeral=True)

# ---------------- RUN BOT ----------------
async def main():
    async with client:
        await client.start(TOKEN)

asyncio.run(main())
