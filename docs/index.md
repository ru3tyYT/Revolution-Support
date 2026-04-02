# Discord Support Bot Documentation

Welcome to the Discord Support Bot documentation! This comprehensive guide covers everything you need to know about deploying, configuring, and using the AI-powered Discord support bot.

## What is Discord Support Bot?

The Discord Support Bot is an intelligent, cost-optimized support bot that leverages multiple AI providers to deliver high-quality automated support for Discord communities. It features smart routing, conversation memory, knowledge base integration, and horizontal scaling support.

## Key Features

- **Multi-Provider AI Support**: Route requests to OpenAI, Anthropic, OpenRouter, Groq, or Ollama Cloud
- **Smart Cost Optimization**: Automatic model selection based on complexity and budget
- **Conversation Memory**: Persistent context across sessions with Redis caching
- **Knowledge Base**: RAG-powered answers from uploaded documents
- **Forum Monitoring**: Automated responses to forum threads with keyword and AI matching
- **Research Subagents**: Advanced research capabilities with web search and analysis
- **Analytics Dashboard**: Track usage, costs, and response quality

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Discord Gateway                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
   │ Shard 1 │    │ Shard 2 │    │ Shard N │
   └────┬────┘    └────┬────┘    └────┬────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
              ┌─────────▼──────────┐
              │   Load Balancer    │
              └─────────┬──────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
   │ Bot Pod │    │ Bot Pod │    │ Bot Pod │
   └────┬────┘    └────┬────┘    └────┬────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
       ┌────────────────┼────────────────┐
       │                │                │
  ┌────▼────┐     ┌────▼────┐     ┌─────▼────┐
  │  Redis  │     │Postgres │     │  Vector  │
  │  Cache  │     │    DB   │     │   Store  │
  └─────────┘     └─────────┘     └──────────┘
```

## Documentation Structure

### Getting Started
- [Getting Started Guide](getting-started.md) - Installation and first-time setup

### Command Reference
- [Commands](commands.md) - Complete list of all bot commands

### Features
- [AI Provider Support](features/ai-support.md) - Multi-provider AI integration
- [Smart Keyword Routing](features/keyword-routing.md) - Keyword-based response system
- [Forum Monitoring](features/forum-monitoring.md) - Automated forum thread support
- [Knowledge Base](features/knowledge-base.md) - RAG-powered documentation
- [Research Subagents](features/subagent-research.md) - Advanced research capabilities

### Configuration
- [Environment Variables](configuration/environment-variables.md) - All configuration options (includes [Web Server & Discord OAuth](configuration/environment-variables.md#web-server--discord-oauth))
- [AI Models](configuration/ai-models.md) - Supported models and providers
- [Cost Optimization](configuration/cost-optimization.md) - Budget management strategies

### Web API & dashboard
- **FastAPI** (`web.main:app`): run with Uvicorn from the project root ([Getting Started](getting-started.md#optional-web-api-fastapi)); OpenAPI at `/docs`; Discord OAuth at `/api/auth/login`.
- **REST endpoints**: knowledge, analytics, AI ask (`POST /api/ai/ask`), guilds, tickets — see [PLAN_03_API_Endpoints.md](../PLAN_03_API_Endpoints.md#implemented-api-paths-reference).
- **React dashboard** (`frontend/`): Vite SPA with login, OAuth callback, and placeholder admin/user areas ([Getting Started](getting-started.md#optional-dashboard-frontend-react--vite)); configure `VITE_API_URL` ([Environment Variables](configuration/environment-variables.md#dashboard-frontend-vite)).

### Deployment
- [Docker Deployment](deployment/docker.md) - Container-based deployment
- [Kubernetes Deployment](deployment/kubernetes.md) - K8s deployment guide
- [Monitoring & Alerting](deployment/monitoring.md) - Observability setup

## Quick Start

1. **Install Prerequisites**: Python 3.11+, PostgreSQL 15+, Redis 7+
2. **Clone Repository**: `git clone https://github.com/yourorg/discord-support-bot.git`
3. **Configure Environment**: Copy `.env.example` to `.env` and fill in your settings
4. **Install Dependencies**: `pip install -e ".[dev]"`
5. **Run Migrations**: `alembic upgrade head`
6. **Start the Bot**: `python -m bot`

## Cost Tiers

| Tier | Models | Avg Cost/1K Tokens | Use Case |
|------|--------|-------------------|----------|
| Free | Groq (Llama), Ollama | $0.00 | Simple queries, high volume |
| Budget | GPT-3.5, Claude 3 Haiku | $0.50-1.50 | Standard support |
| Standard | GPT-4o Mini, Claude 3 Sonnet | $3.00-6.00 | Complex issues |
| Premium | GPT-4o, Claude 3 Opus | $15.00-75.00 | Critical escalations |

## Support

- **Discord**: [Join Support Server](https://discord.gg/yourserver)
- **Issues**: [GitHub Issues](https://github.com/yourorg/discord-support-bot/issues)
- **Email**: support@yourcompany.com

## Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/yourorg/discord-support-bot/blob/main/CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/yourorg/discord-support-bot/blob/main/LICENSE) file for details.
