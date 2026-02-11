"""
FastAPI dependency injection providers.

This module provides dependency injection functions for database connections,
repositories, services, and authentication.
"""

import os
from typing import Optional, Annotated
from fastapi import Depends, Header, HTTPException, status
from asyncpg import Pool

from trend_agent.storage.interfaces import (
    TrendRepository,
    TopicRepository,
    ItemRepository,
    VectorRepository,
    CacheRepository,
)
from trend_agent.storage.postgres import (
    PostgreSQLTrendRepository,
    PostgreSQLTopicRepository,
    PostgreSQLItemRepository,
)
from trend_agent.ingestion.manager import PluginManager


# API Key authentication

VALID_API_KEYS = set(
    os.getenv("API_KEYS", "dev_key_12345,admin_key_67890").split(",")
)


async def verify_api_key(x_api_key: Annotated[str, Header()] = None) -> str:
    """
    Verify API key from request header.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        API key if valid

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


async def verify_admin_api_key(api_key: str = Depends(verify_api_key)) -> str:
    """
    Verify admin API key for admin endpoints.

    Args:
        api_key: API key from verify_api_key dependency

    Returns:
        API key if it has admin privileges

    Raises:
        HTTPException: If API key doesn't have admin privileges
    """
    admin_keys = set(os.getenv("ADMIN_API_KEYS", "admin_key_67890").split(","))

    if api_key not in admin_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return api_key


# Optional API key (for public endpoints with optional auth)

async def optional_api_key(x_api_key: Annotated[Optional[str], Header()] = None) -> Optional[str]:
    """
    Optional API key verification for public endpoints.

    Args:
        x_api_key: Optional API key from X-API-Key header

    Returns:
        API key if provided and valid, None otherwise
    """
    if x_api_key is None:
        return None

    if x_api_key in VALID_API_KEYS:
        return x_api_key

    return None


# Database dependencies

async def get_db_pool() -> Pool:
    """
    Get database connection pool from application state.

    Returns:
        PostgreSQL connection pool

    Raises:
        HTTPException: If database pool is not initialized
    """
    from api.main import app_state

    if app_state.db_pool is None or app_state.db_pool.pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection pool not initialized"
        )

    return app_state.db_pool.pool


async def get_cache_repository() -> Optional[CacheRepository]:
    """
    Get Redis cache repository from application state.

    Returns:
        Redis cache repository or None if not initialized
    """
    from api.main import app_state
    return app_state.redis_cache


async def get_vector_repository() -> Optional[VectorRepository]:
    """
    Get Qdrant vector repository from application state.

    Returns:
        Qdrant vector repository or None if not initialized
    """
    from api.main import app_state
    return app_state.vector_repo


async def get_plugin_manager() -> Optional[PluginManager]:
    """
    Get plugin manager from application state.

    Returns:
        Plugin manager or None if not initialized
    """
    from api.main import app_state
    return app_state.plugin_manager


# Repository dependencies

async def get_trend_repository(
    pool: Pool = Depends(get_db_pool)
) -> TrendRepository:
    """
    Get TrendRepository instance.

    Args:
        pool: Database connection pool

    Returns:
        PostgreSQL TrendRepository instance
    """
    return PostgreSQLTrendRepository(pool)


async def get_topic_repository(
    pool: Pool = Depends(get_db_pool)
) -> TopicRepository:
    """
    Get TopicRepository instance.

    Args:
        pool: Database connection pool

    Returns:
        PostgreSQL TopicRepository instance
    """
    return PostgreSQLTopicRepository(pool)


async def get_item_repository(
    pool: Pool = Depends(get_db_pool)
) -> ItemRepository:
    """
    Get ItemRepository instance.

    Args:
        pool: Database connection pool

    Returns:
        PostgreSQL ItemRepository instance
    """
    return PostgreSQLItemRepository(pool)


# Pagination dependencies

def pagination_params(
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    Common pagination parameters.

    Args:
        limit: Number of items to return (1-100)
        offset: Number of items to skip (>= 0)

    Returns:
        Dictionary with limit and offset

    Raises:
        HTTPException: If parameters are invalid
    """
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100"
        )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset must be >= 0"
        )

    return {"limit": limit, "offset": offset}
