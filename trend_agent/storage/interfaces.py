"""
Storage layer interface contracts.

This module defines Protocol classes that specify the contract for storage
implementations. Different sessions can implement these interfaces independently
while ensuring compatibility.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID

from trend_agent.types import (
    ProcessedItem,
    Topic,
    Trend,
    TrendFilter,
    VectorMatch,
)


# ============================================================================
# Repository Interfaces (Protocol-based for type checking)
# ============================================================================


class TrendRepository(Protocol):
    """Interface for trend persistence operations."""

    async def save(self, trend: Trend) -> UUID:
        """
        Save a trend to the database.

        Args:
            trend: The trend to save

        Returns:
            UUID of the saved trend

        Raises:
            StorageError: If save operation fails
        """
        ...

    async def get(self, trend_id: UUID) -> Optional[Trend]:
        """
        Retrieve a trend by ID.

        Args:
            trend_id: UUID of the trend

        Returns:
            The trend if found, None otherwise
        """
        ...

    async def search(self, filters: TrendFilter) -> List[Trend]:
        """
        Search trends with filters.

        Args:
            filters: Search filter criteria

        Returns:
            List of matching trends
        """
        ...

    async def update(self, trend_id: UUID, updates: Dict[str, Any]) -> bool:
        """
        Update a trend.

        Args:
            trend_id: UUID of the trend to update
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if not found
        """
        ...

    async def delete(self, trend_id: UUID) -> bool:
        """
        Delete a trend.

        Args:
            trend_id: UUID of the trend to delete

        Returns:
            True if deleted, False if not found
        """
        ...

    async def get_top_trends(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
    ) -> List[Trend]:
        """
        Get top-ranked trends.

        Args:
            limit: Maximum number of trends to return
            category: Optional category filter
            date_from: Optional date filter

        Returns:
            List of top trends ordered by rank
        """
        ...

    async def count(self, filters: Optional[TrendFilter] = None) -> int:
        """
        Count trends matching filters.

        Args:
            filters: Optional search filter criteria

        Returns:
            Number of matching trends
        """
        ...


class TopicRepository(Protocol):
    """Interface for topic persistence operations."""

    async def save(self, topic: Topic) -> UUID:
        """Save a topic to the database."""
        ...

    async def get(self, topic_id: UUID) -> Optional[Topic]:
        """Retrieve a topic by ID."""
        ...

    async def search(
        self,
        category: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Topic]:
        """Search topics with filters."""
        ...

    async def update(self, topic_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update a topic."""
        ...

    async def delete(self, topic_id: UUID) -> bool:
        """Delete a topic."""
        ...

    async def get_by_keyword(self, keyword: str, limit: int = 10) -> List[Topic]:
        """Get topics containing a specific keyword."""
        ...

    async def count(self) -> int:
        """
        Count total topics.

        Returns:
            Total number of topics
        """
        ...

    async def get_items_by_topic(
        self,
        topic_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProcessedItem]:
        """
        Get all items belonging to a topic.

        Args:
            topic_id: UUID of the topic
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            List of ProcessedItem objects ordered by added_at DESC
        """
        ...


class ItemRepository(Protocol):
    """Interface for processed item persistence operations."""

    async def save(self, item: ProcessedItem) -> UUID:
        """Save a processed item to the database."""
        ...

    async def save_batch(self, items: List[ProcessedItem]) -> List[UUID]:
        """Save multiple items in a batch."""
        ...

    async def get(self, item_id: UUID) -> Optional[ProcessedItem]:
        """Retrieve an item by ID."""
        ...

    async def get_by_source_id(
        self, source: str, source_id: str
    ) -> Optional[ProcessedItem]:
        """Retrieve an item by source and source ID."""
        ...

    async def exists(self, source: str, source_id: str) -> bool:
        """Check if an item exists by source and source ID."""
        ...

    async def delete_older_than(self, days: int) -> int:
        """Delete items older than specified days."""
        ...

    async def count(self) -> int:
        """
        Count total items.

        Returns:
            Total number of processed items
        """
        ...

    async def get_items_without_embeddings(self, limit: int = 100) -> List[ProcessedItem]:
        """
        Get items that don't have embeddings yet.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of ProcessedItem objects without embeddings
        """
        ...


class VectorRepository(Protocol):
    """Interface for vector database operations."""

    async def upsert(
        self,
        id: str,
        vector: List[float],
        metadata: Dict[str, Any],
    ) -> bool:
        """
        Insert or update a vector embedding.

        Args:
            id: Unique identifier for the vector
            vector: The embedding vector
            metadata: Associated metadata

        Returns:
            True if successful
        """
        ...

    async def upsert_batch(
        self,
        vectors: List[tuple[str, List[float], Dict[str, Any]]],
    ) -> bool:
        """
        Insert or update multiple vectors in a batch.

        Args:
            vectors: List of (id, vector, metadata) tuples

        Returns:
            True if successful
        """
        ...

    async def search(
        self,
        vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[VectorMatch]:
        """
        Search for similar vectors.

        Args:
            vector: Query vector
            limit: Maximum results to return
            filters: Optional metadata filters
            min_score: Minimum similarity score

        Returns:
            List of matching vectors with scores
        """
        ...

    async def get(self, id: str) -> Optional[tuple[List[float], Dict[str, Any]]]:
        """
        Get a vector by ID.

        Args:
            id: Vector identifier

        Returns:
            Tuple of (vector, metadata) if found, None otherwise
        """
        ...

    async def delete(self, id: str) -> bool:
        """Delete a vector by ID."""
        ...

    async def count(self) -> int:
        """Get total number of vectors in the collection."""
        ...


class CacheRepository(Protocol):
    """Interface for caching operations."""

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found, None otherwise
        """
        ...

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (None = default)

        Returns:
            True if successful
        """
        ...

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        ...

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter.

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New counter value
        """
        ...

    async def get_hash(self, key: str, field: str) -> Optional[Any]:
        """Get a field from a hash."""
        ...

    async def set_hash(self, key: str, field: str, value: Any) -> bool:
        """Set a field in a hash."""
        ...

    async def flush(self) -> bool:
        """Flush all cache entries."""
        ...


# ============================================================================
# Abstract Base Classes (for implementations)
# ============================================================================


class BaseTrendRepository(ABC):
    """Abstract base class for trend repository implementations."""

    @abstractmethod
    async def save(self, trend: Trend) -> UUID:
        pass

    @abstractmethod
    async def get(self, trend_id: UUID) -> Optional[Trend]:
        pass

    @abstractmethod
    async def search(self, filters: TrendFilter) -> List[Trend]:
        pass

    @abstractmethod
    async def update(self, trend_id: UUID, updates: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def delete(self, trend_id: UUID) -> bool:
        pass

    @abstractmethod
    async def get_top_trends(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
    ) -> List[Trend]:
        pass


class BaseVectorRepository(ABC):
    """Abstract base class for vector repository implementations."""

    @abstractmethod
    async def upsert(
        self, id: str, vector: List[float], metadata: Dict[str, Any]
    ) -> bool:
        pass

    @abstractmethod
    async def upsert_batch(
        self, vectors: List[tuple[str, List[float], Dict[str, Any]]]
    ) -> bool:
        pass

    @abstractmethod
    async def search(
        self,
        vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[VectorMatch]:
        pass

    @abstractmethod
    async def get(self, id: str) -> Optional[tuple[List[float], Dict[str, Any]]]:
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        pass

    @abstractmethod
    async def count(self) -> int:
        pass


# ============================================================================
# Exceptions
# ============================================================================


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class ConnectionError(StorageError):
    """Exception for connection failures."""

    pass


class IntegrityError(StorageError):
    """Exception for data integrity violations."""

    pass


class NotFoundError(StorageError):
    """Exception when resource is not found."""

    pass
