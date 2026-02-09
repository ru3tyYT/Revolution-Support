# Environment Variables

Complete reference for all environment variables used by the Discord Support Bot.

## Table of Contents

- [Required Variables](#required-variables)
- [Discord Configuration](#discord-configuration)
- [Database Configuration](#database-configuration)
- [AI Provider Configuration](#ai-provider-configuration)
- [Cost Optimization](#cost-optimization)
- [Rate Limiting](#rate-limiting)
- [Conversation Memory](#conversation-memory)
- [Knowledge Base](#knowledge-base)
- [Sharding & Clustering](#sharding--clustering)
- [Monitoring & Analytics](#monitoring--analytics)
- [Ticket System](#ticket-system)
- [Integrations](#integrations)
- [Feature Flags](#feature-flags)
- [Deployment](#deployment)

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

## Discord Configuration

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_TOKEN` | - | Bot authentication token |
| `DISCORD_APPLICATION_ID` | - | Application ID for slash commands |
| `DISCORD_PUBLIC_KEY` | - | Public key for interactions |
| `BOT_PREFIX` | `!` | Prefix for legacy commands |
| `BOT_STATUS_MESSAGE` | `Support Bot \| !help` | Bot activity status |
| `BOT_OWNERS` | - | Comma-separated list of owner Discord IDs |

### Example

```bash
DISCORD_TOKEN=MTA0NzI4Nzg5MDEyMzQ1Njc4OQ.G4bO1a.abcdefghijklmnopqrstuvwxyz
DISCORD_APPLICATION_ID=1047287890123456789
DISCORD_PUBLIC_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
BOT_PREFIX=!
BOT_STATUS_MESSAGE=Support Bot | /help
BOT_OWNERS=123456789012345678,987654321098765432
```

## Database Configuration

### Connection Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | Full PostgreSQL connection string |
| `DATABASE_POOL_SIZE` | `20` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Extra connections beyond pool size |
| `DATABASE_POOL_TIMEOUT` | `30` | Seconds to wait for connection |

### Connection String Examples

```bash
# Local development
DATABASE_URL=postgresql://postgres:password@localhost:5432/supportbot

# With SSL
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Docker Compose
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/supportbot
```

### Pool Configuration

```bash
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
```

## AI Provider Configuration

### OpenAI

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | API key |
| `OPENAI_ORG_ID` | - | Organization ID (optional) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API base URL |

```bash
OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz1234567890
OPENAI_ORG_ID=org-yourorgid
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Anthropic (Claude)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | - | API key |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | API base URL |

```bash
ANTHROPIC_API_KEY=sk-ant-abcdefghijklmnopqrstuvwxyz
ANTHROPIC_BASE_URL=https://api.anthropic.com
```

### OpenRouter

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | API key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | API base URL |
| `OPENROUTER_REFERER` | - | Your site URL |
| `OPENROUTER_TITLE` | - | App name |

```bash
OPENROUTER_API_KEY=sk-or-abcdefghijklmnopqrstuvwxyz
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_REFERER=https://yourdomain.com
OPENROUTER_TITLE=Discord Support Bot
```

### Groq

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | - | API key |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | API base URL |

```bash
GROQ_API_KEY=gsk_abcdefghijklmnopqrstuvwxyz
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

### Ollama

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_CLOUD_KEY` | - | Cloud API key (optional) |
| `OLLAMA_CLOUD_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_CLOUD_MODEL` | `llama3.2` | Default model |

```bash
# Local Ollama
OLLAMA_CLOUD_KEY=
OLLAMA_CLOUD_BASE_URL=http://localhost:11434
OLLAMA_CLOUD_MODEL=llama3.2

# Ollama Cloud
OLLAMA_CLOUD_KEY=your_cloud_key
OLLAMA_CLOUD_BASE_URL=https://api.ollama.com/v1
OLLAMA_CLOUD_MODEL=llama3.2
```

## Cost Optimization

### Budget Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_COST_OPTIMIZATION` | `true` | Enable smart routing |
| `COST_BUDGET_DAILY` | `50.00` | Daily spending limit (USD) |
| `COST_BUDGET_MONTHLY` | `1000.00` | Monthly spending limit (USD) |
| `COST_ALERT_THRESHOLD` | `0.8` | Alert at % of budget |

```bash
ENABLE_COST_OPTIMIZATION=true
COST_BUDGET_DAILY=50.00
COST_BUDGET_MONTHLY=1000.00
COST_ALERT_THRESHOLD=0.8
```

### Routing Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_MODEL` | `gpt-4o-mini` | Default AI model |
| `ENABLE_SMART_ROUTING` | `true` | Enable intelligent routing |
| `FREE_TIER_MODE` | `false` | Prefer free providers |

```bash
DEFAULT_MODEL=gpt-4o-mini
ENABLE_SMART_ROUTING=true
FREE_TIER_MODE=false
```

### Caching

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_RESPONSE_CACHE` | `true` | Cache AI responses |
| `CACHE_TTL_SHORT` | `300` | Short cache (seconds) |
| `CACHE_TTL_MEDIUM` | `3600` | Medium cache (seconds) |
| `CACHE_TTL_LONG` | `86400` | Long cache (seconds) |

```bash
ENABLE_RESPONSE_CACHE=true
CACHE_TTL_SHORT=300      # 5 minutes
CACHE_TTL_MEDIUM=3600    # 1 hour
CACHE_TTL_LONG=86400     # 24 hours
```

## Rate Limiting

### Global Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `GLOBAL_RATE_LIMIT_ENABLED` | `true` | Enable global limits |
| `GLOBAL_RATE_LIMIT_REQUESTS` | `100` | Requests per window |
| `GLOBAL_RATE_LIMIT_WINDOW` | `60` | Window size (seconds) |

```bash
GLOBAL_RATE_LIMIT_ENABLED=true
GLOBAL_RATE_LIMIT_REQUESTS=100
GLOBAL_RATE_LIMIT_WINDOW=60
```

### User Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `USER_RATE_LIMIT_ENABLED` | `true` | Enable per-user limits |
| `USER_RATE_LIMIT_REQUESTS` | `10` | Requests per window |
| `USER_RATE_LIMIT_WINDOW` | `60` | Window size (seconds) |
| `ADMIN_RATE_LIMIT_BYPASS` | `true` | Admins bypass limits |

```bash
USER_RATE_LIMIT_ENABLED=true
USER_RATE_LIMIT_REQUESTS=10
USER_RATE_LIMIT_WINDOW=60
ADMIN_RATE_LIMIT_BYPASS=true
```

### Premium User Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `PREMIUM_USER_RATE_LIMIT_REQUESTS` | `50` | Premium user requests |
| `PREMIUM_USER_RATE_LIMIT_WINDOW` | `60` | Premium user window |

```bash
PREMIUM_USER_RATE_LIMIT_REQUESTS=50
PREMIUM_USER_RATE_LIMIT_WINDOW=60
```

## Conversation Memory

### Memory Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_MEMORY` | `true` | Enable conversation memory |
| `MEMORY_MAX_MESSAGES` | `50` | Max messages per conversation |
| `MEMORY_TTL_DAYS` | `7` | Days to retain memory |
| `MEMORY_SUMMARY_THRESHOLD` | `20` | Summarize after N messages |

```bash
ENABLE_MEMORY=true
MEMORY_MAX_MESSAGES=50
MEMORY_TTL_DAYS=7
MEMORY_SUMMARY_THRESHOLD=20
```

### Context Management

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONTEXT_TOKENS` | `8000` | Maximum context window |
| `CONTEXT_TRIM_STRATEGY` | `oldest` | How to trim context |

```bash
MAX_CONTEXT_TOKENS=8000
CONTEXT_TRIM_STRATEGY=oldest
```

## Knowledge Base

### Vector Database

| Variable | Default | Description |
|----------|---------|-------------|
| `VECTOR_DB_TYPE` | `pgvector` | Vector DB type |
| `VECTOR_DB_URL` | - | Connection string |
| `VECTOR_DIMENSION` | `1536` | Embedding dimensions |

```bash
VECTOR_DB_TYPE=pgvector
VECTOR_DB_URL=postgresql://postgres:pass@localhost:5432/supportbot
VECTOR_DIMENSION=1536
```

### Embeddings

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_PROVIDER` | `openai` | Embedding provider |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Model to use |
| `EMBEDDING_DIMENSION` | `1536` | Output dimensions |

```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

### RAG Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_TOP_K` | `5` | Chunks to retrieve |
| `RAG_SIMILARITY_THRESHOLD` | `0.7` | Minimum similarity |
| `RAG_MAX_TOKENS` | `2000` | Max context tokens |
| `ENABLE_RAG_CACHE` | `true` | Cache RAG results |
| `RAG_CACHE_TTL` | `3600` | Cache TTL (seconds) |

```bash
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_MAX_TOKENS=2000
ENABLE_RAG_CACHE=true
RAG_CACHE_TTL=3600
```

### Document Processing

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_DOCUMENT_SIZE_MB` | `10` | Max upload size (MB) |
| `SUPPORTED_DOCUMENT_TYPES` | `pdf,txt,md,docx` | Allowed file types |
| `DOCUMENT_CHUNK_SIZE` | `1000` | Chunk size (characters) |
| `DOCUMENT_CHUNK_OVERLAP` | `200` | Chunk overlap |

```bash
MAX_DOCUMENT_SIZE_MB=10
SUPPORTED_DOCUMENT_TYPES=pdf,txt,md,docx
DOCUMENT_CHUNK_SIZE=1000
DOCUMENT_CHUNK_OVERLAP=200
```

## Sharding & Clustering

### Sharding

| Variable | Default | Description |
|----------|---------|-------------|
| `SHARD_COUNT` | `auto` | Number of shards |
| `SHARD_CLUSTER_ID` | `0` | Cluster ID |
| `SHARD_CLUSTER_COUNT` | `1` | Total clusters |

```bash
SHARD_COUNT=auto
SHARD_CLUSTER_ID=0
SHARD_CLUSTER_COUNT=1
```

### Gateway Intents

| Variable | Default | Description |
|----------|---------|-------------|
| `INTENT_GUILD_MESSAGES` | `true` | Guild messages |
| `INTENT_DIRECT_MESSAGES` | `true` | DM messages |
| `INTENT_GUILD_MEMBERS` | `true` | Member updates |
| `INTENT_GUILD_PRESENCES` | `false` | Presence updates |
| `INTENT_MESSAGE_CONTENT` | `true` | Message content |
| `INTENT_GUILD_REACTIONS` | `true` | Reactions |

```bash
INTENT_GUILD_MESSAGES=true
INTENT_DIRECT_MESSAGES=true
INTENT_GUILD_MEMBERS=true
INTENT_GUILD_PRESENCES=false
INTENT_MESSAGE_CONTENT=true
INTENT_GUILD_REACTIONS=true
```

## Monitoring & Analytics

### Sentry

| Variable | Default | Description |
|----------|---------|-------------|
| `SENTRY_DSN` | - | Sentry DSN |
| `SENTRY_ENVIRONMENT` | `production` | Environment name |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` | Performance tracing rate |

```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### DataDog

| Variable | Default | Description |
|----------|---------|-------------|
| `DATADOG_API_KEY` | - | API key |
| `DATADOG_APP_KEY` | - | App key |
| `ENABLE_DATADOG` | `false` | Enable integration |

```bash
DATADOG_API_KEY=your_api_key
DATADOG_APP_KEY=your_app_key
ENABLE_DATADOG=false
```

### Prometheus

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_PROMETHEUS` | `true` | Enable metrics endpoint |
| `PROMETHEUS_PORT` | `8000` | Metrics port |

```bash
ENABLE_PROMETHEUS=true
PROMETHEUS_PORT=8000
```

### Analytics

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_ANALYTICS` | `true` | Track usage |
| `ANALYTICS_RETENTION_DAYS` | `90` | Data retention |

```bash
ENABLE_ANALYTICS=true
ANALYTICS_RETENTION_DAYS=90
```

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | Log format |
| `LOG_FILE` | `logs/bot.log` | Log file path |
| `LOG_ROTATION` | `midnight` | Rotation schedule |
| `LOG_RETENTION_DAYS` | `30` | Log retention |

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/bot.log
LOG_ROTATION=midnight
LOG_RETENTION_DAYS=30
```

## Ticket System

### Categories

| Variable | Default | Description |
|----------|---------|-------------|
| `TICKET_CATEGORY_SUPPORT` | `Support Tickets` | Support category name |
| `TICKET_CATEGORY_BUGS` | `Bug Reports` | Bugs category name |
| `TICKET_CATEGORY_FEATURE` | `Feature Requests` | Feature category name |

```bash
TICKET_CATEGORY_SUPPORT=Support Tickets
TICKET_CATEGORY_BUGS=Bug Reports
TICKET_CATEGORY_FEATURE=Feature Requests
```

### Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `TICKET_TRANSCRIPT_ENABLED` | `true` | Save transcripts |
| `TICKET_AUTO_CLOSE_HOURS` | `48` | Auto-close after (hours) |
| `TICKET_AUTO_CLOSE_WARNING_HOURS` | `24` | Warning before close |
| `TICKET_MAX_PER_USER` | `3` | Max open tickets per user |

```bash
TICKET_TRANSCRIPT_ENABLED=true
TICKET_AUTO_CLOSE_HOURS=48
TICKET_AUTO_CLOSE_WARNING_HOURS=24
TICKET_MAX_PER_USER=3
```

### Escalation

| Variable | Default | Description |
|----------|---------|-------------|
| `ESCALATION_ROLE_ID` | - | Role to mention |
| `ESCALATION_WEBHOOK_URL` | - | Webhook for notifications |

```bash
ESCALATION_ROLE_ID=1234567890123456789
ESCALATION_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## Integrations

### Slack

| Variable | Default | Description |
|----------|---------|-------------|
| `SLACK_ENABLED` | `false` | Enable Slack |
| `SLACK_BOT_TOKEN` | - | Bot token (xoxb-) |
| `SLACK_SIGNING_SECRET` | - | Signing secret |
| `SLACK_WEBHOOK_URL` | - | Webhook URL |

```bash
SLACK_ENABLED=false
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### Webhooks

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHOOK_SECRET` | - | Secret for validation |
| `WEBHOOK_ALLOWED_IPS` | - | Allowed IP addresses |

```bash
WEBHOOK_SECRET=your_webhook_secret
WEBHOOK_ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8
```

## Feature Flags

### Core Features

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_TICKETS` | `true` | Ticket system |
| `ENABLE_KNOWLEDGE_BASE` | `true` | Knowledge base |
| `ENABLE_ANALYTICS_DASHBOARD` | `true` | Analytics |
| `ENABLE_COST_TRACKING` | `true` | Cost tracking |
| `ENABLE_MODERATION` | `true` | Auto-moderation |
| `ENABLE_AUTOMATED_RESPONSES` | `true` | AI responses |
| `ENABLE_USER_FEEDBACK` | `true` | Feedback collection |

```bash
ENABLE_TICKETS=true
ENABLE_KNOWLEDGE_BASE=true
ENABLE_ANALYTICS_DASHBOARD=true
ENABLE_COST_TRACKING=true
ENABLE_MODERATION=true
ENABLE_AUTOMATED_RESPONSES=true
ENABLE_USER_FEEDBACK=true
```

### Experimental Features

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_VOICE_SUPPORT` | `false` | Voice channel support |
| `ENABLE_IMAGE_GENERATION` | `false` | AI image generation |
| `ENABLE_CODE_EXECUTION` | `false` | Code execution |

```bash
ENABLE_VOICE_SUPPORT=false
ENABLE_IMAGE_GENERATION=false
ENABLE_CODE_EXECUTION=false
```

## Deployment

### Kubernetes

| Variable | Default | Description |
|----------|---------|-------------|
| `KUBERNETES_NAMESPACE` | `discord-bot` | K8s namespace |
| `KUBERNETES_SERVICE_NAME` | `bot-service` | Service name |
| `KUBERNETES_POD_NAME` | - | Pod name (auto) |

```bash
KUBERNETES_NAMESPACE=discord-bot
KUBERNETES_SERVICE_NAME=bot-service
```

### Health Checks

| Variable | Default | Description |
|----------|---------|-------------|
| `HEALTH_CHECK_ENABLED` | `true` | Enable health endpoint |
| `HEALTH_CHECK_PORT` | `8080` | Health check port |
| `HEALTH_CHECK_PATH` | `/health` | Health endpoint path |

```bash
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PORT=8080
HEALTH_CHECK_PATH=/health
```

### Graceful Shutdown

| Variable | Default | Description |
|----------|---------|-------------|
| `SHUTDOWN_TIMEOUT_SECONDS` | `30` | Graceful shutdown timeout |

```bash
SHUTDOWN_TIMEOUT_SECONDS=30
```

## Environment-Specific Examples

### Development

```bash
ENV=development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Disable costly features
ENABLE_COST_OPTIMIZATION=false
ENABLE_ANALYTICS=false
ENABLE_PROMETHEUS=false

# Use local services
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/supportbot
REDIS_URL=redis://localhost:6379/0

# Free AI provider
GROQ_API_KEY=gsk_your_key
DEFAULT_MODEL=llama-3.1-8b-instant
```

### Production

```bash
ENV=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Enable all optimizations
ENABLE_COST_OPTIMIZATION=true
ENABLE_SMART_ROUTING=true

# Monitoring
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
ENABLE_PROMETHEUS=true
ENABLE_DATADOG=true

# Multiple AI providers
OPENAI_API_KEY=sk_...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...

# Security
ADMIN_RATE_LIMIT_BYPASS=false
```

### Staging

```bash
ENV=staging
DEBUG=false
LOG_LEVEL=INFO

# Test with limited resources
SHARD_COUNT=1
SHARD_CLUSTER_COUNT=1

# Lower limits for testing
COST_BUDGET_DAILY=10.00
USER_RATE_LIMIT_REQUESTS=5
```
