# Monitoring and Alerting

Complete guide for monitoring the Discord Support Bot with metrics, logs, and alerting.

## Table of Contents

- [Overview](#overview)
- [Metrics Collection](#metrics-collection)
- [Prometheus Setup](#prometheus-setup)
- [Grafana Dashboards](#grafana-dashboards)
- [Log Aggregation](#log-aggregation)
- [Alerting](#alerting)
- [Health Checks](#health-checks)
- [Distributed Tracing](#distributed-tracing)
- [Best Practices](#best-practices)

## Overview

The Discord Support Bot provides comprehensive observability through:

1. **Metrics**: Prometheus-compatible metrics for performance monitoring
2. **Logs**: Structured logging for debugging and auditing
3. **Traces**: Distributed tracing for request flow analysis
4. **Alerts**: Automated alerting for critical issues

### Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Discord Bot                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Metrics    │  │    Logs      │  │   Traces     │      │
│  │  (Prometheus)│  │  (Structured)│  │   (Sentry)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │
          ↓                 ↓                 ↓
┌─────────────────────────────────────────────────────────────┐
│              Observability Stack                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Prometheus  │  │    Loki      │  │   Tempo/     │      │
│  │  (Metrics)   │  │   (Logs)     │  │   Jaeger     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ↓
                    ┌──────────────┐
                    │   Grafana    │
                    │ (Dashboards) │
                    └──────────────┘
```

## Metrics Collection

### Built-in Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `bot_requests_total` | Counter | Total requests processed |
| `bot_request_duration_seconds` | Histogram | Request latency |
| `bot_errors_total` | Counter | Total errors |
| `bot_active_conversations` | Gauge | Active conversations |
| `ai_requests_total` | Counter | AI API requests |
| `ai_request_duration_seconds` | Histogram | AI request latency |
| `ai_cost_total` | Counter | Total AI costs |
| `cache_hits_total` | Counter | Cache hits |
| `cache_misses_total` | Counter | Cache misses |
| `db_connections_active` | Gauge | Active DB connections |
| `db_query_duration_seconds` | Histogram | DB query latency |

### Custom Metrics

Add custom metrics in your code:

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
command_counter = Counter(
    'bot_commands_total',
    'Total commands executed',
    ['command', 'guild_id']
)

response_time = Histogram(
    'bot_response_duration_seconds',
    'Response generation time',
    ['provider', 'model']
)

active_tickets = Gauge(
    'bot_active_tickets',
    'Number of active tickets',
    ['guild_id']
)

# Use metrics
command_counter.labels(command='ask', guild_id=str(guild_id)).inc()

with response_time.labels(provider='openai', model='gpt-4').time():
    response = await generate_response()

active_tickets.labels(guild_id=str(guild_id)).set(ticket_count)
```

### Metrics Endpoint

Metrics are exposed at `http://localhost:8000/metrics`:

```bash
# View metrics
curl http://localhost:8000/metrics

# Key metrics
# HELP bot_requests_total Total requests processed
# TYPE bot_requests_total counter
bot_requests_total 15234

# HELP bot_request_duration_seconds Request latency
# TYPE bot_request_duration_seconds histogram
bot_request_duration_seconds_bucket{le="0.1"} 5234
bot_request_duration_seconds_bucket{le="0.5"} 14234
```

## Prometheus Setup

### Docker Compose

```yaml
prometheus:
  image: prom/prometheus:latest
  container_name: discord-bot-prometheus
  restart: unless-stopped
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--storage.tsdb.retention.time=30d'
    - '--web.enable-lifecycle'
  volumes:
    - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - prometheus_data:/prometheus
  ports:
    - "9090:9090"
```

### Configuration

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'discord-bot'
    static_configs:
      - targets: ['bot:8000']
    metrics_path: /metrics
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'flower'
    static_configs:
      - targets: ['flower:5555']
    metrics_path: /metrics
```

### Kubernetes

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
  - port: metrics
    path: /metrics
    interval: 15s
```

## Grafana Dashboards

### Docker Compose

```yaml
grafana:
  image: grafana/grafana:latest
  container_name: discord-bot-grafana
  restart: unless-stopped
  environment:
    - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    - GF_USERS_ALLOW_SIGN_UP=false
    - GF_INSTALL_PLUGINS=grafana-clock-panel
  volumes:
    - grafana_data:/var/lib/grafana
    - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
  ports:
    - "3000:3000"
  depends_on:
    - prometheus
```

### Datasource Configuration

```yaml
# grafana/datasources/datasources.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    
  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
```

### Bot Dashboard

Key panels for bot monitoring:

```json
{
  "dashboard": {
    "title": "Discord Bot Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [{
          "expr": "rate(bot_requests_total[5m])"
        }]
      },
      {
        "title": "Error Rate",
        "type": "stat",
        "targets": [{
          "expr": "rate(bot_errors_total[5m])"
        }],
        "thresholds": {
          "steps": [
            {"color": "green", "value": 0},
            {"color": "yellow", "value": 0.01},
            {"color": "red", "value": 0.05}
          ]
        }
      },
      {
        "title": "AI Costs",
        "type": "graph",
        "targets": [{
          "expr": "increase(ai_cost_total[1h])"
        }]
      },
      {
        "title": "Cache Hit Rate",
        "type": "gauge",
        "targets": [{
          "expr": "cache_hits_total / (cache_hits_total + cache_misses_total)"
        }]
      },
      {
        "title": "Active Conversations",
        "type": "stat",
        "targets": [{
          "expr": "bot_active_conversations"
        }]
      }
    ]
  }
}
```

## Log Aggregation

### Structured Logging

The bot uses structured JSON logging:

```python
import structlog

logger = structlog.get_logger()

# Log with context
logger.info(
    "message_processed",
    guild_id=guild_id,
    user_id=user_id,
    command="ask",
    duration_ms=145,
    model="gpt-4o"
)
```

Output:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "info",
  "event": "message_processed",
  "guild_id": "123456789",
  "user_id": "987654321",
  "command": "ask",
  "duration_ms": 145,
  "model": "gpt-4o"
}
```

### Loki Setup

```yaml
loki:
  image: grafana/loki:latest
  container_name: discord-bot-loki
  ports:
    - "3100:3100"
  volumes:
    - ./loki/loki-config.yml:/etc/loki/local-config.yaml
    - loki_data:/loki
  command: -config.file=/etc/loki/local-config.yaml
```

Configuration:
```yaml
# loki/loki-config.yml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
  filesystem:
    directory: /loki/chunks
```

### Promtail Setup

```yaml
promtail:
  image: grafana/promtail:latest
  volumes:
    - ./logs:/var/log/bot:ro
    - ./promtail/promtail-config.yml:/etc/promtail/config.yml
  command: -config.file=/etc/promtail/config.yml
```

Configuration:
```yaml
# promtail/promtail-config.yml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: bot-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: bot
          __path__: /var/log/bot/*.log
```

## Alerting

### Prometheus Alerts

```yaml
# prometheus/alerts.yml
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
          description: "Error rate is {{ $value }} errors/sec"

      - alert: BotDown
        expr: up{job="discord-bot"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Bot is down"
          description: "Bot has been down for more than 1 minute"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(bot_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response latency"
          description: "95th percentile latency is {{ $value }}s"

      - alert: HighCost
        expr: increase(ai_cost_total[1h]) > 10
        for: 5m
        labels:
          severity: info
        annotations:
          summary: "High AI costs"
          description: "Spent ${{ $value }} in the last hour"
```

### Alertmanager

```yaml
alertmanager:
  image: prom/alertmanager:latest
  volumes:
    - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
  ports:
    - "9093:9093"
```

Configuration:
```yaml
# alertmanager/alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: 'password'

route:
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'default'
    email_configs:
      - to: 'admin@example.com'

  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.summary }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<key>'
```

### PagerDuty Integration

```yaml
# prometheus/alerts.yml
      - alert: BotCriticalFailure
        expr: rate(bot_errors_total[1m]) > 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Critical bot failure"
```

## Health Checks

### HTTP Health Endpoint

```python
from aiohttp import web

async def health_check(request):
    """Health check endpoint"""
    checks = {
        "discord": await check_discord_connection(),
        "database": await check_database_connection(),
        "redis": await check_redis_connection(),
        "ai_provider": await check_ai_provider()
    }
    
    healthy = all(checks.values())
    
    return web.json_response(
        {
            "status": "healthy" if healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        },
        status=200 if healthy else 503
    )

app = web.Application()
app.router.add_get('/health', health_check)
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

### Startup Probe

```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 30
```

## Distributed Tracing

### Sentry Integration

```python
import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT"),
    traces_sample_rate=0.1,
    integrations=[
        AsyncioIntegration(),
    ],
)

# Add custom spans
with sentry_sdk.start_span(op="ai_request", description="GPT-4") as span:
    span.set_tag("model", "gpt-4")
    span.set_data("tokens", 1500)
    response = await generate_response()
```

### OpenTelemetry

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add exporter
otlp_exporter = OTLPSpanExporter(endpoint="tempo:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Create spans
with tracer.start_as_current_span("process_message") as span:
    span.set_attribute("guild.id", guild_id)
    span.set_attribute("user.id", user_id)
    
    with tracer.start_as_current_span("ai_generation"):
        response = await generate_ai_response()
```

## Best Practices

### 1. Metric Naming

Use consistent naming conventions:

```python
# Good
bot_requests_total
ai_cost_dollars
request_duration_seconds

# Bad
requests
aiCost
requestTime
```

### 2. Cardinality Control

Avoid high-cardinality labels:

```python
# Bad - creates too many time series
bot_requests_total{user_id="123"}

# Good - aggregate by guild
bot_requests_total{guild_id="456"}
```

### 3. Log Levels

Use appropriate log levels:

```python
logger.debug("Cache miss", key=key)        # Development
logger.info("Request processed")           # Normal operations
logger.warning("Rate limit approaching")   # Attention needed
logger.error("Database connection failed") # Immediate action
```

### 4. Alert Thresholds

Set meaningful thresholds:

```yaml
# Error rate > 10% for 5 minutes
- alert: HighErrorRate
  expr: rate(errors_total[5m]) / rate(requests_total[5m]) > 0.1
  for: 5m

# Latency > 2s for 95th percentile
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(duration_bucket[5m])) > 2
  for: 5m
```

### 5. Dashboard Organization

Organize dashboards by function:

- **Overview**: Key metrics, health status
- **Performance**: Latency, throughput, errors
- **Costs**: AI spending, cache efficiency
- **Business**: Active users, conversation metrics
- **Infrastructure**: CPU, memory, DB connections

### 6. Runbooks

Document alert responses:

```markdown
# BotHighErrorRate Runbook

## Symptoms
- Error rate > 10%
- Users reporting issues

## Diagnosis
1. Check logs: `kubectl logs deployment/bot`
2. Check AI provider status
3. Check database connectivity

## Resolution
1. Restart bot if needed: `kubectl rollout restart deployment/bot`
2. Switch AI provider if API issues
3. Escalate to on-call if persists > 15 min
```
