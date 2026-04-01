# Getting Started

This guide will walk you through setting up the Discord Support Bot from scratch.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Local Installation](#local-installation)
  - [Docker Installation](#docker-installation)
- [First-Time Configuration](#first-time-configuration)
- [Initial Setup Wizard](#initial-setup-wizard)
- [Next Steps](#next-steps)

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Bot runtime |
| PostgreSQL | 15+ | Primary database |
| Redis | 7+ | Caching and message broker |
| Git | Latest | Version control |

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Navigate to the "Bot" section
4. Click "Add Bot"
5. Enable required intents:
   - **MESSAGE CONTENT INTENT** (required for message reading)
   - **SERVER MEMBERS INTENT** (for user management)
   - **PRESENCE INTENT** (optional, for presence tracking)
6. Copy the bot token (you'll need this for configuration)
7. Under OAuth2 > URL Generator, select:
   - **Scopes**: `bot`, `applications.commands`
   - **Bot Permissions**: Administrator (or granular permissions as needed)

### AI Provider Setup

You'll need at least one AI provider API key:

#### OpenAI
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an account and generate an API key
3. Set up billing (optional but recommended for production)

#### Anthropic (Claude)
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create an account and get API access
3. Generate an API key

#### Groq (Free Tier)
1. Go to [Groq Console](https://console.groq.com/)
2. Create a free account
3. Generate an API key

#### OpenRouter
1. Go to [OpenRouter](https://openrouter.ai/)
2. Create an account and add credits
3. Generate an API key

## Installation

### Local Installation

#### Step 1: Clone the Repository

```bash
git clone https://github.com/yourorg/discord-support-bot.git
cd discord-support-bot
```

#### Step 2: Create Virtual Environment

```bash
# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

#### Step 3: Install Dependencies

```bash
# Standard installation
pip install -e ".[dev]"

# With all providers
pip install -e ".[all]"

# With specific providers
pip install -e ".[all-providers]"
```

#### Step 4: Set Up Database

```bash
# Create database
createdb supportbot

# Or using psql
psql -c "CREATE DATABASE supportbot;"
```

#### Step 5: Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your configuration (see [Environment Variables](configuration/environment-variables.md) for details):

```bash
# Required
discord_bot__token=your_bot_token_here
database__url=postgresql://postgres:postgres@localhost:5432/supportbot
redis__url=redis://localhost:6379/0

# AI Providers (at least one)
openai__api_key=sk-...
anthropic__api_key=sk-ant-...
groq__api_key=gsk_...
```

#### Step 6: Run Database Migrations

```bash
alembic upgrade head
```

#### Step 7: Start the Bot

```bash
# Development mode with hot reload
python -m bot --dev

# Production mode
python -m bot
```

### Optional: Web API (FastAPI)

The project includes a FastAPI layer under `web/` for dashboard APIs and Discord OAuth. It is separate from the Discord bot process.

1. Install Python dependencies (includes FastAPI, Uvicorn, `python-jose`, `httpx`; see `requirements.txt`).
2. In `.env`, set `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI` (must match the Developer Portal), `SECRET_KEY` (32+ characters), and optionally `FRONTEND_URL`, `ADMIN_GUILD_IDS`. See [Web Server & Discord OAuth](configuration/environment-variables.md#web-server--discord-oauth).
3. In the [Discord Developer Portal](https://discord.com/developers/applications) → OAuth2 → Redirects, add `http://localhost:8000/api/auth/callback` (or your deployed callback URL).
4. From the **repository root**:

```bash
uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
```

5. Open [http://localhost:8000/docs](http://localhost:8000/docs) for OpenAPI. Visit [http://localhost:8000/api/auth/login](http://localhost:8000/api/auth/login) to start the OAuth flow; after authorization, the browser is redirected to `{FRONTEND_URL}/auth/callback` with a `token` query parameter. Call protected routes with `Authorization: Bearer <token>`.

### Docker Installation

Docker provides an easier way to get started with all dependencies included.

#### Step 1: Clone the Repository

```bash
git clone https://github.com/yourorg/discord-support-bot.git
cd discord-support-bot
```

#### Step 2: Create Environment File

```bash
cp .env.example .env
```

Edit `.env` with your API keys and configuration.

#### Step 3: Start with Docker Compose

```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f bot

# Scale bot instances (for clustering)
docker-compose -f docker/docker-compose.yml up -d --scale bot=3
```

#### Available Docker Profiles

```bash
# Basic setup (bot, postgres, redis)
docker-compose -f docker/docker-compose.yml up -d

# With monitoring (Prometheus, Grafana, Flower)
docker-compose -f docker/docker-compose.yml --profile monitoring up -d

# With clustering
docker-compose -f docker/docker-compose.yml --profile cluster up -d
```

#### Step 4: Run Database Migrations

```bash
docker-compose -f docker/docker-compose.yml exec bot alembic upgrade head
```

## First-Time Configuration

After installation, you'll need to configure the bot for your server.

### 1. Invite the Bot to Your Server

Use the OAuth2 URL generated in the Discord Developer Portal to invite the bot to your Discord server.

### 2. Verify Bot Permissions

Ensure the bot has the following permissions:

- View Channels
- Send Messages
- Embed Links
- Attach Files
- Read Message History
- Use External Emojis
- Add Reactions
- Create Public Threads
- Send Messages in Threads
- Manage Threads (optional, for cleanup)

### 3. Set Up Command Permissions

By default, slash commands are available to everyone. You can restrict admin commands:

1. Go to Server Settings > Integrations
2. Find your bot
3. Configure command permissions for admin-only commands

### 4. Configure AI Providers

Test your AI providers:

```bash
# Via command (admin only)
/settings provider openai
/settings model gpt-4

# Or test via chat
!ask Test message
```

### 5. Set Up Forum Monitoring (Optional)

If you want the bot to monitor forum channels:

```bash
# Configure forum monitoring
/forum setup #support-forum auto_respond:true
```

### 6. Add Knowledge Base Documents (Optional)

Upload your documentation:

```bash
/knowledge_upload file:documentation.md title:"Product Docs"
```

## Initial Setup Wizard

The bot includes an interactive setup wizard that guides you through configuration:

### Starting the Wizard

```bash
# Run the setup wizard
python -m bot setup

# Or via Docker
docker-compose -f docker/docker-compose.yml exec bot python -m bot setup
```

### Wizard Steps

1. **Discord Configuration**
   - Validate bot token
   - Test Discord connection
   - Configure intents

2. **Database Setup**
   - Test database connection
   - Run migrations
   - Verify tables

3. **Cache Configuration**
   - Test Redis connection
   - Configure cache settings

4. **AI Provider Setup**
   - Test each configured provider
   - Set default provider
   - Configure fallback providers

5. **Guild Configuration**
   - Select guild to configure
   - Set prefix and status
   - Configure permissions

6. **Forum Setup** (Optional)
   - Select forums to monitor
   - Configure auto-responses
   - Set up welcome messages

7. **Knowledge Base** (Optional)
   - Upload initial documents
   - Configure search settings

8. **Review & Confirm**
   - Summary of all settings
   - Test bot functionality
   - Enable bot

### Example Wizard Output

```
Discord Support Bot - Setup Wizard
===================================

Step 1/8: Discord Configuration
-------------------------------
✓ Bot token validated
✓ Discord connection successful
✓ Intents configured

Step 2/8: Database Setup
------------------------
✓ Database connection successful
✓ Migrations completed
✓ Tables verified

Step 3/8: Cache Configuration
-----------------------------
✓ Redis connection successful
✓ Cache configured

Step 4/8: AI Provider Setup
---------------------------
✓ OpenAI: Connected (GPT-4, GPT-3.5)
✓ Anthropic: Connected (Claude 3)
✓ Groq: Connected (Free tier)
→ Default provider set to: OpenAI

Setup complete! The bot is ready to use.
Run 'python -m bot' to start the bot.
```

## Next Steps

Now that your bot is set up:

1. **Explore Commands**: See the [Commands](commands.md) reference
2. **Configure Features**: Set up [Forum Monitoring](features/forum-monitoring.md) or [Knowledge Base](features/knowledge-base.md)
3. **Optimize Costs**: Learn about [Cost Optimization](configuration/cost-optimization.md)
4. **Monitor Usage**: Set up [Monitoring & Alerting](deployment/monitoring.md)
5. **Scale Up**: Learn about [Horizontal Scaling](deployment/kubernetes.md)

## Troubleshooting

### Common Issues

#### Bot Won't Start

```bash
# Check logs
python -m bot 2>&1 | tee bot.log

# Verify environment variables
python -c "from bot.config import settings; print(settings.discord_bot__token)"
```

#### Database Connection Failed

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check if database exists
psql -l | grep supportbot
```

#### AI Provider Errors

```bash
# Test provider connectivity
python -c "from ai.providers.openai_provider import OpenAIProvider; p = OpenAIProvider(); print(p.is_healthy())"
```

### Getting Help

- Check the [FAQ](faq.md)
- Join our [Discord Support Server](https://discord.gg/yourserver)
- Open an issue on [GitHub](https://github.com/yourorg/discord-support-bot/issues)
