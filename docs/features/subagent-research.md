# Research Subagents

Research Subagents provide advanced research capabilities, including web search, document analysis, comparison tasks, and diagnostic assistance powered by AI.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Usage](#usage)
- [Research Types](#research-types)
- [Best Practices](#best-practices)

## Overview

Research Subagents are autonomous AI agents that:

1. **Search the Web**: Find relevant information from multiple sources
2. **Analyze Documents**: Extract insights from text and data
3. **Compare Options**: Evaluate alternatives based on criteria
4. **Diagnose Issues**: Provide troubleshooting guidance
5. **Summarize Content**: Create concise summaries of long texts

### Use Cases

- **Technical Research**: Find solutions to coding problems
- **Product Comparisons**: Compare tools, services, or approaches
- **Issue Diagnosis**: Troubleshoot errors and problems
- **Documentation**: Research and compile information
- **Sentiment Analysis**: Analyze user feedback or reviews

## Features

### Multi-Source Search

Search across multiple platforms simultaneously:

| Source | Type | Description |
|--------|------|-------------|
| Google | Web | General web search |
| Stack Overflow | Technical | Programming Q&A |
| GitHub | Code | Repositories and issues |
| Documentation | Technical | Official docs |
| Reddit | Community | Discussion forums |
| News | Current | Latest articles |

### Intelligent Analysis

- **Relevance Ranking**: Score results by relevance to query
- **Content Summarization**: Extract key points
- **Sentiment Analysis**: Determine tone and sentiment
- **Entity Extraction**: Identify people, places, technologies
- **Keyword Extraction**: Find important terms

### Parallel Processing

Research tasks run in parallel for speed:

```python
# Execute multiple searches concurrently
results = await asyncio.gather(
    search_google(query),
    search_stackoverflow(query),
    search_github(query),
    search_documentation(query)
)
```

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                  Research Request                       │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│                 Task Decomposition                      │
│  (Break complex queries into sub-tasks)                 │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Parallel Research Workers                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ Web     │ │ Code    │ │ Docs    │ │ Social  │       │
│  │ Search  │ │ Search  │ │ Search  │ │ Search  │       │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │
└───────┼───────────┼───────────┼───────────┼────────────┘
        ↓           ↓           ↓           ↓
┌─────────────────────────────────────────────────────────┐
│              Results Aggregation                        │
│  (Combine, deduplicate, rank results)                   │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Analysis & Synthesis                       │
│  (Extract insights, create summary)                     │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Final Report Generation                    │
└─────────────────────────────────────────────────────────┘
```

### Research Worker System

Research tasks are processed by Celery workers:

```python
# Celery configuration
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Worker startup
celery -A research.tasks worker --loglevel=info --concurrency=4
```

### Task Queue

```python
from research.tasks import research_task

# Queue research task
task = research_task.delay(
    query="Python async best practices",
    depth="detailed",
    user_id="123456"
)

# Check status
task.status  # PENDING, STARTED, SUCCESS, FAILURE

# Get result
result = task.get(timeout=300)  # Wait up to 5 minutes
```

## Configuration

### Environment Variables

```bash
# Research Settings
ENABLE_RESEARCH=true
RESEARCH_MAX_DEPTH=3
RESEARCH_TIMEOUT_SECONDS=300
RESEARCH_RESULTS_LIMIT=20

# Search APIs
SERPAPI_KEY=your_serpapi_key      # Google Search
STACKEXCHANGE_KEY=your_key        # Stack Overflow
GITHUB_TOKEN=ghp_...              # GitHub API
REDDIT_CLIENT_ID=...              # Reddit API
REDDIT_CLIENT_SECRET=...

# Analysis Settings
RESEARCH_ANALYZE_SENTIMENT=true
RESEARCH_EXTRACT_KEYWORDS=true
RESEARCH_SUMMARIZE_RESULTS=true
RESEARCH_RANK_BY_RELEVANCE=true
```

### Rate Limiting

Configure API rate limits:

```python
RESEARCH_RATE_LIMITS = {
    "serpapi": {"requests": 100, "window": 86400},     # 100/day
    "github": {"requests": 5000, "window": 3600},       # 5000/hour
    "stackoverflow": {"requests": 300, "window": 86400} # 300/day
}
```

### Worker Scaling

Scale workers based on demand:

```bash
# Docker Compose - scale workers
docker-compose up -d --scale research-worker=4

# Kubernetes - auto-scale
kubectl autoscale deployment research-worker --min=2 --max=10 --cpu-percent=70
```

## Usage

### Basic Research

```bash
# Simple web search with analysis
/research search query:"Python asyncio best practices"

# Detailed research
/research search query:"React vs Vue 2024" depth:comprehensive
```

### Research Depth Levels

| Level | Duration | Sources | Description |
|-------|----------|---------|-------------|
| Basic | 10-30s | 3-5 | Quick overview |
| Detailed | 30-60s | 5-10 | Thorough research |
| Comprehensive | 1-3m | 10-20 | Deep analysis |

### Comparison Research

```bash
# Compare multiple options
/research compare items:"Docker,Kubernetes,Podman" criteria:"ease-of-use,performance,cost"

# Response includes:
# - Side-by-side comparison table
# - Pros/cons for each option
# - Recommendation based on criteria
```

### Document Analysis

```bash
# Analyze text or URL
/research analyze content:"https://example.com/article" type:summary

# Analysis types:
# - summary: Brief overview
# - sentiment: Tone analysis
# - keywords: Key terms extraction
# - entities: Named entities
```

### Issue Diagnosis

```bash
# Diagnose technical issues
/research diagnose problem:"Database connection timeout" symptoms:"slow queries,connection errors"

# Response includes:
# - Severity assessment
# - Step-by-step troubleshooting
# - Estimated resolution time
# - Escalation recommendations
```

## Research Types

### Web Search Research

Search and analyze web content:

```python
from research.web_search import WebSearch

searcher = WebSearch()
results = await searcher.search(
    query="Discord.py tutorial",
    sources=["google", "stackoverflow", "github"],
    limit=10
)

# Results include:
# - Title and URL
# - Snippet/summary
# - Source platform
# - Relevance score
# - Publication date
```

### Code Research

Find code examples and solutions:

```python
from research.code_search import CodeSearch

searcher = CodeSearch()
results = await searcher.search(
    query="async context manager python",
    languages=["python"],
    min_stars=100
)

# Results include:
# - Code snippets
# - Repository info
# - Usage examples
# - Documentation links
```

### Document Analysis

Analyze uploaded or linked documents:

```python
from research.analyzer import ResearchAnalyzer

analyzer = ResearchAnalyzer()

# Summarize content
summary = analyzer.summarize(
    content=long_document,
    max_length=500
)

# Extract sentiment
sentiment = analyzer.analyze_sentiment(content)

# Extract keywords
keywords = analyzer.extract_keywords(content, top_n=10)

# Extract entities
entities = analyzer.extract_entities(content)
```

### Comparison Analysis

Compare items based on criteria:

```python
# Define comparison
comparison = {
    "items": ["Docker", "Kubernetes", "Podman"],
    "criteria": ["ease_of_use", "scalability", "learning_curve"],
    "context": "For a small team deploying web applications"
}

# Score each item
scores = {}
for item in comparison["items"]:
    scores[item] = {}
    for criterion in comparison["criteria"]:
        scores[item][criterion] = analyzer.score_criterion(
            item, criterion, comparison["context"]
        )

# Generate recommendation
recommendation = generate_recommendation(scores)
```

### Diagnostic Research

Diagnose problems with guided troubleshooting:

```python
from research.analyzer import ResearchAnalyzer

analyzer = ResearchAnalyzer()

diagnosis = analyzer.diagnose_issue(
    problem="Database connection timeout",
    symptoms=["slow queries", "intermittent failures"],
    context={
        "database": "PostgreSQL 14",
        "application": "Django 4.2",
        "traffic": "1000 req/min"
    }
)

# Returns:
# - severity: "high"
# - steps: [step-by-step guide]
# - eta: "30-60 minutes"
# - recommendations: [action items]
```

## Best Practices

### Query Optimization

1. **Be Specific**: Include relevant details
2. **Use Keywords**: Include technical terms
3. **Context Matters**: Provide background information
4. **One Topic**: Focus on single subject per query

### Cost Management

1. **Use Appropriate Depth**: Don't use comprehensive for simple questions
2. **Cache Results**: Enable research caching
3. **Limit Sources**: Only search necessary platforms
4. **Monitor Usage**: Track API costs regularly

### Quality Assurance

1. **Verify Sources**: Check result credibility
2. **Cross-Reference**: Confirm with multiple sources
3. **Update Regularly**: Information becomes outdated
4. **Human Review**: Validate critical research

### Example Workflows

#### Technical Troubleshooting

```bash
# 1. User reports issue
"Getting 500 errors when submitting forms"

# 2. Run diagnostic research
/research diagnose problem:"500 errors on form submission"

# 3. Review results and guide user
# Bot provides troubleshooting steps

# 4. If unresolved, escalate
/escalate
```

#### Feature Comparison

```bash
# 1. User asks for recommendations
"Should we use Redis or Memcached?"

# 2. Run comparison research
/research compare items:"Redis,Memcached" criteria:"performance,features,cost"

# 3. Present findings with recommendation
# Bot provides detailed comparison

# 4. Follow up with specific questions
"What's your use case?"
```

#### Documentation Research

```bash
# 1. Add to knowledge base
/research search query:"API rate limiting best practices" depth:comprehensive

# 2. Review and summarize findings
# Bot compiles information from multiple sources

# 3. Create knowledge base document
/knowledge add title:"Rate Limiting Guide" content:"[compiled research]"

# 4. Now available for future queries
/ask How do I implement rate limiting?
```

## Troubleshooting

### Research Taking Too Long

**Solutions:**
1. Reduce research depth
2. Limit number of sources
3. Check worker status
4. Review rate limits

```bash
# Check worker status
celery -A research.tasks inspect active

# Clear stuck tasks
celery -A research.tasks purge
```

### No Results Found

**Check:**
1. API keys are valid
2. Rate limits not exceeded
3. Query is clear and specific
4. Sources are appropriate

### Poor Quality Results

**Improvements:**
1. Add more context to query
2. Try different keywords
3. Include specific technologies
4. Use comprehensive depth

### High API Costs

**Cost Reduction:**
1. Enable result caching
2. Use local analysis where possible
3. Limit searches per user
4. Use cheaper search APIs

```python
# Enable caching
RESEARCH_CACHE_ENABLED=true
RESEARCH_CACHE_TTL=7200  # 2 hours

# Limit per user
USER_RESEARCH_LIMIT_HOURLY=10
```
