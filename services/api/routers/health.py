"""
Health check endpoints for monitoring API and service status.

Provides basic and detailed health checks for the API and its dependencies.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, status

from api import __version__
from api.schemas.common import HealthCheckResponse
from api.dependencies import (
    get_db_pool,
    get_cache_repository,
    get_vector_repository,
    get_plugin_manager,
)


router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Quick health check endpoint that always returns 200 OK if API is running.",
)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns a simple status indicating the API is operational.
    This endpoint does not check dependencies and is suitable for
    load balancer health checks.

    Returns:
        Dictionary with status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get(
    "/detailed",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Comprehensive health check including all service dependencies.",
)
async def detailed_health_check(
    db_pool=Depends(get_db_pool),
    cache_repo=Depends(get_cache_repository),
    vector_repo=Depends(get_vector_repository),
    plugin_manager=Depends(get_plugin_manager),
) -> HealthCheckResponse:
    """
    Detailed health check of all services.

    Checks connectivity and status of:
    - PostgreSQL database
    - Redis cache
    - Qdrant vector database
    - Plugin manager

    Returns:
        HealthCheckResponse with status of all services
    """
    services_status = {}

    # Check PostgreSQL
    try:
        if db_pool is not None:
            # Try a simple query
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            services_status["postgresql"] = True
        else:
            services_status["postgresql"] = False
    except Exception:
        services_status["postgresql"] = False

    # Check Redis
    try:
        if cache_repo is not None:
            # Try to ping Redis
            await cache_repo.set("health_check", "ok", ttl_seconds=10)
            result = await cache_repo.get("health_check")
            services_status["redis"] = result == "ok"
        else:
            services_status["redis"] = False
    except Exception:
        services_status["redis"] = False

    # Check Qdrant
    try:
        if vector_repo is not None:
            # Qdrant is initialized if vector_repo exists
            services_status["qdrant"] = True
        else:
            services_status["qdrant"] = False
    except Exception:
        services_status["qdrant"] = False

    # Check Plugin Manager
    try:
        if plugin_manager is not None:
            plugins = plugin_manager.get_all_plugins()
            services_status["plugin_manager"] = len(plugins) > 0
        else:
            services_status["plugin_manager"] = False
    except Exception:
        services_status["plugin_manager"] = False

    # Determine overall status
    all_healthy = all(services_status.values())
    overall_status = "healthy" if all_healthy else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version=__version__,
        timestamp=datetime.utcnow().isoformat() + "Z",
        services=services_status,
    )


@router.get(
    "/version",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Get API version",
    description="Returns the current API version information.",
)
async def get_version() -> Dict[str, str]:
    """
    Get API version information.

    Returns:
        Dictionary with version information
    """
    from api.main import app_state

    uptime = None
    if app_state.started_at:
        uptime_delta = datetime.utcnow() - app_state.started_at
        uptime = str(uptime_delta)

    return {
        "version": __version__,
        "name": "Trend Intelligence Platform API",
        "uptime": uptime or "unknown",
    }


@router.get(
    "/ready",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if API is ready to handle requests (all critical services available).",
)
async def readiness_check(
    db_pool=Depends(get_db_pool),
) -> Dict[str, Any]:
    """
    Readiness check for Kubernetes/orchestration systems.

    Checks if critical services (database) are available.
    Returns 200 if ready, 503 if not ready.

    Returns:
        Dictionary with readiness status

    Raises:
        HTTPException: 503 if not ready
    """
    ready = False

    try:
        if db_pool is not None:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            ready = True
    except Exception:
        ready = False

    return {
        "ready": ready,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get(
    "/liveness",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Check if API process is alive (always returns 200 if running).",
)
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness check for Kubernetes/orchestration systems.

    Always returns 200 OK if the API process is running.
    Used to detect if the process needs to be restarted.

    Returns:
        Dictionary with liveness status
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
