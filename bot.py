import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
import discord
from discord.ext import tasks, commands
from discord import app_commands, ui
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load environment variables (keep them as strings)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
GUILD_ID = os.getenv("GUILD_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPPORT_ROLE_ID = os.getenv("SUPPORT_ROLE_ID")
SUPPORT_CHANNEL_ID = os.getenv("SUPPORT_CHANNEL_ID")
BACKUP_WEBHOOK_URL = os.getenv("BACKUP_WEBHOOK_URL")

FIXES_FILE = "fixes.json"

# Ensure fixes.json exists
if not os.path.exists(FIXES_FILE):
    with open(FIXES_FILE, "w") as f:
        json.dump([], f)

class SupportBot(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.session = None
        self.bg_task = None

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        # Start background inactivity watcher
        self.bg_task = self.loop.create_task(self.inactivity_watcher())
        # Sync commands to guild
        if GUILD_ID:
            await self.tree.sync(guild=discord.Object(id=int(GUILD_ID)))

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

    async def inactivity_watcher(self):
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(3600)  # check every hour
            if not SUPPORT_CHANNEL_ID or not GUILD_ID:
                continue
            guild = self.get_guild(int(GUILD_ID))
            if guild:
                channel = guild.get_channel(int(SUPPORT_CHANNEL_ID))
                if channel:
                    async for thread in channel.threads:
                        if thread.last_message is None:
                            continue
                        if datetime.utcnow() - thread.last_message.created_at > timedelta(hours=12):
                            await self.send_inactivity_buttons(thread)

    async def send_inactivity_buttons(self, thread):
        view = ui.View()
        view.add_item(ui.Button(label="Solved", style=discord.ButtonStyle.green, custom_id=f"mark_solved:{thread.id}"))
        view.add_item(ui.Button(label="Unsolved", style=discord.ButtonStyle.red, custom_id=f"mark_unsolved:{thread.id}"))
        await thread.send("This thread has been inactive. Please mark it as solved or unsolved.", view=view)

    async def collect_thread_messages(self, thread):
        messages = []
        async for message in thread.history(limit=200):
            if message.author.bot:
                continue
            messages.append(f"{message.author.name}: {message.content}")
        return messages

    async def send_ai_request(self, prompt):
        # Example Gemini API request
        headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}
        json_data = {"prompt": prompt}
        async with self.session.post("https://api.gemini.example/v1/generate", headers=headers, json=json_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("output", "AI failed to generate response.")
            return "AI request failed."

    def save_fix(self, fix_data):
        with open(FIXES_FILE, "r+") as f:
            fixes = json.load(f)
            fixes.append(fix_data)
            f.seek(0)
            json.dump(fixes, f, indent=4)
            f.truncate()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
client = SupportBot(intents=intents)

# Slash Commands
@client.tree.command(name="fix", description="Add or edit a fix for a problem")
@app_commands.describe(problem="Describe the problem", solution="Describe the solution", ai_mode="Use AI to enhance fix?")
async def fix(interaction: discord.Interaction, problem: str, solution: str, ai_mode: bool = False):
    fix_data = {
        "thread_id": str(interaction.channel_id),
        "thread_name": interaction.channel.name if interaction.channel else "unknown",
        "problem": problem,
        "solution": solution,
        "confidence": 1.0 if not ai_mode else 0.9,
        "ai_generated": ai_mode,
        "timestamp": datetime.utcnow().isoformat()
    }
    client.save_fix(fix_data)
    await interaction.response.send_message(f"Fix saved! AI mode: {ai_mode}", ephemeral=True)

@client.tree.command(name="analyze", description="Analyze current thread and generate a fix")
async def analyze(interaction: discord.Interaction):
    if not interaction.channel:
        return
    messages = await client.collect_thread_messages(interaction.channel)
    prompt = "\n".join(messages)
    ai_result = await client.send_ai_request(prompt)
    fix_data = {
        "thread_id": str(interaction.channel_id),
        "thread_name": interaction.channel.name,
        "problem": "Thread analysis",
        "solution": ai_result,
        "confidence": 0.95,
        "ai_generated": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    client.save_fix(fix_data)
    await interaction.response.send_message(f"AI Fix Generated:\n{ai_result}", ephemeral=False)

@client.tree.command(name="say", description="Bot says a message")
@app_commands.describe(message="Message to send", channel="Channel to send to")
async def say(interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
    # Respond to interaction first to avoid timeout
    await interaction.response.send_message("Sending message...", ephemeral=True)
    target_channel = channel or interaction.channel
    await target_channel.send(message)

@client.tree.command(name="backup", description="Backup all fixes to webhook")
async def backup(interaction: discord.Interaction):
    if not BACKUP_WEBHOOK_URL:
        await interaction.response.send_message("Backup webhook URL not configured!", ephemeral=True)
        return
    
    with open(FIXES_FILE, "r") as f:
        data = f.read()
    async with aiohttp.ClientSession() as session:
        await session.post(BACKUP_WEBHOOK_URL, json={"content": f"Backup:\n```json\n{data}\n```"})
    await interaction.response.send_message("Backup uploaded!", ephemeral=True)

@client.tree.command(name="reload", description="Reload all commands (dev only)")
async def reload(interaction: discord.Interaction):
    if GUILD_ID:
        await client.tree.sync(guild=discord.Object(id=int(GUILD_ID)))
    await interaction.response.send_message("Commands reloaded!", ephemeral=True)

# Button interactions
@client.event
async def on_interaction(interaction: discord.Interaction):
    if not interaction.type == discord.InteractionType.component:
        return
    cid = interaction.data.get("custom_id", "")
    if cid.startswith("mark_solved"):
        await interaction.response.send_message("Thread marked as solved ✅", ephemeral=False)
        await interaction.channel.edit(locked=True)
    elif cid.startswith("mark_unsolved"):
        await interaction.response.send_message("Thread marked as unsolved ❌", ephemeral=False)

# Startup message
@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')

client.run(DISCORD_TOKEN)
