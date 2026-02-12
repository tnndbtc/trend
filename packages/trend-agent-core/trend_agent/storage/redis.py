"""
Redis cache repository implementation.

This module provides a Redis-based implementation of the CacheRepository
interface for high-performance caching operations.
"""

import json
import logging
import pickle
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from trend_agent.storage.interfaces import ConnectionError, StorageError

logger = logging.getLogger(__name__)


class RedisCacheRepository:
    """
    Redis implementation of CacheRepository.

    This implementation uses Redis for fast in-memory caching with
    optional TTL (time-to-live) support.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 3600,
        encoding: str = "utf-8",
        decode_responses: bool = False,
        max_connections: int = 50,
    ):
        """
        Initialize Redis cache repository.

        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number (0-15)
            password: Optional authentication password
            default_ttl: Default time-to-live in seconds
            encoding: Character encoding for strings
            decode_responses: Whether to decode byte responses
            max_connections: Maximum number of connections in the pool
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.encoding = encoding
        self.decode_responses = decode_responses
        self.max_connections = max_connections
        self._client: Optional[Redis] = None

    async def connect(self) -> Redis:
        """
        Establish connection to Redis.

        Returns:
            Redis client instance

        Raises:
            ConnectionError: If connection fails
        """
        if self._client is not None:
            return self._client

        try:
            self._client = await aioredis.from_url(
                f"redis://{self.host}:{self.port}/{self.db}",
                password=self.password,
                encoding=self.encoding,
                decode_responses=self.decode_responses,
                max_connections=self.max_connections,
            )

            # Test connection
            await self._client.ping()

            logger.info(f"Connected to Redis at {self.host}:{self.port}/{self.db}")
            return self._client

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(f"Redis connection failed: {e}")

    async def close(self):
        """Close the Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")

    @property
    def client(self) -> Redis:
        """Get the Redis client instance."""
        if self._client is None:
            raise StorageError("Redis client not connected. Call connect() first.")
        return self._client

    def _serialize(self, value: Any) -> bytes:
        """
        Serialize a Python object for storage.

        Args:
            value: Value to serialize

        Returns:
            Serialized bytes
        """
        # Use JSON for simple types, pickle for complex objects
        if isinstance(value, (str, int, float, bool, type(None))):
            return json.dumps(value).encode(self.encoding)
        else:
            # For complex objects (lists, dicts, custom classes)
            return pickle.dumps(value)

    def _deserialize(self, data: bytes) -> Any:
        """
        Deserialize stored data back to Python object.

        Args:
            data: Serialized bytes

        Returns:
            Deserialized Python object
        """
        if data is None:
            return None

        try:
            # Try JSON first (faster and more common)
            return json.loads(data.decode(self.encoding))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle for complex objects
            return pickle.loads(data)

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        try:
            data = await self.client.get(key)

            if data is None:
                logger.debug(f"Cache miss: {key}")
                return None

            value = self._deserialize(data)
            logger.debug(f"Cache hit: {key}")
            return value

        except RedisError as e:
            logger.error(f"Failed to get cache key '{key}': {e}")
            raise StorageError(f"Cache retrieval failed: {e}")

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
            ttl_seconds: Time-to-live in seconds (None = use default)

        Returns:
            True if successful

        Raises:
            StorageError: If set operation fails
        """
        try:
            data = self._serialize(value)
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl

            if ttl > 0:
                await self.client.setex(key, ttl, data)
            else:
                # No expiration
                await self.client.set(key, data)

            logger.debug(f"Cached key '{key}' with TTL={ttl}s")
            return True

        except RedisError as e:
            logger.error(f"Failed to set cache key '{key}': {e}")
            raise StorageError(f"Cache set failed: {e}")

    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if key didn't exist

        Raises:
            StorageError: If deletion fails
        """
        try:
            result = await self.client.delete(key)
            deleted = result > 0

            if deleted:
                logger.debug(f"Deleted cache key: {key}")

            return deleted

        except RedisError as e:
            logger.error(f"Failed to delete cache key '{key}': {e}")
            raise StorageError(f"Cache deletion failed: {e}")

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise

        Raises:
            StorageError: If check fails
        """
        try:
            result = await self.client.exists(key)
            return result > 0

        except RedisError as e:
            logger.error(f"Failed to check cache key existence '{key}': {e}")
            raise StorageError(f"Cache existence check failed: {e}")

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter.

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New counter value

        Raises:
            StorageError: If increment fails
        """
        try:
            new_value = await self.client.incrby(key, amount)
            logger.debug(f"Incremented counter '{key}' by {amount} to {new_value}")
            return new_value

        except RedisError as e:
            logger.error(f"Failed to increment counter '{key}': {e}")
            raise StorageError(f"Counter increment failed: {e}")

    async def decrement(self, key: str, amount: int = 1) -> int:
        """
        Decrement a counter.

        Args:
            key: Counter key
            amount: Amount to decrement

        Returns:
            New counter value

        Raises:
            StorageError: If decrement fails
        """
        try:
            new_value = await self.client.decrby(key, amount)
            logger.debug(f"Decremented counter '{key}' by {amount} to {new_value}")
            return new_value

        except RedisError as e:
            logger.error(f"Failed to decrement counter '{key}': {e}")
            raise StorageError(f"Counter decrement failed: {e}")

    async def get_hash(self, key: str, field: str) -> Optional[Any]:
        """
        Get a field from a hash.

        Args:
            key: Hash key
            field: Field name

        Returns:
            Field value if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        try:
            data = await self.client.hget(key, field)

            if data is None:
                return None

            return self._deserialize(data)

        except RedisError as e:
            logger.error(f"Failed to get hash field '{key}.{field}': {e}")
            raise StorageError(f"Hash field retrieval failed: {e}")

    async def set_hash(self, key: str, field: str, value: Any) -> bool:
        """
        Set a field in a hash.

        Args:
            key: Hash key
            field: Field name
            value: Field value

        Returns:
            True if successful

        Raises:
            StorageError: If set operation fails
        """
        try:
            data = self._serialize(value)
            await self.client.hset(key, field, data)
            logger.debug(f"Set hash field '{key}.{field}'")
            return True

        except RedisError as e:
            logger.error(f"Failed to set hash field '{key}.{field}': {e}")
            raise StorageError(f"Hash field set failed: {e}")

    async def get_all_hash(self, key: str) -> Dict[str, Any]:
        """
        Get all fields from a hash.

        Args:
            key: Hash key

        Returns:
            Dictionary of all fields and values

        Raises:
            StorageError: If retrieval fails
        """
        try:
            data = await self.client.hgetall(key)

            if not data:
                return {}

            # Deserialize all values
            result = {}
            for field, value in data.items():
                # Field names might be bytes
                field_str = field.decode(self.encoding) if isinstance(field, bytes) else field
                result[field_str] = self._deserialize(value)

            return result

        except RedisError as e:
            logger.error(f"Failed to get all hash fields for '{key}': {e}")
            raise StorageError(f"Hash retrieval failed: {e}")

    async def delete_hash_field(self, key: str, field: str) -> bool:
        """
        Delete a field from a hash.

        Args:
            key: Hash key
            field: Field name

        Returns:
            True if deleted, False if field didn't exist

        Raises:
            StorageError: If deletion fails
        """
        try:
            result = await self.client.hdel(key, field)
            deleted = result > 0

            if deleted:
                logger.debug(f"Deleted hash field '{key}.{field}'")

            return deleted

        except RedisError as e:
            logger.error(f"Failed to delete hash field '{key}.{field}': {e}")
            raise StorageError(f"Hash field deletion failed: {e}")

    async def flush(self) -> bool:
        """
        Flush all cache entries in the current database.

        WARNING: This is a destructive operation!

        Returns:
            True if successful

        Raises:
            StorageError: If flush fails
        """
        try:
            await self.client.flushdb()
            logger.warning(f"Flushed all keys from Redis DB {self.db}")
            return True

        except RedisError as e:
            logger.error(f"Failed to flush cache: {e}")
            raise StorageError(f"Cache flush failed: {e}")

    async def set_with_list(self, key: str, values: List[Any], ttl_seconds: Optional[int] = None) -> bool:
        """
        Store a list of values.

        Args:
            key: Cache key
            values: List of values to store
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if successful

        Raises:
            StorageError: If operation fails
        """
        try:
            # Delete existing key first
            await self.client.delete(key)

            # Push all values
            if values:
                serialized = [self._serialize(v) for v in values]
                await self.client.rpush(key, *serialized)

                # Set TTL if specified
                if ttl_seconds:
                    await self.client.expire(key, ttl_seconds)

            logger.debug(f"Stored list with {len(values)} items at '{key}'")
            return True

        except RedisError as e:
            logger.error(f"Failed to set list '{key}': {e}")
            raise StorageError(f"List set failed: {e}")

    async def get_list(self, key: str) -> List[Any]:
        """
        Retrieve a list of values.

        Args:
            key: Cache key

        Returns:
            List of values

        Raises:
            StorageError: If retrieval fails
        """
        try:
            data = await self.client.lrange(key, 0, -1)

            if not data:
                return []

            return [self._deserialize(item) for item in data]

        except RedisError as e:
            logger.error(f"Failed to get list '{key}': {e}")
            raise StorageError(f"List retrieval failed: {e}")

    async def push_to_list(self, key: str, value: Any, left: bool = False) -> int:
        """
        Push a value to a list.

        Args:
            key: Cache key
            value: Value to push
            left: If True, push to left (LPUSH), else push to right (RPUSH)

        Returns:
            New length of the list

        Raises:
            StorageError: If push fails
        """
        try:
            data = self._serialize(value)

            if left:
                length = await self.client.lpush(key, data)
            else:
                length = await self.client.rpush(key, data)

            logger.debug(f"Pushed to list '{key}', new length: {length}")
            return length

        except RedisError as e:
            logger.error(f"Failed to push to list '{key}': {e}")
            raise StorageError(f"List push failed: {e}")

    async def pop_from_list(self, key: str, left: bool = False) -> Optional[Any]:
        """
        Pop a value from a list.

        Args:
            key: Cache key
            left: If True, pop from left (LPOP), else pop from right (RPOP)

        Returns:
            Popped value if list not empty, None otherwise

        Raises:
            StorageError: If pop fails
        """
        try:
            if left:
                data = await self.client.lpop(key)
            else:
                data = await self.client.rpop(key)

            if data is None:
                return None

            return self._deserialize(data)

        except RedisError as e:
            logger.error(f"Failed to pop from list '{key}': {e}")
            raise StorageError(f"List pop failed: {e}")

    async def get_ttl(self, key: str) -> int:
        """
        Get the time-to-live of a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist

        Raises:
            StorageError: If retrieval fails
        """
        try:
            ttl = await self.client.ttl(key)
            return ttl

        except RedisError as e:
            logger.error(f"Failed to get TTL for '{key}': {e}")
            raise StorageError(f"TTL retrieval failed: {e}")

    async def set_ttl(self, key: str, ttl_seconds: int) -> bool:
        """
        Set or update the time-to-live of a key.

        Args:
            key: Cache key
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if successful, False if key doesn't exist

        Raises:
            StorageError: If operation fails
        """
        try:
            result = await self.client.expire(key, ttl_seconds)
            return result == 1

        except RedisError as e:
            logger.error(f"Failed to set TTL for '{key}': {e}")
            raise StorageError(f"TTL set failed: {e}")

    async def keys_matching(self, pattern: str) -> List[str]:
        """
        Get all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "user:*", "cache:*:data")

        Returns:
            List of matching keys

        Raises:
            StorageError: If retrieval fails

        Warning:
            Use with caution on large databases - this is a blocking operation!
        """
        try:
            keys = await self.client.keys(pattern)

            # Decode bytes to strings if needed
            if keys and isinstance(keys[0], bytes):
                keys = [k.decode(self.encoding) for k in keys]

            logger.debug(f"Found {len(keys)} keys matching pattern '{pattern}'")
            return keys

        except RedisError as e:
            logger.error(f"Failed to get keys matching '{pattern}': {e}")
            raise StorageError(f"Key pattern retrieval failed: {e}")

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match

        Returns:
            Number of keys deleted

        Raises:
            StorageError: If deletion fails

        Warning:
            Use with extreme caution - this can delete many keys at once!
        """
        try:
            keys = await self.keys_matching(pattern)

            if not keys:
                return 0

            result = await self.client.delete(*keys)
            logger.warning(f"Deleted {result} keys matching pattern '{pattern}'")
            return result

        except RedisError as e:
            logger.error(f"Failed to delete keys matching '{pattern}': {e}")
            raise StorageError(f"Pattern deletion failed: {e}")
