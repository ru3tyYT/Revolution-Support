# Environment Variables

> **Note:** See `.env.example` for a complete template with all available variables.

Complete reference for environment variables used by the Discord Support Bot.

## Table of Contents

- [Required Variables](#required-variables)
- [Discord Bot Settings](#discord-bot-settings)
- [Database & Cache](#database--cache)
- [AI Provider API Keys](#ai-provider-api-keys)
- [Clustering (Optional)](#clustering-optional)
- [Rate Limiting](#rate-limiting)
- [Monitoring & Logging](#monitoring--logging)
- [Web Server & Discord OAuth](#web-server--discord-oauth)

## Required Variables

These variables must be set for the bot to function:

```bash
# Discord Bot Token (Required)
# Get from: https://discord.com/developers/applications
DISCORD_TOKEN=your_bot_token_here

# Database URL (Required)
# Format: postgresql://user:password@host:port/database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/supportbot

# Redis URL (Required)
# Format: redis://host:port/database
REDIS_URL=redis://localhost:6379/0

# At least one AI Provider API Key (Required)
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...
# OR
GROQ_API_KEY=gsk_...
```

## Discord Bot Settings

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_TOKEN` | - | Bot authentication token |
| `COMMAND_PREFIX` | `!` | Prefix for text commands |

### Support System Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPPORT_GUILD_ID` | - | Discord Guild ID for support |
| `SUPPORT_CHANNEL_ID` | - | Channel ID for support |
| `TICKET_CATEGORY_ID` | - | Category ID for tickets |

### Example

```bash
DISCORD_TOKEN=MTA0NzI4Nzg5MDEyMzQ1Njc4OQ.G4bO1a.abcdefghijklmnopqrstuvwxyz
COMMAND_PREFIX=!
SUPPORT_GUILD_ID=123456789012345678
SUPPORT_CHANNEL_ID=123456789012345679
TICKET_CATEGORY_ID=123456789012345680
```

## Database & Cache

### Connection Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///supportbot.db` | Database connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |

### Message Cache Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_MESSAGES` | `10000` | Max messages to cache per channel |
| `MESSAGE_CACHE_TTL` | `300` | Cache TTL in seconds |

### Connection String Examples

```bash
# Local development
DATABASE_URL=postgresql://postgres:password@localhost:5432/supportbot

# With SSL
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Docker Compose
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/supportbot
```

## AI Provider API Keys

### OpenAI

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |

```bash
OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz1234567890
```

### Anthropic (Claude)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |

```bash
ANTHROPIC_API_KEY=sk-ant-abcdefghijklmnopqrstuvwxyz
```

### Groq

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key |

```bash
GROQ_API_KEY=gsk_abcdefghijklmnopqrstuvwxyz
```

### OpenRouter

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key |

```bash
OPENROUTER_API_KEY=sk-or-abcdefghijklmnopqrstuvwxyz
```

### Ollama

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama server URL |
| `OLLAMA_MODEL` | - | Default local model |
| `OLLAMA_CLOUD_KEY` | - | Ollama Cloud API key |
| `OLLAMA_CLOUD_BASE_URL` | - | Ollama Cloud base URL |
| `OLLAMA_CLOUD_MODEL` | - | Default cloud model |

```bash
# Local Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Ollama Cloud
OLLAMA_CLOUD_KEY=your_cloud_key
OLLAMA_CLOUD_BASE_URL=https://api.ollama.ai/v1
OLLAMA_CLOUD_MODEL=llama3.2
```

## Clustering (Optional)

Enable clustering for large bots (250k+ users recommended).

| Variable | Default | Description |
|----------|---------|-------------|
| `CLUSTER_ENABLED` | `true` | Enable clustering mode |
| `SHARDS_PER_CLUSTER` | `5` | Shards per cluster |
| `TOTAL_SHARDS` | - | Total shards (auto if not set) |
| `CLUSTER_ID` | - | Cluster ID for this instance |

```bash
CLUSTER_ENABLED=true
SHARDS_PER_CLUSTER=5
TOTAL_SHARDS=10
CLUSTER_ID=0
```

## Rate Limiting

Protect the bot from abuse.

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_COMMANDS` | `5` | Max commands per user per minute |

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_COMMANDS=5
```

## Monitoring & Logging

### Logging Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DEBUG` | `false` | Enable debug mode |

### Webhooks

| Variable | Description |
|----------|-------------|
| `STATUS_WEBHOOK` | Discord webhook for status updates |
| `ERROR_WEBHOOK` | Discord webhook for error alerts |

### Example

```bash
LOG_LEVEL=INFO
DEBUG=false

STATUS_WEBHOOK=https://discord.com/api/webhooks/...
ERROR_WEBHOOK=https://discord.com/api/webhooks/...
```

## Web Server & Discord OAuth

Used by the FastAPI app in `web/` for the dashboard and Discord OAuth2 login. Set these when you run `uvicorn web.main:app` (see [Getting Started](../getting-started.md#optional-web-api-fastapi)).

| Variable | Default | Description |
|----------|---------|-------------|
| `WEB_HOST` | `0.0.0.0` | Bind address for Uvicorn |
| `WEB_PORT` | `8000` | Port (pass to Uvicorn; not read automatically by FastAPI) |
| `FRONTEND_URL` | `http://localhost:5173` | Allowed CORS origin and OAuth redirect target for the SPA |
| `DISCORD_CLIENT_ID` | - | OAuth2 application Client ID from the [Discord Developer Portal](https://discord.com/developers/applications) |
| `DISCORD_CLIENT_SECRET` | - | OAuth2 Client Secret |
| `DISCORD_REDIRECT_URI` | `http://localhost:8000/api/auth/callback` | Must match **exactly** an entry under OAuth2 → Redirects in the Developer Portal |
| `SECRET_KEY` | - | JWT signing secret; use at least 32 characters (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ADMIN_GUILD_IDS` | - | Comma-separated guild IDs where admin checks apply (user must have Administrator in that guild) |

OAuth scopes requested by the backend include `identify`, `guilds`, and `guilds.members.read` (required for per-guild member permission checks).

```bash
WEB_HOST=0.0.0.0
WEB_PORT=8000
FRONTEND_URL=http://localhost:5173
DISCORD_CLIENT_ID=your_application_client_id
DISCORD_CLIENT_SECRET=your_client_secret
DISCORD_REDIRECT_URI=http://localhost:8000/api/auth/callback
SECRET_KEY=your_32_character_minimum_secret_key
ADMIN_GUILD_IDS=123456789012345678,987654321098765432
```

## Environment-Specific Examples

### Development

```bash
ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# Local services
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/supportbot
REDIS_URL=redis://localhost:6379/0

# Free AI provider
GROQ_API_KEY=gsk_your_key
```

### Production

```bash
ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Enable clustering
CLUSTER_ENABLED=true
SHARDS_PER_CLUSTER=5

# Multiple AI providers
OPENAI_API_KEY=sk_...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...

# Webhooks for monitoring
STATUS_WEBHOOK=https://discord.com/api/webhooks/...
ERROR_WEBHOOK=https://discord.com/api/webhooks/...
```
