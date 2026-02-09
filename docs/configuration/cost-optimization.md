# Cost Optimization

Strategies and features for managing and minimizing AI API costs while maintaining quality.

## Table of Contents

- [Overview](#overview)
- [Cost Tracking](#cost-tracking)
- [Smart Routing](#smart-routing)
- [Response Caching](#response-caching)
- [Budget Management](#budget-management)
- [Provider Optimization](#provider-optimization)
- [Best Practices](#best-practices)
- [Cost Calculator](#cost-calculator)

## Overview

The Discord Support Bot includes multiple strategies to optimize AI costs:

1. **Smart Routing**: Automatically select cheapest suitable model
2. **Response Caching**: Avoid repeated API calls
3. **Free Tier Usage**: Leverage free providers when possible
4. **Budget Controls**: Set spending limits with alerts
5. **Usage Analytics**: Track and analyze costs

### Cost Components

| Component | Description | Typical Cost |
|-----------|-------------|--------------|
| AI Inference | Token generation | $0-75/1M tokens |
| Embeddings | Vector generation | $0.02-0.13/1M tokens |
| Search APIs | Web research | $0-100/month |
| Vector DB | Storage & queries | Included in Postgres |
| Bandwidth | Data transfer | Minimal |

## Cost Tracking

### Real-Time Cost Monitoring

Track costs as they occur:

```bash
# View current day's costs
/admin costs

# Output example:
💰 Cost Summary (Today)
════════════════════════
Total Spent: $12.45 / $50.00 (24.9%)

By Provider:
• OpenAI: $8.30 (GPT-4o, GPT-4o Mini)
• Anthropic: $3.15 (Claude 3 Haiku)
• Groq: $0.00 (Free tier)

By Feature:
• Support Responses: $9.20
• Knowledge Base: $2.10
• Research: $1.15
```

### Detailed Analytics

```bash
# View detailed breakdown
/admin costs period:week

# Export to CSV
/admin costs export format:csv period:month
```

### Cost Tracking Configuration

```bash
# Enable cost tracking
ENABLE_COST_TRACKING=true

# Set daily budget
COST_BUDGET_DAILY=50.00

# Alert threshold (0.0-1.0)
COST_ALERT_THRESHOLD=0.8  # Alert at 80% of budget
```

### Database Schema

Costs are tracked in the database:

```sql
CREATE TABLE cost_analytics (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    provider VARCHAR(50),
    model VARCHAR(100),
    input_tokens INT,
    output_tokens INT,
    cost DECIMAL(10,6),
    feature VARCHAR(50),
    guild_id VARCHAR(20)
);

-- Daily cost aggregation
SELECT 
    DATE(timestamp) as date,
    provider,
    SUM(cost) as daily_cost
FROM cost_analytics
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), provider
ORDER BY date DESC;
```

## Smart Routing

### Routing Strategies

| Strategy | Description | Savings |
|----------|-------------|---------|
| `COST_PRIORITY` | Always cheapest option | Up to 90% |
| `BALANCED` | Balance cost and quality | Up to 70% |
| `QUALITY_PRIORITY` | Best quality, cost secondary | 0-20% |
| `FREE_TIER_MODE` | Prefer free providers | Up to 95% |

### Strategy Configuration

```bash
# Set default strategy
DEFAULT_STRATEGY=cost_priority

# Or configure per guild
/settings strategy cost_priority
```

### Query Complexity Detection

The bot automatically detects query complexity:

```python
complexity_indicators = {
    "simple": {
        "keywords": ["how do i", "what is", "where", "when"],
        "max_length": 50,
        "max_tokens": 100
    },
    "medium": {
        "keywords": ["explain", "compare", "difference"],
        "max_length": 200,
        "max_tokens": 500
    },
    "complex": {
        "keywords": ["analyze", "implement", "troubleshoot", "debug"],
        "max_length": 500,
        "max_tokens": 2000
    }
}

# Route based on complexity
if complexity == "simple":
    model = "llama-3.1-8b-instant"  # Free/cheap
elif complexity == "medium":
    model = "gpt-4o-mini"           # Mid-range
else:
    model = "gpt-4o"                # Premium
```

### Provider Priority by Cost

```python
provider_priority = {
    "ollama": 10,     # Free (local)
    "groq": 9,        # Free tier
    "openrouter": 8,  # Often cheaper
    "openai": 5,      # Moderate
    "anthropic": 4    # Premium
}
```

## Response Caching

### Cache Levels

| Level | TTL | Use Case |
|-------|-----|----------|
| Short | 5 min | Time-sensitive queries |
| Medium | 1 hour | Common questions |
| Long | 24 hours | Static information |
| Permanent | ∞ | FAQ responses |

### Cache Configuration

```bash
# Enable caching
ENABLE_RESPONSE_CACHE=true

# TTL settings
CACHE_TTL_SHORT=300      # 5 minutes
CACHE_TTL_MEDIUM=3600    # 1 hour
CACHE_TTL_LONG=86400     # 24 hours
```

### Cache Key Strategy

```python
def generate_cache_key(query, guild_id):
    """Generate deterministic cache key"""
    # Normalize query
    normalized = query.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Create hash
    key_data = f"{guild_id}:{normalized}"
    return hashlib.sha256(key_data.encode()).hexdigest()
```

### Cache Hit Rate

Monitor cache effectiveness:

```bash
# View cache statistics
/admin cache-stats

# Output:
📊 Cache Statistics
════════════════════
Total Requests: 10,234
Cache Hits: 6,891 (67.3%)
Cache Misses: 3,343 (32.7%)

By TTL:
• Short (5m): 45% hit rate
• Medium (1h): 72% hit rate
• Long (24h): 89% hit rate

Estimated Savings: $145.30
```

## Budget Management

### Daily Budgets

Set maximum daily spending:

```bash
# Daily budget
COST_BUDGET_DAILY=50.00

# Actions when budget exceeded:
# 1. Switch to cheaper models
# 2. Disable non-essential features
# 3. Send alerts to admins
```

### Monthly Budgets

```bash
# Monthly budget
COST_BUDGET_MONTHLY=1000.00

# Progressive restrictions:
# 50% - Warning notification
# 80% - Enable cost priority mode
# 95% - Disable research features
# 100% - Pause AI responses (keywords only)
```

### Budget Alerts

```bash
# Alert configuration
COST_ALERT_THRESHOLD=0.8  # Alert at 80%

# Notification channels:
# - Discord DM to admins
# - Webhook to monitoring
# - Email notification
```

### Budget Monitoring

```python
async def check_budget():
    """Check current spending against budget"""
    daily_spent = await get_daily_cost()
    budget = settings.COST_BUDGET_DAILY
    
    percentage = daily_spent / budget
    
    if percentage >= 1.0:
        await enable_emergency_mode()
    elif percentage >= 0.95:
        await send_alert("Budget 95% exhausted")
        await disable_research()
    elif percentage >= 0.8:
        await send_alert("Budget 80% exhausted")
        await enable_cost_priority()
```

## Provider Optimization

### Free Tier Maximization

```bash
# Configure free providers
GROQ_API_KEY=gsk_...    # 100K tokens/day free
OLLAMA_CLOUD_KEY=       # Self-hosted = free

# Priority settings
FREE_TIER_MODE=true
```

### Provider Fallback Chain

```python
# Define fallback chain
fallback_chain = [
    ("groq", "llama-3.1-8b-instant"),     # Free tier
    ("openrouter", "meta-llama/llama-3"), # Cheap
    ("openai", "gpt-4o-mini"),            # Moderate
    ("anthropic", "claude-3-haiku"),      # Reliable
]

# Try each provider in order
for provider, model in fallback_chain:
    try:
        response = await generate_response(provider, model, query)
        break
    except Exception:
        continue
```

### API Key Rotation

Distribute load across multiple keys:

```python
# Multiple API keys for same provider
openai_keys = [
    "sk-key1",
    "sk-key2",
    "sk-key3"
]

# Round-robin rotation
current_key_index = (current_key_index + 1) % len(openai_keys)
api_key = openai_keys[current_key_index]
```

## Best Practices

### 1. Start with Free Tiers

```bash
# Initial setup
GROQ_API_KEY=gsk_...           # Free tier
OLLAMA_LOCAL=true              # Free local models
DEFAULT_MODEL=llama-3.1-8b-instant

# Add paid providers as backup
OPENAI_API_KEY=sk-...          # Only for complex queries
FALLBACK_MODEL=gpt-4o-mini
```

### 2. Use Smart Routing

```bash
# Enable smart routing
ENABLE_SMART_ROUTING=true
DEFAULT_STRATEGY=balanced

# Configure complexity thresholds
SIMPLE_QUERY_MAX_TOKENS=100
COMPLEX_QUERY_MIN_LENGTH=200
```

### 3. Implement Caching

```bash
# Enable all caching
ENABLE_RESPONSE_CACHE=true
ENABLE_RAG_CACHE=true

# Set appropriate TTLs
CACHE_TTL_SHORT=300
CACHE_TTL_MEDIUM=3600
CACHE_TTL_LONG=86400
```

### 4. Set Budget Limits

```bash
# Conservative limits
COST_BUDGET_DAILY=50.00
COST_BUDGET_MONTHLY=1000.00
COST_ALERT_THRESHOLD=0.7

# Progressive restrictions
ENABLE_BUDGET_ESCALATION=true
```

### 5. Monitor Usage

```bash
# Enable analytics
ENABLE_ANALYTICS=true
ENABLE_COST_TRACKING=true

# Regular reviews
# - Daily: Check spending
# - Weekly: Review cache hit rates
# - Monthly: Analyze cost trends
```

### 6. Optimize Queries

```python
# Pre-process queries to reduce tokens
def optimize_query(query):
    # Remove filler words
    query = remove_stopwords(query)
    
    # Fix typos (reduce repetition)
    query = correct_spelling(query)
    
    # Extract keywords
    keywords = extract_keywords(query)
    
    return keywords
```

### 7. Use Context Efficiently

```python
# Trim context to essentials
def trim_context(context, max_tokens=4000):
    """Keep only relevant context"""
    # Remove old messages
    context = keep_recent(context, hours=24)
    
    # Summarize long conversations
    if count_tokens(context) > max_tokens:
        context = summarize_conversation(context)
    
    return context
```

## Cost Calculator

### Estimation Tool

```python
def estimate_cost(model, input_tokens, output_tokens):
    """Calculate estimated API cost"""
    
    pricing = {
        "gpt-4o": {"input": 5.00, "output": 15.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "llama-3.1-8b": {"input": 0.00, "output": 0.00},  # Free
    }
    
    rate = pricing.get(model, {"input": 5.00, "output": 15.00})
    
    input_cost = (input_tokens / 1_000_000) * rate["input"]
    output_cost = (output_tokens / 1_000_000) * rate["output"]
    
    return input_cost + output_cost

# Example usage
cost = estimate_cost("gpt-4o", 500, 300)  # $0.007
```

### Monthly Estimator

```bash
# Estimate monthly costs based on usage

# Input parameters:
QUERIES_PER_DAY=1000
AVG_INPUT_TOKENS=500
AVG_OUTPUT_TOKENS=300
MODEL=gpt-4o-mini

# Calculation:
DAILY_INPUT=1000 * 500 = 500,000 tokens
DAILY_OUTPUT=1000 * 300 = 300,000 tokens

MONTHLY_INPUT=500,000 * 30 = 15,000,000 tokens
MONTHLY_OUTPUT=300,000 * 30 = 9,000,000 tokens

# GPT-4o Mini pricing:
INPUT_COST=15 * 0.15 = $2.25
OUTPUT_COST=9 * 0.60 = $5.40

TOTAL_MONTHLY=$7.65
```

### Cost Comparison Table

| Setup | Monthly Queries | Est. Cost |
|-------|----------------|-----------|
| Free Only (Groq + Ollama) | 10,000 | $0.00 |
| Budget (GPT-4o Mini) | 10,000 | $7.65 |
| Balanced (GPT-4o + Mini) | 10,000 | $35.00 |
| Premium (GPT-4o) | 10,000 | $120.00 |
| Enterprise (Claude Opus) | 10,000 | $450.00 |

## Emergency Cost Controls

### Automatic Throttling

When budget is exceeded:

```python
async def emergency_throttle():
    """Reduce costs when budget exceeded"""
    
    # 1. Switch to cheapest provider
    settings.DEFAULT_MODEL = "llama-3.1-8b-instant"
    
    # 2. Disable research
    settings.ENABLE_RESEARCH = False
    
    # 3. Increase cache TTL
    settings.CACHE_TTL_SHORT = 3600
    
    # 4. Notify admins
    await notify_admins("Emergency cost controls activated")
```

### Manual Override

```bash
# Emergency mode
/admin emergency-mode on

# Effects:
# - All queries use cheapest provider
# - Research features disabled
# - Maximum caching enabled
# - Admin-only commands remain
```
