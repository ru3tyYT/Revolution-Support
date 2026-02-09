# Discord Support Bot - Docker & Kubernetes Deployment

## Quick Start

### Docker Compose

1. Copy environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

2. Start services:
   ```bash
   cd docker
   docker-compose up -d
   ```

3. With monitoring:
   ```bash
   docker-compose --profile monitoring up -d
   ```

4. With clustering:
   ```bash
   docker-compose --profile cluster up -d
   ```

### Kubernetes

1. Create namespace and secrets:
   ```bash
   kubectl apply -f docker/k8s/namespace.yaml
   kubectl create secret generic discord-bot-secrets \
     --from-literal=discord-token='YOUR_TOKEN' \
     --from-literal=postgres-password='YOUR_PASSWORD' \
     --from-literal=database-url='YOUR_DB_URL' \
     --from-literal=openai-api-key='YOUR_OPENAI_KEY' \
     --from-literal=serpapi-key='YOUR_SERPAPI_KEY' \
     --namespace=supportbot
   ```

2. Deploy with script:
   ```bash
   ./scripts/deploy.sh production deploy
   ```

3. Or deploy manually:
   ```bash
   kubectl apply -f docker/k8s/
   ```

## Scripts

### Deployment Script
```bash
./scripts/deploy.sh [environment] [action]

# Examples
./scripts/deploy.sh staging deploy      # Full deployment
./scripts/deploy.sh production scale 5  # Scale to 5 replicas
./scripts/deploy.sh staging rollback    # Rollback deployment
./scripts/deploy.sh production migrate  # Run migrations only
```

### Backup Script
```bash
./scripts/backup.sh [action] [options]

# Examples
./scripts/backup.sh backup              # Create backup
./scripts/backup.sh list                # List backups
./scripts/backup.sh restore <file>      # Restore from backup
./scripts/backup.sh snapshot            # Create volume snapshots
```

## Architecture

```
┌─────────────────────────────────────────────┐
│           Discord Support Bot               │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │   Bot    │  │  Worker  │  │  Worker  │  │
│  │  Node 1  │  │    1     │  │    2     │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │             │        │
│  ┌────┴─────────────┴─────────────┴─────┐  │
│  │              Redis                   │  │
│  │         (Cache + Queue)              │  │
│  └─────────────────┬───────────────────┘  │
│                    │                       │
│  ┌─────────────────┴───────────────────┐  │
│  │           PostgreSQL + pgvector      │  │
│  │      (Data + Vector Storage)         │  │
│  └─────────────────────────────────────┘  │
│                                           │
│  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Prometheus │  │      Grafana        │ │
│  │  (Metrics)  │  │   (Dashboards)      │ │
│  └─────────────┘  └─────────────────────┘ │
│                                           │
└───────────────────────────────────────────┘
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | Required |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `CLUSTER_MODE` | Enable clustering | false |
| `CLUSTER_SHARD_COUNT` | Number of shards | 1 |

### Resource Limits

**Bot Service:**
- CPU: 250m - 1000m
- Memory: 256Mi - 512Mi

**Research Workers:**
- CPU: 250m - 1000m
- Memory: 512Mi - 1Gi

**PostgreSQL:**
- CPU: 250m - 2000m
- Memory: 512Mi - 2Gi

**Redis:**
- CPU: 100m - 500m
- Memory: 128Mi - 256Mi

## Monitoring

### Access Points

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Flower (Celery)**: http://localhost:5555

### Health Checks

- Bot: Built-in Discord connection check
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`

## Security

- All containers run as non-root user
- Network policies restrict traffic
- Secrets stored in Kubernetes Secrets
- No secrets in Docker images
- Resource quotas enabled

## Troubleshooting

### Check pod status:
```bash
kubectl get pods -n supportbot
kubectl logs -f deployment/discord-bot -n supportbot
```

### Check database connection:
```bash
kubectl exec -it deployment/discord-bot -n supportbot -- python -c "import asyncpg; print('DB OK')"
```

### Scale manually:
```bash
kubectl scale deployment/discord-bot --replicas=3 -n supportbot
```
