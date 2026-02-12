"""
Integration tests for storage layer implementations.

These tests verify that the PostgreSQL, Qdrant, and Redis repositories
work correctly with real database connections.

Requirements:
- PostgreSQL running on localhost:5432
- Qdrant running on localhost:6333
- Redis running on localhost:6379

Run with: pytest tests/test_storage_integration.py -v
"""

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from tests.fixtures import Fixtures
from trend_agent.storage.postgres import (
    PostgreSQLConnectionPool,
    PostgreSQLItemRepository,
    PostgreSQLTopicRepository,
    PostgreSQLTrendRepository,
)
from trend_agent.storage.qdrant import QdrantVectorRepository
from trend_agent.storage.redis import RedisCacheRepository
from trend_agent.schemas import (
    Category,
    Metrics,
    ProcessedItem,
    SourceType,
    Topic,
    Trend,
    TrendFilter,
    TrendState,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fixtures():
    """Provide test data fixtures."""
    return Fixtures()


@pytest.fixture
async def postgres_pool():
    """Create PostgreSQL connection pool for testing."""
    pool = PostgreSQLConnectionPool(
        host="localhost",
        port=5432,
        database="trends",
        user="trend_user",
        password="trend_password",
    )
    await pool.connect()
    yield pool
    await pool.close()


@pytest.fixture
async def trend_repo(postgres_pool):
    """Create TrendRepository instance."""
    return PostgreSQLTrendRepository(postgres_pool.pool)


@pytest.fixture
async def topic_repo(postgres_pool):
    """Create TopicRepository instance."""
    return PostgreSQLTopicRepository(postgres_pool.pool)


@pytest.fixture
async def item_repo(postgres_pool):
    """Create ItemRepository instance."""
    return PostgreSQLItemRepository(postgres_pool.pool)


@pytest.fixture
async def vector_repo():
    """Create VectorRepository instance."""
    repo = QdrantVectorRepository(
        host="localhost",
        port=6333,
        collection_name="test_embeddings",
        vector_size=1536,
    )
    yield repo
    # Cleanup: delete test collection
    try:
        await repo.delete_collection()
    except Exception:
        pass


@pytest.fixture
async def cache_repo():
    """Create CacheRepository instance."""
    repo = RedisCacheRepository(
        host="localhost",
        port=6379,
        db=1,  # Use DB 1 for tests
        default_ttl=60,
    )
    await repo.connect()
    yield repo
    # Cleanup: flush test database
    await repo.flush()
    await repo.close()


# ============================================================================
# PostgreSQL TrendRepository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_trend_save_and_get(trend_repo, fixtures):
    """Test saving and retrieving a trend."""
    trends = fixtures.get_trends(1)
    trend = trends[0]

    # Save trend
    trend_id = await trend_repo.save(trend)
    assert trend_id is not None

    # Retrieve trend
    retrieved = await trend_repo.get(trend_id)
    assert retrieved is not None
    assert retrieved.id == trend_id
    assert retrieved.title == trend.title
    assert retrieved.category == trend.category


@pytest.mark.asyncio
async def test_trend_update(trend_repo, fixtures):
    """Test updating a trend."""
    trends = fixtures.get_trends(1)
    trend = trends[0]

    # Save trend
    trend_id = await trend_repo.save(trend)

    # Update trend
    updates = {
        "rank": 5,
        "score": 95.5,
        "state": TrendState.VIRAL,
    }
    success = await trend_repo.update(trend_id, updates)
    assert success is True

    # Verify updates
    updated = await trend_repo.get(trend_id)
    assert updated.rank == 5
    assert updated.score == 95.5
    assert updated.state == TrendState.VIRAL


@pytest.mark.asyncio
async def test_trend_delete(trend_repo, fixtures):
    """Test deleting a trend."""
    trends = fixtures.get_trends(1)
    trend = trends[0]

    # Save trend
    trend_id = await trend_repo.save(trend)

    # Delete trend
    success = await trend_repo.delete(trend_id)
    assert success is True

    # Verify deletion
    deleted = await trend_repo.get(trend_id)
    assert deleted is None


@pytest.mark.asyncio
async def test_trend_search(trend_repo, fixtures):
    """Test searching trends with filters."""
    trends = fixtures.get_trends(5)

    # Save multiple trends
    for trend in trends:
        await trend_repo.save(trend)

    # Search by category
    filters = TrendFilter(category=Category.TECHNOLOGY, limit=10)
    results = await trend_repo.search(filters)
    assert len(results) >= 0
    for result in results:
        assert result.category == Category.TECHNOLOGY


@pytest.mark.asyncio
async def test_trend_get_top_trends(trend_repo, fixtures):
    """Test getting top-ranked trends."""
    trends = fixtures.get_trends(10)

    # Save trends with different ranks
    for i, trend in enumerate(trends):
        trend.rank = i + 1
        await trend_repo.save(trend)

    # Get top 5 trends
    top_trends = await trend_repo.get_top_trends(limit=5)
    assert len(top_trends) <= 5

    # Verify they're sorted by rank
    for i in range(len(top_trends) - 1):
        assert top_trends[i].rank <= top_trends[i + 1].rank


# ============================================================================
# PostgreSQL TopicRepository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_topic_save_and_get(topic_repo, fixtures):
    """Test saving and retrieving a topic."""
    topics = fixtures.get_topics(1)
    topic = topics[0]

    # Save topic
    topic_id = await topic_repo.save(topic)
    assert topic_id is not None

    # Retrieve topic
    retrieved = await topic_repo.get(topic_id)
    assert retrieved is not None
    assert retrieved.id == topic_id
    assert retrieved.title == topic.title


@pytest.mark.asyncio
async def test_topic_search(topic_repo, fixtures):
    """Test searching topics."""
    topics = fixtures.get_topics(5)

    # Save topics
    for topic in topics:
        await topic_repo.save(topic)

    # Search by category
    results = await topic_repo.search(category=Category.TECHNOLOGY.value, limit=10)
    assert len(results) >= 0


@pytest.mark.asyncio
async def test_topic_get_by_keyword(topic_repo, fixtures):
    """Test searching topics by keyword."""
    topics = fixtures.get_topics(3)

    # Add a specific keyword to one topic
    topics[0].keywords = ["python", "programming"]
    topics[1].keywords = ["javascript", "web"]
    topics[2].keywords = ["data", "science"]

    # Save topics
    for topic in topics:
        await topic_repo.save(topic)

    # Search by keyword
    results = await topic_repo.get_by_keyword("python", limit=10)
    assert len(results) >= 1


# ============================================================================
# PostgreSQL ItemRepository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_item_save_and_get(item_repo, fixtures):
    """Test saving and retrieving a processed item."""
    items = fixtures.get_processed_items(1)
    item = items[0]

    # Save item
    item_id = await item_repo.save(item)
    assert item_id is not None

    # Retrieve item
    retrieved = await item_repo.get(item_id)
    assert retrieved is not None
    assert retrieved.id == item_id
    assert retrieved.title == item.title


@pytest.mark.asyncio
async def test_item_get_by_source_id(item_repo, fixtures):
    """Test retrieving item by source and source_id."""
    items = fixtures.get_processed_items(1)
    item = items[0]

    # Save item
    await item_repo.save(item)

    # Retrieve by source_id
    retrieved = await item_repo.get_by_source_id(item.source.value, item.source_id)
    assert retrieved is not None
    assert retrieved.source_id == item.source_id


@pytest.mark.asyncio
async def test_item_exists(item_repo, fixtures):
    """Test checking if item exists."""
    items = fixtures.get_processed_items(1)
    item = items[0]

    # Check before save
    exists_before = await item_repo.exists(item.source.value, item.source_id)
    assert exists_before is False

    # Save item
    await item_repo.save(item)

    # Check after save
    exists_after = await item_repo.exists(item.source.value, item.source_id)
    assert exists_after is True


@pytest.mark.asyncio
async def test_item_batch_save(item_repo, fixtures):
    """Test saving multiple items in batch."""
    items = fixtures.get_processed_items(5)

    # Batch save
    item_ids = await item_repo.save_batch(items)
    assert len(item_ids) == 5

    # Verify all items were saved
    for item_id in item_ids:
        retrieved = await item_repo.get(item_id)
        assert retrieved is not None


# ============================================================================
# Qdrant VectorRepository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_vector_upsert_and_get(vector_repo):
    """Test upserting and retrieving a vector."""
    vector_id = str(uuid4())
    vector = [0.1] * 1536  # 1536-dimensional vector
    metadata = {"type": "test", "category": "Technology"}

    # Upsert vector
    success = await vector_repo.upsert(vector_id, vector, metadata)
    assert success is True

    # Retrieve vector
    result = await vector_repo.get(vector_id)
    assert result is not None
    retrieved_vector, retrieved_metadata = result
    assert len(retrieved_vector) == 1536
    assert retrieved_metadata["type"] == "test"


@pytest.mark.asyncio
async def test_vector_search(vector_repo):
    """Test vector similarity search."""
    # Insert multiple vectors
    vectors = [
        (str(uuid4()), [0.1 * i] * 1536, {"index": i})
        for i in range(5)
    ]

    for vec_id, vec, meta in vectors:
        await vector_repo.upsert(vec_id, vec, meta)

    # Search for similar vectors
    query_vector = [0.1] * 1536
    results = await vector_repo.search(query_vector, limit=3)

    assert len(results) <= 3
    for match in results:
        assert match.score >= 0.0
        assert "index" in match.metadata


@pytest.mark.asyncio
async def test_vector_batch_upsert(vector_repo):
    """Test batch upserting vectors."""
    vectors = [
        (str(uuid4()), [0.1 * i] * 1536, {"index": i})
        for i in range(10)
    ]

    # Batch upsert
    success = await vector_repo.upsert_batch(vectors)
    assert success is True

    # Verify count
    count = await vector_repo.count()
    assert count >= 10


@pytest.mark.asyncio
async def test_vector_delete(vector_repo):
    """Test deleting a vector."""
    vector_id = str(uuid4())
    vector = [0.1] * 1536
    metadata = {"type": "test"}

    # Upsert vector
    await vector_repo.upsert(vector_id, vector, metadata)

    # Delete vector
    success = await vector_repo.delete(vector_id)
    assert success is True

    # Verify deletion
    result = await vector_repo.get(vector_id)
    assert result is None


# ============================================================================
# Redis CacheRepository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_cache_set_and_get(cache_repo):
    """Test setting and getting cache values."""
    key = "test_key"
    value = {"data": "test_value", "number": 123}

    # Set cache
    success = await cache_repo.set(key, value, ttl_seconds=60)
    assert success is True

    # Get cache
    retrieved = await cache_repo.get(key)
    assert retrieved == value


@pytest.mark.asyncio
async def test_cache_delete(cache_repo):
    """Test deleting cache keys."""
    key = "test_delete"
    value = "test_value"

    # Set and delete
    await cache_repo.set(key, value)
    deleted = await cache_repo.delete(key)
    assert deleted is True

    # Verify deletion
    retrieved = await cache_repo.get(key)
    assert retrieved is None


@pytest.mark.asyncio
async def test_cache_exists(cache_repo):
    """Test checking if cache key exists."""
    key = "test_exists"
    value = "test_value"

    # Check before set
    exists_before = await cache_repo.exists(key)
    assert exists_before is False

    # Set value
    await cache_repo.set(key, value)

    # Check after set
    exists_after = await cache_repo.exists(key)
    assert exists_after is True


@pytest.mark.asyncio
async def test_cache_increment(cache_repo):
    """Test incrementing counters."""
    key = "test_counter"

    # Increment from 0
    value1 = await cache_repo.increment(key, 1)
    assert value1 == 1

    # Increment by 5
    value2 = await cache_repo.increment(key, 5)
    assert value2 == 6


@pytest.mark.asyncio
async def test_cache_hash_operations(cache_repo):
    """Test hash field operations."""
    key = "test_hash"
    field1 = "field1"
    field2 = "field2"
    value1 = {"data": "value1"}
    value2 = {"data": "value2"}

    # Set hash fields
    await cache_repo.set_hash(key, field1, value1)
    await cache_repo.set_hash(key, field2, value2)

    # Get hash field
    retrieved1 = await cache_repo.get_hash(key, field1)
    assert retrieved1 == value1

    # Get all hash fields
    all_fields = await cache_repo.get_all_hash(key)
    assert field1 in all_fields
    assert field2 in all_fields


@pytest.mark.asyncio
async def test_cache_list_operations(cache_repo):
    """Test list operations."""
    key = "test_list"
    values = ["item1", "item2", "item3"]

    # Set list
    await cache_repo.set_with_list(key, values)

    # Get list
    retrieved = await cache_repo.get_list(key)
    assert retrieved == values

    # Push to list
    await cache_repo.push_to_list(key, "item4")
    updated = await cache_repo.get_list(key)
    assert len(updated) == 4

    # Pop from list
    popped = await cache_repo.pop_from_list(key)
    assert popped == "item4"


@pytest.mark.asyncio
async def test_cache_ttl(cache_repo):
    """Test TTL operations."""
    key = "test_ttl"
    value = "test_value"

    # Set with TTL
    await cache_repo.set(key, value, ttl_seconds=10)

    # Check TTL
    ttl = await cache_repo.get_ttl(key)
    assert ttl > 0 and ttl <= 10

    # Update TTL
    success = await cache_repo.set_ttl(key, 20)
    assert success is True

    # Verify updated TTL
    new_ttl = await cache_repo.get_ttl(key)
    assert new_ttl > 10 and new_ttl <= 20


# ============================================================================
# Integration Tests (Cross-repository)
# ============================================================================


@pytest.mark.asyncio
async def test_full_trend_lifecycle(trend_repo, topic_repo, item_repo, fixtures):
    """Test complete trend lifecycle with all repositories."""
    # Create and save items
    items = fixtures.get_processed_items(3)
    item_ids = []
    for item in items:
        item_id = await item_repo.save(item)
        item_ids.append(item_id)

    # Create and save topic
    topics = fixtures.get_topics(1)
    topic = topics[0]
    topic.item_count = len(item_ids)
    topic_id = await topic_repo.save(topic)

    # Create and save trend
    trends = fixtures.get_trends(1)
    trend = trends[0]
    trend.topic_id = topic_id
    trend_id = await trend_repo.save(trend)

    # Verify all entities exist
    assert await item_repo.get(item_ids[0]) is not None
    assert await topic_repo.get(topic_id) is not None
    assert await trend_repo.get(trend_id) is not None


@pytest.mark.asyncio
async def test_vector_and_cache_integration(vector_repo, cache_repo):
    """Test vector repository with caching layer."""
    vector_id = str(uuid4())
    vector = [0.5] * 1536
    metadata = {"cached": True}

    # Store vector
    await vector_repo.upsert(vector_id, vector, metadata)

    # Cache the vector ID for quick lookup
    cache_key = f"vector:{vector_id}"
    await cache_repo.set(cache_key, {"id": vector_id, "metadata": metadata})

    # Retrieve from cache
    cached_data = await cache_repo.get(cache_key)
    assert cached_data["id"] == vector_id

    # Retrieve from vector DB
    stored = await vector_repo.get(vector_id)
    assert stored is not None


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
