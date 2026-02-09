# Knowledge Base

The Knowledge Base feature provides Retrieval-Augmented Generation (RAG) capabilities, allowing the bot to answer questions based on uploaded documents and previous support interactions.

## Table of Contents

- [Overview](#overview)
- [RAG Pipeline](#rag-pipeline)
- [Document Management](#document-management)
- [Search Capabilities](#search-capabilities)
- [Configuration](#configuration)
- [Usage](#usage)
- [Best Practices](#best-practices)

## Overview

The Knowledge Base enables:

1. **Document Storage**: Upload and store documentation
2. **Semantic Search**: Find relevant information using embeddings
3. **Context Injection**: Provide relevant context to AI responses
4. **Multi-Modal Support**: Text, PDF, Markdown, and more
5. **Version Control**: Track document changes

### Benefits

- **Accurate Answers**: Grounded in your documentation
- **Reduced AI Costs**: Faster, more focused responses
- **Consistent Information**: Same answers from same sources
- **Source Citations**: Show users where information comes from

## RAG Pipeline

### Architecture

```
Document Upload
      ↓
Text Extraction
      ↓
Text Chunking
      ↓
Embedding Generation
      ↓
Vector Storage (pgvector)
      ↓
Query → Embedding → Vector Search
      ↓
Context Assembly
      ↓
AI Response with Context
```

### Pipeline Stages

#### 1. Document Ingestion

Upload documents via:
- Discord file upload (`/knowledge_upload`)
- Text input (`/knowledge add`)
- API endpoint
- Bulk import

#### 2. Text Extraction

Extract text from various formats:

| Format | Extension | Handler |
|--------|-----------|---------|
| Plain Text | .txt | Direct |
| Markdown | .md | Markdown parser |
| PDF | .pdf | PyPDF2 |
| Word | .docx | python-docx |
| HTML | .html | BeautifulSoup |
| JSON | .json | JSON parser |
| Code Files | .py, .js, etc. | Syntax-aware |

#### 3. Text Chunking

Split documents into chunks for optimal retrieval:

```python
chunk_config = ChunkConfig(
    chunk_size=1000,      # Characters per chunk
    chunk_overlap=200,    # Overlap between chunks
    separator="\n\n"       # Split on paragraphs
)
```

**Chunking Strategies:**

| Strategy | Use Case |
|----------|----------|
| Fixed Size | General documents |
| Paragraph | Articles, guides |
| Semantic | Technical docs |
| Recursive | Complex structures |

#### 4. Embedding Generation

Convert chunks to vector embeddings:

```python
# Using OpenAI embeddings
embedding_model = "text-embedding-3-small"
embedding_dimension = 1536

# Generate embeddings
embeddings = await embedding_generator.generate_batch(
    texts=chunks,
    model=embedding_model
)
```

**Supported Embedding Providers:**

| Provider | Model | Dimension | Cost |
|----------|-------|-----------|------|
| OpenAI | text-embedding-3-small | 1536 | $0.02/1M tokens |
| OpenAI | text-embedding-3-large | 3072 | $0.13/1M tokens |
| OpenAI | text-embedding-ada-002 | 1536 | $0.10/1M tokens |
| Local | sentence-transformers | 768-1024 | Free |

#### 5. Vector Storage

Store embeddings in PostgreSQL with pgvector:

```sql
CREATE TABLE knowledge_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES knowledge_docs(id),
    chunk_index INT,
    content TEXT,
    token_count INT,
    embedding VECTOR(1536)
);

-- Create index for fast similarity search
CREATE INDEX ON knowledge_chunks 
USING ivfflat (embedding vector_cosine_ops);
```

#### 6. Retrieval

Search for relevant chunks:

```python
# Generate query embedding
query_embedding = await embedding_generator.generate(query)

# Search vector database
results = db.query(KnowledgeChunk).order_by(
    KnowledgeChunk.embedding.cosine_distance(query_embedding)
).limit(top_k).all()
```

### Similarity Metrics

| Metric | Use Case | Range |
|--------|----------|-------|
| Cosine Similarity | General semantic search | -1 to 1 |
| Euclidean Distance | Exact matching | 0 to ∞ |
| Dot Product | Fast approximate search | -∞ to ∞ |

## Document Management

### Uploading Documents

#### Via Discord Command

```bash
# Upload a file
/knowledge_upload file:documentation.pdf title:"API Documentation"

# Add text directly
/knowledge add title:"FAQ" content:"Q: How do I reset my password? A: ..."
```

#### Supported File Types

| Type | Max Size | Notes |
|------|----------|-------|
| .txt | 1 MB | Plain text |
| .md | 1 MB | Markdown |
| .json | 1 MB | Structured data |
| .pdf | 10 MB | Extracts text only |
| .docx | 10 MB | Word documents |
| .py, .js, etc. | 1 MB | Code files |

#### Via API

```bash
curl -X POST http://api.example.com/knowledge/upload \
  -H "Authorization: Bearer $API_TOKEN" \
  -F "file=@documentation.pdf" \
  -F "title=Product Documentation"
```

### Document Metadata

Each document stores:

```python
class KnowledgeDoc:
    id: UUID
    guild_id: int           # Discord server
    title: str              # Document title
    content: str            # Full text (optional)
    doc_type: str           # File type
    created_by: int         # User ID
    created_at: datetime
    updated_at: datetime
    is_active: bool         # Soft delete
    file_size: int          # Size in bytes
    chunk_count: int        # Number of chunks
```

### Document Versioning

Track document changes:

```bash
# Update document creates new version
/knowledge edit document_id:abc-123 content:"Updated content"

# View version history
/knowledge history document_id:abc-123

# Restore previous version
/knowledge restore document_id:abc-123 version:2
```

## Search Capabilities

### Vector Search

Semantic similarity search:

```bash
# Search knowledge base
/knowledge search query:"How do I reset my password?"

# Results:
1. Password Reset Guide (95% match)
   > To reset your password, go to Settings...
   
2. Account Management (87% match)
   > Managing your account settings...
```

### Hybrid Search

Combine keyword and vector search:

```python
# Keyword search (fast, exact)
keyword_results = keyword_search(query)

# Vector search (semantic, fuzzy)
vector_results = vector_search(query_embedding)

# Combine and rerank
final_results = reciprocal_rank_fusion(
    keyword_results, 
    vector_results
)
```

### Search Filters

Filter search results:

```bash
# Search by document type
/knowledge search query:"API" type:technical

# Search by date
/knowledge search query:"billing" after:2024-01-01

# Search by author
/knowledge search query:"feature" author:@admin
```

### Context Assembly

Build context for AI responses:

```python
# Retrieve relevant chunks
chunks = search_knowledge_base(query, top_k=5)

# Filter by similarity threshold
chunks = [c for c in chunks if c.similarity > 0.7]

# Assemble context
context = "\n\n".join([
    f"Source: {chunk.document.title}\n{chunk.content}"
    for chunk in chunks
])

# Generate response with context
response = await ai.complete(
    f"Context: {context}\n\nQuestion: {query}"
)
```

## Configuration

### Environment Variables

```bash
# Vector Database
VECTOR_DB_TYPE=pgvector
VECTOR_DB_URL=postgresql://postgres:pass@localhost:5432/supportbot
VECTOR_DIMENSION=1536

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# RAG Settings
RAG_TOP_K=5                    # Number of chunks to retrieve
RAG_SIMILARITY_THRESHOLD=0.7   # Minimum similarity score
RAG_MAX_TOKENS=2000            # Max tokens in context
ENABLE_RAG_CACHE=true          # Cache search results
RAG_CACHE_TTL=3600             # Cache TTL in seconds

# Document Processing
MAX_DOCUMENT_SIZE_MB=10
SUPPORTED_DOCUMENT_TYPES=pdf,txt,md,docx
DOCUMENT_CHUNK_SIZE=1000
DOCUMENT_CHUNK_OVERLAP=200
```

### RAG Configuration

```python
rag_config = RAGConfig(
    top_k=5,                      # Retrieve top 5 chunks
    max_context_tokens=2000,      # Limit context size
    similarity_threshold=0.7,     # Minimum relevance
    include_metadata=True,        # Include source info
    rerank_results=True,          # Rerank by relevance
    deduplicate=True              # Remove duplicate content
)
```

### Caching

Cache search results for performance:

```python
# Cache configuration
RAG_CACHE_ENABLED=true
RAG_CACHE_TTL=3600  # 1 hour

# Cache key format
cache_key = f"rag:{guild_id}:{hash(query)}"

# Check cache first
result = await redis.get(cache_key)
if result:
    return json.loads(result)

# Search and cache
results = await search(query)
await redis.setex(cache_key, 3600, json.dumps(results))
```

## Usage

### Asking Questions

Users can query the knowledge base:

```bash
# Ask a question
/ask question:"How do I enable two-factor authentication?"

# Response includes:
# - AI-generated answer
# - Source documents
# - Confidence score
# - Related topics
```

### In Forum Threads

Automatic knowledge base lookup:

```python
# User posts in forum
"How do I reset my password?"

# Bot automatically searches KB
results = search_kb("reset password")

# If good match found:
# - Respond with KB answer
# - Include source links

# If no match:
# - Fall back to AI
# - Suggest escalation
```

### Admin Commands

```bash
# List all documents
/knowledge list

# View document
/knowledge view document_id:abc-123

# Remove document
/knowledge remove document_id:abc-123

# Get document statistics
/knowledge stats
```

## Best Practices

### Document Organization

1. **Use Clear Titles**: Make documents easy to identify
2. **Organize by Category**: Use consistent naming conventions
3. **Keep Updated**: Regularly update outdated documents
4. **Remove Duplicates**: Avoid multiple versions of same info

### Content Guidelines

1. **Be Comprehensive**: Include all relevant details
2. **Use Headers**: Structure with clear headings
3. **Add Examples**: Include code samples, screenshots
4. **Link Related**: Reference related documents

### Optimization

1. **Right-Size Chunks**: Balance between too small and too large
2. **Strategic Overlap**: Ensure context isn't lost at chunk boundaries
3. **Quality Over Quantity**: Better to have fewer high-quality docs
4. **Regular Review**: Remove outdated or low-use documents

### Example Workflow

```bash
# 1. Upload documentation
/knowledge_upload file:api-reference.md title:"API Reference"

# 2. Test search
/knowledge search query:"authentication"

# 3. Verify results look good
# Check relevance scores are high

# 4. Monitor usage
/knowledge stats

# 5. Update based on gaps
# Add missing topics users ask about

# 6. Clean up quarterly
/knowledge list
# Remove old versions and unused docs
```

## Troubleshooting

### Search Returns No Results

**Check:**
1. Documents are uploaded and active
2. Embeddings generated successfully
3. Similarity threshold not too high
4. Query is clear and specific

**Debug:**
```python
# Check document count
SELECT COUNT(*) FROM knowledge_docs WHERE is_active = true;

# Check chunk count
SELECT COUNT(*) FROM knowledge_chunks;

# Test embedding generation
curl https://api.openai.com/v1/embeddings \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{"input": "test", "model": "text-embedding-3-small"}'
```

### Slow Search Performance

**Optimization:**
1. Add vector indexes
2. Enable caching
3. Reduce top_k value
4. Filter by guild before search

```sql
-- Create vector index
CREATE INDEX ON knowledge_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Vacuum and analyze
VACUUM ANALYZE knowledge_chunks;
```

### Inaccurate Results

**Improvements:**
1. Adjust similarity threshold
2. Try different embedding model
3. Improve chunking strategy
4. Add more context to documents

### High Embedding Costs

**Cost Reduction:**
1. Use smaller embedding model
2. Use local embeddings (sentence-transformers)
3. Cache embeddings aggressively
4. Batch embedding requests

```python
# Use local embeddings (free)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2
```
