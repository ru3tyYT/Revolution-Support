# Docker Deployment

Complete guide for deploying the Discord Support Bot using Docker and Docker Compose.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Docker Compose Configuration](#docker-compose-configuration)
- [Production Deployment](#production-deployment)
- [Development Environment](#development-environment)
- [Scaling](#scaling)
- [Monitoring Profile](#monitoring-profile)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Git | Latest | Clone repository |

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Disk | 20 GB | 50+ GB SSD |
| Network | 10 Mbps | 100+ Mbps |

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourorg/discord-support-bot.git
cd discord-support-bot
```

### 2. Create Environment File

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Required
DISCORD_TOKEN=your_bot_token
POSTGRES_PASSWORD=secure_password_here

# AI Providers (at least one)
OPENAI_API_KEY=sk-...
# Or
GROQ_API_KEY=gsk_...
```

### 3. Start Services

```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f bot

# Check status
docker-compose -f docker/docker-compose.yml ps
```

### 4. Run Database Migrations

```bash
docker-compose -f docker/docker-compose.yml exec bot alembic upgrade head
```

### 5. Verify Deployment

```bash
# Check bot is responding
# In Discord, send: /ping

# Check health endpoint
curl http://localhost:8080/health
```

## Docker Compose Configuration

### Services Overview

| Service | Purpose | Port |
|---------|---------|------|
| `bot` | Main Discord bot | - |
| `bot-cluster-1` | Additional bot instance | - |
| `postgres` | PostgreSQL + pgvector | 5432 |
| `redis` | Cache & message broker | 6379 |
| `research-worker` | Celery workers | - |
| `celery-beat` | Scheduled tasks | - |
| `flower` | Celery monitoring | 5555 |
| `prometheus` | Metrics collection | 9090 |
| `grafana` | Dashboards | 3000 |
| `postgres-exporter` | DB metrics | 9187 |
| `redis-exporter` | Redis metrics | 9121 |

### Basic Configuration

```yaml
version: "3.8"

services:
  bot:
    build:
      context: ..
      dockerfile: docker/Dockerfile
      target: production
    container_name: discord-bot
    restart: unless-stopped
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/supportbot
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: ankane/pgvector:latest
    container_name: discord-bot-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=supportbot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    container_name: discord-bot-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
```

### Environment Variables

Pass environment variables to containers:

```yaml
services:
  bot:
    environment:
      # Core
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/supportbot
      - REDIS_URL=redis://redis:6379/0
      
      # AI Providers
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - GROQ_API_KEY=${GROQ_API_KEY:-}
      
      # Configuration
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - ENVIRONMENT=${ENVIRONMENT:-production}
```

### Volume Persistence

Data persists across container restarts:

```yaml
volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
```

View volume usage:

```bash
docker volume ls
docker volume inspect discord-support-bot_postgres_data
```

## Production Deployment

### Security Checklist

- [ ] Use strong passwords
- [ ] Enable SSL/TLS for database connections
- [ ] Use secrets management (not .env files)
- [ ] Run containers as non-root user
- [ ] Enable firewall rules
- [ ] Regular security updates

### Production Compose File

Create `docker-compose.prod.yml`:

```yaml
version: "3.8"

services:
  bot:
    build:
      context: ..
      dockerfile: docker/Dockerfile
      target: production
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    environment:
      - ENV=production
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
    healthcheck:
      test: ["CMD", "python", "-c", "import discord"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
    command: >
      postgres
      -c ssl=on
      -c ssl_cert_file=/etc/ssl/certs/server.crt
      -c ssl_key_file=/etc/ssl/private/server.key
```

### SSL/TLS Configuration

```yaml
services:
  postgres:
    volumes:
      - ./ssl/server.crt:/etc/ssl/certs/server.crt:ro
      - ./ssl/server.key:/etc/ssl/private/server.key:ro
    environment:
      - POSTGRES_SSL_MODE=require
```

### Secrets Management

Use Docker secrets for sensitive data:

```yaml
services:
  bot:
    secrets:
      - discord_token
      - openai_key

secrets:
  discord_token:
    file: ./secrets/discord_token.txt
  openai_key:
    file: ./secrets/openai_key.txt
```

Access in container:

```python
# Read secret
with open('/run/secrets/discord_token', 'r') as f:
    token = f.read().strip()
```

### Backup Strategy

Automated database backups:

```yaml
services:
  backup:
    image: postgres:15-alpine
    volumes:
      - ./backups:/backups
    command: >
      sh -c 'while true; do
        pg_dump -h postgres -U postgres supportbot > /backups/backup_$$(date +%Y%m%d_%H%M%S).sql;
        sleep 86400;
      done'
    environment:
      - PGPASSWORD=${POSTGRES_PASSWORD}
```

## Development Environment

### Development Compose

```yaml
version: "3.8"

services:
  bot:
    build:
      context: ..
      dockerfile: docker/Dockerfile
      target: development
    volumes:
      - ../bot:/app/bot:ro
      - ../config:/app/config:ro
    environment:
      - ENV=development
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    command: python -m bot --dev --reload
```

### Hot Reload

```bash
# Start with hot reload
docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up

# Changes to Python files are automatically reloaded
```

### Local Testing

```bash
# Run tests in container
docker-compose exec bot pytest

# Run with coverage
docker-compose exec bot pytest --cov=bot --cov-report=html

# Run specific test
docker-compose exec bot pytest tests/test_ai_router.py -v
```

## Scaling

### Horizontal Scaling

Scale bot instances:

```bash
# Scale to 3 instances
docker-compose up -d --scale bot=3

# With clustering enabled
CLUSTER_MODE=true
CLUSTER_SHARD_COUNT=3
```

### Resource Limits

```yaml
services:
  bot:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### Load Balancing

For multiple bot instances:

```yaml
services:
  bot-1:
    environment:
      - CLUSTER_ID=0
      - SHARD_COUNT=3
  
  bot-2:
    environment:
      - CLUSTER_ID=1
      - SHARD_COUNT=3
  
  bot-3:
    environment:
      - CLUSTER_ID=2
      - SHARD_COUNT=3
```

## Monitoring Profile

### Enable Monitoring

```bash
# Start with monitoring stack
docker-compose -f docker/docker-compose.yml --profile monitoring up -d
```

### Access Services

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| Flower | http://localhost:5555 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin |

### Flower Configuration

```yaml
flower:
  image: mher/flower:latest
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/1
    - FLOWER_BASIC_AUTH=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin}
  ports:
    - "5555:5555"
```

### Prometheus Configuration

```yaml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - prometheus_data:/prometheus
  ports:
    - "9090:9090"
```

### Grafana Dashboards

```yaml
grafana:
  image: grafana/grafana:latest
  environment:
    - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
  volumes:
    - grafana_data:/var/lib/grafana
    - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
  ports:
    - "3000:3000"
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs bot

# Check for errors
docker-compose logs bot | grep ERROR

# Verify environment variables
docker-compose exec bot env | grep DISCORD
```

### Database Connection Issues

```bash
# Test database connectivity
docker-compose exec bot python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('$DATABASE_URL')
    print(await conn.fetchval('SELECT 1'))
asyncio.run(test())
"

# Check PostgreSQL logs
docker-compose logs postgres
```

### Redis Connection Issues

```bash
# Test Redis
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis
```

### High Memory Usage

```bash
# Check container stats
docker stats

# View memory usage
docker-compose exec bot python -c "
import psutil
print(f'Memory: {psutil.virtual_memory().percent}%')
"

# Restart service
docker-compose restart bot
```

### Update Containers

```bash
# Pull latest images
docker-compose pull

# Rebuild with changes
docker-compose up -d --build

# Clean up old images
docker image prune -f
```

### Reset Environment

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: Data loss!)
docker-compose down -v

# Start fresh
docker-compose up -d
```

## Docker Commands Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service]

# Execute command in container
docker-compose exec [service] [command]

# Scale service
docker-compose up -d --scale [service]=[count]

# Build images
docker-compose build

# Pull latest images
docker-compose pull

# View status
docker-compose ps

# Clean up
docker system prune
```
