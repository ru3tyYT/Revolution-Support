# Forum Monitoring

The Forum Monitoring feature automatically tracks and responds to threads in Discord forum channels, providing AI-powered support with keyword matching and intelligent routing.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Configuration](#configuration)
- [Auto-Response System](#auto-response-system)
- [Tag Filtering](#tag-filtering)
- [Thread Tracking](#thread-tracking)
- [Analytics](#analytics)
- [Best Practices](#best-practices)

## Overview

Forum Monitoring allows the bot to:

1. **Monitor forum channels** for new threads
2. **Send welcome messages** when threads are created
3. **Respond automatically** to messages using AI or keywords
4. **Track thread metrics** for analytics
5. **Filter by tags** for targeted responses

### Use Cases

- **Support Forums**: Auto-respond to common questions
- **Q&A Channels**: Provide instant answers from knowledge base
- **Bug Reports**: Route to appropriate teams based on tags
- **Feature Requests**: Acknowledge and track suggestions

## Features

### Real-Time Monitoring

- Listens for new thread creation events
- Processes messages in monitored forums
- Responds within configured time limits

### Smart Response System

- **Keyword Priority**: Check keywords first for instant responses
- **AI Fallback**: Use AI when no keyword match found
- **Context Awareness**: Maintains conversation context
- **Rate Limiting**: Prevents spam and abuse

### Thread Lifecycle Management

- Tracks thread from creation to resolution
- Monitors message count and response history
- Identifies resolved threads automatically
- Generates transcripts if enabled

## Configuration

### Basic Setup

Configure a forum for monitoring:

```bash
/forum setup channel:#support-forum
```

### Advanced Configuration

```bash
/forum setup \
    channel:#support-forum \
    auto_respond:true \
    welcome_message:"Welcome! How can we help you today?" \
    ai_model:gpt-4 \
    response_delay:5 \
    max_responses:3
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `channel` | ForumChannel | Required | Forum to monitor |
| `auto_respond` | boolean | true | Enable automatic responses |
| `welcome_message` | string | - | Custom welcome message |
| `ai_model` | string | gpt-4 | AI model for responses |
| `response_delay` | int | 5 | Seconds to wait before responding |
| `max_responses` | int | 3 | Max AI responses per thread |

### Required Bot Permissions

For forum monitoring, the bot needs:

- **View Channel**: See the forum channel
- **Send Messages**: Post responses
- **Read Message History**: Access thread content
- **Create Public Threads**: Participate in threads
- **Embed Links**: Send rich embeds
- **Attach Files**: Upload attachments if needed

### Database Schema

Forum configuration is stored in the `forum_configs` table:

```sql
CREATE TABLE forum_configs (
    id UUID PRIMARY KEY,
    guild_id UUID REFERENCES guilds(id),
    forum_channel_id VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    auto_respond BOOLEAN DEFAULT true,
    max_responses_per_thread INT DEFAULT 5,
    include_tags TEXT[],
    exclude_tags TEXT[],
    welcome_message_template TEXT,
    ai_temperature INT DEFAULT 7,
    use_keywords_first BOOLEAN DEFAULT true,
    threads_created INT DEFAULT 0,
    responses_sent INT DEFAULT 0
);
```

## Auto-Response System

### Response Flow

```
New Thread Created
        ↓
Welcome Message Sent
        ↓
User Posts Message
        ↓
┌─────────────────┐
│ Keyword Match?  │
└────────┬────────┘
         ↓
    ┌────┴────┐
   YES       NO
    ↓         ↓
Keyword    AI Response
Response   Generated
    ↓         ↓
  Send     Send
  to User  to User
        ↓
Update Thread Stats
```

### Welcome Messages

Custom welcome messages support variables:

```
Hello {{ user_mention }}! Welcome to {{ channel_name }}.

I'll do my best to help you with your question. 
Please provide as much detail as possible!
```

**Available Variables:**
- `{{ user_mention }}` - Mention the thread creator
- `{{ user_name }}` - Display name of creator
- `{{ channel_name }}` - Forum channel name
- `{{ guild_name }}` - Server name

### AI Response Configuration

Control AI behavior per forum:

```bash
# Set temperature (0-10, mapped to 0.0-1.0)
# Lower = more focused, Higher = more creative
/forum setup channel:#support ai_temperature:3
```

**Temperature Guidelines:**
- **1-3**: Factual, technical support
- **4-6**: Balanced responses
- **7-10**: Creative, conversational

### Rate Limiting

Prevent spam and control costs:

```bash
# Global settings
GLOBAL_RATE_LIMIT_REQUESTS=100
GLOBAL_RATE_LIMIT_WINDOW=60

# Per-user settings
USER_RATE_LIMIT_REQUESTS=10
USER_RATE_LIMIT_WINDOW=60

# Per-thread settings
max_responses_per_thread=3
```

## Tag Filtering

### Include Tags

Monitor only threads with specific tags:

```bash
# Only monitor threads with "bug" or "urgent" tags
/forum edit include_tags channel:#support tags:bug,urgent

# Monitor all threads (default)
/forum edit include_tags channel:#support
```

### Exclude Tags

Skip threads with certain tags:

```bash
# Skip "off-topic" and "spam" tagged threads
/forum edit exclude_tags channel:#support tags:off-topic,spam
```

### Tag Matching Logic

```python
# Thread passes if:
# - No include_tags specified, OR
# - Thread has at least one include_tags

# AND

# - No exclude_tags specified, OR  
# - Thread has no exclude_tags
```

### Tag Examples

```bash
# Technical support only
/forum setup channel:#support
/forum edit include_tags channel:#support tags:technical

# Exclude spam/off-topic
/forum edit exclude_tags channel:#support tags:spam,off-topic

# Specific product support
/forum setup channel:#product-support
/forum edit include_tags channel:#product-tags tags:product-a,product-b
```

## Thread Tracking

### Thread Metadata

Each thread is tracked with:

```python
class ForumThread:
    thread_id: str          # Discord thread ID
    guild_id: str           # Server ID
    channel_id: str         # Forum channel ID
    owner_id: str           # Thread creator ID
    title: str              # Thread title
    initial_message_id: str # First message ID
    tags: List[str]         # Applied tags
    response_count: int     # AI responses sent
    last_response_at: datetime
    is_resolved: bool
    first_response_time_ms: int
    total_messages: int
```

### Resolution Detection

Automatic resolution detection:

```python
# Thread marked resolved when:
# - User says "thank you", "thanks", "solved", "resolved"
# - Admin marks as resolved
# - Auto-close after inactivity

# Keywords that trigger resolution
RESOLUTION_KEYWORDS = [
    "thank you", "thanks", "solved", "resolved",
    "working", "fixed", "done", "complete"
]
```

### First Response Time

Track support responsiveness:

```sql
-- Average first response time
SELECT AVG(first_response_time_ms) / 1000.0 as avg_seconds
FROM forum_threads
WHERE created_at > NOW() - INTERVAL '30 days';
```

## Analytics

### Forum Statistics

View comprehensive forum stats:

```bash
# Stats for specific forum
/forum stats channel:#support

# Stats for all forums
/forum stats
```

**Metrics Tracked:**
- Total threads created
- AI responses sent
- Resolution rate
- Average first response time
- Active vs closed threads

### Example Output

```
📊 Forum Statistics
═══════════════════
Support Forum (#support)

Total Threads: 234
AI Responses: 189
Resolution Rate: 84.2%

Breakdown:
• Resolved: 197 (84.2%)
• Closed: 28 (12.0%)
• Active: 9 (3.8%)

Performance:
• Avg First Response: 12.4 seconds
• Avg Resolution Time: 2.3 hours
• Escalation Rate: 8.5%
```

### Analytics Dashboard

Enable detailed analytics:

```bash
ENABLE_ANALYTICS=true
ENABLE_ANALYTICS_DASHBOARD=true
```

Access dashboard at:
```
http://your-bot-url:3000/analytics
```

### Exporting Data

Export forum data for analysis:

```bash
# Export to CSV
/admin export forum-stats format:csv period:month

# Export to JSON
/admin export forum-stats format:json period:week
```

## Best Practices

### Forum Setup

1. **Start with One Forum**: Begin with your main support channel
2. **Set Clear Expectations**: Configure welcome messages
3. **Limit Responses**: Set max_responses to prevent spam
4. **Use Tags**: Organize threads with tags for better filtering

### Response Optimization

1. **Fast First Response**: Keep response_delay low (2-5 seconds)
2. **Quality Over Quantity**: Limit AI responses per thread
3. **Monitor Keywords**: Keep keyword system updated
4. **Review Regularly**: Check analytics weekly

### Thread Management

1. **Auto-Close Old Threads**: Configure auto-close after 48 hours
2. **Archive Resolved**: Move resolved threads to archive
3. **Clean Up Spam**: Use exclude_tags to filter noise
4. **Track Metrics**: Monitor first response time

### Example Configurations

#### Standard Support Forum

```bash
/forum setup \
    channel:#support \
    auto_respond:true \
    ai_model:gpt-4 \
    response_delay:3 \
    max_responses:5 \
    welcome_message:"Welcome to Support! Please describe your issue in detail."
```

#### Bug Reports Forum

```bash
/forum setup \
    channel:#bug-reports \
    auto_respond:true \
    ai_model:gpt-4 \
    response_delay:5 \
    max_responses:2 \
    welcome_message:"Thanks for reporting! Please include: 1) Steps to reproduce 2) Expected behavior 3) Actual behavior"

# Only respond to confirmed bugs
/forum edit include_tags channel:#bug-reports tags:confirmed
```

#### Feature Requests Forum

```bash
/forum setup \
    channel:#feature-requests \
    auto_respond:true \
    ai_model:gpt-3.5-turbo \
    response_delay:10 \
    max_responses:1 \
    welcome_message:"Thanks for the suggestion! The team reviews all requests weekly."
```

## Troubleshooting

### Bot Not Responding

**Check:**
1. Bot has required permissions in forum
2. Forum is configured (`/forum status`)
3. Bot is not in maintenance mode
4. Rate limits not exceeded

### Duplicate Responses

**Causes:**
- Multiple bot instances
- Race condition in thread creation

**Solutions:**
```bash
# Check for duplicate configs
/forum list

# Disable and re-enable forum
/forum disable channel:#support
/forum enable channel:#support
```

### High Costs

**Optimization:**
```bash
# Use cheaper AI model
/forum edit ai_model channel:#support model:gpt-3.5-turbo

# Reduce max responses
/forum edit max_responses channel:#support count:2

# Increase response delay
/forum edit response_delay channel:#support seconds:10

# Enable keyword priority
/forum setup channel:#support use_keywords_first:true
```

### False Positives

**When bot responds inappropriately:**

1. **Exclude problematic tags:**
```bash
/forum edit exclude_tags channel:#support tags:off-topic
```

2. **Increase response delay:**
```bash
/forum edit response_delay channel:#support seconds:30
```

3. **Disable auto-respond:**
```bash
/forum edit auto_respond channel:#support enabled:false
```
