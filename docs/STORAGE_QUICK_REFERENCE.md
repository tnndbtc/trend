# Storage Layer - Quick Reference

## 🚀 Quick Start

```bash
# 1. Start services
docker compose up postgres qdrant redis -d

# 2. Verify services
python scripts/verify-storage-services.py

# 3. Install dependencies
pip install -r requirements-storage.txt

# 4. Run tests
pytest tests/test_storage_unit.py -v
```

---

## 📦 Import Examples

```python
# PostgreSQL repositories
from trend_agent.storage import (
    PostgreSQLConnectionPool,
    PostgreSQLTrendRepository,
    PostgreSQLTopicRepository,
    PostgreSQLItemRepository,
)

# Vector database
from trend_agent.storage import QdrantVectorRepository

# Cache
from trend_agent.storage import RedisCacheRepository

# Types
from trend_agent.types import (
    Trend, Topic, ProcessedItem,
    Category, TrendState, SourceType,
    TrendFilter, VectorMatch,
)
```

---

## 🔧 Common Operations

### Save a Trend

```python
trend_id = await trend_repo.save(trend)
```

### Search Trends

```python
filters = TrendFilter(
    category=Category.TECHNOLOGY,
    state=TrendState.VIRAL,
    min_score=80.0,
    limit=10
)
results = await trend_repo.search(filters)
```

### Get Top Trends

```python
top_trends = await trend_repo.get_top_trends(
    limit=10,
    category="Technology"
)
```

### Store Vector

```python
await vector_repo.upsert(
    id="trend_123",
    vector=embedding,  # List[float] of size 1536
    metadata={"category": "Technology"}
)
```

### Search Vectors

```python
results = await vector_repo.search(
    vector=query_embedding,
    limit=10,
    filters={"category": "Technology"},
    min_score=0.7
)
```

### Cache Data

```python
# Simple cache
await cache.set("key", value, ttl_seconds=3600)
data = await cache.get("key")

# Counter
views = await cache.increment("views:trend_123")

# Hash
await cache.set_hash("trend:123", "title", "AI News")
title = await cache.get_hash("trend:123", "title")

# List
await cache.set_with_list("trending", ["AI", "Climate"])
items = await cache.get_list("trending")
```

---

## 🎯 Connection Setup

### PostgreSQL

```python
pool = PostgreSQLConnectionPool(
    host="localhost",
    port=5432,
    database="trends",
    user="trend_user",
    password="trend_password",
)
await pool.connect()

# Use repositories
trend_repo = PostgreSQLTrendRepository(pool.pool)
topic_repo = PostgreSQLTopicRepository(pool.pool)
item_repo = PostgreSQLItemRepository(pool.pool)

# Cleanup
await pool.close()
```

### Qdrant

```python
vector_repo = QdrantVectorRepository(
    host="localhost",
    port=6333,
    collection_name="trend_embeddings",
    vector_size=1536,
)
```

### Redis

```python
cache = RedisCacheRepository(
    host="localhost",
    port=6379,
    db=0,
    default_ttl=3600,
)
await cache.connect()

# Cleanup
await cache.close()
```

---

## 🧪 Testing

### With Mocks (Fast)

```python
from tests.mocks.storage import (
    MockTrendRepository,
    MockVectorRepository,
    MockCacheRepository,
)

trend_repo = MockTrendRepository()
await trend_repo.save(trend)
```

### With Real Databases

```python
# Ensure Docker services are running
from trend_agent.storage import PostgreSQLConnectionPool

pool = PostgreSQLConnectionPool()
await pool.connect()
trend_repo = PostgreSQLTrendRepository(pool.pool)
```

---

## 📊 Database Schema

### Main Tables

- **trends** - Ranked topics with state tracking
- **topics** - Clusters of related items
- **processed_items** - Normalized source data
- **topic_items** - Many-to-many topic↔item
- **plugin_health** - Plugin monitoring
- **pipeline_runs** - Pipeline execution history

### Key Columns

**trends:**
- `id` (UUID), `topic_id` (UUID)
- `rank` (INT), `score` (FLOAT), `state` (ENUM)
- `category` (ENUM), `sources` (ARRAY)
- `total_engagement` (JSONB)
- `first_seen`, `last_updated` (TIMESTAMPTZ)

**topics:**
- `id` (UUID), `title`, `summary`
- `category` (ENUM), `item_count` (INT)
- `keywords` (ARRAY), `language`

**processed_items:**
- `id` (UUID), `source` (ENUM), `source_id`
- `url`, `title`, `title_normalized`
- `metrics` (JSONB), `published_at`

---

## 🔍 Advanced Queries

### Search with Multiple Filters

```python
filters = TrendFilter(
    category=Category.TECHNOLOGY,
    state=TrendState.VIRAL,
    sources=[SourceType.REDDIT, SourceType.HACKERNEWS],
    min_score=80.0,
    language="en",
    date_from=datetime(2024, 1, 1),
    limit=20,
    offset=0
)
results = await trend_repo.search(filters)
```

### Batch Operations

```python
# Save multiple items
item_ids = await item_repo.save_batch(items)

# Upsert multiple vectors
vectors = [
    (id1, embedding1, metadata1),
    (id2, embedding2, metadata2),
]
await vector_repo.upsert_batch(vectors)
```

### Cleanup Old Data

```python
# Delete items older than 30 days
deleted_count = await item_repo.delete_older_than(days=30)
```

---

## 🐛 Troubleshooting

### Check Service Status

```bash
docker ps | grep -E "(postgres|qdrant|redis)"
docker logs trend-postgres
docker logs trend-qdrant
docker logs trend-redis
```

### Test Connections

```bash
# PostgreSQL
docker exec -it trend-postgres psql -U trend_user -d trends -c "SELECT version();"

# Qdrant
curl http://localhost:6333/collections

# Redis
docker exec -it trend-redis redis-cli ping
```

### Reset Database

```bash
# Drop and recreate
docker exec -it trend-postgres psql -U trend_user -d postgres -c "DROP DATABASE trends;"
docker exec -it trend-postgres psql -U trend_user -d postgres -c "CREATE DATABASE trends;"
docker exec -i trend-postgres psql -U trend_user -d trends < scripts/init-db.sql
```

---

## 📈 Performance Tips

1. **Use connection pooling** - Reuse database connections
2. **Batch operations** - Insert multiple records at once
3. **Set appropriate TTLs** - Prevent cache bloat
4. **Create payload indexes** - For frequently filtered metadata
5. **Use EXPLAIN ANALYZE** - Optimize slow queries

---

## 🔗 Related Files

- Full documentation: `docs/SESSION_1_STORAGE_LAYER.md`
- Schema: `trend_agent/storage/schema.sql`
- Repositories: `trend_agent/storage/postgres.py`, `qdrant.py`, `redis.py`
- Tests: `tests/test_storage_*.py`
- Health check: `scripts/verify-storage-services.py`

---

## 💡 Tips

- Use `TrendFilter` for complex searches instead of manual SQL
- Store embeddings in Qdrant, metadata in PostgreSQL
- Cache frequently accessed data in Redis
- Use JSONB for flexible metadata without schema changes
- Leverage PostgreSQL triggers for automatic timestamp updates
- Test with mocks first, then integration tests with real DBs
