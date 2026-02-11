# AI Services Documentation

## Overview

The Trend Intelligence Platform now includes production-ready AI services for embeddings, LLM operations, and semantic search. This document explains how to configure, use, and integrate these services.

## 📋 Table of Contents

- [Architecture](#architecture)
- [Available Services](#available-services)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Service Factory](#service-factory)
- [Integration](#integration)
- [Cost Tracking](#cost-tracking)
- [Error Handling](#error-handling)
- [Testing](#testing)

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Application Layer                      │
│  (Orchestrator, Celery Tasks, API Endpoints)              │
└─────────────────────┬────────────────────────────────────┘
                      │
                      │ Uses
                      ▼
┌──────────────────────────────────────────────────────────┐
│                    ServiceFactory                         │
│  (Centralized service creation and lifecycle mgmt)        │
└───┬─────────────┬────────────────┬───────────────────────┘
    │             │                │
    │ Creates     │ Creates        │ Creates
    ▼             ▼                ▼
┌──────────┐  ┌──────────┐  ┌────────────────────────┐
│Embedding │  │   LLM    │  │   Semantic Search      │
│ Service  │  │ Service  │  │      Service           │
└──────────┘  └──────────┘  └────────────────────────┘
    │             │                │
    │ OpenAI      │ OpenAI         │ Qdrant + OpenAI
    │             │ Anthropic      │
    ▼             ▼                ▼
┌──────────┐  ┌──────────┐  ┌────────────────────────┐
│  OpenAI  │  │  OpenAI  │  │  Qdrant Vector DB      │
│   API    │  │  Claude  │  │  + Trend Repository    │
└──────────┘  └──────────┘  └────────────────────────┘
```

---

## Available Services

### 1. Embedding Services

**OpenAIEmbeddingService** - Generate vector embeddings for text

- **Models**:
  - `text-embedding-3-small` (1536 dim, $0.00002/1k tokens) - Default
  - `text-embedding-3-large` (3072 dim, $0.00013/1k tokens)
  - `text-embedding-ada-002` (1536 dim, $0.0001/1k tokens)

- **Features**:
  - Automatic batch processing
  - Retry logic with exponential backoff
  - Cost tracking per request
  - Prometheus metrics integration

### 2. LLM Services

**OpenAILLMService** - GPT-powered text generation and analysis

- **Models**:
  - `gpt-4-turbo` (128k context, $0.01/$0.03 per 1k in/out) - Default
  - `gpt-4` (8k context, $0.03/$0.06 per 1k in/out)
  - `gpt-3.5-turbo` (16k context, $0.0005/$0.0015 per 1k in/out)

- **Capabilities**:
  - Text summarization (concise, detailed, bullet points)
  - Key point extraction
  - Trend analysis with JSON output
  - Tag generation
  - Topic summarization

**AnthropicLLMService** - Claude-powered text generation and analysis

- **Models**:
  - `claude-3-sonnet` (200k context, $3/$15 per 1M in/out) - Default
  - `claude-3-opus` (200k context, $15/$75 per 1M in/out)
  - `claude-3-haiku` (200k context, $0.25/$1.25 per 1M in/out)

- Same capabilities as OpenAI service

### 3. Search Services

**QdrantSemanticSearchService** - Vector-based semantic search

- **Features**:
  - Natural language queries
  - Similarity-based trend discovery
  - Metadata filtering (category, language, state, etc.)
  - Find similar trends by ID
  - Direct embedding search

---

## Configuration

### Environment Variables

```bash
# OpenAI Configuration
export OPENAI_API_KEY="sk-..."
export OPENAI_EMBEDDING_MODEL="text-embedding-3-small"  # Optional
export OPENAI_LLM_MODEL="gpt-4-turbo"                   # Optional

# Anthropic Configuration
export ANTHROPIC_API_KEY="sk-ant-..."
export ANTHROPIC_MODEL="claude-3-sonnet"                # Optional

# Qdrant Configuration
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"
export QDRANT_COLLECTION="trend_embeddings"
export QDRANT_API_KEY=""                                # Optional (for Qdrant Cloud)

# PostgreSQL Configuration
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="trends"
export POSTGRES_USER="trend_user"
export POSTGRES_PASSWORD="trend_password"

# Service Selection
export USE_REAL_AI_SERVICES="true"                      # Use real services vs mocks
export LLM_PROVIDER="openai"                            # "openai" or "anthropic"
```

### Docker Compose

Add to your `.env` file:

```env
# AI Services
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
USE_REAL_AI_SERVICES=true
LLM_PROVIDER=openai
```

---

## Usage Examples

### Direct Service Usage

```python
from trend_agent.services import (
    OpenAIEmbeddingService,
    OpenAILLMService,
    AnthropicLLMService,
    QdrantSemanticSearchService,
)

# 1. Embedding Service
async def generate_embeddings():
    async with OpenAIEmbeddingService() as embedding_service:
        # Single embedding
        embedding = await embedding_service.embed("AI trends in 2024")
        print(f"Embedding dimension: {len(embedding)}")

        # Batch embeddings
        texts = ["Machine learning", "Cloud computing", "Quantum computing"]
        embeddings = await embedding_service.embed_batch(texts)
        print(f"Generated {len(embeddings)} embeddings")

        # Get usage stats
        stats = embedding_service.get_usage_stats()
        print(f"Total cost: ${stats['total_cost_usd']:.6f}")

# 2. LLM Service - OpenAI
async def use_openai_llm():
    async with OpenAILLMService() as llm:
        # Summarize text
        text = "Long article about AI trends..."
        summary = await llm.summarize(text, max_length=200, style="concise")

        # Extract key points
        points = await llm.extract_key_points(text, max_points=5)

        # Generate tags
        tags = await llm.generate_tags(text, max_tags=10)

        # Analyze trend
        analysis = await llm.analyze_trend(trend_object)
        print(f"Sentiment: {analysis['sentiment']}")

# 3. LLM Service - Anthropic Claude
async def use_anthropic_llm():
    async with AnthropicLLMService(model="claude-3-opus") as llm:
        # Same interface as OpenAI
        summary = await llm.summarize(text, style="detailed")
        tags = await llm.generate_tags(text)

# 4. Semantic Search
async def search_trends():
    from trend_agent.services import ServiceFactory
    from trend_agent.types import SemanticSearchRequest, TrendFilter

    factory = ServiceFactory()
    search_service = factory.get_search_service()

    # Natural language search
    request = SemanticSearchRequest(
        query="latest developments in quantum computing",
        limit=10,
        min_similarity=0.75,
    )
    trends = await search_service.search(request)

    # Find similar trends
    similar = await search_service.search_similar(
        trend_id="123e4567-e89b-12d3-a456-426614174000",
        limit=5,
        min_similarity=0.7,
    )

    await factory.close()
```

---

## Service Factory

The `ServiceFactory` provides centralized service instantiation with dependency injection.

### Basic Usage

```python
from trend_agent.services import ServiceFactory

# Create factory
factory = ServiceFactory()

# Get services
embedding_service = factory.get_embedding_service()
llm_service = factory.get_llm_service(provider="openai")
search_service = factory.get_search_service()

# Services are cached (singleton pattern)
same_embedding_service = factory.get_embedding_service()
assert embedding_service is same_embedding_service

# Cleanup
await factory.close()
```

### Context Manager

```python
from trend_agent.services import ServiceFactory

async with ServiceFactory() as factory:
    embedding_service = factory.get_embedding_service()
    result = await embedding_service.embed("Hello world")
    # Automatic cleanup when exiting context
```

### Global Factory

```python
from trend_agent.services import get_service_factory, close_global_factory

# Get singleton factory
factory = get_service_factory()
llm = factory.get_llm_service()

# Use throughout application
result = await llm.generate("Explain AI")

# Cleanup at application shutdown
await close_global_factory()
```

### Configuration Override

```python
# Custom configuration
config = {
    "openai_api_key": "sk-custom-key",
    "openai_llm_model": "gpt-3.5-turbo",
    "anthropic_api_key": "sk-ant-custom",
    "qdrant_host": "qdrant.example.com",
    "qdrant_port": 6333,
}

factory = ServiceFactory(config=config)
```

---

## Integration

### Orchestrator Integration

The orchestrator automatically uses the ServiceFactory when `use_real_ai_services=True`:

```python
from trend_agent.orchestrator import TrendIntelligenceOrchestrator

# Use real AI services
orchestrator = TrendIntelligenceOrchestrator(
    use_real_ai_services=True,
    llm_provider="openai"  # or "anthropic"
)

await orchestrator.connect()
await orchestrator.run_full_pipeline()
await orchestrator.disconnect()
```

### Celery Task Integration

Celery tasks check the `USE_REAL_AI_SERVICES` environment variable:

```bash
# Enable real services in .env
USE_REAL_AI_SERVICES=true
LLM_PROVIDER=anthropic

# Run Celery worker
celery -A trend_agent.tasks worker --loglevel=info
```

Tasks will automatically use:
- Real OpenAI/Anthropic services if `USE_REAL_AI_SERVICES=true`
- Mock services if `USE_REAL_AI_SERVICES=false` (default for testing)

### API Endpoint Integration

```python
from fastapi import APIRouter, Depends
from trend_agent.services import get_service_factory, ServiceFactory

router = APIRouter()

async def get_factory() -> ServiceFactory:
    """Dependency for getting service factory."""
    return get_service_factory()

@router.post("/analyze")
async def analyze_text(
    text: str,
    factory: ServiceFactory = Depends(get_factory)
):
    llm = factory.get_llm_service()
    analysis = await llm.analyze_trend(text)
    return analysis

@router.post("/search")
async def semantic_search(
    query: str,
    factory: ServiceFactory = Depends(get_factory)
):
    search = factory.get_search_service()
    results = await search.search(
        SemanticSearchRequest(query=query, limit=20)
    )
    return results
```

---

## Cost Tracking

All AI services track usage and costs automatically.

### Per-Request Costs

```python
from trend_agent.services import OpenAIEmbeddingService, OpenAILLMService

# Embeddings
async with OpenAIEmbeddingService() as embed:
    embedding = await embed.embed("test")
    stats = embed.get_usage_stats()
    print(f"Total tokens: {stats['total_tokens']}")
    print(f"Total cost: ${stats['total_cost_usd']:.6f}")

# LLM
async with OpenAILLMService() as llm:
    result = await llm.generate("Explain AI")
    stats = llm.get_usage_stats()
    print(f"Input tokens: {stats['total_input_tokens']}")
    print(f"Output tokens: {stats['total_output_tokens']}")
    print(f"Total cost: ${stats['total_cost_usd']:.4f}")
```

### Prometheus Metrics

All services expose metrics via Prometheus:

```
# API request counts
api_request_total{method="POST",endpoint="openai_embeddings",status_code="200"} 150

# API request durations
api_request_duration_seconds{method="POST",endpoint="openai_llm"} 1.234

# Custom metrics in application logs
```

View metrics at `http://localhost:8000/metrics` (FastAPI) or `http://localhost:9091/metrics` (Celery worker).

---

## Error Handling

All services implement robust error handling with automatic retries.

### Retry Logic

- **Max Retries**: 3 attempts by default
- **Backoff**: Exponential (2^attempt seconds)
- **Retry Conditions**:
  - Network errors
  - Timeout errors
  - Rate limit errors (429)
  - Server errors (5xx)

### Exception Types

```python
from trend_agent.intelligence.interfaces import (
    EmbeddingError,
    LLMError,
    SearchError,
)

# Catch service-specific errors
try:
    embedding = await embedding_service.embed("test")
except EmbeddingError as e:
    logger.error(f"Embedding failed: {e}")

try:
    summary = await llm_service.summarize(text)
except LLMError as e:
    logger.error(f"LLM failed: {e}")

try:
    results = await search_service.search(request)
except SearchError as e:
    logger.error(f"Search failed: {e}")
```

### Timeout Configuration

```python
# Custom timeouts
embedding_service = OpenAIEmbeddingService(timeout=60)  # 60 seconds
llm_service = OpenAILLMService(timeout=120)  # 2 minutes
```

---

## Testing

### Using Mock Services

For testing, use mock services instead of real API calls:

```python
from tests.mocks.intelligence import MockEmbeddingService, MockLLMService

# Mock services return deterministic results
embedding_service = MockEmbeddingService()
llm_service = MockLLMService()

# Use in tests
embedding = await embedding_service.embed("test")
assert len(embedding) == 1536  # Always returns 1536-dim vector

summary = await llm_service.summarize("text")
assert "This is a test summary" in summary  # Deterministic output
```

### Integration Testing

Test with real services using environment variables:

```bash
# Set API keys for testing
export OPENAI_API_KEY="sk-test-..."
export USE_REAL_AI_SERVICES=true

# Run tests
pytest tests/integration/test_ai_services.py
```

### Service Factory Testing

```python
import pytest
from trend_agent.services import ServiceFactory

@pytest.fixture
async def factory():
    """Fixture for service factory."""
    factory = ServiceFactory(config={
        "openai_api_key": "sk-test-..."
    })
    yield factory
    await factory.close()

async def test_embedding_service(factory):
    embedding_service = factory.get_embedding_service()
    result = await embedding_service.embed("test")
    assert len(result) == 1536

async def test_llm_service(factory):
    llm = factory.get_llm_service(provider="openai")
    summary = await llm.summarize("Long text here", style="concise")
    assert isinstance(summary, str)
    assert len(summary) > 0
```

---

## Best Practices

### 1. Use Context Managers

Always use async context managers to ensure proper resource cleanup:

```python
# ✅ Good
async with OpenAIEmbeddingService() as service:
    result = await service.embed("text")

# ❌ Bad (may leak resources)
service = OpenAIEmbeddingService()
result = await service.embed("text")
# Missing cleanup!
```

### 2. Batch Operations

Use batch methods when processing multiple items:

```python
# ✅ Good - Single API call
texts = ["text1", "text2", "text3"]
embeddings = await service.embed_batch(texts)

# ❌ Bad - Multiple API calls
embeddings = []
for text in texts:
    embeddings.append(await service.embed(text))
```

### 3. Error Handling

Always handle service errors gracefully:

```python
from trend_agent.intelligence.interfaces import LLMError

try:
    result = await llm.generate(prompt)
except LLMError as e:
    logger.error(f"LLM generation failed: {e}")
    # Fallback logic
    result = "Default response"
```

### 4. Monitor Costs

Track usage regularly to avoid surprises:

```python
# Log costs periodically
stats = service.get_usage_stats()
if stats['total_cost_usd'] > 10.0:
    logger.warning(f"High API costs: ${stats['total_cost_usd']:.2f}")
```

### 5. Use Service Factory

Use the factory pattern for dependency injection:

```python
# ✅ Good - Easy to test and configure
factory = ServiceFactory()
llm = factory.get_llm_service()

# ❌ Bad - Hard to test and configure
llm = OpenAILLMService(api_key="sk-...")
```

---

## Troubleshooting

### API Key Issues

```
Error: OpenAI API key required
```

**Solution**: Set the `OPENAI_API_KEY` environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

### Rate Limiting

```
Error: Rate limit exceeded (429)
```

**Solution**: The service automatically retries with backoff. For persistent issues:
- Upgrade your API plan
- Reduce batch sizes
- Add delays between requests

### Timeout Errors

```
Error: Request timeout after 30 seconds
```

**Solution**: Increase timeout:

```python
service = OpenAILLMService(timeout=120)  # 2 minutes
```

### Cost Concerns

**Monitor usage**:

```python
stats = service.get_usage_stats()
print(f"Cost so far: ${stats['total_cost_usd']:.4f}")
```

**Use cheaper models**:

```python
# Use GPT-3.5-turbo instead of GPT-4
llm = OpenAILLMService(model="gpt-3.5-turbo")

# Use Claude Haiku instead of Opus
llm = AnthropicLLMService(model="claude-3-haiku")
```

---

## Migration Guide

### From Mock to Real Services

**1. Update Orchestrator**:

```python
# Before
orchestrator = TrendIntelligenceOrchestrator()  # Uses mocks

# After
orchestrator = TrendIntelligenceOrchestrator(
    use_real_ai_services=True,
    llm_provider="openai"
)
```

**2. Update Environment Variables**:

```bash
# .env file
USE_REAL_AI_SERVICES=true
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**3. Update Celery Configuration**:

```bash
# docker-compose.yml - add to celery-worker service
environment:
  - USE_REAL_AI_SERVICES=true
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

**4. Test Integration**:

```bash
# Run with real services
USE_REAL_AI_SERVICES=true python -m trend_agent.orchestrator
```

---

## Summary

✅ **Completed**: Production-ready AI services are now integrated
✅ **Services**: Embeddings (OpenAI), LLM (OpenAI + Anthropic), Search (Qdrant)
✅ **Factory Pattern**: Centralized service creation and configuration
✅ **Integration**: Orchestrator and Celery tasks updated
✅ **Monitoring**: Prometheus metrics and cost tracking
✅ **Testing**: Mock services for testing, real services for production

**Next Steps**: See [Translation Services](./TRANSLATION.md) for multi-language support.
