# AI Provider Support

The Discord Support Bot supports multiple AI providers, allowing you to route requests intelligently based on cost, quality, and availability.

## Table of Contents

- [Supported Providers](#supported-providers)
- [Configuration](#configuration)
- [Routing Strategies](#routing-strategies)
- [Provider Health Monitoring](#provider-health-monitoring)
- [API Key Rotation](#api-key-rotation)
- [Troubleshooting](#troubleshooting)

## Supported Providers

### OpenAI

**Models:** GPT-4o, GPT-4o Mini, GPT-4 Turbo, GPT-3.5 Turbo, DALL-E 3

**Configuration:**
```bash
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...  # Optional
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional, for proxies
```

**Features:**
- Industry-leading quality
- Vision support (GPT-4o)
- Function calling
- JSON mode

**Cost:** $0.50-30.00 per 1K tokens depending on model

**Best For:**
- High-quality responses
- Complex reasoning tasks
- Vision/multimodal tasks
- Production workloads

---

### Anthropic (Claude)

**Models:** Claude 3 Opus, Claude 3.5 Sonnet, Claude 3 Haiku

**Configuration:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_BASE_URL=https://api.anthropic.com  # Optional
```

**Features:**
- Excellent reasoning
- Long context window (up to 200K tokens)
- Strong safety features
- Vision support

**Cost:** $0.25-75.00 per 1K tokens depending on model

**Best For:**
- Long document analysis
- Thoughtful, nuanced responses
- Safety-critical applications

---

### OpenRouter

**Models:** Access to 100+ models from various providers

**Configuration:**
```bash
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_REFERER=https://yourdomain.com
OPENROUTER_TITLE=Discord Support Bot
```

**Features:**
- Unified API for multiple providers
- Automatic fallback
- Cost tracking
- Free tier available

**Cost:** Varies by model, often cheaper than direct API access

**Best For:**
- Access to diverse models
- Cost optimization
- Redundancy

---

### Groq

**Models:** Llama 3.3 70B, Llama 3.1 70B, Mixtral 8x7B, Gemma

**Configuration:**
```bash
GROQ_API_KEY=gsk_...
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

**Features:**
- Extremely fast inference
- Free tier available
- Competitive pricing
- Good for high-volume use

**Cost:** Free tier available, then $0.50-2.00 per 1M tokens

**Best For:**
- High-volume, low-cost scenarios
- Simple queries
- Fast responses

---

### Ollama (Local/Cloud)

**Models (Local):** Llama 3.2, Llama 3.1, Mistral, Gemma, and more

**Models (Cloud):** Kimi K2.5, Gemini 2.0 Flash/Pro

**Configuration (Local):**
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

**Configuration (Cloud):**
```bash
OLLAMA_CLOUD_KEY=your_key
OLLAMA_CLOUD_BASE_URL=https://api.ollama.ai/v1
OLLAMA_CLOUD_MODEL=kimi-k2.5
```

**Features:**
- Free (self-hosted)
- Full data privacy
- No API limits
- Custom models

**Cost:** $0 (hardware costs only)

**Best For:**
- Data privacy requirements
- Offline environments
- Custom fine-tuned models

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

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_CLOUD_KEY=your-key
OLLAMA_CLOUD_BASE_URL=https://api.ollama.ai/v1
OLLAMA_CLOUD_MODEL=kimi-k2.5
```

### Provider Priority

Set provider priority (higher = preferred):

```python
# In bot configuration
router = AIRouter()
router.register_openai(api_key="sk-...", priority=5)
router.register_groq(api_key="gsk_...", priority=8)  # Preferred
router.register_ollama(priority=9)  # Most preferred
```

### Default Model

Set the default model when no specific routing matches:

```bash
DEFAULT_MODEL=gpt-4o-mini
```

## Routing Strategies

### Available Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `COST_PRIORITY` | Prefer cheaper/free models | Budget-conscious deployments |
| `QUALITY_PRIORITY` | Prefer best quality models | Premium support experience |
| `LATENCY_PRIORITY` | Prefer fastest models | Real-time responses |
| `RELIABILITY_PRIORITY` | Prefer most reliable providers | Critical uptime requirements |
| `BALANCED` | Balance all factors | General use (default) |

### Using Strategies

**Via Command:**
```bash
/settings strategy cost_priority
```

**Via Configuration:**
```bash
DEFAULT_STRATEGY=balanced
```

**Per Request:**
```python
response = await router.chat_completion(
    request,
    strategy=RoutingStrategy.COST_PRIORITY
)
```

### Smart Routing Logic

The bot automatically considers:

1. **Query Complexity**: Routes simple queries to cheaper models
2. **Context Length**: Selects models with sufficient context window
3. **Vision Requirements**: Uses vision-capable models for images
4. **Budget Status**: Falls back to cheaper models when budget exceeded
5. **Provider Health**: Avoids degraded providers

### Routing Decision Example

```
Input: "How do I reset my password?"
Complexity: Low (simple FAQ)
Strategy: COST_PRIORITY

Decision:
- Provider: Groq
- Model: llama-3.1-8b-instant
- Reason: Free tier, sufficient for simple query
- Estimated Cost: $0.00
- Confidence: 0.92
```

## Provider Health Monitoring

### Automatic Health Checks

The bot continuously monitors provider health:

- **Success Rate**: Tracks request success/failure ratio
- **Latency**: Monitors response times
- **Rate Limits**: Detects rate limit issues
- **Availability**: Checks provider API status

### Health Status Levels

| Status | Description | Action |
|--------|-------------|--------|
| `HEALTHY` | Operating normally | Use normally |
| `DEGRADED` | Some issues detected | Reduce usage, enable fallback |
| `UNHEALTHY` | Significant issues | Avoid if possible |
| `DOWN` | Not responding | Exclude from routing |

### Viewing Health Status

```bash
# Check all providers
/admin system

# Or check specific provider
/settings provider openai
```

## API Key Rotation

### Manual Rotation

```bash
# Rotate API key for a provider
/settings rotate-api-key
```

### Automatic Rotation

Enable automatic key rotation:

```bash
# Enable auto-rotation
/settings auto-rotate on

# Configure rotation interval (default: 30 days)
AUTO_ROTATE_INTERVAL_DAYS=30
```

### Multiple API Keys

Configure multiple keys for redundancy:

```python
router.register_openai(
    api_keys=["sk-key1", "sk-key2", "sk-key3"],
    priority=5
)
```

## Model Quality Tiers

### Quality Rankings

| Tier | Score | Models |
|------|-------|--------|
| Tier 1 | 10 | o1, o1-mini, GPT-4o, Claude 3 Opus, Claude 3.5 Sonnet |
| Tier 2 | 8 | GPT-4o Mini, GPT-4 Turbo, Claude 3 Sonnet, Claude 3 Haiku, Llama 3.3 70B |
| Tier 3 | 7 | GPT-3.5 Turbo, Llama 3.1 8B, Mixtral 8x7B |
| Tier 4 | 6 | Llama 3.2 1B, Gemma 7B |

### Cost Tiers

| Tier | Models | Cost/1K Tokens |
|------|--------|----------------|
| Free | Groq, Ollama | $0.00 |
| Budget | GPT-3.5, Claude 3 Haiku | $0.50-1.50 |
| Standard | GPT-4o Mini, Claude 3 Sonnet | $3.00-6.00 |
| Premium | GPT-4o, Claude 3 Opus | $15.00-75.00 |

## Troubleshooting

### Provider Connection Issues

**Symptom:** "Failed to connect to provider" errors

**Solutions:**
1. Verify API key is correct
2. Check network connectivity
3. Verify API endpoint URL
4. Check provider status page

```bash
# Test provider connectivity
python -c "
from ai.providers.openai_provider import OpenAIProvider
p = OpenAIProvider(api_key='sk-...')
print('Healthy:', p.is_healthy())
"
```

### Rate Limit Errors

**Symptom:** "Rate limit exceeded" errors

**Solutions:**
1. Enable rate limiting in config
2. Configure multiple API keys
3. Switch to different provider
4. Upgrade provider plan

```bash
# Check rate limits
/admin costs
```

### High Costs

**Symptom:** Unexpectedly high API costs

**Solutions:**
1. Switch to COST_PRIORITY strategy
2. Enable free tier providers (Groq, Ollama)
3. Set daily budget limits
4. Enable response caching

```bash
# Set daily budget
COST_BUDGET_DAILY=50.00

# Enable cost optimization
ENABLE_COST_OPTIMIZATION=true
```

### Model Not Available

**Symptom:** "Model not available" errors

**Solutions:**
1. Check model name spelling
2. Verify model is available in your region
3. Check provider model list
4. Use fallback models

```bash
# List available models for a provider
/settings provider openai
```

## Best Practices

1. **Configure Multiple Providers**: Always have at least 2 providers for redundancy
2. **Use Cost Optimization**: Enable smart routing to minimize costs
3. **Monitor Usage**: Regularly check cost breakdowns
4. **Set Budgets**: Configure daily/monthly spending limits
5. **Test Fallbacks**: Verify fallback providers work correctly
6. **Rotate Keys**: Regularly rotate API keys for security
