"""
S3-Compatible Object Storage Implementation.

Works with AWS S3, MinIO, and other S3-compatible services.
"""

import logging
import mimetypes
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from trend_agent.storage.object.interface import (
    ObjectStorageRepository,
    ObjectMetadata,
    StorageClass,
)

logger = logging.getLogger(__name__)


class S3ObjectStorageRepository(ObjectStorageRepository):
    """
    S3-compatible object storage implementation.

    Works with:
    - AWS S3
    - MinIO
    - DigitalOcean Spaces
    - Wasabi
    - Backblaze B2 (with S3 API)
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        use_ssl: bool = True,
    ):
        """
        Initialize S3 object storage.

        Args:
            endpoint_url: Custom endpoint URL (for MinIO, etc.)
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
            region_name: AWS region name
            use_ssl: Use HTTPS
        """
        self._endpoint_url = endpoint_url
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._region_name = region_name
        self._use_ssl = use_ssl
        self._client = None
        self._session = None

    async def connect(self) -> None:
        """Connect to S3."""
        try:
            import aioboto3

            self._session = aioboto3.Session()

            # Create client configuration
            config_kwargs = {
                "region_name": self._region_name,
                "aws_access_key_id": self._access_key_id,
                "aws_secret_access_key": self._secret_access_key,
            }

            if self._endpoint_url:
                config_kwargs["endpoint_url"] = self._endpoint_url

            # We'll use context manager for each operation
            # Test connection
            async with self._session.client("s3", **config_kwargs) as client:
                # List buckets to test connection
                await client.list_buckets()

            logger.info(f"Connected to S3 at {self._endpoint_url or 'AWS'}")

        except ImportError:
            logger.error("aioboto3 not installed. Install with: pip install aioboto3")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
            raise

    async def close(self) -> None:
        """Close S3 connection."""
        # aioboto3 uses context managers, no persistent connection to close
        logger.info("S3 connection closed")

    def _get_client_kwargs(self) -> Dict:
        """Get client configuration."""
        config = {
            "region_name": self._region_name,
            "aws_access_key_id": self._access_key_id,
            "aws_secret_access_key": self._secret_access_key,
        }

        if self._endpoint_url:
            config["endpoint_url"] = self._endpoint_url

        return config

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
        storage_class: StorageClass = StorageClass.STANDARD,
    ) -> str:
        """Upload an object."""
        async with self._session.client("s3", **self._get_client_kwargs()) as client:
            response = await client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                Metadata=metadata or {},
                StorageClass=storage_class.value,
            )

            etag = response["ETag"].strip('"')
            logger.debug(f"Uploaded object {key} to bucket {bucket}")
            return etag

    async def put_object_from_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        storage_class: StorageClass = StorageClass.STANDARD,
    ) -> str:
        """Upload an object from a file."""
        # Auto-detect content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(file_path)
            content_type = content_type or "application/octet-stream"

        # Read file and upload
        with open(file_path, "rb") as f:
            data = f.read()

        return await self.put_object(
            bucket=bucket,
            key=key,
            data=data,
            content_type=content_type,
            metadata=metadata,
            storage_class=storage_class,
        )

    async def get_object(
        self,
        bucket: str,
        key: str,
    ) -> bytes:
        """Download an object."""
        async with self._session.client("s3", **self._get_client_kwargs()) as client:
            response = await client.get_object(
                Bucket=bucket,
                Key=key,
            )

            # Read body
            data = await response["Body"].read()
            logger.debug(f"Downloaded object {key} from bucket {bucket}")
            return data

    async def get_object_to_file(
        self,
        bucket: str,
        key: str,
        file_path: str,
    ) -> None:
        """Download an object to a file."""
        data = await self.get_object(bucket, key)

        with open(file_path, "wb") as f:
            f.write(data)

        logger.debug(f"Saved object {key} to {file_path}")

    async def delete_object(
        self,
        bucket: str,
        key: str,
    ) -> None:
        """Delete an object."""
        async with self._session.client("s3", **self._get_client_kwargs()) as client:
            await client.delete_object(
                Bucket=bucket,
                Key=key,
            )

            logger.debug(f"Deleted object {key} from bucket {bucket}")

    async def delete_objects(
        self,
        bucket: str,
        keys: List[str],
    ) -> List[str]:
        """Delete multiple objects."""
        if not keys:
            return []

        async with self._session.client("s3", **self._get_client_kwargs()) as client:
            # Build delete request
            delete_request = {
                "Objects": [{"Key": key} for key in keys],
                "Quiet": False,
            }

            response = await client.delete_objects(
                Bucket=bucket,
                Delete=delete_request,
            )

            # Extract successfully deleted keys
            deleted_keys = [
                obj["Key"] for obj in response.get("Deleted", [])
            ]

            logger.debug(f"Deleted {len(deleted_keys)} objects from bucket {bucket}")
            return deleted_keys

    async def list_objects(
        self,
        bucket: str,
        prefix: Optional[str] = None,
        max_keys: int = 1000,
    ) -> List[ObjectMetadata]:
        """List objects in a bucket."""
        async with self._session.client("s3", **self._get_client_kwargs()) as client:
            kwargs = {
                "Bucket": bucket,
                "MaxKeys": max_keys,
            }

            if prefix:
                kwargs["Prefix"] = prefix

            response = await client.list_objects_v2(**kwargs)

            objects = []
            for obj in response.get("Contents", []):
                metadata = ObjectMetadata(
                    key=obj["Key"],
                    size=obj["Size"],
                    content_type="application/octet-stream",  # Not in list response
                    etag=obj["ETag"].strip('"'),
                    last_modified=obj["LastModified"],
                    storage_class=StorageClass(obj.get("StorageClass", "STANDARD")),
                )
                objects.append(metadata)

            logger.debug(f"Listed {len(objects)} objects in bucket {bucket}")
            return objects

    async def object_exists(
        self,
        bucket: str,
        key: str,
    ) -> bool:
        """Check if an object exists."""
        try:
            await self.get_object_metadata(bucket, key)
            return True
        except Exception:
            return False

    async def get_object_metadata(
        self,
        bucket: str,
        key: str,
    ) -> ObjectMetadata:
        """Get object metadata without downloading."""
        async with self._session.client("s3", **self._get_client_kwargs()) as client:
            response = await client.head_object(
                Bucket=bucket,
                Key=key,
            )

            metadata = ObjectMetadata(
                key=key,
                size=response["ContentLength"],
                content_type=response.get("ContentType", "application/octet-stream"),
                etag=response["ETag"].strip('"'),
                last_modified=response["LastModified"],
                storage_class=StorageClass(response.get("StorageClass", "STANDARD")),
                custom_metadata=response.get("Metadata", {}),
            )

            return metadata

    async def copy_object(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Copy an object."""
        async with self._session.client("s3", **self._get_client_kwargs()) as client:
            copy_source = {
                "Bucket": source_bucket,
                "Key": source_key,
            }

            kwargs = {
                "CopySource": copy_source,
                "Bucket": dest_bucket,
                "Key": dest_key,
            }

            if metadata:
                kwargs["Metadata"] = metadata
                kwargs["MetadataDirective"] = "REPLACE"

            response = await client.copy_object(**kwargs)

            etag = response["CopyObjectResult"]["ETag"].strip('"')
            logger.debug(f"Copied object {source_key} to {dest_key}")
            return etag

    async def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        expiration: timedelta = timedelta(hours=1),
        method: str = "GET",
    ) -> str:
        """Generate a presigned URL for temporary access."""
        async with self._session.client("s3", **self._get_client_kwargs()) as client:
            # Map method to boto3 client method
            client_method_map = {
                "GET": "get_object",
                "PUT": "put_object",
                "DELETE": "delete_object",
            }

            client_method = client_method_map.get(method.upper(), "get_object")

            url = await client.generate_presigned_url(
                ClientMethod=client_method,
                Params={
                    "Bucket": bucket,
                    "Key": key,
                },
                ExpiresIn=int(expiration.total_seconds()),
            )

            logger.debug(f"Generated presigned URL for {key}")
            return url

    async def create_bucket(
        self,
        bucket: str,
        region: Optional[str] = None,
    ) -> None:
        """Create a new bucket."""
        async with self._session.client("s3", **self._get_client_kwargs()) as client:
            kwargs = {"Bucket": bucket}

            # AWS requires LocationConstraint for non-us-east-1 regions
            if region and region != "us-east-1":
                kwargs["CreateBucketConfiguration"] = {
                    "LocationConstraint": region
                }

            await client.create_bucket(**kwargs)
            logger.info(f"Created bucket: {bucket}")

    async def delete_bucket(
        self,
        bucket: str,
        force: bool = False,
    ) -> None:
        """Delete a bucket."""
        async with self._session.client("s3", **self._get_client_kwargs()) as client:
            if force:
                # Delete all objects first
                objects = await self.list_objects(bucket)
                if objects:
                    keys = [obj.key for obj in objects]
                    await self.delete_objects(bucket, keys)

            await client.delete_bucket(Bucket=bucket)
            logger.info(f"Deleted bucket: {bucket}")

    async def bucket_exists(
        self,
        bucket: str,
    ) -> bool:
        """Check if a bucket exists."""
        try:
            async with self._session.client("s3", **self._get_client_kwargs()) as client:
                await client.head_bucket(Bucket=bucket)
                return True
        except Exception:
            return False
