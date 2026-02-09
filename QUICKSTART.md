# Discord Support Bot - Quick Start Guide

> Complete step-by-step guide to deploy a production-ready Discord support bot with AI-powered responses and cost optimization.

**Estimated Total Time:** 2-3 hours (first time) | **30 minutes** (subsequent deployments)

---

## Prerequisites

### Required Accounts

- [ ] **Discord Account** - [Sign up](https://discord.com/register) (if you don't have one)
- [ ] **Discord Developer Account** - Same as Discord account, access at [Discord Developer Portal](https://discord.com/developers/applications)
- [ ] **AI Provider Account(s)** - We'll set up free tiers:
  - Groq (Free tier available)
  - OpenRouter (Free tier available)
  - Optional: OpenAI (paid, but we'll minimize usage)

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.12+ | Bot runtime |
| PostgreSQL | 15+ | Database |
| Redis | 7+ | Cache & sessions |
| Docker | Latest | Containerization |
| Git | Latest | Version control |

### System Requirements

**Minimum (Development):**
- 2 CPU cores
- 4GB RAM
- 20GB disk space

**Recommended (Production):**
- 4+ CPU cores
- 8GB+ RAM
- 50GB+ SSD storage
- Stable internet connection

---

## Step 1: Discord Bot Setup

**Time: 15-20 minutes**

### 1.1 Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** (top right)
3. Enter your bot name (e.g., "MySupportBot")
4. Click **"Create"**
5. Navigate to the **"General Information"** tab

**What you'll find here:**
- Application ID (you'll need this later)
- Public Key (for interactions)

### 1.2 Get Bot Token

1. Click **"Bot"** in the left sidebar
2. Click **"Reset Token"** or **"Copy"** if one exists
3. **⚠️ SAVE THIS IMMEDIATELY** - Discord only shows it once!
4. Store it securely (we'll use it in Step 3)

**Expected format:**
```
MTA0MjAxMjM0NTY3ODkwMTIzNA.Gxk9a1.abcdefghijklmnopqrstuvwxyz123456789
```

### 1.3 Configure OAuth2 Permissions

1. Click **"OAuth2"** in the left sidebar
2. Click **"URL Generator"**
3. Select these **Scopes**:
   - ✅ `bot`
   - ✅ `applications.commands`

4. Select these **Bot Permissions**:
   - ✅ `Send Messages`
   - ✅ `Send Messages in Threads`
   - ✅ `Create Public Threads`
   - ✅ `Create Private Threads`
   - ✅ `Embed Links`
   - ✅ `Attach Files`
   - ✅ `Read Message History`
   - ✅ `Mention Everyone`
   - ✅ `Use External Emojis`
   - ✅ `Add Reactions`
   - ✅ `Use Slash Commands`
   - ✅ `Manage Messages` (for auto-moderation)
   - ✅ `Manage Threads` (for forum support)
   - ✅ `View Audit Log`
   - ✅ `Manage Channels` (optional, for ticket system)

5. **Copy the generated URL** - you'll use it in Step 1.4

### 1.4 Add Bot to Your Server

1. Open the URL from Step 1.3 in a new browser tab
2. Select your server from the dropdown
3. Click **"Authorize"**
4. Complete the CAPTCHA
5. You should see a success message

### 1.5 Enable Required Intents

**⚠️ CRITICAL STEP** - Without these, the bot won't work properly!

1. Go back to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"Bot"** in the left sidebar
3. Scroll to **"Privileged Gateway Intents"**
4. Enable these three intents:
   - ✅ **SERVER MEMBERS INTENT** - Required to see server members
   - ✅ **MESSAGE CONTENT INTENT** - Required to read message content
   - ✅ **PRESENCE INTENT** - Required to see user presence (optional but recommended)

5. Click **"Save Changes"**

**Expected Result:**
- Bot appears in your Discord server as an offline user
- Bot has a role with the permissions you selected

### Step 1 Checklist

- [ ] Application created
- [ ] Bot token saved securely
- [ ] OAuth2 URL generated
- [ ] Bot added to server
- [ ] All three privileged intents enabled

---

## Step 2: Environment Setup

**Time: 10-15 minutes**

### 2.1 Clone Repository

```bash
# Create a directory for your bot
cd ~ && mkdir -p discord-bots && cd discord-bots

# Clone the repository
git clone https://github.com/yourorg/discord-support-bot.git
cd discord-support-bot

# Verify the clone worked
ls -la
```

**Expected output:**
```
total 152
drwxr-xr-x  24 user  staff   768 Feb  8 21:53 .
drwxr-xr-x   6 user  staff   192 Feb  8 21:52 ..
-rw-r--r--@  1 user  staff  1406 Feb  8 21:17 .dockerignore
-rw-r--r--@  1 user  staff  5748 Feb  8 21:22 .env.example
-rw-r--r--@  1 user  staff  6417 Feb  8 21:22 .gitignore
-rw-r--r--@  1 user  staff  10016 Feb  8 21:21 pyproject.toml
...
```

### 2.2 Create Virtual Environment

```bash
# Create virtual environment
python3.12 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# On Windows (CMD):
# .venv\Scripts\activate.bat

# Verify activation (should show path to .venv)
which python
```

**Expected output:**
```
/Users/username/discord-bots/discord-support-bot/.venv/bin/python
```

### 2.3 Install Dependencies

```bash
# Install the bot package with development dependencies
pip install -e ".[dev,all-providers]"

# Verify installation
pip list | grep -i discord
```

**Expected output:**
```
discord.py              2.3.0
discord-support-bot     1.0.0
```

**If you encounter errors:**

1. **Python version error:**
   ```bash
   # Check Python version
   python --version  # Should be 3.12+
   
   # If using wrong version:
   python3.12 -m venv .venv
   ```

2. **Permission error:**
   ```bash
   # Try with --user flag
   pip install -e ".[dev,all-providers]" --user
   ```

### 2.4 Copy Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Verify file was created
ls -la .env
```

**Expected output:**
```
-rw-r--r--  1 user  staff  5769 Feb  9 10:30 .env
```

### Step 2 Checklist

- [ ] Repository cloned
- [ ] Virtual environment created and activated
- [ ] Dependencies installed successfully
- [ ] .env file created

---

## Step 3: Database Setup

**Time: 15-20 minutes**

### 3.1 Install PostgreSQL with pgvector

#### Option A: Docker (Recommended for Development)

```bash
# Run PostgreSQL with pgvector in Docker
docker run -d \
  --name supportbot-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=supportbot \
  -p 5432:5432 \
  ankane/pgvector:latest

# Wait for database to start
sleep 5

# Verify it's running
docker ps | grep supportbot-db
```

**Expected output:**
```
CONTAINER ID   IMAGE                  STATUS          PORTS
abc123def456   ankane/pgvector:latest Up 10 seconds   0.0.0.0:5432->5432/tcp
```

#### Option B: Local Installation (macOS)

```bash
# Install PostgreSQL
brew install postgresql@15

# Install pgvector
brew install pgvector

# Start PostgreSQL
brew services start postgresql@15

# Create database and user
psql postgres -c "CREATE USER supportbot WITH PASSWORD 'your_secure_password';"
psql postgres -c "CREATE DATABASE supportbot OWNER supportbot;"
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE supportbot TO supportbot;"
```

#### Option C: Local Installation (Ubuntu/Debian)

```bash
# Install PostgreSQL
sudo apt update
sudo apt install -y postgresql-15 postgresql-contrib

# Install pgvector
sudo apt install -y postgresql-15-pgvector

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE USER supportbot WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE supportbot OWNER supportbot;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE supportbot TO supportbot;"
```

### 3.2 Create Database and User

If you used Docker (Option A), the database is already created. Skip to Step 3.3.

For local installations:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE supportbot;

# Create user
CREATE USER supportbot_user WITH PASSWORD 'your_secure_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE supportbot TO supportbot_user;

# Enable pgvector extension (if not already enabled)
\c supportbot
CREATE EXTENSION IF NOT EXISTS vector;

# Exit
\q
```

### 3.3 Update Environment Variables

Edit your `.env` file:

```bash
# Open .env in your preferred editor
nano .env  # or vim, code, etc.
```

Update the database URL:

```bash
# Find this line:
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/supportbot

# Replace with your credentials:
DATABASE_URL=postgresql://supportbot_user:your_secure_password@localhost:5432/supportbot
```

**Common pitfall:** Make sure the URL format is exactly:
```
postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
```

### 3.4 Run Migrations

```bash
# Run database migrations
alembic upgrade head

# Verify migrations ran successfully
alembic current
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> abc123, create initial tables
```

### 3.5 Verify Connection

```bash
# Test database connection using Python
python -c "
from sqlalchemy import create_engine
from bot.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute('SELECT version();')
    print(result.fetchone()[0])
"
```

**Expected output:**
```
PostgreSQL 15.4 on x86_64-pc-linux-gnu...
```

### Step 3 Checklist

- [ ] PostgreSQL installed and running
- [ ] pgvector extension enabled
- [ ] Database created
- [ ] User created with privileges
- [ ] .env updated with database URL
- [ ] Migrations ran successfully

---

## Step 4: AI Provider Configuration

**Time: 20-30 minutes**

### 4.1 Set Up Groq (Free Tier - Recommended)

**Why Groq?** Ultra-fast inference, completely free tier with generous limits.

1. Go to [Groq Console](https://console.groq.com/)
2. Sign up with your email or GitHub
3. Navigate to **"API Keys"** in the left sidebar
4. Click **"Create API Key"**
5. Give it a name (e.g., "DiscordBot")
6. **Copy the API key immediately** (starts with `gsk_`)

**Add to .env:**
```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Free Tier Limits:**
- 144,000 tokens/minute
- Llama 3 70B, Mixtral 8x7B available
- Perfect for keyword routing

### 4.2 Set Up OpenRouter (Free Tier - Fallback)

**Why OpenRouter?** Access to 100+ models, many with free tiers.

1. Go to [OpenRouter](https://openrouter.ai/)
2. Click **"Sign In"** and create an account
3. Navigate to **"Keys"**
4. Click **"Create Key"**
5. **Copy the key** (starts with `sk-or-`)

**Add to .env:**
```bash
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_REFERER=https://yourdomain.com  # Optional: your website
OPENROUTER_TITLE=Discord Support Bot       # Optional: your bot name
```

**Free Models Available:**
- Mistral 7B Instruct
- OpenChat 3.5
- Nous Hermes 2 Mixtral

### 4.3 Set Up Ollama Cloud (Optional - Self-Hosted)

**Why Ollama?** Run models locally for complete privacy.

1. Install Ollama locally:
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. Pull a model:
   ```bash
   ollama pull llama3.2
   ```

3. Start Ollama server:
   ```bash
   ollama serve
   ```

**Add to .env:**
```bash
OLLAMA_CLOUD_KEY=local
OLLAMA_CLOUD_BASE_URL=http://localhost:11434/v1
OLLAMA_CLOUD_MODEL=llama3.2
```

### 4.4 Set Up OpenAI (Optional - Premium)

**Why OpenAI?** Best-in-class models for complex queries.

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up/login
3. Navigate to **"API keys"**
4. Click **"Create new secret key"**
5. **Copy the key** (starts with `sk-`)
6. Add payment method (you control spending)

**Add to .env:**
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**💰 Cost Tip:** Only enable OpenAI for complex queries. Use Groq/OpenRouter for 70-80% of traffic.

### 4.5 Configure AI Routing

Edit `.env` to set up smart routing:

```bash
# Default model (use Groq for cost savings)
DEFAULT_MODEL=llama3-70b-8192

# Cost optimization
ENABLE_COST_OPTIMIZATION=true
COST_BUDGET_DAILY=10.00      # Adjust based on your budget
COST_BUDGET_MONTHLY=200.00
COST_ALERT_THRESHOLD=0.8

# Enable smart routing
ENABLE_SMART_ROUTING=true
```

### Step 4 Checklist

- [ ] Groq API key obtained and added to .env
- [ ] OpenRouter API key obtained and added to .env
- [ ] Ollama set up locally (optional)
- [ ] OpenAI API key obtained (optional)
- [ ] AI routing configured in .env

---

## Step 5: Redis Setup

**Time: 10-15 minutes**

### 5.1 Install Redis

#### Option A: Docker (Recommended)

```bash
# Run Redis in Docker
docker run -d \
  --name supportbot-redis \
  -p 6379:6379 \
  redis:7-alpine

# Verify it's running
docker ps | grep supportbot-redis
```

**Expected output:**
```
CONTAINER ID   IMAGE            STATUS          PORTS
def789abc012   redis:7-alpine   Up 5 seconds    0.0.0.0:6379->6379/tcp
```

#### Option B: Local Installation (macOS)

```bash
# Install Redis
brew install redis

# Start Redis
brew services start redis

# Verify it's running
redis-cli ping
```

#### Option C: Local Installation (Ubuntu/Debian)

```bash
# Install Redis
sudo apt update
sudo apt install -y redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify it's running
redis-cli ping
```

### 5.2 Configure Redis Connection

Your `.env` file should already have the default Redis URL:

```bash
REDIS_URL=redis://localhost:6379/0
```

If using Docker with a custom network:

```bash
# Create a network for your containers
docker network create supportbot-network

# Run Redis on the network
docker run -d \
  --name supportbot-redis \
  --network supportbot-network \
  -p 6379:6379 \
  redis:7-alpine

# Update .env
REDIS_URL=redis://supportbot-redis:6379/0
```

### 5.3 Test Connection

```bash
# Test Redis connection
redis-cli ping

# Or using Python
python -c "
import redis
r = redis.from_url('redis://localhost:6379/0')
print(r.ping())  # Should print: True
print(r.info()['redis_version'])  # Should print version
"
```

**Expected output:**
```
True
7.0.12
```

### Step 5 Checklist

- [ ] Redis installed and running
- [ ] Connection tested successfully
- [ ] .env configured with Redis URL

---

## Step 6: Basic Configuration

**Time: 10-15 minutes**

### 6.1 Configure Bot Settings

Edit `.env` with your bot configuration:

```bash
# Discord Bot Token (from Step 1.2)
DISCORD_TOKEN=MTA0MjAxMjM0NTY3ODkwMTIzNA.Gxk9a1.abcdefghijklmnopqrstuvwxyz123456789

# Bot Settings
BOT_PREFIX=!
BOT_STATUS_MESSAGE=Support Bot | !help
BOT_OWNERS=123456789,987654321  # Your Discord user ID(s)

# Environment
ENV=development  # Change to 'production' for live deployment
DEBUG=false
LOG_LEVEL=INFO
```

**To get your Discord User ID:**
1. Enable Developer Mode in Discord (User Settings > Advanced)
2. Right-click your username
3. Click **"Copy User ID"**

### 6.2 Configure Rate Limits

```bash
# Global rate limits
GLOBAL_RATE_LIMIT_ENABLED=true
GLOBAL_RATE_LIMIT_REQUESTS=100
GLOBAL_RATE_LIMIT_WINDOW=60

# Per-user rate limits
USER_RATE_LIMIT_ENABLED=true
USER_RATE_LIMIT_REQUESTS=10
USER_RATE_LIMIT_WINDOW=60

# Admin bypass
ADMIN_RATE_LIMIT_BYPASS=true
```

### 6.3 Configure Sharding (If Needed)

For most servers (< 2,500 guilds), auto-sharding is fine:

```bash
SHARD_COUNT=auto
SHARD_CLUSTER_ID=0
SHARD_CLUSTER_COUNT=1
```

For larger deployments, see the Scaling documentation.

### 6.4 Enable Required Intents

Ensure these are set to `true` in `.env`:

```bash
INTENT_GUILD_MESSAGES=true
INTENT_DIRECT_MESSAGES=true
INTENT_GUILD_MEMBERS=true
INTENT_MESSAGE_CONTENT=true
INTENT_GUILD_REACTIONS=true
```

### Step 6 Checklist

- [ ] Discord token added to .env
- [ ] Bot prefix configured
- [ ] Owner IDs added
- [ ] Rate limits configured
- [ ] Sharding configured
- [ ] All intents enabled

---

## Step 7: First Run

**Time: 10-15 minutes**

### 7.1 Verify Environment

```bash
# Run configuration check
python -c "
from bot.config import settings
print('Discord Token:', '✓ Set' if settings.DISCORD_TOKEN else '✗ Missing')
print('Database URL:', '✓ Set' if settings.DATABASE_URL else '✗ Missing')
print('Redis URL:', '✓ Set' if settings.REDIS_URL else '✗ Missing')
print('AI Providers:', len([k for k in settings.__dict__ if 'API_KEY' in k and settings.__dict__[k]]))
"
```

### 7.2 Start Services

If using Docker:

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

If using local installations:

```bash
# Ensure PostgreSQL is running
brew services list | grep postgresql  # macOS
sudo systemctl status postgresql      # Linux

# Ensure Redis is running
brew services list | grep redis       # macOS
sudo systemctl status redis-server    # Linux
```

### 7.3 Start the Bot

```bash
# Start the bot
python -m bot
```

**Expected output:**
```
2026-02-09 14:30:15 [INFO] bot.main: Starting Discord Support Bot v1.0.0
2026-02-09 14:30:15 [INFO] bot.database: Database connection established
2026-02-09 14:30:15 [INFO] bot.cache: Redis connection established
2026-02-09 14:30:15 [INFO] bot.ai: AI router initialized with 2 providers
2026-02-09 14:30:16 [INFO] bot.discord: Logging in...
2026-02-09 14:30:17 [INFO] bot.discord: Logged in as MySupportBot#1234
2026-02-09 14:30:17 [INFO] bot.discord: Connected to 1 guild(s)
2026-02-09 14:30:17 [INFO] bot.main: Bot is ready!
```

### 7.4 Verify Bot is Working

In your Discord server:

1. Type: `!ping`
2. **Expected response:**
   ```
   Pong! Latency: 45ms | API Latency: 120ms
   ```

3. Type: `!stats`
4. **Expected response:** Rich embed showing:
   - Bot uptime
   - Servers connected
   - Total users
   - Commands processed
   - AI provider status

### 7.5 Test AI Response

1. Type: `!ask What is 2+2?`
2. **Expected response:** Rich embed with answer:
   ```
   🤖 AI Response
   
   2+2 equals 4.
   
   Model: llama3-70b-8192
   Cost: $0.0000 (Free tier)
   ```

### Common Issues

**Issue: "Bot doesn't respond to commands"**
- Check that MESSAGE_CONTENT intent is enabled
- Verify bot has SEND_MESSAGES permission
- Check console for errors

**Issue: "Database connection failed"**
- Ensure PostgreSQL is running: `docker ps` or `brew services list`
- Check DATABASE_URL in .env
- Verify database exists: `psql -U supportbot_user -d supportbot -c "\dt"`

**Issue: "Redis connection failed"**
- Ensure Redis is running: `redis-cli ping`
- Check REDIS_URL in .env

**Issue: "No AI providers available"**
- Verify at least one API key is set in .env
- Check that keys are valid (test with curl)

### Step 7 Checklist

- [ ] Environment verified
- [ ] Services running
- [ ] Bot starts without errors
- [ ] `!ping` responds
- [ ] `!stats` works
- [ ] AI responds to `!ask`

---

## Step 8: Configure Keywords

**Time: 15-20 minutes**

### 8.1 Add Your First Keywords

Create a keywords configuration file:

```bash
# Create keywords directory if not exists
mkdir -p config

# Create keywords.yaml
cat > config/keywords.yaml << 'EOF'
# FAQ Keywords - Route to free models (70% of queries)
faq_keywords:
  - keywords: ["password", "reset", "forgot"]
    response_template: "To reset your password: 1) Go to login page 2) Click 'Forgot Password' 3) Check your email"
    confidence_threshold: 0.85
    use_free_model: true
    
  - keywords: ["login", "signin", "access"]
    response_template: "Having trouble logging in? Try clearing your browser cache or using incognito mode."
    confidence_threshold: 0.80
    use_free_model: true
    
  - keywords: ["billing", "payment", "invoice"]
    response_template: "For billing inquiries, please check your account settings or contact billing@example.com"
    confidence_threshold: 0.75
    use_free_model: false  # Use paid model for accuracy
    
  - keywords: ["download", "install", "setup"]
    response_template: "You can download our software from the official website. Installation guides are in the docs."
    confidence_threshold: 0.80
    use_free_model: true

# Simple question keywords - Use budget models
simple_keywords:
  - keywords: ["how to", "what is", "where"]
    model: "gpt-3.5-turbo"
    max_tokens: 500
    
# Complex issue keywords - Use premium models
complex_keywords:
  - keywords: ["integrate", "api", "webhook"]
    model: "gpt-4o"
    max_tokens: 2000
    
  - keywords: ["bug", "crash", "error"]
    model: "gpt-4o"
    max_tokens: 2000
    require_context: true
EOF
```

### 8.2 Load Keywords into Database

```bash
# Run the keyword loader script
python -c "
from bot.keywords.loader import load_keywords
from bot.database import get_db

load_keywords('config/keywords.yaml')
print('Keywords loaded successfully!')
"
```

### 8.3 Test Keyword Matching

In Discord, test these commands:

1. `!ask I forgot my password`
   - **Expected:** Quick response using Groq (free)
   - **Response time:** < 500ms

2. `!ask How do I integrate with your API?`
   - **Expected:** Detailed response using GPT-4o (premium)
   - **Response time:** 2-3 seconds

3. Check cost savings:
   ```bash
   # View cost statistics
   !costs
   ```

### 8.4 Monitor Keyword Performance

```bash
# View keyword match statistics
python -c "
from bot.analytics.keywords import get_stats
stats = get_stats()
print(f'FAQ matches: {stats.faq_matches}')
print(f'Simple matches: {stats.simple_matches}')
print(f'Complex matches: {stats.complex_matches}')
print(f'Estimated savings: {stats.estimated_savings}%')
"
```

### Step 8 Checklist

- [ ] Keywords YAML file created
- [ ] Keywords loaded into database
- [ ] Password reset keyword tested
- [ ] API integration keyword tested
- [ ] Cost savings verified with !costs

---

## Step 9: Set Up Forum Support

**Time: 20-25 minutes**

### 9.1 Create Forum Channel

In Discord:

1. Right-click your server name
2. Click **"Create Channel"**
3. Select **"Forum"** as channel type
4. Name it: `support-forum`
5. Click **"Create Channel"**

### 9.2 Configure Forum Settings

1. Click the channel settings (gear icon)
2. Configure:
   - **Guidelines:** Add support guidelines
   - **Tags:** Create tags like `Bug`, `Feature Request`, `Question`
   - **Slowmode:** Set to 5-10 seconds to prevent spam
   - **Permissions:** Ensure bot can read/send messages

### 9.3 Configure Bot for Forum Monitoring

Edit `.env`:

```bash
# Enable forum monitoring
ENABLE_AUTOMATED_RESPONSES=true

# Forum channel ID (get this by right-clicking the channel > Copy Channel ID)
FORUM_CHANNEL_ID=1234567890123456789

# Auto-response settings
FORUM_AUTO_RESPOND=true
FORUM_RESPONSE_DELAY=5  # Seconds to wait before responding
FORUM_CONFIDENCE_THRESHOLD=0.7  # Minimum confidence to auto-respond
FORUM_MAX_RESPONSES_PER_THREAD=3  # Limit responses per thread
```

**To get the Forum Channel ID:**
1. Enable Developer Mode in Discord
2. Right-click the forum channel
3. Click **"Copy Channel ID"**

### 9.4 Test Forum Monitoring

1. Create a new post in the forum:
   - Title: "How do I reset my password?"
   - Content: "I forgot my password and can't log in"

2. Wait 5 seconds

3. **Expected:** Bot should auto-respond with:
   ```
   🤖 Auto-Response
   
   To reset your password:
   1) Go to the login page
   2) Click "Forgot Password"
   3) Check your email for reset link
   
   If you need more help, reply here!
   ```

### 9.5 Configure Human Handoff

Set up escalation for complex issues:

```bash
# In .env
ESCALATION_ROLE_ID=1234567890123456789  # Support team role ID
ESCALATION_WEBHOOK_URL=https://hooks.slack.com/...  # Optional: Slack webhook
```

### Step 9 Checklist

- [ ] Forum channel created
- [ ] Forum permissions configured
- [ ] Channel ID added to .env
- [ ] Forum monitoring enabled
- [ ] Test post created and bot responded
- [ ] Human escalation configured

---

## Step 10: Knowledge Base

**Time: 20-30 minutes**

### 10.1 Create First Knowledge Document

Create a sample documentation file:

```bash
mkdir -p docs/knowledge

cat > docs/knowledge/getting-started.md << 'EOF'
# Getting Started Guide

## Account Setup

### Creating an Account
1. Visit our website
2. Click "Sign Up"
3. Enter your email and password
4. Verify your email address

### Logging In
1. Go to the login page
2. Enter your credentials
3. Click "Sign In"

## Troubleshooting

### Forgot Password
If you forgot your password:
1. Click "Forgot Password" on the login page
2. Enter your email address
3. Check your email for reset instructions
4. Create a new password

### Account Locked
If your account is locked:
- Wait 30 minutes and try again
- Contact support if the issue persists

## Features

### Dashboard
The dashboard provides an overview of your account:
- Recent activity
- Quick actions
- Notifications
- Settings access

### Settings
Access settings to customize your experience:
- Profile information
- Notification preferences
- Security settings
- Connected apps
EOF
```

### 10.2 Upload to Knowledge Base

```bash
# Upload the document
python -c "
from bot.knowledge.uploader import upload_document
import asyncio

async def upload():
    result = await upload_document(
        file_path='docs/knowledge/getting-started.md',
        title='Getting Started Guide',
        category='user-guide'
    )
    print(f'Document uploaded: {result.document_id}')
    print(f'Chunks created: {result.chunk_count}')

asyncio.run(upload())
"
```

**Expected output:**
```
Document uploaded: doc_abc123def456
Chunks created: 12
```

### 10.3 Test RAG Responses

In Discord:

1. `!kb search how to create an account`

**Expected response:**
```
📚 Knowledge Base Results

Found 3 relevant sections:

1. Creating an Account
   Visit our website, click "Sign Up", enter your email...
   
2. Account Setup
   The account setup process includes verification...
   
3. Dashboard Features
   The dashboard provides an overview after account creation...
```

2. `!ask How do I reset my password?`

**Expected response:**
```
🤖 AI Response (with KB context)

Based on our documentation, here's how to reset your password:

1. Click "Forgot Password" on the login page
2. Enter your email address
3. Check your email for reset instructions
4. Create a new password

Source: Getting Started Guide
Confidence: 95%
```

### 10.4 Upload Additional Documents

```bash
# Create FAQ document
cat > docs/knowledge/faq.md << 'EOF'
# Frequently Asked Questions

## Billing

Q: How do I update my payment method?
A: Go to Settings > Billing > Payment Methods and click "Add New Card"

Q: Can I get a refund?
A: Refunds are available within 14 days of purchase. Contact billing@example.com

## Technical

Q: What browsers are supported?
A: We support Chrome, Firefox, Safari, and Edge (latest 2 versions)

Q: Is there a mobile app?
A: Yes! Download from the App Store or Google Play

## Account

Q: Can I change my username?
A: Yes, go to Settings > Profile > Edit Username

Q: How do I delete my account?
A: Contact support@example.com to request account deletion
EOF

# Upload it
python -c "
from bot.knowledge.uploader import upload_document
import asyncio

async def upload():
    result = await upload_document(
        file_path='docs/knowledge/faq.md',
        title='Frequently Asked Questions',
        category='faq'
    )
    print(f'FAQ uploaded: {result.document_id}')

asyncio.run(upload())
"
```

### Step 10 Checklist

- [ ] Knowledge base directory created
- [ ] First document uploaded
- [ ] RAG search tested
- [ ] AI response with context tested
- [ ] Additional documents uploaded

---

## Step 11: Production Deployment

**Time: 30-45 minutes**

### 11.1 Docker Deployment

#### Build Production Image

```bash
# Build the Docker image
docker build -t discord-support-bot:latest -f docker/Dockerfile .

# Verify image was built
docker images | grep discord-support-bot
```

#### Create Production Compose File

```bash
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  bot:
    image: discord-support-bot:latest
    container_name: supportbot-prod
    restart: unless-stopped
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis
    networks:
      - supportbot-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

  postgres:
    image: ankane/pgvector:latest
    container_name: supportbot-db-prod
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER:-supportbot}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-change_me_in_production}
      POSTGRES_DB: ${DB_NAME:-supportbot}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - supportbot-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-supportbot}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: supportbot-redis-prod
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - supportbot-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Optional: Nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: supportbot-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/ssl:/etc/nginx/ssl:ro
    networks:
      - supportbot-network
    depends_on:
      - bot

volumes:
  postgres_data:
  redis_data:

networks:
  supportbot-network:
    driver: bridge
EOF
```

#### Create Production Environment File

```bash
# Copy and edit production environment
cp .env .env.production

# Edit with production values
nano .env.production
```

**Key changes for production:**

```bash
# Environment
ENV=production
DEBUG=false
LOG_LEVEL=WARNING

# Security
BOT_OWNERS=your_discord_user_id  # Only you

# Database - use strong password
DATABASE_URL=postgresql://supportbot:STRONG_PASSWORD@postgres:5432/supportbot

# Redis
REDIS_URL=redis://redis:6379/0

# Rate limiting - stricter for production
GLOBAL_RATE_LIMIT_REQUESTS=50
USER_RATE_LIMIT_REQUESTS=5

# Cost control
COST_BUDGET_DAILY=50.00
COST_ALERT_THRESHOLD=0.75

# Monitoring
ENABLE_PROMETHEUS=true
PROMETHEUS_PORT=8000
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PORT=8080
```

### 11.2 Deploy with Docker Compose

```bash
# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f bot
```

### 11.3 Health Checks

```bash
# Test health endpoint
curl http://localhost:8080/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2026-02-09T14:30:00Z",
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "discord": "connected"
  }
}
```

### 11.4 SSL/TLS Configuration (Optional but Recommended)

For production, use a reverse proxy with SSL:

```bash
# Create Nginx config
cat > docker/nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream bot {
        server bot:8080;
    }

    server {
        listen 443 ssl http2;
        server_name bot.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://bot;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }
    }
}
EOF
```

### Step 11 Checklist

- [ ] Docker image built
- [ ] Production compose file created
- [ ] .env.production configured
- [ ] Stack deployed with docker-compose
- [ ] Health check endpoint responding
- [ ] SSL configured (optional)

---

## Step 12: Monitoring Setup

**Time: 30-40 minutes**

### 12.1 Set Up Prometheus

Create Prometheus configuration:

```bash
mkdir -p monitoring/prometheus

cat > monitoring/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: []

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'discord-bot'
    static_configs:
      - targets: ['bot:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
EOF
```

Create alert rules:

```bash
cat > monitoring/prometheus/alert_rules.yml << 'EOF'
groups:
  - name: discord-bot
    rules:
      - alert: BotDown
        expr: up{job="discord-bot"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Discord bot is down"
          description: "The Discord bot has been down for more than 1 minute"

      - alert: HighErrorRate
        expr: rate(bot_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 10% for the last 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(bot_response_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response latency"
          description: "95th percentile latency is above 5 seconds"

      - alert: HighCost
        expr: bot_daily_cost_dollars > 40
        for: 1h
        labels:
          severity: info
        annotations:
          summary: "Approaching daily cost budget"
          description: "Daily cost is above $40 (threshold: $50)"
EOF
```

### 12.2 Set Up Grafana

Add to docker-compose.prod.yml:

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: supportbot-prometheus
    restart: unless-stopped
    volumes:
      - ./monitoring/prometheus:/etc/prometheus:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    networks:
      - supportbot-network
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    container_name: supportbot-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=your_secure_password
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    networks:
      - supportbot-network
    ports:
      - "3000:3000"
    depends_on:
      - prometheus

volumes:
  prometheus_data:
  grafana_data:
```

Create Grafana datasources:

```bash
mkdir -p monitoring/grafana/datasources

cat > monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF
```

Create dashboards directory:

```bash
mkdir -p monitoring/grafana/dashboards
```

### 12.3 Configure Alerts

Set up alert notifications:

1. Access Grafana at `http://localhost:3000`
2. Login with admin credentials
3. Go to **Alerting > Notification channels**
4. Add your preferred channels:
   - Email
   - Slack
   - Discord webhook
   - PagerDuty

### 12.4 Key Metrics to Monitor

| Metric | Normal Range | Alert Threshold |
|--------|--------------|-----------------|
| Bot Uptime | 100% | < 99% |
| Response Latency | < 2s | > 5s |
| Error Rate | < 1% | > 5% |
| Daily Cost | <$30 | > $40 |
| Database Connections | < 80% | > 90% |
| Redis Memory | < 70% | > 85% |

### Step 12 Checklist

- [ ] Prometheus configured
- [ ] Alert rules created
- [ ] Grafana added to compose
- [ ] Dashboards directory created
- [ ] Datasources configured
- [ ] Alert notifications set up
- [ ] Metrics verified in Grafana

---

## Verification Checklist

### Bot Commands Test

Run these commands in Discord to verify functionality:

| Command | Expected Result | Status |
|---------|-----------------|--------|
| `!ping` | Shows latency stats | [ ] |
| `!status` | Rich embed with health info | [ ] |
| `!stats` | Usage statistics | [ ] |
| `!ask What is 2+2?` | AI response with embed | [ ] |
| `!ask How do I reset my password?` | Keyword-matched response | [ ] |
| `!kb search account` | Knowledge base results | [ ] |
| `!costs` | Cost breakdown | [ ] |
| `!help` | Command list | [ ] |

### System Health Checks

```bash
# Run these commands to verify system health

# 1. Bot container running
docker ps | grep supportbot

# 2. Database connection
psql $DATABASE_URL -c "SELECT version();"

# 3. Redis connection
redis-cli -u $REDIS_URL ping

# 4. Health endpoint
curl http://localhost:8080/health

# 5. Prometheus metrics
curl http://localhost:8000/metrics | head -20

# 6. Grafana access
curl -I http://localhost:3000
```

### Troubleshooting Guide

**Bot not responding:**
```bash
# Check logs
docker-compose logs -f bot

# Verify Discord token
grep DISCORD_TOKEN .env

# Test Discord connection
python -c "
import discord
import asyncio

async def test():
    client = discord.Client(intents=discord.Intents.default())
    try:
        await client.login('YOUR_TOKEN')
        print('Login successful')
        await client.close()
    except Exception as e:
        print(f'Error: {e}')

asyncio.run(test())
"
```

**Database connection failed:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check database exists
docker exec supportbot-db psql -U supportbot -c "\l" | grep supportbot

# Run migrations
docker-compose exec bot alembic upgrade head
```

**High response times:**
```bash
# Check AI provider latency
curl -w "@curl-format.txt" -o /dev/null -s https://api.groq.com/openai/v1/models

# Check Redis latency
redis-cli --latency

# Monitor database queries
# Enable query logging in PostgreSQL
```

**Cost overruns:**
```bash
# Check current cost tracking
!costs  # In Discord

# Enable free tier mode
# Edit .env: FREE_TIER_MODE=true

# Review keyword routing
# Check logs for routing decisions
```

---

## Next Steps

### Scaling for Production

**Horizontal Scaling:**
```bash
# Scale bot instances
docker-compose up -d --scale bot=3

# Use load balancer (Nginx/HAProxy)
# Configure sticky sessions for Discord gateway
```

**Database Optimization:**
```bash
# Add read replicas for analytics queries
# Enable connection pooling (PgBouncer)
# Set up automated backups
```

**Redis Clustering:**
```bash
# For high availability
# Set up Redis Sentinel or Cluster mode
```

### Customization Options

1. **Custom Commands:**
   - Edit `bot/commands/custom.py`
   - Add your business-specific commands

2. **Custom AI Prompts:**
   - Edit `config/prompts.yaml`
   - Customize response style

3. **Custom Embeds:**
   - Edit `bot/embeds/` directory
   - Match your brand colors

4. **Custom Integrations:**
   - Slack webhook support
   - Custom API endpoints
   - Webhook notifications

### Documentation Links

- [Full Documentation](./docs/)
- [API Reference](./docs/api/)
- [Deployment Guides](./docs/deployment/)
- [Configuration Reference](./docs/configuration.md)
- [Troubleshooting](./docs/troubleshooting.md)

### Support Channels

- 🎮 **Discord:** [Join our support server](https://discord.gg/yourserver)
- 🐛 **GitHub Issues:** [Report bugs](https://github.com/yourorg/discord-support-bot/issues)
- 📧 **Email:** support@yourcompany.com

---

## Summary

Congratulations! You now have a fully functional Discord support bot with:

✅ Multi-provider AI support (Groq, OpenRouter, OpenAI)  
✅ Smart keyword routing (up to 70% cost savings)  
✅ Knowledge base with RAG  
✅ Forum monitoring  
✅ Docker deployment  
✅ Prometheus & Grafana monitoring  
✅ Production-ready configuration  

**Your bot is ready for production!** 🚀

**Estimated Monthly Costs:**
- Groq: $0 (free tier)
- OpenRouter: $0-$5 (minimal usage)
- OpenAI: $0-$50 (depending on traffic)
- Hosting: $10-$50 (VPS/cloud)

**Total: $10-$105/month** (vs $500+ without optimization)

**Time Saved:** 70%+ reduction in support tickets

---

*Last updated: 2026-02-09*  
*Version: 1.0.0*
