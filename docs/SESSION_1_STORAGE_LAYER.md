# Session 1: Storage Layer - Implementation Guide

## Overview

This document describes the implementation of the storage layer for the Trend Intelligence Platform, completed as part of Session 1 from the parallel development guide.

## What Was Implemented

### 1. Database Schema (`trend_agent/storage/schema.sql`)

A comprehensive PostgreSQL schema with:

- **Tables:**
  - `trends` - Ranked, analyzed topics with state tracking
  - `topics` - Clusters of related content items
  - `processed_items` - Normalized items from data sources
  - `topic_items` - Many-to-many relationship between topics and items
  - `plugin_health` - Health monitoring for data collection plugins
  - `pipeline_runs` - Execution history of processing pipelines

- **Features:**
  - Custom ENUM types for trend states, sources, categories, and processing status
  - Automatic timestamp updates via triggers
  - Automatic item count tracking for topics
  - Full-text search support with GIN indexes
  - JSONB fields for flexible metadata storage
  - Utility functions for data cleanup and querying
  - Materialized views for common queries

### 2. PostgreSQL Repositories (`trend_agent/storage/postgres.py`)

Three repository implementations:

- **PostgreSQLTrendRepository** - Manages trend data
  - CRUD operations with UUID support
  - Advanced search with filters (category, state, date range, etc.)
  - Top trends retrieval with pagination
  - Transaction support via asyncpg

- **PostgreSQLTopicRepository** - Manages topic data
  - Topic clustering and categorization
  - Keyword-based search
  - Language filtering

- **PostgreSQLItemRepository** - Manages processed items
  - Batch insert support for performance
  - Source deduplication (unique constraint on source + source_id)
  - Time-based cleanup for old items
  - Efficient existence checks

- **PostgreSQLConnectionPool** - Connection management
  - Async connection pooling
  - Automatic reconnection
  - Connection health monitoring

### 3. Qdrant Vector Repository (`trend_agent/storage/qdrant.py`)

**QdrantVectorRepository** - Vector similarity search:

- High-dimensional embedding storage (default: 1536 dimensions for OpenAI)
- Cosine, Euclidean, and Dot product distance metrics
- Metadata filtering during search
- Batch upsert for performance
- Collection management (create, delete, index)
- Scroll API for bulk operations
- Payload indexing for fast metadata filtering

### 4. Redis Cache Repository (`trend_agent/storage/redis.py`)

**RedisCacheRepository** - High-performance caching:

- Simple key-value operations with TTL
- Hash operations for structured data
- List operations (push, pop, range queries)
- Counter operations (increment, decrement)
- Pattern-based key matching and deletion
- Automatic serialization (JSON for simple types, pickle for complex objects)
- Connection pooling with automatic reconnection

### 5. Database Initialization (`scripts/init-db.sql`)

Complete initialization script that:
- Creates the database and user (if needed)
- Installs required PostgreSQL extensions (uuid-ossp, pgcrypto)
- Defines all custom types and tables
- Sets up indexes, triggers, and views
- Creates utility functions
- Grants appropriate permissions

### 6. Tests

**Unit Tests** (`tests/test_storage_unit.py`):
- Uses mock implementations for fast testing
- Tests all repository methods
- Covers edge cases and error conditions
- No database required

**Integration Tests** (`tests/test_storage_integration.py`):
- Tests against real databases
- Verifies PostgreSQL, Qdrant, and Redis connectivity
- Tests full CRUD lifecycle
- Tests cross-repository integration
- Requires running Docker services

### 7. Utilities

**Service Verification Script** (`scripts/verify-storage-services.py`):
- Checks PostgreSQL connection and schema initialization
- Checks Qdrant availability
- Checks Redis connectivity
- Provides colored output with clear status indicators
- Exit codes for CI/CD integration

---

## Architecture

```
trend_agent/storage/
├── __init__.py              # Package exports
├── interfaces.py            # Protocol definitions (contracts)
├── schema.sql              # PostgreSQL schema
├── postgres.py             # PostgreSQL implementations
├── qdrant.py               # Qdrant vector database
└── redis.py                # Redis cache

scripts/
├── init-db.sql             # Database initialization
└── verify-storage-services.py  # Health check script

tests/
├── test_storage_unit.py         # Unit tests (with mocks)
└── test_storage_integration.py  # Integration tests (real DBs)
```

---

## Getting Started

### Prerequisites

1. **Docker** installed and running
2. **Python 3.10+** with pip
3. **PostgreSQL client** (optional, for manual testing)

### Step 1: Install Dependencies

```bash
pip install -r requirements-storage.txt
```

This installs:
- `asyncpg` - PostgreSQL async driver
- `qdrant-client` - Qdrant vector database client
- `redis[hiredis]` - Redis async client with performance optimizations
- `pytest` and `pytest-asyncio` - Testing frameworks

### Step 2: Start Docker Services

```bash
# Start all storage services
docker compose up postgres qdrant redis -d

# Check status
docker compose ps
```

**Expected services:**
- `trend-postgres` on port 5432
- `trend-qdrant` on ports 6333 (HTTP) and 6334 (gRPC)
- `trend-redis` on port 6379

**Note:** If you see port conflicts, you can:
1. Stop conflicting services: `docker stop <container-name>`
2. Or modify `docker-compose.yml` to use different ports

### Step 3: Initialize Database

The database is automatically initialized via `docker-entrypoint-initdb.d` when PostgreSQL first starts.

To manually initialize or reset:

```bash
# Connect to PostgreSQL
docker exec -it trend-postgres psql -U trend_user -d trends

# Or initialize from file
docker exec -i trend-postgres psql -U trend_user -d trends < scripts/init-db.sql
```

### Step 4: Verify Services

```bash
python scripts/verify-storage-services.py
```

**Expected output:**
```
======================================================================
Storage Services Health Check
======================================================================

Checking database connections...

✓ OK                 PostgreSQL           PostgreSQL connected: PostgreSQL 16.x
✓ OK                 PostgreSQL Schema    Schema initialized: trends, topics, processed_items
✓ OK                 Qdrant              Qdrant connected: 0 collections
✓ OK                 Redis               Redis connected: version 7.x

======================================================================
All checks passed! (4/4)
Storage layer is ready for use.
======================================================================
```

---

## Usage Examples

### PostgreSQL Repositories

```python
import asyncio
from trend_agent.storage import (
    PostgreSQLConnectionPool,
    PostgreSQLTrendRepository,
    PostgreSQLTopicRepository,
)
from trend_agent.types import Trend, Topic, Category, TrendState, Metrics
from datetime import datetime
from uuid import uuid4

async def main():
    # Create connection pool
    pool = PostgreSQLConnectionPool(
        host="localhost",
        port=5432,
        database="trends",
        user="trend_user",
        password="trend_password",
    )
    await pool.connect()

    # Create repositories
    trend_repo = PostgreSQLTrendRepository(pool.pool)
    topic_repo = PostgreSQLTopicRepository(pool.pool)

    # Create and save a topic
    topic = Topic(
        id=uuid4(),
        title="AI Breakthrough in 2024",
        summary="Major advances in artificial intelligence",
        category=Category.TECHNOLOGY,
        sources=[],
        item_count=5,
        total_engagement=Metrics(upvotes=100, comments=20, score=120.0),
        first_seen=datetime.utcnow(),
        last_updated=datetime.utcnow(),
    )
    topic_id = await topic_repo.save(topic)
    print(f"Saved topic: {topic_id}")

    # Create and save a trend
    trend = Trend(
        id=uuid4(),
        topic_id=topic_id,
        rank=1,
        title="AI Breakthrough in 2024",
        summary="Major advances in artificial intelligence",
        category=Category.TECHNOLOGY,
        state=TrendState.EMERGING,
        score=95.5,
        sources=[],
        item_count=5,
        total_engagement=Metrics(upvotes=100, comments=20, score=120.0),
        first_seen=datetime.utcnow(),
        last_updated=datetime.utcnow(),
    )
    trend_id = await trend_repo.save(trend)
    print(f"Saved trend: {trend_id}")

    # Search trends
    from trend_agent.types import TrendFilter
    filters = TrendFilter(category=Category.TECHNOLOGY, limit=10)
    results = await trend_repo.search(filters)
    print(f"Found {len(results)} technology trends")

    # Cleanup
    await pool.close()

asyncio.run(main())
```

### Vector Repository

```python
import asyncio
from trend_agent.storage import QdrantVectorRepository

async def main():
    # Create vector repository
    vector_repo = QdrantVectorRepository(
        host="localhost",
        port=6333,
        collection_name="trend_embeddings",
        vector_size=1536,  # OpenAI embedding size
    )

    # Upsert a vector
    embedding = [0.1] * 1536  # Replace with actual embedding
    metadata = {
        "trend_id": "123e4567-e89b-12d3-a456-426614174000",
        "category": "Technology",
        "language": "en",
    }

    await vector_repo.upsert(
        id="trend_123",
        vector=embedding,
        metadata=metadata,
    )
    print("Vector saved!")

    # Search for similar vectors
    query_vector = [0.1] * 1536
    results = await vector_repo.search(
        vector=query_vector,
        limit=10,
        filters={"category": "Technology"},
        min_score=0.7,
    )

    for match in results:
        print(f"Match: {match.id}, Score: {match.score:.3f}")

asyncio.run(main())
```

### Cache Repository

```python
import asyncio
from trend_agent.storage import RedisCacheRepository

async def main():
    # Create cache repository
    cache = RedisCacheRepository(
        host="localhost",
        port=6379,
        default_ttl=3600,  # 1 hour
    )
    await cache.connect()

    # Simple cache operations
    await cache.set("trending:today", ["AI", "Climate", "Sports"], ttl_seconds=1800)
    trends = await cache.get("trending:today")
    print(f"Today's trends: {trends}")

    # Counter operations
    await cache.increment("views:trend_123", amount=1)
    views = await cache.get("views:trend_123")
    print(f"Views: {views}")

    # Hash operations (for structured data)
    await cache.set_hash("trend:123", "title", "AI Breakthrough")
    await cache.set_hash("trend:123", "score", 95.5)

    title = await cache.get_hash("trend:123", "title")
    print(f"Trend title: {title}")

    # Cleanup
    await cache.close()

asyncio.run(main())
```

---

## Running Tests

### Unit Tests (No Database Required)

```bash
pytest tests/test_storage_unit.py -v
```

These tests use mock implementations and run instantly.

### Integration Tests (Requires Running Services)

```bash
# Ensure services are running
python scripts/verify-storage-services.py

# Run integration tests
pytest tests/test_storage_integration.py -v
```

**Note:** Integration tests may take longer as they interact with real databases.

### Run All Tests

```bash
pytest tests/test_storage*.py -v
```

---

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trends
POSTGRES_USER=trend_user
POSTGRES_PASSWORD=trend_password

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Optional
```

### Connection Pool Settings

```python
from trend_agent.storage import PostgreSQLConnectionPool

pool = PostgreSQLConnectionPool(
    host="localhost",
    port=5432,
    database="trends",
    user="trend_user",
    password="trend_password",
    min_size=10,   # Minimum connections in pool
    max_size=20,   # Maximum connections in pool
)
```

---

## Performance Considerations

### PostgreSQL

1. **Indexes:** All critical fields are indexed (category, language, timestamps, keywords)
2. **JSONB:** Metadata stored as JSONB with GIN indexes for fast queries
3. **Connection Pooling:** Reuses connections for better performance
4. **Batch Inserts:** Use `save_batch()` for multiple items

### Qdrant

1. **Batch Upserts:** Use `upsert_batch()` for inserting multiple vectors
2. **Payload Indexes:** Create indexes on frequently filtered metadata fields
3. **Distance Metrics:** Choose appropriate metric (Cosine for semantic similarity)

### Redis

1. **TTL:** Set appropriate TTL to avoid memory bloat
2. **Pipelining:** Use Redis pipelines for multiple operations
3. **Serialization:** Simple types use JSON, complex objects use pickle
4. **Connection Pooling:** Async connection pool for concurrency

---

## Troubleshooting

### PostgreSQL Connection Fails

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check logs
docker logs trend-postgres

# Test connection
docker exec -it trend-postgres psql -U trend_user -d trends -c "SELECT version();"
```

### Qdrant Connection Fails

```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check logs
docker logs trend-qdrant

# Test via HTTP
curl http://localhost:6333/collections
```

### Redis Connection Fails

```bash
# Check if Redis is running
docker ps | grep redis

# Check logs
docker logs trend-redis

# Test connection
docker exec -it trend-redis redis-cli ping
```

### Schema Not Initialized

```bash
# Re-run initialization
docker exec -i trend-postgres psql -U trend_user -d trends < scripts/init-db.sql
```

---

## Next Steps

Now that the storage layer is complete, other sessions can:

1. **Session 2 (Ingestion):** Use `ItemRepository` to save collected data
2. **Session 3 (Processing):** Use `TopicRepository` and `TrendRepository` to save analyzed data
3. **Session 4 (API):** Query repositories to serve API requests
4. **Session 5 (Tasks):** Use repositories in Celery tasks
5. **Session 6 (Observability):** Monitor repository performance

---

## Success Criteria ✅

- [x] PostgreSQL schema created with all tables, indexes, and triggers
- [x] TrendRepository implemented with full CRUD operations
- [x] TopicRepository implemented with search and keyword filtering
- [x] ItemRepository implemented with batch operations
- [x] VectorRepository (Qdrant) implemented with similarity search
- [x] CacheRepository (Redis) implemented with various data structures
- [x] Integration tests passing with real databases
- [x] Unit tests passing with mocks
- [x] Docker services configured and running
- [x] Health check script created and working
- [x] Documentation complete

---

## Files Created

```
trend_agent/storage/
├── schema.sql              ✅ PostgreSQL schema
├── postgres.py             ✅ PostgreSQL repositories
├── qdrant.py               ✅ Qdrant vector repository
└── redis.py                ✅ Redis cache repository

scripts/
├── init-db.sql             ✅ Database initialization
└── verify-storage-services.py  ✅ Health check script

tests/
├── test_storage_unit.py         ✅ Unit tests
└── test_storage_integration.py  ✅ Integration tests

docs/
└── SESSION_1_STORAGE_LAYER.md   ✅ This document

requirements-storage.txt    ✅ Dependencies
```

---

## Contributors

- **Session 1:** Storage Layer Implementation
- **Claude Code:** AI-assisted development

---

## License

Part of the Trend Intelligence Platform project.
