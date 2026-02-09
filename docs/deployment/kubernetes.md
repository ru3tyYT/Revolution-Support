# Kubernetes Deployment

Complete guide for deploying the Discord Support Bot on Kubernetes with high availability and auto-scaling.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Namespace Configuration](#namespace-configuration)
- [Database Deployment](#database-deployment)
- [Cache Deployment](#cache-deployment)
- [Bot Deployment](#bot-deployment)
- [Research Workers](#research-workers)
- [Monitoring Setup](#monitoring-setup)
- [Scaling Configuration](#scaling-configuration)
- [Production Checklist](#production-checklist)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| kubectl | 1.25+ | Kubernetes CLI |
| helm | 3.12+ | Package manager |
| kustomize | 5.0+ | Configuration management |

### Cluster Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| Nodes | 2 | 3+ |
| CPU | 4 cores | 8+ cores |
| Memory | 8 GB | 16+ GB |
| Storage | 50 GB | 100+ GB SSD |

### Required Components

- [ ] Kubernetes cluster (EKS, GKE, AKS, or self-hosted)
- [ ] Ingress controller (nginx, traefik, or cloud provider)
- [ ] Cert-manager (for SSL certificates)
- [ ] Persistent volume provisioner

## Architecture

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Ingress                              │
│              (SSL termination, rate limiting)               │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
   │ Bot Pod │    │ Bot Pod │    │ Bot Pod │
   │  (HPA)  │    │  (HPA)  │    │  (HPA)  │
   └────┬────┘    └────┬────┘    └────┬────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
       ┌────────────────┼────────────────┐
       │                │                │
  ┌────▼────┐     ┌────▼────┐     ┌─────▼────┐
  │  Redis  │     │ Postgres│     │ Research │
  │ Cluster │     │  HA     │     │ Workers  │
  │ (3 rep) │     │ (1 pod) │     │ (Celery) │
  └─────────┘     └─────────┘     └──────────┘
```

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f docker/k8s/namespace.yaml
```

### 2. Configure Secrets

```bash
# Create secrets from environment variables
kubectl create secret generic bot-secrets \
  --from-literal=discord-token=$DISCORD_TOKEN \
  --from-literal=postgres-password=$POSTGRES_PASSWORD \
  --from-literal=openai-key=$OPENAI_API_KEY \
  -n discord-bot
```

### 3. Deploy Database

```bash
kubectl apply -f docker/k8s/postgres-statefulset.yaml
```

### 4. Deploy Cache

```bash
kubectl apply -f docker/k8s/redis-deployment.yaml
```

### 5. Deploy Bot

```bash
kubectl apply -f docker/k8s/bot-deployment.yaml
kubectl apply -f docker/k8s/bot-service.yaml
```

### 6. Verify Deployment

```bash
# Check pods
kubectl get pods -n discord-bot

# Check services
kubectl get svc -n discord-bot

# View logs
kubectl logs -f deployment/bot -n discord-bot
```

## Namespace Configuration

### Namespace Definition

```yaml
# docker/k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: discord-bot
  labels:
    app: discord-bot
    environment: production
```

### Resource Quotas

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: bot-quota
  namespace: discord-bot
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "20"
```

## Database Deployment

### PostgreSQL StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: discord-bot
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: ankane/pgvector:latest
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_USER
          value: postgres
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: postgres-password
        - name: POSTGRES_DB
          value: supportbot
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
```

### Database Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: discord-bot
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
```

### Database Migration Job

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  namespace: discord-bot
spec:
  template:
    spec:
      containers:
      - name: migration
        image: your-registry/discord-bot:latest
        command: ["alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          value: "postgresql://postgres:$(POSTGRES_PASSWORD)@postgres:5432/supportbot"
        envFrom:
        - secretRef:
            name: bot-secrets
      restartPolicy: OnFailure
  backoffLimit: 4
```

## Cache Deployment

### Redis Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: discord-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command:
        - redis-server
        - --appendonly
        - "yes"
        - --maxmemory
        - "256mb"
        - --maxmemory-policy
        - allkeys-lru
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc
```

### Redis Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: discord-bot
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
```

## Bot Deployment

### Bot Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bot
  namespace: discord-bot
  labels:
    app: bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: bot
  template:
    metadata:
      labels:
        app: bot
    spec:
      containers:
      - name: bot
        image: your-registry/discord-bot:latest
        ports:
        - containerPort: 8080
          name: health
        env:
        - name: DISCORD_TOKEN
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: discord-token
        - name: DATABASE_URL
          value: "postgresql://postgres:$(POSTGRES_PASSWORD)@postgres:5432/supportbot"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        envFrom:
        - secretRef:
            name: bot-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Bot Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: bot
  namespace: discord-bot
  labels:
    app: bot
spec:
  selector:
    app: bot
  ports:
  - port: 80
    targetPort: 8080
    name: http
  type: ClusterIP
```

### Bot ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: bot-config
  namespace: discord-bot
data:
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
  DEFAULT_MODEL: "gpt-4o-mini"
  ENABLE_COST_OPTIMIZATION: "true"
  COST_BUDGET_DAILY: "50.00"
```

## Research Workers

### Celery Worker Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: research-worker
  namespace: discord-bot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: research-worker
  template:
    metadata:
      labels:
        app: research-worker
    spec:
      containers:
      - name: worker
        image: your-registry/discord-bot:latest
        command: ["celery", "-A", "research.tasks", "worker", "--loglevel=info", "--concurrency=4"]
        env:
        - name: DATABASE_URL
          value: "postgresql://postgres:$(POSTGRES_PASSWORD)@postgres:5432/supportbot"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: CELERY_BROKER_URL
          value: "redis://redis:6379/1"
        envFrom:
        - secretRef:
            name: bot-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### Celery Beat Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-beat
  namespace: discord-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: celery-beat
  template:
    metadata:
      labels:
        app: celery-beat
    spec:
      containers:
      - name: beat
        image: your-registry/discord-bot:latest
        command: ["celery", "-A", "research.tasks", "beat", "--loglevel=info"]
        env:
        - name: DATABASE_URL
          value: "postgresql://postgres:$(POSTGRES_PASSWORD)@postgres:5432/supportbot"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        envFrom:
        - secretRef:
            name: bot-secrets
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "250m"
```

## Monitoring Setup

### Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: bot-metrics
  namespace: discord-bot
  labels:
    app: bot
spec:
  selector:
    matchLabels:
      app: bot
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### Prometheus Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: bot-alerts
  namespace: discord-bot
spec:
  groups:
  - name: bot
    rules:
    - alert: BotHighErrorRate
      expr: rate(bot_errors_total[5m]) > 0.1
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High error rate in bot"
        
    - alert: BotDown
      expr: up{job="bot"} == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Bot is down"
```

### Grafana Dashboard

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: bot-dashboard
  namespace: discord-bot
  labels:
    grafana_dashboard: "1"
data:
  bot-dashboard.json: |
    {
      "dashboard": {
        "title": "Discord Bot Metrics",
        "panels": [
          {
            "title": "Request Rate",
            "targets": [
              {
                "expr": "rate(bot_requests_total[5m])"
              }
            ]
          }
        ]
      }
    }
```

## Scaling Configuration

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: bot-hpa
  namespace: discord-bot
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: bot
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

### Vertical Pod Autoscaler

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: bot-vpa
  namespace: discord-bot
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: bot
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: bot
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 1000m
        memory: 1Gi
```

### Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: bot-pdb
  namespace: discord-bot
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: bot
```

## Production Checklist

### Security

- [ ] Use Kubernetes secrets for sensitive data
- [ ] Enable network policies
- [ ] Run containers as non-root
- [ ] Use read-only root filesystems
- [ ] Enable PodSecurityPolicies
- [ ] Configure RBAC
- [ ] Enable audit logging

### High Availability

- [ ] Deploy across multiple availability zones
- [ ] Use PodDisruptionBudgets
- [ ] Configure anti-affinity rules
- [ ] Enable cluster autoscaling
- [ ] Set up database backups
- [ ] Configure health checks

### Monitoring

- [ ] Deploy Prometheus and Grafana
- [ ] Configure alerts
- [ ] Set up log aggregation
- [ ] Enable distributed tracing
- [ ] Create dashboards

### Performance

- [ ] Configure resource limits
- [ ] Set up HPA
- [ ] Optimize database queries
- [ ] Enable caching
- [ ] Configure connection pooling

## Troubleshooting

### Pod Won't Start

```bash
# Check pod status
kubectl get pods -n discord-bot

# Describe pod for details
kubectl describe pod <pod-name> -n discord-bot

# View events
kubectl get events -n discord-bot --sort-by=.lastTimestamp

# Check logs
kubectl logs <pod-name> -n discord-bot
```

### Database Connection Issues

```bash
# Test database connectivity
kubectl exec -it <bot-pod> -n discord-bot -- python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('postgresql://postgres:password@postgres:5432/supportbot')
    print('Connected!')
    await conn.close()
asyncio.run(test())
"
```

### Scaling Issues

```bash
# Check HPA status
kubectl get hpa -n discord-bot

# Describe HPA
kubectl describe hpa bot-hpa -n discord-bot

# View metrics
kubectl top pods -n discord-bot
```

### Common Commands

```bash
# Get all resources
kubectl get all -n discord-bot

# Port forward for local testing
kubectl port-forward svc/bot 8080:80 -n discord-bot

# Execute command in pod
kubectl exec -it <pod-name> -n discord-bot -- /bin/sh

# Scale deployment manually
kubectl scale deployment bot --replicas=5 -n discord-bot

# Rollout restart
kubectl rollout restart deployment/bot -n discord-bot

# View rollout status
kubectl rollout status deployment/bot -n discord-bot
```
