# Single Server Deployment Guide

This guide covers deploying the Discord Support Bot on a **single server**, optimized for ease of setup and management. This is the recommended approach for most communities.

## When to Use Single Server Deployment

Use this deployment method if:
- Your Discord server has fewer than 50,000 members
- You want the simplest setup possible
- You're running on a single VPS or dedicated server
- You don't need horizontal scaling

## Quick Start (One Command)

```bash
# 1. Clone the repository
git clone https://github.com/yourorg/discord-support-bot.git
cd discord-support-bot

# 2. Run the setup script
./scripts/setup.sh
```

The setup script will:
- Check prerequisites (Docker, Python 3.11+)
- Create and configure `.env` file
- Start all services (PostgreSQL, Redis, Bot, Workers)
- Run database migrations
- Validate the installation

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 50 GB SSD
- **OS**: Ubuntu 20.04+, Debian 11+, or CentOS 8+

### Recommended
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 100 GB SSD
- **Network**: 100 Mbps

## Manual Setup

If you prefer manual setup or the automated script doesn't work for your environment:

### Step 1: Install Prerequisites

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git

# CentOS/RHEL
sudo yum install -y docker docker-compose-plugin git
sudo systemctl enable --now docker

# macOS
brew install docker docker-compose git
```

### Step 2: Clone Repository

```bash
git clone https://github.com/yourorg/discord-support-bot.git
cd discord-support-bot
```

### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

**Required settings:**
- `DISCORD_TOKEN` - Your Discord bot token
- `POSTGRES_PASSWORD` - Database password
- At least one AI provider API key (OpenAI, Anthropic, Groq, or OpenRouter)

### Step 4: Start Services

```bash
# Using the simplified single-server compose file
docker-compose -f docker-compose.single.yml up -d

# Or rename it for convenience
cp docker-compose.single.yml docker-compose.yml
docker-compose up -d
```

### Step 5: Run Migrations

```bash
docker-compose exec bot alembic upgrade head
```

### Step 6: Verify Installation

```bash
# Check all services are running
docker-compose ps

# View bot logs
docker-compose logs -f bot

# Test in Discord
# Use /ping command in your server
```

## Service Overview

The single-server deployment includes:

| Service | Description | Resource Usage |
|---------|-------------|----------------|
| **bot** | Main Discord bot | 512MB RAM, 1 CPU |
| **postgres** | PostgreSQL with pgvector | 1GB RAM, 0.5 CPU |
| **redis** | Cache and message broker | 256MB RAM, 0.25 CPU |
| **research-worker** | Background task workers (2 replicas) | 1GB RAM, 1 CPU |

**Total**: ~2.8GB RAM, 2.75 CPU cores

## Configuration

### Environment Variables

See `.env.example` for all available options. Key variables:

```bash
# Required
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://postgres:your_password@postgres:5432/supportbot
REDIS_URL=redis://redis:6379/0

# AI Providers (at least one)
OPENAI_API_KEY=sk-...          # OpenAI
ANTHROPIC_API_KEY=sk-ant-...   # Claude
GROQ_API_KEY=gsk-...            # Free tier available

# Optional
SERPAPI_KEY=...                 # For web search
SENTRY_DSN=...                  # Error tracking
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
```

### Cost Optimization

The single-server deployment is already optimized for cost:

1. **Use Groq** (free tier) for simple queries
2. **Enable keyword routing** (configured by default)
3. **Set daily budgets**:
   ```bash
   COST_BUDGET_DAILY=10.00
   ENABLE_COST_OPTIMIZATION=true
   ```

## Monitoring

### Basic Health Check

```bash
# Check all services
docker-compose ps

# View resource usage
docker stats
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f bot
docker-compose logs -f postgres
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d supportbot

# Common queries
\dt                    # List tables
SELECT COUNT(*) FROM guilds;  # Count servers
```

## Backup and Recovery

### Automated Backups

Create a backup script (`backup.sh`):

```bash
#!/bin/bash
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U postgres supportbot > $BACKUP_DIR/db_backup_$DATE.sql

# Backup Redis (optional)
docker-compose exec redis redis-cli BGSAVE
docker cp $(docker-compose ps -q redis):/data/dump.rdb $BACKUP_DIR/redis_backup_$DATE.rdb

echo "Backup completed: $BACKUP_DIR/db_backup_$DATE.sql"
```

Make it executable and add to cron:

```bash
chmod +x backup.sh
# Add to crontab for daily backups at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /path/to/backup.sh") | crontab -
```

### Restore from Backup

```bash
# Stop services
docker-compose down

# Restore database
docker-compose up -d postgres
docker-compose exec -T postgres psql -U postgres -d supportbot < backups/db_backup_YYYYMMDD_HHMMSS.sql

# Restart all services
docker-compose up -d
```

## Upgrading

```bash
# Pull latest changes
git pull

# Rebuild containers
docker-compose down
docker-compose pull
docker-compose up -d --build

# Run migrations
docker-compose exec bot alembic upgrade head
```

## Troubleshooting

### Bot won't start

```bash
# Check logs
docker-compose logs bot

# Verify environment variables
docker-compose exec bot env | grep DISCORD

# Test Discord connection
docker-compose exec bot python -c "import discord; print('Discord OK')"
```

### Database connection failed

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec bot python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('postgresql://postgres:password@postgres:5432/supportbot')
    print('Connected!')
    await conn.close()
asyncio.run(test())
"
```

### High memory usage

```bash
# View memory stats
docker stats --no-stream

# Restart services
docker-compose restart

# If persistent issue, increase server RAM or reduce worker count
# Edit docker-compose.single.yml and change research-worker replicas to 1
```

## Migrating to Multi-Server

If you outgrow single-server deployment:

1. **Export data**:
   ```bash
   docker-compose exec postgres pg_dump -U postgres supportbot > migration_backup.sql
   ```

2. **Follow Kubernetes deployment guide**: See `docs/deployment/kubernetes.md`

3. **Import data** to new cluster

## Next Steps

- [Configure AI Providers](docs/configuration/ai-models.md)
- [Set up Forum Monitoring](docs/features/forum-monitoring.md)
- [Add Knowledge Base](docs/features/knowledge-base.md)
- [Learn about Cost Optimization](docs/configuration/cost-optimization.md)

## Support

- 🎮 **Discord**: [Join our support server](https://discord.gg/yourserver)
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourorg/discord-support-bot/issues)
- 📧 **Email**: support@yourcompany.com
