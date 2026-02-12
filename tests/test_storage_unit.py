"""
Unit tests for storage layer using mocks.

These tests verify storage layer logic without requiring actual database connections.
They use the mock implementations from tests/mocks/storage.py.

Run with: pytest tests/test_storage_unit.py -v
"""

from datetime import datetime
from uuid import uuid4

import pytest

from tests.fixtures import Fixtures
from tests.mocks.storage import (
    MockCacheRepository,
    MockTopicRepository,
    MockTrendRepository,
    MockVectorRepository,
)
from trend_agent.schemas import Category, TrendFilter, TrendState, VectorMatch


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fixtures():
    """Provide test data fixtures."""
    return Fixtures()


@pytest.fixture
def trend_repo():
    """Create mock TrendRepository instance."""
    return MockTrendRepository()


@pytest.fixture
def topic_repo():
    """Create mock TopicRepository instance."""
    return MockTopicRepository()


@pytest.fixture
def vector_repo():
    """Create mock VectorRepository instance."""
    return MockVectorRepository()


@pytest.fixture
def cache_repo():
    """Create mock CacheRepository instance."""
    return MockCacheRepository()


# ============================================================================
# TrendRepository Unit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_trend_save_generates_id(trend_repo, fixtures):
    """Test that saving a trend without ID generates one."""
    trends = fixtures.get_trends(1)
    trend = trends[0]
    trend.id = None  # Ensure no ID

    trend_id = await trend_repo.save(trend)
    assert trend_id is not None
    assert trend.id is not None


@pytest.mark.asyncio
async def test_trend_get_nonexistent_returns_none(trend_repo):
    """Test that getting a non-existent trend returns None."""
    result = await trend_repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_trend_update_nonexistent_returns_false(trend_repo):
    """Test that updating a non-existent trend returns False."""
    result = await trend_repo.update(uuid4(), {"rank": 5})
    assert result is False


@pytest.mark.asyncio
async def test_trend_delete_nonexistent_returns_false(trend_repo):
    """Test that deleting a non-existent trend returns False."""
    result = await trend_repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_trend_search_by_category(trend_repo, fixtures):
    """Test searching trends by category."""
    trends = fixtures.get_trends(5)

    # Save trends with different categories
    for i, trend in enumerate(trends):
        if i < 3:
            trend.category = Category.TECHNOLOGY
        else:
            trend.category = Category.POLITICS
        await trend_repo.save(trend)

    # Search for technology trends
    filters = TrendFilter(category=Category.TECHNOLOGY, limit=10)
    results = await trend_repo.search(filters)

    assert len(results) == 3
    for result in results:
        assert result.category == Category.TECHNOLOGY


@pytest.mark.asyncio
async def test_trend_search_by_state(trend_repo, fixtures):
    """Test searching trends by state."""
    trends = fixtures.get_trends(4)

    # Save trends with different states
    trends[0].state = TrendState.EMERGING
    trends[1].state = TrendState.VIRAL
    trends[2].state = TrendState.EMERGING
    trends[3].state = TrendState.DECLINING

    for trend in trends:
        await trend_repo.save(trend)

    # Search for emerging trends
    filters = TrendFilter(state=TrendState.EMERGING, limit=10)
    results = await trend_repo.search(filters)

    assert len(results) == 2
    for result in results:
        assert result.state == TrendState.EMERGING


@pytest.mark.asyncio
async def test_trend_search_pagination(trend_repo, fixtures):
    """Test trend search pagination."""
    trends = fixtures.get_trends(10)

    for trend in trends:
        await trend_repo.save(trend)

    # Get first page
    filters = TrendFilter(limit=3, offset=0)
    page1 = await trend_repo.search(filters)
    assert len(page1) == 3

    # Get second page
    filters = TrendFilter(limit=3, offset=3)
    page2 = await trend_repo.search(filters)
    assert len(page2) == 3

    # Verify different results
    page1_ids = {t.id for t in page1}
    page2_ids = {t.id for t in page2}
    assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.asyncio
async def test_trend_get_top_trends_sorted_by_rank(trend_repo, fixtures):
    """Test that top trends are sorted by rank."""
    trends = fixtures.get_trends(5)

    # Assign different ranks
    for i, trend in enumerate(trends):
        trend.rank = i + 1
        await trend_repo.save(trend)

    # Get top 3
    top_trends = await trend_repo.get_top_trends(limit=3)

    assert len(top_trends) == 3
    # Verify sorted by rank
    for i in range(len(top_trends) - 1):
        assert top_trends[i].rank <= top_trends[i + 1].rank


# ============================================================================
# TopicRepository Unit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_topic_save_and_retrieve(topic_repo, fixtures):
    """Test saving and retrieving a topic."""
    topics = fixtures.get_topics(1)
    topic = topics[0]

    topic_id = await topic_repo.save(topic)
    retrieved = await topic_repo.get(topic_id)

    assert retrieved is not None
    assert retrieved.id == topic_id
    assert retrieved.title == topic.title


@pytest.mark.asyncio
async def test_topic_search_by_language(topic_repo, fixtures):
    """Test searching topics by language."""
    topics = fixtures.get_topics(3)

    topics[0].language = "en"
    topics[1].language = "es"
    topics[2].language = "en"

    for topic in topics:
        await topic_repo.save(topic)

    # Search for English topics
    results = await topic_repo.search(language="en", limit=10)
    assert len(results) == 2
    for result in results:
        assert result.language == "en"


@pytest.mark.asyncio
async def test_topic_get_by_keyword(topic_repo, fixtures):
    """Test getting topics by keyword."""
    topics = fixtures.get_topics(3)

    topics[0].keywords = ["python", "programming"]
    topics[1].keywords = ["javascript", "web"]
    topics[2].keywords = ["python", "data"]

    for topic in topics:
        await topic_repo.save(topic)

    # Search for python topics
    results = await topic_repo.get_by_keyword("python", limit=10)
    assert len(results) == 2


# ============================================================================
# VectorRepository Unit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_vector_upsert_and_get(vector_repo):
    """Test upserting and getting a vector."""
    vector_id = "test_vector_1"
    vector = [0.1, 0.2, 0.3]
    metadata = {"type": "test"}

    success = await vector_repo.upsert(vector_id, vector, metadata)
    assert success is True

    result = await vector_repo.get(vector_id)
    assert result is not None

    retrieved_vector, retrieved_metadata = result
    assert retrieved_vector == vector
    assert retrieved_metadata == metadata


@pytest.mark.asyncio
async def test_vector_upsert_updates_existing(vector_repo):
    """Test that upserting updates existing vectors."""
    vector_id = "test_vector_2"
    vector1 = [0.1, 0.2, 0.3]
    metadata1 = {"version": 1}

    # First upsert
    await vector_repo.upsert(vector_id, vector1, metadata1)

    # Update with new data
    vector2 = [0.4, 0.5, 0.6]
    metadata2 = {"version": 2}
    await vector_repo.upsert(vector_id, vector2, metadata2)

    # Verify update
    result = await vector_repo.get(vector_id)
    retrieved_vector, retrieved_metadata = result
    assert retrieved_vector == vector2
    assert retrieved_metadata["version"] == 2


@pytest.mark.asyncio
async def test_vector_search_returns_similar(vector_repo):
    """Test that vector search returns similar vectors."""
    # Insert vectors
    vectors = [
        ("vec1", [1.0, 0.0, 0.0], {"name": "vec1"}),
        ("vec2", [0.9, 0.1, 0.0], {"name": "vec2"}),
        ("vec3", [0.0, 1.0, 0.0], {"name": "vec3"}),
    ]

    for vid, vec, meta in vectors:
        await vector_repo.upsert(vid, vec, meta)

    # Search for vectors similar to [1.0, 0.0, 0.0]
    query = [1.0, 0.0, 0.0]
    results = await vector_repo.search(query, limit=2)

    assert len(results) <= 2
    # First result should be exact match
    assert results[0].id == "vec1"
    assert results[0].score >= 0.9  # High similarity


@pytest.mark.asyncio
async def test_vector_search_with_filters(vector_repo):
    """Test vector search with metadata filters."""
    # Insert vectors with different metadata
    vectors = [
        ("vec1", [1.0, 0.0], {"category": "tech", "lang": "en"}),
        ("vec2", [0.9, 0.1], {"category": "tech", "lang": "es"}),
        ("vec3", [0.8, 0.2], {"category": "news", "lang": "en"}),
    ]

    for vid, vec, meta in vectors:
        await vector_repo.upsert(vid, vec, meta)

    # Search with category filter
    query = [1.0, 0.0]
    filters = {"category": "tech"}
    results = await vector_repo.search(query, limit=10, filters=filters)

    # Should only return tech vectors
    assert len(results) == 2
    for result in results:
        assert result.metadata["category"] == "tech"


@pytest.mark.asyncio
async def test_vector_delete(vector_repo):
    """Test deleting a vector."""
    vector_id = "test_vector_delete"
    vector = [0.1, 0.2, 0.3]
    metadata = {"temp": True}

    # Insert vector
    await vector_repo.upsert(vector_id, vector, metadata)

    # Delete vector
    success = await vector_repo.delete(vector_id)
    assert success is True

    # Verify deletion
    result = await vector_repo.get(vector_id)
    assert result is None


@pytest.mark.asyncio
async def test_vector_count(vector_repo):
    """Test counting vectors."""
    # Insert multiple vectors
    for i in range(5):
        await vector_repo.upsert(f"vec_{i}", [float(i)], {"index": i})

    count = await vector_repo.count()
    assert count == 5


# ============================================================================
# CacheRepository Unit Tests
# ============================================================================


@pytest.mark.asyncio
async def test_cache_set_and_get(cache_repo):
    """Test setting and getting cache values."""
    key = "test_key"
    value = "test_value"

    success = await cache_repo.set(key, value)
    assert success is True

    retrieved = await cache_repo.get(key)
    assert retrieved == value


@pytest.mark.asyncio
async def test_cache_get_nonexistent_returns_none(cache_repo):
    """Test that getting non-existent key returns None."""
    result = await cache_repo.get("nonexistent_key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_delete(cache_repo):
    """Test deleting cache keys."""
    key = "delete_me"
    value = "data"

    await cache_repo.set(key, value)
    deleted = await cache_repo.delete(key)
    assert deleted is True

    # Verify deletion
    result = await cache_repo.get(key)
    assert result is None


@pytest.mark.asyncio
async def test_cache_increment_counter(cache_repo):
    """Test incrementing counters."""
    key = "counter"

    # First increment
    value1 = await cache_repo.increment(key, 1)
    assert value1 == 1

    # Second increment
    value2 = await cache_repo.increment(key, 5)
    assert value2 == 6


@pytest.mark.asyncio
async def test_cache_hash_operations(cache_repo):
    """Test hash field operations."""
    key = "user:123"
    field = "name"
    value = "John Doe"

    # Set hash field
    success = await cache_repo.set_hash(key, field, value)
    assert success is True

    # Get hash field
    retrieved = await cache_repo.get_hash(key, field)
    assert retrieved == value


@pytest.mark.asyncio
async def test_cache_flush(cache_repo):
    """Test flushing all cache entries."""
    # Set multiple keys
    await cache_repo.set("key1", "value1")
    await cache_repo.set("key2", "value2")

    # Flush
    success = await cache_repo.flush()
    assert success is True

    # Verify all keys are gone
    assert await cache_repo.get("key1") is None
    assert await cache_repo.get("key2") is None


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
