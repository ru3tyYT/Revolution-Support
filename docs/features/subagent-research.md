# Research Subagents

Research Subagents provide research capabilities including web search, document analysis, comparison tasks, and diagnostic assistance powered by AI.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Usage](#usage)
- [Research Types](#research-types)
- [Best Practices](#best-practices)

## Overview

Research Subagents are AI agents that:

1. **Search the Web**: Find relevant information from web sources
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

### Web Search

Basic web search integration supporting multiple providers:

| Source | Type | Description |
|--------|------|-------------|
| DuckDuckGo | Web | Default search provider (no API key required) |
| Google | Web | Google Custom Search API (optional) |
| Bing | Web | Bing Search API (optional) |

**Note:** The system performs web searches through a single provider at a time, not multiple simultaneous sources.

### Intelligent Analysis

- **Relevance Ranking**: Score results by relevance to query
- **Content Summarization**: Extract key points
- **Sentiment Analysis**: Determine tone and sentiment
- **Entity Extraction**: Identify people, places, technologies
- **Keyword Extraction**: Find important terms

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                  Research Request                       │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│                 Task Queue (Celery)                     │
│  Queue research tasks for async processing              │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Research Worker                            │
│  Process tasks: web search, comparison, diagnosis       │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Results Processing                         │
│  (Rank, analyze, and format results)                    │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Response Generation                        │
└─────────────────────────────────────────────────────────┘
```

### Research Worker System

Research tasks are processed by Celery workers with Redis backend:

```python
# Celery configuration
REDIS_URL=redis://localhost:6379/0

# Worker startup
celery -A research.tasks worker --loglevel=info --concurrency=4
```

### Task Queue

```python
from research.tasks import web_search, comparison, troubleshooting

# Queue web search task
task = web_search.delay(
    query="Python async best practices",
    provider="auto",
    max_results=10
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
RESEARCH_TIMEOUT_SECONDS=300
RESEARCH_RESULTS_LIMIT=20

# Search APIs (optional - DuckDuckGo works without API keys)
GOOGLE_SEARCH_API_KEY=your_google_api_key
GOOGLE_SEARCH_CX=your_custom_search_engine_id
BING_SEARCH_API_KEY=your_bing_api_key

# Analysis Settings
RESEARCH_ANALYZE_SENTIMENT=true
RESEARCH_EXTRACT_KEYWORDS=true
RESEARCH_SUMMARIZE_RESULTS=true
```

**Note:** Stack Overflow API, GitHub API, and Reddit API integrations are not currently implemented. The system uses web search only.

### Rate Limiting

Basic rate limiting is configured for research tasks:

```python
# Web search: 10 per minute
# API queries: 30 per minute
```

## Usage

### Basic Research

```bash
# Simple web search with analysis
/research query:"Python asyncio best practices"

# Search with specific provider
/research query:"React vs Vue 2024"
```

**Note:** The `depth` parameter (basic/detailed/comprehensive) is not currently implemented.

### Comparison Research

```bash
# Compare multiple options
/research_compare items:"Docker,Kubernetes,Podman" criteria:"ease-of-use,performance,cost"

# Response includes:
# - Side-by-side comparison table
# - Scores for each option
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
# - Similar issues from knowledge base
```

### Task Management

```bash
# Check task status
/research_status task_id:<task_id>

# View task queue
/research_queue

# Cancel a task
/research_cancel task_id:<task_id>
```

## Research Types

### Web Search Research

Search and analyze web content:

```python
from research.web_search import WebSearchProvider

searcher = WebSearchProvider()
results = searcher.search(
    query="Discord.py tutorial",
    provider="auto",  # auto, google, bing, duckduckgo
    max_results=10
)

# Results include:
# - Title and URL
# - Snippet/summary
# - Source platform
# - Relevance score
```

### Document Analysis

Analyze uploaded or linked documents:

```python
from research.tasks import document_analysis

# Queue document analysis
task = document_analysis.delay(
    document_url="https://example.com/article",
    analysis_type="summary"  # summary, sentiment, entities, keywords
)

result = task.get()
```

### Comparison Analysis

Compare items based on criteria:

```python
from research.tasks import comparison

# Define comparison
items = [
    {"name": "Docker", "attributes": {...}},
    {"name": "Kubernetes", "attributes": {...}},
    {"name": "Podman", "attributes": {...}}
]
criteria = ["ease_of_use", "scalability", "learning_curve"]

# Queue comparison
task = comparison.delay(items=items, criteria=criteria, context="For a small team")
result = task.get()

# Returns rankings with scores and recommendation
```

### Diagnostic Research

Diagnose problems with guided troubleshooting:

```python
from research.tasks import troubleshooting

# Queue troubleshooting task
task = troubleshooting.delay(
    problem="Database connection timeout",
    symptoms=["slow queries", "intermittent failures"],
    context={"database": "PostgreSQL 14", "application": "Django 4.2"},
    category="technical"
)

result = task.get()

# Returns:
# - severity: "high"
# - diagnosis: analysis results
# - troubleshooting_steps: [step-by-step guide]
# - similar_issues: [related knowledge base entries]
```

### Database Lookup

Query internal databases for research:

```python
from research.tasks import database_lookup

# Queue database query
task = database_lookup.delay(
    query_type="tickets",  # tickets, users, knowledge, analytics
    filters={"status": "open", "date_from": "2024-01-01"},
    limit=100
)

result = task.get()
```

## Best Practices

### Query Optimization

1. **Be Specific**: Include relevant details
2. **Use Keywords**: Include technical terms
3. **Context Matters**: Provide background information
4. **One Topic**: Focus on single subject per query

### Cost Management

1. **Use Appropriate Provider**: DuckDuckGo requires no API key
2. **Limit Results**: Use `max_results` parameter
3. **Monitor Usage**: Track API costs regularly
4. **Cache Results**: Results expire after 1 hour by default

### Quality Assurance

1. **Verify Sources**: Check result credibility
2. **Cross-Reference**: Confirm with multiple queries
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
/research_compare items:"Redis,Memcached" criteria:"performance,features,cost"

# 3. Present findings with recommendation
# Bot provides detailed comparison

# 4. Follow up with specific questions
"What's your use case?"
```

#### Documentation Research

```bash
# 1. Add to knowledge base
/research query:"API rate limiting best practices"

# 2. Review and summarize findings
# Bot compiles information from web search

# 3. Create knowledge base document
/knowledge add title:"Rate Limiting Guide" content:"[compiled research]"

# 4. Now available for future queries
/ask How do I implement rate limiting?
```

## Troubleshooting

### Research Taking Too Long

**Solutions:**
1. Reduce number of results requested
2. Check worker status
3. Cancel and retry task

```bash
# Check task status
/research_status task_id:<task_id>

# Cancel stuck task
/research_cancel task_id:<task_id>
```

### No Results Found

**Check:**
1. API keys are valid (if using Google/Bing)
2. Query is clear and specific
3. Try different keywords

### Poor Quality Results

**Improvements:**
1. Add more context to query
2. Try different keywords
3. Include specific technologies

### Web Search Unavailable

If search fails, the system will return a fallback message. To enable search:

1. For DuckDuckGo: Install `duckduckgo-search` library
2. For Google: Set `GOOGLE_SEARCH_API_KEY` and `GOOGLE_SEARCH_CX`
3. For Bing: Set `BING_SEARCH_API_KEY`

```bash
pip install duckduckgo-search
```
