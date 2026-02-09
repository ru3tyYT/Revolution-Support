# Smart Keyword Routing

The Smart Keyword Routing system provides fast, cost-effective responses by matching user queries against predefined keywords and responses before falling back to AI generation.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Keyword Categories](#keyword-categories)
- [Creating Keywords](#creating-keywords)
- [Matching Logic](#matching-logic)
- [Response Templates](#response-templates)
- [Analytics](#analytics)
- [Best Practices](#best-practices)

## Overview

Smart Keyword Routing is a hybrid support system that:

1. **Matches keywords** in user messages against a database of common queries
2. **Returns instant responses** when a match is found (zero AI cost)
3. **Falls back to AI** for unmatched queries
4. **Learns from interactions** to improve matching over time

### Benefits

- **Zero cost** for matched queries
- **Instant responses** (no AI latency)
- **Consistent answers** to common questions
- **Reduced AI load** for simple queries

## How It Works

### Routing Flow

```
User Message
    ↓
Keyword Engine Analysis
    ↓
┌─────────────────┐
│  Match Found?   │
└────────┬────────┘
         ↓
    ┌────┴────┐
   YES       NO
    ↓         ↓
Keyword    AI Router
Response    (Fallback)
    ↓         ↓
  Send     Response
  to User  to User
```

### Keyword Processing Pipeline

1. **Preprocessing**
   - Normalize text (lowercase, remove punctuation)
   - Tokenize into words
   - Remove stopwords
   - Stem/lemmatize words

2. **Matching**
   - Exact match
   - Partial match
   - Fuzzy match (typo tolerance)
   - Semantic similarity

3. **Scoring**
   - Calculate confidence scores
   - Rank multiple matches
   - Apply category weights

4. **Response Selection**
   - Select best match
   - Apply response template
   - Format for Discord

## Configuration

### Enable Keyword Routing

```bash
# In .env
ENABLE_KEYWORD_ROUTING=true
USE_KEYWORDS_FIRST=true  # Try keywords before AI
```

### Forum Configuration

```bash
# Per-forum setting
/forum setup channel:#support use_keywords_first:true
```

### Keyword Engine Settings

```bash
# Sensitivity thresholds
KEYWORD_MATCH_THRESHOLD=0.7
KEYWORD_FUZZY_THRESHOLD=0.6

# Response limits
KEYWORD_MAX_RESPONSES_PER_THREAD=5
```

## Keyword Categories

### Built-in Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `FAQ` | Frequently asked questions | Password reset, account issues |
| `TROUBLESHOOTING` | Common problems and fixes | Connection errors, lag |
| `HOWTO` | Step-by-step guides | Installation, configuration |
| `POLICY` | Rules and guidelines | Terms of service, refunds |
| `ESCALATION` | When to escalate | Human support triggers |

### Custom Categories

Create custom categories for your organization:

```python
from keywords.categories import CategoryConfig

# Define custom category
custom_category = CategoryConfig(
    name="PRODUCT_FEATURES",
    description="Questions about product features",
    priority=5,
    auto_escalate=False
)
```

## Creating Keywords

### Via Command

```bash
# Add keyword via Discord command
/keyword add keyword:"password reset" response:"To reset your password..." category:FAQ

# Add with variations
/keyword add keyword:"forgot password" variations:"can't login, password not working" response:"..."
```

### Via Configuration File

Create a `keywords.yaml` file:

```yaml
keywords:
  - term: "password reset"
    category: FAQ
    priority: high
    responses:
      - "To reset your password:"
      - "1. Click 'Forgot Password' on the login page"
      - "2. Enter your email address"
      - "3. Check your inbox for the reset link"
      - "4. Create a new secure password"
    variations:
      - "forgot password"
      - "can't login"
      - "password not working"
      - "reset my password"
    tags:
      - account
      - security

  - term: "api rate limit"
    category: TROUBLESHOOTING
    priority: medium
    responses:
      - "Our API has the following rate limits:"
      - "• Free tier: 100 requests/minute"
      - "• Pro tier: 1000 requests/minute"
      - "• Enterprise: Custom limits"
    related_keywords:
      - "throttling"
      - "429 error"
```

### Via Database

```python
from keywords.engine import KeywordEngine
from database.models import Keyword

engine = KeywordEngine()

# Add keyword
engine.add_keyword(
    term="server status",
    responses=["Check our status page: https://status.example.com"],
    category="TROUBLESHOOTING",
    confidence_threshold=0.8
)
```

## Matching Logic

### Match Types

| Type | Description | Confidence |
|------|-------------|------------|
| Exact | Word-for-word match | 1.0 |
| Partial | Contains keyword phrase | 0.8-0.9 |
| Fuzzy | Similar words (typo-tolerant) | 0.6-0.8 |
| Semantic | Related meaning | 0.5-0.7 |

### Fuzzy Matching

Uses Levenshtein distance for typo tolerance:

```python
# User types: "pasword reset"
# Matches: "password reset" with 0.95 similarity
```

Configuration:

```bash
# Enable fuzzy matching
KEYWORD_FUZZY_ENABLED=true
KEYWORD_FUZZY_THRESHOLD=0.6  # Minimum similarity
```

### Semantic Matching

Uses embeddings to match semantically similar queries:

```python
# User asks: "How do I change my secret code?"
# Matches: "password reset" (semantic similarity: 0.82)
```

Configuration:

```bash
# Enable semantic matching
KEYWORD_SEMANTIC_ENABLED=true
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

### Multi-Keyword Matching

Supports complex queries with multiple keywords:

```python
# Query: "password reset not working"
# Matches:
# - "password reset" (confidence: 0.9)
# - "reset not working" (confidence: 0.7)
# Combines for overall match
```

## Response Templates

### Basic Templates

```yaml
responses:
  - "{{ greeting }}, {{ user_mention }}!"
  - "{{ response_text }}"
  - "If you need more help, type /escalate"
```

### Variables

Available template variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{ user_mention }}` | Mention the user | @username |
| `{{ user_name }}` | User's display name | John Doe |
| `{{ guild_name }}` | Server name | My Server |
| `{{ keyword }}` | Matched keyword | password reset |
| `{{ confidence }}` | Match confidence | 95% |
| `{{ response_text }}` | The response content | See below |

### Conditional Responses

```yaml
responses:
  - condition: "{{ confidence }} > 0.9"
    text: "Here's the solution: {{ response_text }}"
  - condition: "{{ confidence }} < 0.9"
    text: "You might be asking about: {{ response_text }}\n\nDid this help?"
```

### Rich Embeds

```yaml
embed:
  title: "{{ keyword }}"
  description: "{{ response_text }}"
  color: "#00FF00"
  fields:
    - name: "Related Articles"
      value: "{{ related_links }}"
    - name: "Still Need Help?"
      value: "React with ❓ to escalate"
```

## Analytics

### Keyword Performance Metrics

Track keyword effectiveness:

```bash
# View keyword analytics
/stats keywords

# Output:
Keyword Performance (Last 30 Days)
═══════════════════════════════════
password reset
  Uses: 234
  Positive: 198 (84.6%)
  Negative: 12 (5.1%)
  Escalated: 24 (10.3%)
api rate limit
  Uses: 156
  Positive: 142 (91.0%)
  Negative: 8 (5.1%)
  Escalated: 6 (3.8%)
```

### Adding Analytics

```python
from keywords.analytics import KeywordAnalytics

analytics = KeywordAnalytics()

# Track keyword use
analytics.track_use(
    keyword="password reset",
    user_id="123456",
    channel_id="789012",
    confidence=0.92
)

# Track feedback
analytics.track_feedback(
    keyword="password reset",
    helpful=True,
    user_id="123456"
)
```

### Optimization Recommendations

The system provides recommendations:

```
Keyword Optimization Report
═══════════════════════════

High-Performing Keywords:
✓ "api rate limit" - 91% positive rate
✓ "installation guide" - 88% positive rate

Underperforming Keywords:
⚠ "billing issue" - 45% escalation rate
  Suggestion: Add more detailed steps
  Suggestion: Include refund policy link

Missing Keywords (from AI logs):
• "mobile app" - mentioned 47 times
• "two factor authentication" - mentioned 34 times
• "export data" - mentioned 28 times
```

## Best Practices

### Keyword Creation

1. **Start with FAQs**: Begin with your most common questions
2. **Use Natural Language**: Write keywords as users would ask
3. **Include Variations**: Add synonyms and alternate phrasings
4. **Keep It Current**: Update keywords as products change

### Response Writing

1. **Be Concise**: Keep responses under 200 words
2. **Use Formatting**: Bold important steps, use lists
3. **Add Links**: Include links to detailed documentation
4. **Offer Escalation**: Always provide a way to get human help

### Maintenance

1. **Review Regularly**: Check analytics monthly
2. **Remove Unused**: Delete keywords with <5% match rate
3. **Update Responses**: Keep information accurate
4. **Test Changes**: Verify keywords work after updates

### Example Workflow

```bash
# 1. Review AI conversations for common queries
/admin logs

# 2. Identify patterns
# "How do I..." questions appear frequently

# 3. Create keywords for common patterns
/keyword add keyword:"how do I upgrade" category:HOWTO response:"..."

# 4. Test the keyword
/ask how do I upgrade my plan

# 5. Monitor performance
/stats keywords

# 6. Optimize based on feedback
# If escalation rate is high, improve response
/keyword edit keyword:"how do I upgrade" response:"Improved explanation..."
```

## Integration with AI

### Priority Order

```
1. Exact Keyword Match (confidence 1.0)
2. Partial Keyword Match (confidence 0.8+)
3. Fuzzy Keyword Match (confidence 0.6+)
4. Semantic Keyword Match (confidence 0.5+)
5. AI Generation (fallback)
```

### Hybrid Responses

Combine keywords with AI for enhanced responses:

```python
# Keyword provides template
keyword_response = "To reset your password: {steps}"

# AI fills in details
ai_enhanced = await ai.complete(
    f"Fill in these steps: {keyword_response}"
)
```

### Learning Mode

Enable automatic keyword creation from AI conversations:

```bash
# In .env
KEYWORD_LEARNING_MODE=true
KEYWORD_LEARNING_THRESHOLD=3  # Create after 3 similar queries
```

When enabled:
1. Tracks AI responses that get positive feedback
2. Identifies repeated patterns
3. Suggests new keywords
4. Admin approves before adding
