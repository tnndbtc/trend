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

# Concrete implementations (conditional imports for parallel development)
try:
    from trend_agent.storage.postgres import (
        PostgreSQLConnectionPool,
        PostgreSQLItemRepository,
        PostgreSQLTopicRepository,
        PostgreSQLTrendRepository,
    )
except ImportError:
    # Postgres dependencies not installed yet (parallel development)
    pass

try:
    from trend_agent.storage.qdrant import QdrantVectorRepository
except ImportError:
    # Qdrant dependencies not installed yet
    pass

try:
    from trend_agent.storage.redis import RedisCacheRepository
except ImportError:
    # Redis dependencies not installed yet
    pass

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
