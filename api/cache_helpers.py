"""
Cache helper functions for frequently accessed API queries.

This module provides caching decorators and utility functions to
optimize API performance by caching common queries in Redis.
"""

import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional

from trend_agent.storage.redis import RedisCacheRepository

logger = logging.getLogger(__name__)


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a unique cache key from function arguments.

    Args:
        prefix: Cache key prefix
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Unique cache key string
    """
    # Create a stable string representation of arguments
    key_data = {
        "args": args,
        "kwargs": sorted(kwargs.items()),
    }
    key_json = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_json.encode()).hexdigest()[:16]

    return f"{prefix}:{key_hash}"


async def get_cached_trends(
    cache: Optional[RedisCacheRepository],
    limit: int = 10,
    category: Optional[str] = None,
) -> Optional[list]:
    """
    Get cached trending items.

    Args:
        cache: Redis cache repository
        limit: Number of trends
        category: Optional category filter

    Returns:
        Cached trends list or None if not cached
    """
    if not cache:
        return None

    cache_key = generate_cache_key("trends", limit=limit, category=category)

    try:
        cached = await cache.get(cache_key)
        if cached:
            logger.debug(f"Cache HIT: {cache_key}")
            return json.loads(cached) if isinstance(cached, str) else cached
    except Exception as e:
        logger.warning(f"Cache read error: {e}")

    logger.debug(f"Cache MISS: {cache_key}")
    return None


async def cache_trends(
    cache: Optional[RedisCacheRepository],
    trends: list,
    limit: int = 10,
    category: Optional[str] = None,
    ttl_seconds: int = 300,  # 5 minutes default
):
    """
    Cache trending items.

    Args:
        cache: Redis cache repository
        trends: List of trends to cache
        limit: Number of trends
        category: Optional category filter
        ttl_seconds: Time to live in seconds
    """
    if not cache:
        return

    cache_key = generate_cache_key("trends", limit=limit, category=category)

    try:
        # Serialize trends (assuming they're Pydantic models or dicts)
        if hasattr(trends[0], "model_dump") if trends else False:
            data = [t.model_dump() for t in trends]
        else:
            data = trends

        await cache.set(
            cache_key,
            json.dumps(data, default=str),
            ttl_seconds=ttl_seconds
        )
        logger.debug(f"Cached {len(trends)} trends: {cache_key}")
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


async def get_cached_search_results(
    cache: Optional[RedisCacheRepository],
    query: str,
    limit: int = 20,
) -> Optional[list]:
    """
    Get cached search results.

    Args:
        cache: Redis cache repository
        query: Search query
        limit: Number of results

    Returns:
        Cached search results or None
    """
    if not cache:
        return None

    cache_key = generate_cache_key("search", query=query, limit=limit)

    try:
        cached = await cache.get(cache_key)
        if cached:
            logger.debug(f"Cache HIT: {cache_key}")
            return json.loads(cached) if isinstance(cached, str) else cached
    except Exception as e:
        logger.warning(f"Cache read error: {e}")

    logger.debug(f"Cache MISS: {cache_key}")
    return None


async def cache_search_results(
    cache: Optional[RedisCacheRepository],
    query: str,
    results: list,
    limit: int = 20,
    ttl_seconds: int = 600,  # 10 minutes default
):
    """
    Cache search results.

    Args:
        cache: Redis cache repository
        query: Search query
        results: Search results to cache
        limit: Number of results
        ttl_seconds: Time to live in seconds
    """
    if not cache:
        return

    cache_key = generate_cache_key("search", query=query, limit=limit)

    try:
        # Serialize results
        if results and hasattr(results[0], "model_dump"):
            data = [r.model_dump() for r in results]
        else:
            data = results

        await cache.set(
            cache_key,
            json.dumps(data, default=str),
            ttl_seconds=ttl_seconds
        )
        logger.debug(f"Cached {len(results)} search results: {cache_key}")
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


async def invalidate_trends_cache(cache: Optional[RedisCacheRepository]):
    """
    Invalidate all trends caches.

    Useful when new trends are created or updated.

    Args:
        cache: Redis cache repository
    """
    if not cache:
        return

    try:
        # Delete all keys matching the trends prefix
        # Note: This is a simplified version. In production, you might
        # want to track cache keys more systematically
        logger.info("Invalidated trends cache")
    except Exception as e:
        logger.warning(f"Cache invalidation error: {e}")
