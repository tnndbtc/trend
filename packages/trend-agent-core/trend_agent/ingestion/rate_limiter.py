"""
Rate limiting for collector plugins.

This module implements rate limiting using a sliding window algorithm
to prevent plugins from exceeding their configured request limits.
Supports both in-memory and Redis-backed storage for distributed systems.
"""

import asyncio
import logging
import time
from typing import Dict, Optional

from trend_agent.ingestion.base import PluginRegistry
from trend_agent.ingestion.interfaces import BaseRateLimiter

logger = logging.getLogger(__name__)


class InMemoryRateLimiter(BaseRateLimiter):
    """
    In-memory rate limiter using sliding window algorithm.

    This implementation stores request timestamps in memory and uses
    a sliding window to enforce rate limits. Suitable for single-instance
    deployments.

    For distributed deployments, use RedisRateLimiter instead.
    """

    def __init__(self, default_limit: int = 100, window_seconds: int = 3600):
        """
        Initialize the rate limiter.

        Args:
            default_limit: Default requests per window if plugin doesn't specify
            window_seconds: Time window in seconds (default: 1 hour)
        """
        self.default_limit = default_limit
        self.window_seconds = window_seconds

        # Storage: plugin_name -> list of request timestamps
        self._requests: Dict[str, list] = {}

        # Lock for thread-safe access
        self._lock = asyncio.Lock()

        logger.info(
            f"Rate limiter initialized. Default limit: {default_limit} "
            f"requests per {window_seconds}s"
        )

    async def check_rate_limit(self, plugin_name: str) -> bool:
        """
        Check if plugin can make a request.

        Args:
            plugin_name: Name of the plugin

        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            # Get plugin metadata for rate limit
            plugin = PluginRegistry.get_plugin(plugin_name)
            if not plugin:
                logger.warning(f"Plugin {plugin_name} not found, denying request")
                return False

            # Get rate limit (requests per hour from metadata)
            rate_limit = plugin.metadata.rate_limit or self.default_limit

            # Clean old requests outside the window
            current_time = time.time()
            window_start = current_time - self.window_seconds

            if plugin_name not in self._requests:
                self._requests[plugin_name] = []

            # Remove requests outside the current window
            self._requests[plugin_name] = [
                ts for ts in self._requests[plugin_name] if ts > window_start
            ]

            # Check if under limit
            request_count = len(self._requests[plugin_name])

            if request_count >= rate_limit:
                logger.warning(
                    f"Rate limit exceeded for {plugin_name}: "
                    f"{request_count}/{rate_limit} in last {self.window_seconds}s"
                )
                return False

            return True

    async def record_request(self, plugin_name: str) -> None:
        """
        Record a request for rate limiting.

        Args:
            plugin_name: Name of the plugin
        """
        async with self._lock:
            current_time = time.time()

            if plugin_name not in self._requests:
                self._requests[plugin_name] = []

            self._requests[plugin_name].append(current_time)

            logger.debug(
                f"Request recorded for {plugin_name}. "
                f"Total in window: {len(self._requests[plugin_name])}"
            )

    async def get_remaining_quota(self, plugin_name: str) -> int:
        """
        Get remaining request quota for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Number of requests remaining in current window
        """
        async with self._lock:
            # Get plugin metadata
            plugin = PluginRegistry.get_plugin(plugin_name)
            if not plugin:
                return 0

            rate_limit = plugin.metadata.rate_limit or self.default_limit

            # Clean old requests
            current_time = time.time()
            window_start = current_time - self.window_seconds

            if plugin_name not in self._requests:
                return rate_limit

            # Remove old requests
            self._requests[plugin_name] = [
                ts for ts in self._requests[plugin_name] if ts > window_start
            ]

            request_count = len(self._requests[plugin_name])
            remaining = max(0, rate_limit - request_count)

            return remaining

    async def reset_quota(self, plugin_name: str) -> None:
        """
        Reset quota for a plugin.

        Args:
            plugin_name: Name of the plugin
        """
        async with self._lock:
            if plugin_name in self._requests:
                self._requests[plugin_name].clear()
                logger.info(f"Quota reset for {plugin_name}")


class RedisRateLimiter(BaseRateLimiter):
    """
    Redis-backed rate limiter for distributed deployments.

    Uses Redis sorted sets to store request timestamps, enabling
    rate limiting across multiple instances of the application.
    """

    def __init__(
        self,
        redis_client,
        default_limit: int = 100,
        window_seconds: int = 3600,
        key_prefix: str = "ratelimit"
    ):
        """
        Initialize the Redis rate limiter.

        Args:
            redis_client: Redis client instance (from redis.asyncio)
            default_limit: Default requests per window
            window_seconds: Time window in seconds
            key_prefix: Prefix for Redis keys
        """
        self.redis = redis_client
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

        logger.info(
            f"Redis rate limiter initialized. Default limit: {default_limit} "
            f"requests per {window_seconds}s"
        )

    def _get_key(self, plugin_name: str) -> str:
        """Get Redis key for a plugin."""
        return f"{self.key_prefix}:{plugin_name}"

    async def check_rate_limit(self, plugin_name: str) -> bool:
        """
        Check if plugin can make a request.

        Uses Redis sorted set with timestamps as scores.

        Args:
            plugin_name: Name of the plugin

        Returns:
            True if request is allowed, False if rate limited
        """
        try:
            # Get plugin metadata
            plugin = PluginRegistry.get_plugin(plugin_name)
            if not plugin:
                logger.warning(f"Plugin {plugin_name} not found, denying request")
                return False

            rate_limit = plugin.metadata.rate_limit or self.default_limit
            key = self._get_key(plugin_name)

            # Current timestamp
            current_time = time.time()
            window_start = current_time - self.window_seconds

            # Remove old entries outside the window
            await self.redis.zremrangebyscore(key, "-inf", window_start)

            # Count requests in current window
            count = await self.redis.zcard(key)

            if count >= rate_limit:
                logger.warning(
                    f"Rate limit exceeded for {plugin_name}: "
                    f"{count}/{rate_limit} in last {self.window_seconds}s"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking rate limit for {plugin_name}: {e}", exc_info=True)
            # Fail open: allow request if Redis is unavailable
            return True

    async def record_request(self, plugin_name: str) -> None:
        """
        Record a request in Redis.

        Args:
            plugin_name: Name of the plugin
        """
        try:
            key = self._get_key(plugin_name)
            current_time = time.time()

            # Add current timestamp to sorted set
            # Use timestamp as both score and member (with microsecond precision)
            member = f"{current_time}:{id(self)}"
            await self.redis.zadd(key, {member: current_time})

            # Set expiration on the key to prevent memory leaks
            await self.redis.expire(key, self.window_seconds * 2)

            logger.debug(f"Request recorded for {plugin_name} in Redis")

        except Exception as e:
            logger.error(f"Error recording request for {plugin_name}: {e}", exc_info=True)

    async def get_remaining_quota(self, plugin_name: str) -> int:
        """
        Get remaining request quota for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Number of requests remaining in current window
        """
        try:
            # Get plugin metadata
            plugin = PluginRegistry.get_plugin(plugin_name)
            if not plugin:
                return 0

            rate_limit = plugin.metadata.rate_limit or self.default_limit
            key = self._get_key(plugin_name)

            # Clean old entries
            current_time = time.time()
            window_start = current_time - self.window_seconds
            await self.redis.zremrangebyscore(key, "-inf", window_start)

            # Count requests
            count = await self.redis.zcard(key)
            remaining = max(0, rate_limit - count)

            return remaining

        except Exception as e:
            logger.error(f"Error getting quota for {plugin_name}: {e}", exc_info=True)
            return 0

    async def reset_quota(self, plugin_name: str) -> None:
        """
        Reset quota for a plugin.

        Args:
            plugin_name: Name of the plugin
        """
        try:
            key = self._get_key(plugin_name)
            await self.redis.delete(key)
            logger.info(f"Quota reset for {plugin_name} in Redis")

        except Exception as e:
            logger.error(f"Error resetting quota for {plugin_name}: {e}", exc_info=True)


# Factory function for creating rate limiters
def create_rate_limiter(
    redis_client=None,
    default_limit: int = 100,
    window_seconds: int = 3600
) -> BaseRateLimiter:
    """
    Create a rate limiter instance.

    If Redis client is provided, creates a RedisRateLimiter for distributed systems.
    Otherwise, creates an InMemoryRateLimiter for single-instance deployments.

    Args:
        redis_client: Optional Redis client instance
        default_limit: Default requests per window
        window_seconds: Time window in seconds

    Returns:
        Rate limiter instance
    """
    if redis_client:
        return RedisRateLimiter(redis_client, default_limit, window_seconds)
    else:
        return InMemoryRateLimiter(default_limit, window_seconds)
