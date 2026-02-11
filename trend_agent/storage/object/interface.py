"""
Object Storage Interface.

For storing large files, media, backups, and unstructured data.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, BinaryIO
from datetime import datetime, timedelta
from enum import Enum


class StorageClass(Enum):
    """Object storage class for cost optimization."""

    STANDARD = "STANDARD"
    INTELLIGENT_TIERING = "INTELLIGENT_TIERING"
    GLACIER = "GLACIER"
    GLACIER_DEEP_ARCHIVE = "GLACIER_DEEP_ARCHIVE"
    REDUCED_REDUNDANCY = "REDUCED_REDUNDANCY"


class ObjectMetadata:
    """Metadata for stored object."""

    def __init__(
        self,
        key: str,
        size: int,
        content_type: str,
        etag: str,
        last_modified: datetime,
        storage_class: StorageClass = StorageClass.STANDARD,
        custom_metadata: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize object metadata.

        Args:
            key: Object key/path
            size: Size in bytes
            content_type: MIME content type
            etag: Entity tag (usually MD5 hash)
            last_modified: Last modification timestamp
            storage_class: Storage class
            custom_metadata: Custom metadata tags
        """
        self.key = key
        self.size = size
        self.content_type = content_type
        self.etag = etag
        self.last_modified = last_modified
        self.storage_class = storage_class
        self.custom_metadata = custom_metadata or {}


class ObjectStorageRepository(ABC):
    """Abstract interface for object storage operations."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to object storage service."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection to object storage service."""
        pass

    @abstractmethod
    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
        storage_class: StorageClass = StorageClass.STANDARD,
    ) -> str:
        """
        Upload an object.

        Args:
            bucket: Bucket name
            key: Object key/path
            data: Object data as bytes
            content_type: MIME content type
            metadata: Custom metadata tags
            storage_class: Storage class for cost optimization

        Returns:
            ETag of uploaded object
        """
        pass

    @abstractmethod
    async def put_object_from_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        storage_class: StorageClass = StorageClass.STANDARD,
    ) -> str:
        """
        Upload an object from a file.

        Args:
            bucket: Bucket name
            key: Object key/path
            file_path: Path to local file
            content_type: MIME content type (auto-detected if None)
            metadata: Custom metadata tags
            storage_class: Storage class

        Returns:
            ETag of uploaded object
        """
        pass

    @abstractmethod
    async def get_object(
        self,
        bucket: str,
        key: str,
    ) -> bytes:
        """
        Download an object.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            Object data as bytes
        """
        pass

    @abstractmethod
    async def get_object_to_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> None:
        """
        Download an object to a file.

        Args:
            bucket: Bucket name
            key: Object key/path
            file_path: Path to save file
        """
        pass

    @abstractmethod
    async def delete_object(
        self,
        bucket: str,
        key: str,
    ) -> None:
        """
        Delete an object.

        Args:
            bucket: Bucket name
            key: Object key/path
        """
        pass

    @abstractmethod
    async def delete_objects(
        self,
        bucket: str,
        keys: List[str],
    ) -> List[str]:
        """
        Delete multiple objects.

        Args:
            bucket: Bucket name
            keys: List of object keys

        Returns:
            List of successfully deleted keys
        """
        pass

    @abstractmethod
    async def list_objects(
        self,
        bucket: str,
        prefix: Optional[str] = None,
        max_keys: int = 1000,
    ) -> List[ObjectMetadata]:
        """
        List objects in a bucket.

        Args:
            bucket: Bucket name
            prefix: Filter by key prefix
            max_keys: Maximum number of objects to return

        Returns:
            List of object metadata
        """
        pass

    @abstractmethod
    async def object_exists(
        self,
        bucket: str,
        key: str,
    ) -> bool:
        """
        Check if an object exists.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            True if object exists
        """
        pass

    @abstractmethod
    async def get_object_metadata(
        self,
        bucket: str,
        key: str,
    ) -> ObjectMetadata:
        """
        Get object metadata without downloading.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            Object metadata
        """
        pass

    @abstractmethod
    async def copy_object(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Copy an object.

        Args:
            source_bucket: Source bucket name
            source_key: Source object key
            dest_bucket: Destination bucket name
            dest_key: Destination object key
            metadata: Custom metadata for copied object

        Returns:
            ETag of copied object
        """
        pass

    @abstractmethod
    async def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        expiration: timedelta = timedelta(hours=1),
        method: str = "GET",
    ) -> str:
        """
        Generate a presigned URL for temporary access.

        Args:
            bucket: Bucket name
            key: Object key/path
            expiration: URL expiration time
            method: HTTP method (GET, PUT, etc.)

        Returns:
            Presigned URL
        """
        pass

    @abstractmethod
    async def create_bucket(
        self,
        bucket: str,
        region: Optional[str] = None,
    ) -> None:
        """
        Create a new bucket.

        Args:
            bucket: Bucket name
            region: AWS region (if applicable)
        """
        pass

    @abstractmethod
    async def delete_bucket(
        self,
        bucket: str,
        force: bool = False,
    ) -> None:
        """
        Delete a bucket.

        Args:
            bucket: Bucket name
            force: Delete even if bucket is not empty
        """
        pass

    @abstractmethod
    async def bucket_exists(
        self,
        bucket: str,
    ) -> bool:
        """
        Check if a bucket exists.

        Args:
            bucket: Bucket name

        Returns:
            True if bucket exists
        """
        pass
