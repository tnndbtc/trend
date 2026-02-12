"""Object Storage implementations."""

from trend_agent.storage.object.interface import (
    ObjectStorageRepository,
    ObjectMetadata,
    StorageClass,
)

__all__ = [
    "ObjectStorageRepository",
    "ObjectMetadata",
    "StorageClass",
]
