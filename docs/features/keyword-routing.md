# Smart Keyword Routing

The Smart Keyword Routing system provides fast, cost-effective responses by matching user queries against predefined keywords and responses before falling back to AI generation.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Keyword Categories](#keyword-categories)
- [Keyword Management](#keyword-management)
- [Matching Logic](#matching-logic)
- [Analytics](#analytics)
- [Best Practices](#best-practices)

## Overview

Smart Keyword Routing is a hybrid support system that:

1. **Matches keywords** in user messages against a database of common queries
2. **Returns instant responses** when a match is found (zero AI cost)
3. **Falls back to AI** for unmatched queries
4. **Tracks analytics** to monitor keyword performance

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
   - Normalize text (lowercase)
   - Tokenize into words

2. **Matching**
   - Exact match
   - Regex pattern match
   - Fuzzy match (typo tolerance)

3. **Scoring**
   - Calculate confidence scores
   - Sort by priority (higher = more important)

4. **Response Selection**
   - Group matches by category
   - Create Discord embeds
   - Send response to user

## Keyword Categories

The system uses predefined categories to organize keywords:

| Category | Description | Emoji |
|----------|-------------|-------|
| `FAQ` | Frequently asked questions | ❓ |
| `TECHNICAL` | Technical issues and configuration | ⚙️ |
| `BILLING` | Billing and subscription questions | 💳 |
| `TROUBLESHOOTING` | Problem diagnosis and solutions | 🔧 |
| `SUPPORT` | Support requests and help | 🆘 |
| `GENERAL` | General questions and information | 💬 |

### Category Priority

Categories are ordered by priority (lower number = higher priority):

1. FAQ
2. BILLING
3. TECHNICAL
4. TROUBLESHOOTING
5. SUPPORT
6. GENERAL

## Keyword Management

Keywords are stored in the database via the `Keyword` and `KeywordEmbedding` models. There is no YAML configuration file or admin commands for keyword management - keywords must be added directly to the database.

### Database Schema

**Keyword Table:**
- `id`: UUID primary key
- `guild_id`: Guild this keyword belongs to
- `pattern`: The keyword/pattern to match (max 500 chars)
- `category`: Category name (e.g., "faq", "technical")
- `response_template`: The response text
- `match_type`: "exact", "contains", "regex", or "semantic"
- `priority`: Integer priority (higher = more important)
- `is_active`: Whether the keyword is active
- `metadata`: JSON metadata
- `tags`: Array of string tags

**KeywordEmbedding Table:**
- Stores 1536-dimensional vector embeddings for semantic matching
- Uses pgvector for efficient similarity search

### Programmatic Keyword Management

```python
from keywords.engine import KeywordEngine
from database.models import Keyword
from keywords.categories import Category

# Initialize the engine
engine = KeywordEngine()

# Add a keyword programmatically
match = engine.add_keyword(
    keyword="password reset",
    response="To reset your password:\n1. Click 'Forgot Password' on the login page\n2. Enter your email address\n3. Check your inbox for the reset link",
    category=Category.FAQ,
    match_type="exact",
    priority=10
)

# Add multiple keywords at once
keywords = [
    {
        "keyword": "api rate limit",
        "response": "Our API rate limits:\n• Free tier: 100 requests/minute\n• Pro tier: 1000 requests/minute",
        "category": Category.TECHNICAL,
        "match_type": "contains",
        "priority": 5
    },
    {
        "keyword": "^how do I (upgrade|downgrade)",
        "response": "Plan changes can be made in your account settings under Billing.",
        "category": Category.BILLING,
        "match_type": "regex",
        "priority": 8
    }
]
engine.add_keywords_batch(keywords)

# Remove a keyword
engine.remove_keyword("password reset", match_type="exact")

# Export all keywords
keywords_data = engine.export_keywords()

# Import keywords
engine.import_keywords(keywords_data)
```

### Engine Configuration

```python
from keywords.engine import KeywordEngine

engine = KeywordEngine(
    fuzzy_threshold=0.8,      # Minimum similarity for fuzzy matches
    max_fuzzy_matches=3,      # Max fuzzy matches to return
    enable_analytics=True     # Enable cost analytics tracking
)
```

## Matching Logic

### Match Types

| Type | Description | Confidence |
|------|-------------|------------|
| Exact | Word-for-word match | 1.0 |
| Contains | Keyword phrase found in message | 1.0 |
| Regex | Pattern match | 0.95 |
| Fuzzy | Similar words (typo-tolerant) | 0.6-1.0 |

### Fuzzy Matching

Uses Levenshtein distance for typo tolerance:

```python
# User types: "pasword reset"
# Matches: "password reset" with 0.95 similarity
```

Configuration:

```python
engine = KeywordEngine(fuzzy_threshold=0.8)
```

### Processing Messages

```python
from keywords.engine import KeywordEngine

engine = KeywordEngine()

# Process a user message
result = engine.process_message(
    message="How do I reset my password?",
    include_intent=True  # Also classify intent
)

# Result contains:
# - matches: List of KeywordMatch objects
# - categories: List of matched categories
# - embeds: List of Discord embeds ready to send
# - processing_time_ms: Processing time
# - intent_classification: Intent classification (if enabled)
```

### MatchResult Structure

```python
@dataclass
class MatchResult:
    message: str                    # Original message
    matches: List[KeywordMatch]     # All matches found
    categories: List[Category]      # Categories with matches
    embeds: List[discord.Embed]     # Generated embeds
    processing_time_ms: float       # Processing time
    total_matches: int              # Number of matches
    intent_classification: Optional[IntentClassification]
```

## Analytics

### Cost Analytics

The keyword engine includes analytics tracking via the `CostAnalytics` class:

```python
from keywords.analytics import CostAnalytics

analytics = CostAnalytics(storage_path="analytics_data.json")
```

**Note:** Analytics exist in the codebase but there is no admin command (`/stats keywords`) to view them. Analytics data is stored in a JSON file and can be accessed programmatically.

### Available Analytics Methods

```python
from keywords.engine import KeywordEngine

engine = KeywordEngine(enable_analytics=True)

# Get engine stats
stats = engine.get_stats()
# Returns:
# {
#     "total_keywords": 150,
#     "exact_keywords": 100,
#     "regex_patterns": 30,
#     "fuzzy_keywords": 20,
#     "categories": {"faq": 45, "technical": 30, ...},
#     "analytics": {...},
#     "cost_summary": {...}
# }

# Access analytics directly
analytics = engine.analytics

# Get top keywords
analytics.get_top_keywords(limit=10)

# Get top categories
analytics.get_top_categories(limit=10)

# Get cost summary
analytics.get_cost_summary()

# Generate report
report = analytics.generate_report(days=7)
```

### Analytics Data Tracked

- **Message Processing**: Total messages, response times
- **Keyword Matches**: Count per keyword, match types
- **Category Matches**: Count per category
- **Cost Metrics**: Estimated costs for different operations
- **Daily Statistics**: Aggregated daily stats

## Best Practices

### Keyword Creation

1. **Start with FAQs**: Begin with your most common questions
2. **Use Natural Language**: Write keywords as users would ask
3. **Include Variations**: Use regex patterns or fuzzy matching for alternate phrasings
4. **Set Priorities**: Higher priority for critical/common keywords
5. **Keep It Current**: Update keywords as products change

### Response Writing

1. **Be Concise**: Keep responses under 200 words
2. **Use Formatting**: Use Discord markdown (bold, lists, code blocks)
3. **Add Links**: Include links to detailed documentation
4. **Offer Escalation**: Always provide a way to get human help

### Match Type Selection

- **Exact**: Use for specific phrases (e.g., "password reset")
- **Contains**: Use for keywords that appear anywhere (e.g., "api key")
- **Regex**: Use for patterns (e.g., "^how do I (upgrade|downgrade)")
- **Fuzzy**: Use for typo-prone terms (e.g., common misspellings)

### Maintenance

1. **Monitor Match Rates**: Check analytics to see which keywords are used
2. **Review Unused**: Consider removing keywords with very low match rates
3. **Update Responses**: Keep information accurate and up-to-date
4. **Test Changes**: Verify keywords work after updates

### Example Workflow

```python
# 1. Review support conversations for common queries
#    Look for patterns in what users ask

# 2. Identify high-frequency questions
#    "How do I..." questions that appear frequently

# 3. Create keywords for common patterns
from keywords.engine import KeywordEngine
from keywords.categories import Category

engine = KeywordEngine()

engine.add_keyword(
    keyword="how do I upgrade",
    response="To upgrade your plan:\n1. Go to Account Settings\n2. Click 'Billing'\n3. Select your new plan\n4. Confirm payment",
    category=Category.BILLING,
    match_type="contains",
    priority=8
)

# 4. Test the keyword
result = engine.process_message("how do I upgrade my plan?")
print(f"Found {result.total_matches} matches")

# 5. Monitor performance via analytics
stats = engine.get_stats()
print(f"Total keywords: {stats['total_keywords']}")

# 6. Optimize based on data
# If certain keywords never match, review or remove them
unused = engine.analytics.get_unused_keywords(days=30)
```

## Integration with AI

### Priority Order

```
1. Exact/Contains Match (confidence 1.0)
2. Regex Match (confidence 0.95)
3. Fuzzy Match (confidence 0.6+)
4. AI Generation (fallback)
```

### Hook System

The engine supports pre and post-match hooks:

```python
# Add pre-match hook
def before_match(message: str):
    print(f"Processing: {message}")

engine.add_pre_match_hook(before_match)

# Add post-match hook
def after_match(message: str, matches: List[KeywordMatch]):
    print(f"Found {len(matches)} matches for: {message}")

engine.add_post_match_hook(after_match)
```
