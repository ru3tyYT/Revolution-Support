# AI Provider Support

The Discord Support Bot supports multiple AI providers with automatic failover between providers.

## Table of Contents

- [Supported Providers](#supported-providers)
- [Configuration](#configuration)
- [Basic Routing](#basic-routing)
- [Provider Failover](#provider-failover)
- [Cost Tracking](#cost-tracking)
- [Troubleshooting](#troubleshooting)

## Supported Providers

### OpenAI

**Models:** GPT-4o, GPT-4o Mini, o1, o3-mini, GPT-4 Turbo

**Configuration:**
```bash
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...  # Optional
```

**Features:**
- Industry-leading quality
- Vision support (GPT-4o)
- Function calling
- JSON mode

**Cost:** $0.15-60.00 per 1M tokens depending on model

**Best For:**
- High-quality responses
- Complex reasoning tasks
- Vision/multimodal tasks

---

### Anthropic (Claude)

**Models:** Claude 3 Opus, Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Haiku

**Configuration:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

**Features:**
- Excellent reasoning
- Long context window (up to 200K tokens)
- Strong safety features
- Vision support

**Cost:** $0.25-75.00 per 1M tokens depending on model

**Best For:**
- Long document analysis
- Thoughtful, nuanced responses

---

### OpenRouter

**Models:** Access to GPT-4o, Claude 3.5 Sonnet, Llama 3.1 405B, DeepSeek V3

**Configuration:**
```bash
OPENROUTER_API_KEY=sk-or-...
```

**Features:**
- Unified API for multiple providers
- Automatic failover
- Access to models from various providers

**Cost:** Varies by model

**Best For:**
- Access to diverse models
- Redundancy

---

### Groq

**Models:** Llama 3.3 70B, Llama 3.1 8B, Mixtral 8x7B, Gemma 2 9B

**Configuration:**
```bash
GROQ_API_KEY=gsk_...
```

**Features:**
- Free tier available
- Fast inference
- Good for high-volume use

**Cost:** Free tier available

**Best For:**
- Cost-conscious deployments
- Simple queries

---

### Ollama

**Models:** Llama 3.2, Mistral, CodeLlama (configurable)

**Configuration:**
```bash
# Local Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Cloud Ollama
OLLAMA_CLOUD_KEY=your_key
OLLAMA_CLOUD_BASE_URL=https://api.ollama.com/v1
```

**Features:**
- Self-hosted option (free)
- Full data privacy
- Custom models

**Cost:** $0 (hardware costs only for self-hosted)

**Best For:**
- Data privacy requirements
- Offline environments

## Configuration

### Environment Variables

Configure providers in your `.env` file:

```bash
# ============================================
# AI PROVIDER API KEYS
# At least one provider is required
# ============================================

# OpenAI
OPENAI_API_KEY=sk-your-key
OPENAI_ORG_ID=org-your-org

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-key

# OpenRouter
OPENROUTER_API_KEY=sk-or-your-key

# Groq
GROQ_API_KEY=gsk-your-key

# Ollama (Local)
OLLAMA_BASE_URL=http://localhost:11434

# Ollama (Cloud)
OLLAMA_CLOUD_KEY=your-key
OLLAMA_CLOUD_BASE_URL=https://api.ollama.com/v1
```

### Model Configuration

Models are configured in `config/models.yaml`. This file defines:
- Available models for each provider
- Model capabilities (vision, function calling, etc.)
- Context lengths
- Cost per token
- Rate limits

See `config/models.yaml` for the complete model definitions.

### Provider Priority

When multiple providers are configured, the router selects providers based on:
1. Provider health status
2. Model availability
3. Request requirements (vision, context length)
4. Priority values set during registration

## Basic Routing

The AI router (`ai/router.py`) handles provider selection automatically based on:

- **Provider Health**: Only healthy providers are considered
- **Model Requirements**: Vision-capable models selected when needed
- **Context Length**: Models with sufficient context window selected
- **Priority**: Higher priority providers preferred

### Example Routing

```python
from ai.router import AIRouter

router = AIRouter()
router.register_openai(api_key="sk-...")
router.register_groq(api_key="gsk_...")

# Router automatically selects best provider
response = await router.chat_completion(request)
```

### Routing Strategies (Programmatic)

The router supports these strategies when used programmatically:

```python
from ai.router import RoutingStrategy

# Cost priority - prefer cheaper/free models
response = await router.chat_completion(
    request,
    strategy=RoutingStrategy.COST_PRIORITY
)

# Quality priority - prefer best quality models
response = await router.chat_completion(
    request,
    strategy=RoutingStrategy.QUALITY_PRIORITY
)

# Balanced - balance all factors (default)
response = await router.chat_completion(
    request,
    strategy=RoutingStrategy.BALANCED
)
```

**Note:** Routing strategies are only available programmatically. There is no `/settings strategy` command.

## Provider Failover

The router automatically fails over to alternative providers when:
- A provider returns an error
- Rate limits are hit
- A provider is unhealthy

### Failover Configuration

```python
router = AIRouter(
    enable_fallback=True,
    max_fallback_attempts=3
)
```

### Failover Behavior

1. Primary provider selected based on routing logic
2. If request fails, next best provider is tried
3. Process continues until success or max attempts reached
4. Failed providers temporarily excluded from routing

## Cost Tracking

Basic cost tracking is implemented in the provider base class:

- **Usage Statistics**: Tracks tokens used and estimated costs
- **Per-Provider Stats**: Success/failure rates and latency
- **History**: Last 1000 requests stored per provider

### Viewing Cost Information

```python
# Get usage stats for a provider
stats = provider.get_usage_stats(minutes=60)
print(f"Total cost: ${stats['total_cost']:.2f}")

# Get routing statistics
routing_stats = router.get_routing_stats()
print(f"Total routes: {routing_stats['total_routes']}")
```

### Provider Health

Basic health monitoring tracks:
- Provider status (healthy, degraded, error, rate_limited, offline)
- Success/failure rates
- Average latency

```python
# Check all provider health
health = await router.get_provider_health()
for provider, status in health.items():
    print(f"{provider}: {status['status']}")
```

**Note:** There is no continuous health monitoring or automatic health check system. Health status is updated during request execution.

## Troubleshooting

### Provider Connection Issues

**Symptom:** "Failed to connect to provider" errors

**Solutions:**
1. Verify API key is correct
2. Check network connectivity
3. Verify API endpoint URL
4. Check provider status page

### Rate Limit Errors

**Symptom:** "Rate limit exceeded" errors

**Solutions:**
1. Configure multiple providers for failover
2. Switch to different provider
3. Upgrade provider plan

### Model Not Available

**Symptom:** "Model not available" errors

**Solutions:**
1. Check model name in config/models.yaml
2. Verify model is available for your API key
3. Check provider model list

## Best Practices

1. **Configure Multiple Providers**: Always have at least 2 providers for redundancy
2. **Use Free Tiers**: Groq and Ollama offer free tiers for cost savings
3. **Monitor Usage**: Check routing statistics periodically
4. **Test Fallbacks**: Verify fallback providers work correctly

## Limitations

- No `/settings strategy` command (strategies are programmatic only)
- No continuous health monitoring (basic status tracking only)
- No automatic API key rotation UI (key rotation requires multiple pre-configured keys)
- Configuration is via `config/models.yaml`, not environment variables for cost/optimization settings
