"""
Storage layer for the Trend Intelligence Platform.

This package provides interfaces and implementations for data persistence,
including relational databases, vector databases, and caching systems.
"""

# Interface exports
from trend_agent.storage.interfaces import (
    CacheRepository,
    ItemRepository,
    StorageError,
    ConnectionError,
    IntegrityError,
    NotFoundError,
    TopicRepository,
    TrendRepository,
    VectorRepository,
)

# Concrete implementations
from trend_agent.storage.postgres import (
    PostgreSQLConnectionPool,
    PostgreSQLItemRepository,
    PostgreSQLTopicRepository,
    PostgreSQLTrendRepository,
)
from trend_agent.storage.qdrant import QdrantVectorRepository
from trend_agent.storage.redis import RedisCacheRepository

__all__ = [
    # Interfaces
    "TrendRepository",
    "TopicRepository",
    "ItemRepository",
    "VectorRepository",
    "CacheRepository",
    # Exceptions
    "StorageError",
    "ConnectionError",
    "IntegrityError",
    "NotFoundError",
    # PostgreSQL implementations
    "PostgreSQLConnectionPool",
    "PostgreSQLTrendRepository",
    "PostgreSQLTopicRepository",
    "PostgreSQLItemRepository",
    # Qdrant implementation
    "QdrantVectorRepository",
    # Redis implementation
    "RedisCacheRepository",
]
