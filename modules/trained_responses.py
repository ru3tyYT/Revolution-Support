# modules/trained_responses.py
"""
Trained/cached responses for common issues - no API calls needed
This saves API costs and speeds up responses for frequently asked questions
"""
import re
from typing import Optional

# Common patterns and their instant responses
TRAINED_PATTERNS = {
    "discord.py install": {
        "keywords": ["install discord.py", "pip install discord", "how to install"],
        "response": """**Installing discord.py**

Run this command in your terminal:
```bash
pip install discord.py
```

If you're using Python 3.10+:
```bash
pip install -U discord.py
```

**Common Issues:**
• If you get a permission error, try: `pip install --user discord.py`
• Make sure you're using the correct Python version
• On some systems, use `pip3` instead of `pip`

**Verify Installation:**
```python
import discord
print(discord.__version__)
```
"""
    },
    
    "intents": {
        "keywords": ["intents are required", "privileged intent", "enable intents", "intent error"],
        "response": """**Discord Bot Intents Error**

You need to enable Privileged Gateway Intents in the Discord Developer Portal:

**Steps:**
1. Go to https://discord.com/developers/applications
2. Select your bot application
3. Navigate to the "Bot" section
4. Scroll down to "Privileged Gateway Intents"
5. Enable these intents:
   • **Presence Intent** (if you need member status)
   • **Server Members Intent** (if you need member events)
   • **Message Content Intent** (if you need to read message content)

**In your code:**
```python
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
```

After enabling intents in the portal, restart your bot.
"""
    },
    
    "token invalid": {
        "keywords": ["invalid token", "improper token", "token error", "401 unauthorized"],
        "response": """**Invalid Bot Token**

Your bot token is either incorrect or has been regenerated.

**Steps to Fix:**
1. Go to https://discord.com/developers/applications
2. Select your bot application
3. Navigate to "Bot" section
4. Click "Reset Token" (you'll need to confirm)
5. Copy the new token **immediately** (it won't be shown again)
6. Replace the token in your `.env` file or configuration

**Security Tips:**
• Never share your token publicly
• Never commit tokens to GitHub
• Use environment variables or `.env` files
• Add `.env` to `.gitignore`

**Example .env file:**
```
DISCORD_TOKEN=your_token_here
```

**In code:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
```
"""
    },
    
    "slash commands not showing": {
        "keywords": ["slash commands not showing", "commands don't appear", "sync commands", "/ commands not working"],
        "response": """**Slash Commands Not Appearing**

**Common Causes:**

1. **Commands not synced:**
```python
await tree.sync()  # Global (takes up to 1 hour)
await tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))  # Instant for testing
```

2. **Bot missing `applications.commands` scope:**
   • Reinvite your bot with this URL format:
   • `https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=8&scope=bot%20applications.commands`

3. **Bot lacks permissions in the server:**
   • Make sure the bot has "Use Application Commands" permission

4. **Try these debug steps:**
```python
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync: {e}")
```

**Wait Time:**
• Guild sync: Instant
• Global sync: Up to 1 hour

If still not working, try kicking and re-inviting the bot.
"""
    },
    
    "rate limit": {
        "keywords": ["rate limit", "429", "too many requests", "ratelimit"],
        "response": """**Discord Rate Limit**

You're sending too many requests to Discord's API.

**Solutions:**

1. **Add delays between actions:**
```python
import asyncio

for item in items:
    await do_something(item)
    await asyncio.sleep(1)  # Wait 1 second
```

2. **Batch operations when possible**

3. **Use built-in rate limit handling:**
Discord.py automatically handles most rate limits, but you can adjust:
```python
# Increase max_messages for bulk operations
async for message in channel.history(limit=100):
    await message.delete()
    # discord.py handles rate limits automatically
```

4. **Check your code for loops that spam API calls**

**Common Mistakes:**
• Deleting many messages in a loop (use `channel.purge()` instead)
• Sending many messages quickly (batch or add delays)
• Excessive permission checks

**If you see 429 errors, your code is making too many requests. Review your logic.**
"""
    },
    
    "on_message not working": {
        "keywords": ["on_message not working", "bot not responding to messages", "message event not firing"],
        "response": """**on_message Event Not Working**

**Common Issues:**

1. **Missing Message Content Intent:**
```python
intents = discord.Intents.default()
intents.message_content = True  # Required!

bot = commands.Bot(command_prefix='!', intents=intents)
```

Enable "Message Content Intent" in Discord Developer Portal → Bot section.

2. **Forgetting to process commands (if using commands.Bot):**
```python
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Your code here
    print(message.content)
    
    await bot.process_commands(message)  # Essential!
```

3. **Bot responding to itself:**
```python
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore own messages
    
    # Rest of code
```

4. **Check bot has permission to read messages in that channel**
"""
    },

    "embed": {
        "keywords": ["how to make embed", "create embed", "embed tutorial", "discord embed"],
        "response": """**Creating Discord Embeds**

**Basic Embed:**
```python
embed = discord.Embed(
    title="Title Here",
    description="Description here",
    color=discord.Color.blue()  # or 0x0000FF
)

embed.add_field(name="Field Name", value="Field Value", inline=False)
embed.set_footer(text="Footer text")
embed.set_thumbnail(url="image_url")

await channel.send(embed=embed)
```

**Full Example:**
```python
embed = discord.Embed(
    title="⭐ Cool Embed",
    description="This is the description",
    color=0x00FF00,
    timestamp=datetime.datetime.now()
)

embed.set_author(name="Author Name", icon_url="url")
embed.add_field(name="Field 1", value="Value 1", inline=True)
embed.add_field(name="Field 2", value="Value 2", inline=True)
embed.set_image(url="large_image_url")
embed.set_thumbnail(url="small_image_url")
embed.set_footer(text="Footer", icon_url="icon_url")

await ctx.send(embed=embed)
```

**Colors:**
• `discord.Color.blue()`, `.red()`, `.green()`, etc.
• Hex: `0xFF5733`
• RGB: `discord.Color.from_rgb(255, 87, 51)`
"""
    }
}

def get_trained_response(title: str, content: str) -> Optional[str]:
    """
    Check if we have a trained response for this issue
    Returns the response if found, None otherwise
    """
    combined_text = f"{title} {content}".lower()
    
    for pattern_name, pattern_data in TRAINED_PATTERNS.items():
        keywords = pattern_data["keywords"]
        
        # Check if any keyword matches
        for keyword in keywords:
            if keyword.lower() in combined_text:
                return pattern_data["response"]
    
    return None

def add_trained_pattern(name: str, keywords: list, response: str):
    """
    Add a new trained pattern at runtime
    """
    TRAINED_PATTERNS[name] = {
        "keywords": keywords,
        "response": response
    }
