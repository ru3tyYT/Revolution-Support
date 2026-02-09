# Supported AI Models

Complete reference for all AI models and providers supported by the Discord Support Bot.

## Table of Contents

- [Provider Overview](#provider-overview)
- [OpenAI Models](#openai-models)
- [Anthropic (Claude) Models](#anthropic-claude-models)
- [OpenRouter Models](#openrouter-models)
- [Groq Models](#groq-models)
- [Ollama Models](#ollama-models)
- [Model Comparison](#model-comparison)
- [Capability Matrix](#capability-matrix)
- [Context Windows](#context-windows)
- [Pricing](#pricing)

## Provider Overview

| Provider | Models | Free Tier | Vision | Streaming |
|----------|--------|-----------|--------|-----------|
| OpenAI | 5+ | No | Yes | Yes |
| Anthropic | 3+ | No | Yes | Yes |
| OpenRouter | 100+ | Limited | Varies | Yes |
| Groq | 10+ | Yes | No | Yes |
| Ollama | 50+ | Yes | Limited | Yes |

## OpenAI Models

### GPT-4o

**Model ID:** `gpt-4o`

| Attribute | Value |
|-----------|-------|
| **Quality Tier** | 9/10 |
| **Context Window** | 128K tokens |
| **Input Cost** | $5.00 / 1M tokens |
| **Output Cost** | $15.00 / 1M tokens |
| **Vision** | Yes |
| **Streaming** | Yes |
| **Function Calling** | Yes |

**Best For:**
- Complex reasoning tasks
- Code generation
- Multi-modal interactions
- Production workloads

**Example Configuration:**
```bash
OPENAI_API_KEY=sk-...
DEFAULT_MODEL=gpt-4o
```

---

### GPT-4o Mini

**Model ID:** `gpt-4o-mini`

| Attribute | Value |
|-----------|-------|
| **Quality Tier** | 8/10 |
| **Context Window** | 128K tokens |
| **Input Cost** | $0.15 / 1M tokens |
| **Output Cost** | $0.60 / 1M tokens |
| **Vision** | Yes |
| **Streaming** | Yes |
| **Function Calling** | Yes |

**Best For:**
- Cost-effective production
- High-volume applications
- Simple to moderate complexity

---

### GPT-4 Turbo

**Model ID:** `gpt-4-turbo`

| Attribute | Value |
|-----------|-------|
| **Quality Tier** | 8/10 |
| **Context Window** | 128K tokens |
| **Input Cost** | $10.00 / 1M tokens |
| **Output Cost** | $30.00 / 1M tokens |
| **Vision** | Yes |
| **Streaming** | Yes |

**Best For:**
- Legacy compatibility
- Document analysis
- Complex tasks

---

### GPT-3.5 Turbo

**Model ID:** `gpt-3.5-turbo`

| Attribute | Value |
|-----------|-------|
| **Quality Tier** | 7/10 |
| **Context Window** | 16K tokens |
| **Input Cost** | $0.50 / 1M tokens |
| **Output Cost** | $1.50 / 1M tokens |
| **Vision** | No |
| **Streaming** | Yes |

**Best For:**
- Budget-conscious deployments
- Simple queries
- High-volume use

---

### o1 / o1-mini

**Model IDs:** `o1`, `o1-mini`

| Attribute | Value |
|-----------|-------|
| **Quality Tier** | 10/10 |
| **Context Window** | 128K tokens |
| **Input Cost** | $15.00 / 1M tokens (o1) |
| **Output Cost** | $60.00 / 1M tokens (o1) |
| **Vision** | Limited |
| **Streaming** | No |
| **Reasoning** | Advanced |

**Best For:**
- Complex problem-solving
- Research tasks
- Math and logic
- Code reasoning

## Anthropic (Claude) Models

### Claude 3 Opus

**Model ID:** `claude-3-opus-20240229`

| Attribute | Value |
|-----------|-------|
| **Quality Tier** | 9/10 |
| **Context Window** | 200K tokens |
| **Input Cost** | $15.00 / 1M tokens |
| **Output Cost** | $75.00 / 1M tokens |
| **Vision** | Yes |
| **Streaming** | Yes |

**Best For:**
- Long document analysis
- Nuanced responses
- Safety-critical applications
- Complex reasoning

---

### Claude 3.5 Sonnet

**Model ID:** `claude-3-5-sonnet-20241022`

| Attribute | Value |
|-----------|-------|
| **Quality Tier** | 9/10 |
| **Context Window** | 200K tokens |
| **Input Cost** | $3.00 / 1M tokens |
| **Output Cost** | $15.00 / 1M tokens |
| **Vision** | Yes |
| **Streaming** | Yes |

**Best For:**
- Balanced quality and cost
- Long contexts
- General-purpose use

---

### Claude 3 Haiku

**Model ID:** `claude-3-haiku-20240307`

| Attribute | Value |
|-----------|-------|
| **Quality Tier** | 8/10 |
| **Context Window** | 200K tokens |
| **Input Cost** | $0.25 / 1M tokens |
| **Output Cost** | $1.25 / 1M tokens |
| **Vision** | Yes |
| **Streaming** | Yes |

**Best For:**
- Fast responses
- Cost-effective
- High-volume use

---

### Claude 3.5 Haiku

**Model ID:** `claude-3-5-haiku-20241022`

| Attribute | Value |
|-----------|-------|
| **Quality Tier** | 8/10 |
| **Context Window** | 200K tokens |
| **Input Cost** | $1.00 / 1M tokens |
| **Output Cost** | $5.00 / 1M tokens |
| **Vision** | No |
| **Streaming** | Yes |

**Best For:**
- Fast, cheap responses
- Simple tasks
- High throughput

## OpenRouter Models

OpenRouter provides access to 100+ models from various providers.

### Popular Models

| Model | Provider | Context | Cost/1M (In/Out) |
|-------|----------|---------|------------------|
| `anthropic/claude-3.5-sonnet` | Anthropic | 200K | $3.00 / $15.00 |
| `anthropic/claude-3-opus` | Anthropic | 200K | $15.00 / $75.00 |
| `openai/gpt-4o` | OpenAI | 128K | $5.00 / $15.00 |
| `google/gemini-2.0-pro` | Google | 128K | $3.50 / $10.50 |
| `meta-llama/llama-3.3-70b-instruct` | Meta | 128K | $0.50 / $0.75 |
| `mistralai/mistral-large` | Mistral | 32K | $2.00 / $6.00 |

### Free Tier Models

| Model | Provider | Limitations |
|-------|----------|-------------|
| `google/gemini-2.0-flash` | Google | Rate limited |
| `meta-llama/llama-3.1-8b-instruct` | Meta | Rate limited |
| `nousresearch/hermes-3-llama-3.1-405b` | Nous | Rate limited |

**Configuration:**
```bash
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

## Groq Models

Groq offers extremely fast inference with free tier available.

### Production Models

| Model | Context | Cost/1M (In/Out) | Speed |
|-------|---------|------------------|-------|
| `llama-3.3-70b-versatile` | 128K | $0.59 / $0.79 | Very Fast |
| `llama-3.1-70b-versatile` | 128K | $0.59 / $0.79 | Very Fast |
| `mixtral-8x7b-32768` | 32K | $0.24 / $0.24 | Very Fast |
| `gemma2-9b-it` | 8K | $0.20 / $0.20 | Fast |

### Preview Models

| Model | Context | Cost/1M (In/Out) |
|-------|---------|------------------|
| `llama-3.1-8b-instant` | 128K | $0.05 / $0.08 |
| `llama-3.2-3b-preview` | 128K | $0.04 / $0.04 |
| `llama-3.2-1b-preview` | 128K | $0.04 / $0.04 |

**Free Tier:** 100K tokens/day

**Configuration:**
```bash
GROQ_API_KEY=gsk_...
DEFAULT_MODEL=llama-3.1-8b-instant
```

## Ollama Models

Ollama allows running open-source models locally.

### Recommended Models

| Model | Size | Quality | VRAM Required |
|-------|------|---------|---------------|
| `llama3.2` | 3B/1B | 6/10 | 4-8 GB |
| `llama3.1` | 8B/70B | 7-8/10 | 8-48 GB |
| `mistral` | 7B | 7/10 | 8 GB |
| `mixtral` | 47B | 7/10 | 32 GB |
| `qwen2.5` | 7B/72B | 7-8/10 | 8-48 GB |
| `codellama` | 7B/13B | 7/10 | 8-16 GB |
| `phi3` | 3.8B | 6/10 | 4 GB |

### Installation

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.2

# Start server
ollama serve
```

**Configuration:**
```bash
OLLAMA_CLOUD_KEY=  # Leave empty for local
OLLAMA_CLOUD_BASE_URL=http://localhost:11434
OLLAMA_CLOUD_MODEL=llama3.2
```

## Model Comparison

### Quality vs Cost

```
Cost per 1K Tokens (Output)
│
$75 ┤                           ● Claude 3 Opus
    │
$60 ┤           ● o1
    │
$30 ┤       ● GPT-4 Turbo
    │
$15 ┤   ● GPT-4o              ● Claude 3.5 Sonnet
    │
$10 ┤
    │
$ 5 ┤   ● GPT-4o Mini
    │                   ● Claude 3 Haiku
$ 1 ┤       ● GPT-3.5 Turbo
    │
$0.5┤                       ● Groq Llama 3
    │
$ 0 ┼────────────────────────────────────────
    │ Low          Medium         High
    │         Quality →
```

### Speed vs Quality

| Model | Quality | Speed | Best For |
|-------|---------|-------|----------|
| GPT-4o | ★★★★★ | ★★★★☆ | Premium support |
| Claude 3.5 Sonnet | ★★★★★ | ★★★★☆ | Long documents |
| GPT-4o Mini | ★★★★☆ | ★★★★★ | Cost-effective |
| Claude 3 Haiku | ★★★★☆ | ★★★★★ | Fast responses |
| Groq Llama 3 | ★★★☆☆ | ★★★★★ | High volume |
| GPT-3.5 Turbo | ★★★☆☆ | ★★★★☆ | Legacy support |

## Capability Matrix

### Feature Support

| Model | Vision | JSON Mode | Function Calling | Streaming |
|-------|--------|-----------|------------------|-----------|
| GPT-4o | ✅ | ✅ | ✅ | ✅ |
| GPT-4o Mini | ✅ | ✅ | ✅ | ✅ |
| Claude 3 Opus | ✅ | ✅ | ✅ | ✅ |
| Claude 3.5 Sonnet | ✅ | ✅ | ✅ | ✅ |
| Claude 3 Haiku | ✅ | ✅ | ✅ | ✅ |
| Groq Llama 3 | ❌ | ✅ | ✅ | ✅ |
| Ollama Models | Varies | Varies | Varies | ✅ |

### Language Support

| Model | English | Code | Multilingual |
|-------|---------|------|--------------|
| GPT-4o | ★★★★★ | ★★★★★ | ★★★★★ |
| Claude 3.5 | ★★★★★ | ★★★★★ | ★★★★☆ |
| GPT-3.5 | ★★★★☆ | ★★★★☆ | ★★★★☆ |
| Groq Llama | ★★★★☆ | ★★★☆☆ | ★★★☆☆ |

## Context Windows

### Comparison Table

| Model | Context Window | Max Output |
|-------|---------------|------------|
| Claude 3 Opus | 200,000 tokens | 4,096 tokens |
| Claude 3.5 Sonnet | 200,000 tokens | 8,192 tokens |
| Claude 3 Haiku | 200,000 tokens | 4,096 tokens |
| GPT-4o | 128,000 tokens | 4,096 tokens |
| GPT-4o Mini | 128,000 tokens | 16,384 tokens |
| GPT-4 Turbo | 128,000 tokens | 4,096 tokens |
| GPT-3.5 Turbo | 16,385 tokens | 4,096 tokens |
| Groq Llama 3 | 128,000 tokens | 8,192 tokens |

### Context Usage Guidelines

```python
# Small context (under 4K tokens)
# Use: GPT-3.5 Turbo, Claude 3 Haiku
# Best for: Simple Q&A, short conversations

# Medium context (4K-32K tokens)
# Use: GPT-4o Mini, Claude 3 Haiku
# Best for: Most support queries

# Large context (32K-128K tokens)
# Use: GPT-4o, Claude 3.5 Sonnet
# Best for: Document analysis, long conversations

# Extra large context (128K+ tokens)
# Use: Claude 3 Opus
# Best for: Large codebases, extensive documentation
```

## Pricing

### Cost Calculator Example

```python
# Example: 1000 support queries per day
# Average: 500 input tokens, 300 output tokens

# GPT-4o
input_cost = (1000 * 500 / 1_000_000) * 5.00   # $2.50
output_cost = (1000 * 300 / 1_000_000) * 15.00 # $4.50
daily_cost = input_cost + output_cost            # $7.00
monthly_cost = daily_cost * 30                   # $210.00

# GPT-4o Mini
input_cost = (1000 * 500 / 1_000_000) * 0.15   # $0.075
output_cost = (1000 * 300 / 1_000_000) * 0.60  # $0.18
daily_cost = input_cost + output_cost          # $0.255
monthly_cost = daily_cost * 30                 # $7.65

# Groq Llama 3 (Free tier: 100K tokens/day)
# First 100K tokens free, then:
input_cost = (500 / 1_000_000) * 0.05  # $0.000025 per query
output_cost = (300 / 1_000_000) * 0.08 # $0.000024 per query
```

### Cost Optimization Tips

1. **Use Free Tiers**: Groq, Ollama for simple queries
2. **Smart Routing**: Route complex queries to premium models
3. **Caching**: Cache common responses
4. **Context Management**: Keep context within limits
5. **Response Limits**: Set max tokens for outputs

### Recommended Model by Budget

| Monthly Budget | Recommended Setup |
|----------------|-------------------|
| Free | Groq (free tier) + Ollama |
| $10-50 | GPT-4o Mini + Groq |
| $50-200 | GPT-4o + GPT-4o Mini |
| $200-500 | GPT-4o + Claude 3.5 Sonnet |
| $500+ | Claude 3 Opus + GPT-4o |

## Configuration Examples

### Budget Configuration

```bash
# Primary: Free tier
GROQ_API_KEY=gsk_...
DEFAULT_MODEL=llama-3.1-8b-instant

# Fallback: Cheap model
OPENAI_API_KEY=sk-...
FALLBACK_MODEL=gpt-4o-mini

# Cost optimization
ENABLE_COST_OPTIMIZATION=true
FREE_TIER_MODE=true
```

### Quality Configuration

```bash
# Primary: High quality
OPENAI_API_KEY=sk-...
DEFAULT_MODEL=gpt-4o

# Fallback: Claude
ANTHROPIC_API_KEY=sk-ant-...
FALLBACK_MODEL=claude-3-5-sonnet-20241022

# Smart routing
ENABLE_SMART_ROUTING=true
ENABLE_COST_OPTIMIZATION=true
```

### Balanced Configuration

```bash
# Multiple providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...

# Smart routing
DEFAULT_MODEL=gpt-4o-mini
ENABLE_SMART_ROUTING=true
COST_BUDGET_DAILY=50.00
```
