# Research Subagent System

A Celery-based async research system for the Discord support bot.

## Features

- **Web Search**: Multi-provider search (Google, Bing, DuckDuckGo)
- **API Queries**: External API integration
- **Database Lookup**: Deep database queries with filters
- **Document Analysis**: Summarization, sentiment, entity extraction
- **Comparison**: Compare options based on criteria
- **Troubleshooting**: Automated issue diagnosis

## Architecture

```
Discord Bot → Celery Tasks → Redis Queue → Celery Workers
     ↓              ↓              ↓              ↓
  Commands    Async Tasks    Task Queue     Execution
```

## Setup

### 1. Install Dependencies

```bash
pip install -r research/requirements.txt
```

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_BACKEND_URL=redis://localhost:6379/0

# Search API Keys (optional)
GOOGLE_SEARCH_API_KEY=your_google_api_key
GOOGLE_SEARCH_CX=your_custom_search_engine_id
BING_SEARCH_API_KEY=your_bing_api_key
```

### 3. Start Redis

```bash
redis-server
```

### 4. Start Celery Worker

```bash
cd discord-support-bot

celery -A research worker --loglevel=info
```

For production with multiple workers:

```bash
celery -A research worker --loglevel=info --concurrency=4
```

## Discord Commands

### Basic Research

```
/research <query> [task_type]
```

Triggers a research task. Task types:
- `web_search` - Search the web
- `database_lookup` - Query internal database
- `troubleshooting` - Diagnose issues

### Check Status

```
/research_status <task_id>
```

Check the progress of a running task.

### View Queue

```
/reearch_queue
```

View current queue status and your active tasks.

### Cancel Task

```
/research_cancel <task_id>
```

Cancel a pending or running task.

### Compare Options

```
/research_compare items:<item1,item2,item3> [criteria:<price,features>]
```

Compare multiple items based on specified criteria.

## Task Types

### Web Search (`web_search`)

```python
from research.tasks import web_search

task = web_search.delay(
    query="Python async programming",
    provider="auto",  # auto, google, bing, duckduckgo
    max_results=10,
    filters={"site": "stackoverflow.com"}
)
```

### API Query (`api_query`)

```python
from research.tasks import api_query

task = api_query.delay(
    endpoint="https://api.example.com/data",
    method="GET",
    params={"limit": 100},
    headers={"Authorization": "Bearer token"}
)
```

### Database Lookup (`database_lookup`)

```python
from research.tasks import database_lookup

task = database_lookup.delay(
    query_type="tickets",  # tickets, users, knowledge, analytics
    filters={"status": "open", "date_from": "2024-01-01"},
    limit=100
)
```

### Document Analysis (`document_analysis`)

```python
from research.tasks import document_analysis

task = document_analysis.delay(
    content="Long document text...",
    analysis_type="summary"  # summary, sentiment, entities, keywords
)
```

### Comparison (`comparison`)

```python
from research.tasks import comparison

task = comparison.delay(
    items=[
        {"name": "Option A", "attributes": {"price": 100, "quality": 0.8}},
        {"name": "Option B", "attributes": {"price": 150, "quality": 0.9}},
    ],
    criteria=["price", "quality"]
)
```

### Troubleshooting (`troubleshooting`)

```python
from research.tasks import troubleshooting

task = troubleshooting.delay(
    problem="Bot not responding",
    symptoms=["no messages", "commands timeout"],
    context={"uptime": "2 hours", "error_logs": "Connection timeout"},
    category="technical"
)
```

## Worker Configuration

### Basic Worker

```bash
celery -A research worker -l info
```

### Production Worker

```bash
celery -A research worker \
    --loglevel=info \
    --concurrency=4 \
    --prefetch-multiplier=1 \
    --max-tasks-per-child=50
```

### Multiple Queues

```bash
# Web search queue
celery -A research worker -Q research -n web_search_worker@%h

# Database queue
celery -A research worker -Q database -n db_worker@%h
```

### Monitoring

```bash
# Flower dashboard
celery -A research flower --port=5555

# View queue
celery -A research inspect active
celery -A research inspect scheduled
celery -A research inspect reserved
```

## API Reference

### Worker Functions

- `get_task_result(task_id)` - Get task result by ID
- `revoke_task(task_id, terminate=False)` - Cancel a task
- `get_queue_status()` - Get queue statistics

### Analyzer Methods

- `rank_search_results(query, results)` - Rank search results
- `summarize(content, max_length)` - Summarize text
- `analyze_sentiment(content)` - Sentiment analysis
- `extract_entities(content)` - Named entity extraction
- `extract_keywords(content, top_n)` - Keyword extraction
- `score_criterion(item, criterion, context)` - Score comparison criteria
- `diagnose_issue(problem, symptoms, context)` - Issue diagnosis

## Monitoring Tasks

Tasks automatically report progress:

```python
# In a task
from research.worker import update_progress

update_progress(self, current=50, total=100, message="Processing...")
```

Progress is available via:

```python
result = get_task_result(task_id)
if result["status"] == "PROGRESS":
    percent = result["result"]["percent"]
    message = result["result"]["message"]
```

## Error Handling

Tasks automatically retry on failure:

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def my_task(self, ...):
    try:
        # Task logic
        pass
    except Exception as exc:
        raise self.retry(exc=exc)
```

## License

MIT
