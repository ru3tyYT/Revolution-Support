# Knowledge Base

The Knowledge Base feature provides Retrieval-Augmented Generation (RAG) capabilities, allowing the bot to answer questions based on uploaded documents.

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
2. **Vector Search**: Find relevant information using embeddings
3. **Context Injection**: Provide relevant context to AI responses
4. **Multi-Modal Support**: Text, PDF, Markdown, and more

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

Upload documents via Discord commands:
- `/knowledge_upload` - Upload a file
- `/knowledge add` - Add text directly

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
| Recursive | Complex structures |

#### 4. Embedding Generation

Convert chunks to vector embeddings using OpenAI:

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

Search for relevant chunks using vector similarity:

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

### Document Metadata

Each document stores:

```python
class KnowledgeDoc:
    id: UUID
    guild_id: int           # Discord server
    title: str              # Document title
    content: str            # Full text
    doc_type: str           # File type
    created_by: int         # User ID
    created_at: datetime
    updated_at: datetime
    is_active: bool         # Soft delete
    file_size: int          # Size in bytes
    chunk_count: int        # Number of chunks
```

## Search Capabilities

### Vector Search

Semantic similarity search using pgvector:

```bash
# Search knowledge base
/knowledge search query:"How do I reset my password?"

# Results:
1. Password Reset Guide (95% match)
   > To reset your password, go to Settings...
   
2. Account Management (87% match)
   > Managing your account settings...
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

Configuration is managed in `config/config.yaml`:

```yaml
# Knowledge Base (RAG) Settings
knowledge_base:
  enabled: true
  
  # Vector database settings
  vector_db:
    provider: "pgvector"
    dimension: 1536
    metric: "cosine"
    index_type: "ivfflat"
    lists: 100
  
  # Embedding settings
  embedding:
    provider: "openai"
    model: "text-embedding-3-small"
    dimension: 1536
    batch_size: 100
  
  # Retrieval settings
  retrieval:
    top_k: 5
    similarity_threshold: 0.7
    max_tokens: 2000
  
  # Document processing
  document:
    max_size_mb: 10
    chunk_size: 1000
    chunk_overlap: 200
    supported_types:
      - "pdf"
      - "txt"
      - "md"
      - "docx"
      - "html"
```

### Database Models

The knowledge base uses these database models:

**KnowledgeDoc**: Stores document metadata
- `id`: UUID primary key
- `guild_id`: Discord server reference
- `title`: Document title
- `content`: Full document text
- `doc_type`: File type (text, markdown, pdf, etc.)
- `chunk_count`: Number of chunks created
- `is_active`: Soft delete flag

**KnowledgeChunk**: Stores document chunks with embeddings
- `id`: UUID primary key
- `document_id`: Reference to parent document
- `chunk_index`: Position in document
- `content`: Chunk text content
- `embedding`: 1536-dimensional vector
- `model`: Embedding model used

## Usage

### Asking Questions

Users can query the knowledge base:

```bash
# Ask a question
/knowledge search query:"How do I enable two-factor authentication?"

# Response includes:
# - Relevant document chunks
# - Similarity scores
# - Source document titles
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
# Remove old and unused docs
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
2. Reduce top_k value
3. Filter by guild before search

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
2. Improve chunking strategy
3. Add more context to documents

### High Embedding Costs

**Cost Reduction:**
1. Use smaller embedding model
2. Batch embedding requests
3. Monitor usage with `/knowledge stats`
