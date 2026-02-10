"""
Mock storage implementations for testing.

These mocks provide in-memory implementations of storage interfaces
for use during development and testing.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from trend_agent.storage.interfaces import (
    BaseTrendRepository,
    BaseVectorRepository,
    CacheRepository,
    TopicRepository,
)
from trend_agent.types import (
    ProcessedItem,
    Topic,
    Trend,
    TrendFilter,
    VectorMatch,
)


class MockTrendRepository(BaseTrendRepository):
    """In-memory mock implementation of TrendRepository."""

    def __init__(self):
        self._trends: Dict[UUID, Trend] = {}

    async def save(self, trend: Trend) -> UUID:
        """Save a trend to in-memory storage."""
        if trend.id is None:
            trend.id = uuid4()
        self._trends[trend.id] = trend
        return trend.id

    async def get(self, trend_id: UUID) -> Optional[Trend]:
        """Get a trend by ID."""
        return self._trends.get(trend_id)

    async def search(self, filters: TrendFilter) -> List[Trend]:
        """Search trends with filters."""
        results = list(self._trends.values())

        # Apply filters
        if filters.category:
            results = [t for t in results if t.category.value == filters.category]

        if filters.sources:
            results = [
                t for t in results if any(s in filters.sources for s in t.sources)
            ]

        if filters.state:
            results = [t for t in results if t.state.value == filters.state]

        if filters.min_score is not None:
            results = [t for t in results if t.score >= filters.min_score]

        if filters.language:
            results = [t for t in results if t.language == filters.language]

        # Apply pagination
        results = results[filters.offset : filters.offset + filters.limit]

        return results

    async def update(self, trend_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update a trend."""
        if trend_id not in self._trends:
            return False

        trend = self._trends[trend_id]
        for key, value in updates.items():
            if hasattr(trend, key):
                setattr(trend, key, value)

        return True

    async def delete(self, trend_id: UUID) -> bool:
        """Delete a trend."""
        if trend_id in self._trends:
            del self._trends[trend_id]
            return True
        return False

    async def get_top_trends(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
    ) -> List[Trend]:
        """Get top-ranked trends."""
        results = list(self._trends.values())

        if category:
            results = [t for t in results if t.category.value == category]

        if date_from:
            results = [t for t in results if t.first_seen >= date_from]

        # Sort by rank
        results.sort(key=lambda t: t.rank)

        return results[:limit]


class MockTopicRepository:
    """In-memory mock implementation of TopicRepository."""

    def __init__(self):
        self._topics: Dict[UUID, Topic] = {}

    async def save(self, topic: Topic) -> UUID:
        """Save a topic to in-memory storage."""
        if topic.id is None:
            topic.id = uuid4()
        self._topics[topic.id] = topic
        return topic.id

    async def get(self, topic_id: UUID) -> Optional[Topic]:
        """Get a topic by ID."""
        return self._topics.get(topic_id)

    async def search(
        self,
        category: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Topic]:
        """Search topics with filters."""
        results = list(self._topics.values())

        if category:
            results = [t for t in results if t.category.value == category]

        if language:
            results = [t for t in results if t.language == language]

        return results[offset : offset + limit]

    async def update(self, topic_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update a topic."""
        if topic_id not in self._topics:
            return False

        topic = self._topics[topic_id]
        for key, value in updates.items():
            if hasattr(topic, key):
                setattr(topic, key, value)

        return True

    async def delete(self, topic_id: UUID) -> bool:
        """Delete a topic."""
        if topic_id in self._topics:
            del self._topics[topic_id]
            return True
        return False

    async def get_by_keyword(self, keyword: str, limit: int = 10) -> List[Topic]:
        """Get topics containing a keyword."""
        results = [
            t
            for t in self._topics.values()
            if keyword.lower() in t.title.lower()
            or keyword.lower() in " ".join(t.keywords).lower()
        ]
        return results[:limit]


class MockVectorRepository(BaseVectorRepository):
    """In-memory mock implementation of VectorRepository."""

    def __init__(self):
        self._vectors: Dict[str, tuple[List[float], Dict[str, Any]]] = {}

    async def upsert(
        self, id: str, vector: List[float], metadata: Dict[str, Any]
    ) -> bool:
        """Insert or update a vector."""
        self._vectors[id] = (vector, metadata)
        return True

    async def upsert_batch(
        self, vectors: List[tuple[str, List[float], Dict[str, Any]]]
    ) -> bool:
        """Insert or update multiple vectors."""
        for id, vector, metadata in vectors:
            self._vectors[id] = (vector, metadata)
        return True

    async def search(
        self,
        vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[VectorMatch]:
        """Search for similar vectors using cosine similarity."""
        import math

        def cosine_similarity(v1: List[float], v2: List[float]) -> float:
            """Calculate cosine similarity between two vectors."""
            dot_product = sum(a * b for a, b in zip(v1, v2))
            magnitude1 = math.sqrt(sum(a * a for a in v1))
            magnitude2 = math.sqrt(sum(b * b for b in v2))
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            return dot_product / (magnitude1 * magnitude2)

        results = []
        for id, (stored_vector, metadata) in self._vectors.items():
            # Apply metadata filters if provided
            if filters:
                matches_filters = all(
                    metadata.get(k) == v for k, v in filters.items()
                )
                if not matches_filters:
                    continue

            # Calculate similarity
            similarity = cosine_similarity(vector, stored_vector)

            if similarity >= min_score:
                results.append(
                    VectorMatch(id=id, score=similarity, metadata=metadata)
                )

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    async def get(self, id: str) -> Optional[tuple[List[float], Dict[str, Any]]]:
        """Get a vector by ID."""
        return self._vectors.get(id)

    async def delete(self, id: str) -> bool:
        """Delete a vector."""
        if id in self._vectors:
            del self._vectors[id]
            return True
        return False

    async def count(self) -> int:
        """Get total number of vectors."""
        return len(self._vectors)


class MockCacheRepository:
    """In-memory mock implementation of CacheRepository."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._hashes: Dict[str, Dict[str, Any]] = {}
        self._counters: Dict[str, int] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        return self._cache.get(key)

    async def set(
        self, key: str, value: Any, ttl_seconds: Optional[int] = None
    ) -> bool:
        """Set a value in cache."""
        self._cache[key] = value
        # Note: TTL not implemented in mock
        return True

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return key in self._cache

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        current = self._counters.get(key, 0)
        new_value = current + amount
        self._counters[key] = new_value
        return new_value

    async def get_hash(self, key: str, field: str) -> Optional[Any]:
        """Get a field from a hash."""
        if key in self._hashes:
            return self._hashes[key].get(field)
        return None

    async def set_hash(self, key: str, field: str, value: Any) -> bool:
        """Set a field in a hash."""
        if key not in self._hashes:
            self._hashes[key] = {}
        self._hashes[key][field] = value
        return True

    async def flush(self) -> bool:
        """Flush all cache entries."""
        self._cache.clear()
        self._hashes.clear()
        self._counters.clear()
        return True
