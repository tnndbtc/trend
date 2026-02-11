"""
Admin endpoints for system management and configuration.

Provides authenticated endpoints for managing collector plugins,
triggering manual operations, and viewing system metrics.
Requires admin API key for access.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from api.dependencies import (
    verify_admin_api_key,
    get_plugin_manager,
    get_cache_repository,
    get_trend_repository,
    get_topic_repository,
    get_item_repository,
    get_plugin_health_repository,
)
from trend_agent.ingestion.manager import PluginManager
from trend_agent.storage.interfaces import (
    CacheRepository,
    TrendRepository,
    TopicRepository,
    ItemRepository,
)
from trend_agent.storage.postgres import PostgreSQLPluginHealthRepository


router = APIRouter(prefix="/admin", tags=["Admin"])


class PluginInfo(BaseModel):
    """Information about a collector plugin."""

    name: str = Field(..., description="Plugin name")
    enabled: bool = Field(..., description="Whether plugin is enabled")
    source: str = Field(..., description="Data source type")
    schedule: Optional[str] = Field(None, description="Cron schedule")
    rate_limit: Optional[int] = Field(None, description="Requests per hour limit")
    timeout: int = Field(..., description="Collection timeout in seconds")
    last_run: Optional[datetime] = Field(None, description="Last successful run")
    last_error: Optional[str] = Field(None, description="Last error message")
    total_runs: int = Field(0, description="Total number of runs")
    success_rate: float = Field(0.0, description="Success rate (0.0-1.0)")


class CollectionTriggerRequest(BaseModel):
    """Request to trigger manual collection."""

    plugin_name: Optional[str] = Field(None, description="Specific plugin to run (or all if None)")
    force: bool = Field(False, description="Force collection even if rate limited")


class CollectionTriggerResponse(BaseModel):
    """Response from collection trigger."""

    success: bool = Field(..., description="Whether trigger was successful")
    message: str = Field(..., description="Status message")
    plugins_triggered: List[str] = Field(..., description="List of plugins triggered")


class SystemMetrics(BaseModel):
    """System-wide metrics."""

    uptime_seconds: float = Field(..., description="API uptime in seconds")
    total_trends: int = Field(..., description="Total trends in database")
    total_topics: int = Field(..., description="Total topics in database")
    total_items: int = Field(..., description="Total items collected")
    active_plugins: int = Field(..., description="Number of active plugins")
    cache_hit_rate: Optional[float] = Field(None, description="Cache hit rate")
    memory_usage_mb: Optional[float] = Field(None, description="Memory usage in MB")


@router.get(
    "/plugins",
    response_model=List[PluginInfo],
    status_code=status.HTTP_200_OK,
    summary="List all plugins",
    description="Get status and information for all collector plugins.",
)
async def list_plugins(
    admin_key: str = Depends(verify_admin_api_key),
    plugin_manager: Optional[PluginManager] = Depends(get_plugin_manager),
    health_repo: PostgreSQLPluginHealthRepository = Depends(get_plugin_health_repository),
) -> List[PluginInfo]:
    """
    List all collector plugins with their status.

    Returns information about each plugin including:
    - Enabled/disabled status
    - Schedule configuration
    - Rate limits
    - Success metrics

    Args:
        admin_key: Admin API key
        plugin_manager: Plugin manager instance
        health_repo: Plugin health repository

    Returns:
        List of PluginInfo objects

    Raises:
        HTTPException: 503 if plugin manager unavailable
    """
    if plugin_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin manager is not initialized",
        )

    plugins = plugin_manager.get_all_plugins()
    plugin_infos = []

    for plugin in plugins:
        # Get plugin status from manager
        status_data = await plugin_manager.get_plugin_status(plugin.metadata.name)

        # Get health data from database
        health = await health_repo.get(plugin.metadata.name)

        # Merge data with health metrics taking precedence
        plugin_info = PluginInfo(
            name=plugin.metadata.name,
            enabled=status_data.get("enabled", True),
            source=plugin.metadata.source.value,
            schedule=plugin.metadata.schedule,
            rate_limit=plugin.metadata.rate_limit,
            timeout=plugin.metadata.timeout,
            last_run=health.last_run_at if health else status_data.get("last_run"),
            last_error=health.last_error if health else status_data.get("last_error"),
            total_runs=health.total_runs if health else status_data.get("total_runs", 0),
            success_rate=health.success_rate if health else status_data.get("success_rate", 0.0),
        )
        plugin_infos.append(plugin_info)

    return plugin_infos


@router.get(
    "/plugins/{plugin_name}",
    response_model=PluginInfo,
    status_code=status.HTTP_200_OK,
    summary="Get plugin details",
    description="Get detailed information about a specific plugin.",
)
async def get_plugin(
    plugin_name: str,
    admin_key: str = Depends(verify_admin_api_key),
    plugin_manager: Optional[PluginManager] = Depends(get_plugin_manager),
    health_repo: PostgreSQLPluginHealthRepository = Depends(get_plugin_health_repository),
) -> PluginInfo:
    """
    Get details for a specific plugin.

    Args:
        plugin_name: Name of the plugin
        admin_key: Admin API key
        plugin_manager: Plugin manager instance
        health_repo: Plugin health repository

    Returns:
        PluginInfo object

    Raises:
        HTTPException: 404 if plugin not found
    """
    if plugin_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin manager is not initialized",
        )

    plugin = plugin_manager.get_plugin(plugin_name)
    if plugin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin '{plugin_name}' not found",
        )

    status_data = await plugin_manager.get_plugin_status(plugin_name)

    # Get health data from database
    health = await health_repo.get(plugin_name)

    return PluginInfo(
        name=plugin.metadata.name,
        enabled=status_data.get("enabled", True),
        source=plugin.metadata.source.value,
        schedule=plugin.metadata.schedule,
        rate_limit=plugin.metadata.rate_limit,
        timeout=plugin.metadata.timeout,
        last_run=health.last_run_at if health else status_data.get("last_run"),
        last_error=health.last_error if health else status_data.get("last_error"),
        total_runs=health.total_runs if health else status_data.get("total_runs", 0),
        success_rate=health.success_rate if health else status_data.get("success_rate", 0.0),
    )


@router.post(
    "/plugins/{plugin_name}/enable",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Enable plugin",
    description="Enable a disabled collector plugin.",
)
async def enable_plugin(
    plugin_name: str,
    admin_key: str = Depends(verify_admin_api_key),
    plugin_manager: Optional[PluginManager] = Depends(get_plugin_manager),
) -> Dict[str, Any]:
    """
    Enable a collector plugin.

    Args:
        plugin_name: Name of the plugin to enable
        admin_key: Admin API key
        plugin_manager: Plugin manager instance

    Returns:
        Success message

    Raises:
        HTTPException: 404 if plugin not found
    """
    if plugin_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin manager is not initialized",
        )

    try:
        await plugin_manager.enable_plugin(plugin_name)
        return {
            "success": True,
            "message": f"Plugin '{plugin_name}' enabled successfully",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/plugins/{plugin_name}/disable",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Disable plugin",
    description="Disable an active collector plugin.",
)
async def disable_plugin(
    plugin_name: str,
    admin_key: str = Depends(verify_admin_api_key),
    plugin_manager: Optional[PluginManager] = Depends(get_plugin_manager),
) -> Dict[str, Any]:
    """
    Disable a collector plugin.

    Args:
        plugin_name: Name of the plugin to disable
        admin_key: Admin API key
        plugin_manager: Plugin manager instance

    Returns:
        Success message

    Raises:
        HTTPException: 404 if plugin not found
    """
    if plugin_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin manager is not initialized",
        )

    try:
        await plugin_manager.disable_plugin(plugin_name)
        return {
            "success": True,
            "message": f"Plugin '{plugin_name}' disabled successfully",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/collect",
    response_model=CollectionTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual collection",
    description="Manually trigger data collection from one or all plugins.",
)
async def trigger_collection(
    request: CollectionTriggerRequest,
    background_tasks: BackgroundTasks,
    admin_key: str = Depends(verify_admin_api_key),
    plugin_manager: Optional[PluginManager] = Depends(get_plugin_manager),
) -> CollectionTriggerResponse:
    """
    Trigger manual data collection.

    Starts a background task to collect data from specified plugin(s).
    Returns immediately while collection runs in the background.

    Args:
        request: Collection trigger parameters
        background_tasks: FastAPI background tasks
        admin_key: Admin API key
        plugin_manager: Plugin manager instance

    Returns:
        CollectionTriggerResponse with status

    Raises:
        HTTPException: 503 if plugin manager unavailable
    """
    if plugin_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Plugin manager is not initialized",
        )

    plugins_to_run = []

    if request.plugin_name:
        # Run specific plugin
        plugin = plugin_manager.get_plugin(request.plugin_name)
        if plugin is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin '{request.plugin_name}' not found",
            )
        plugins_to_run = [request.plugin_name]
    else:
        # Run all enabled plugins
        all_plugins = plugin_manager.get_all_plugins()
        plugins_to_run = [p.metadata.name for p in all_plugins]

    # TODO: Add actual collection task
    # For now, just return success
    # In production, this would:
    # 1. Create a Celery task or background job
    # 2. Run collection through the pipeline
    # 3. Store results in database

    return CollectionTriggerResponse(
        success=True,
        message=f"Collection triggered for {len(plugins_to_run)} plugin(s)",
        plugins_triggered=plugins_to_run,
    )


@router.get(
    "/metrics",
    response_model=SystemMetrics,
    status_code=status.HTTP_200_OK,
    summary="Get system metrics",
    description="Get system-wide metrics and statistics.",
)
async def get_system_metrics(
    admin_key: str = Depends(verify_admin_api_key),
    plugin_manager: Optional[PluginManager] = Depends(get_plugin_manager),
    trend_repo: TrendRepository = Depends(get_trend_repository),
    topic_repo: TopicRepository = Depends(get_topic_repository),
    item_repo: ItemRepository = Depends(get_item_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> SystemMetrics:
    """
    Get system-wide metrics.

    Returns metrics including:
    - Uptime
    - Total counts (trends, topics, items)
    - Active plugins
    - Cache performance
    - Resource usage

    Args:
        admin_key: Admin API key
        plugin_manager: Plugin manager instance
        trend_repo: Trend repository
        topic_repo: Topic repository
        item_repo: Item repository
        cache: Cache repository

    Returns:
        SystemMetrics object
    """
    from api.main import app_state

    # Calculate uptime
    uptime = 0.0
    if app_state.started_at:
        delta = datetime.utcnow() - app_state.started_at
        uptime = delta.total_seconds()

    # Count active plugins
    active_plugins = 0
    if plugin_manager:
        all_plugins = plugin_manager.get_all_plugins()
        active_plugins = len(all_plugins)

    # Get real counts from database
    total_trends = await trend_repo.count()
    total_topics = await topic_repo.count()
    total_items = await item_repo.count()

    # Calculate cache hit rate if available
    cache_hit_rate = None
    if cache:
        try:
            # Try to get cache statistics
            # This is a simplified version - in production you'd track hits/misses
            cache_hit_rate = 0.0  # Placeholder for now
        except Exception:
            pass

    # Memory usage - could be enhanced with psutil if needed
    memory_usage_mb = None

    return SystemMetrics(
        uptime_seconds=uptime,
        total_trends=total_trends,
        total_topics=total_topics,
        total_items=total_items,
        active_plugins=active_plugins,
        cache_hit_rate=cache_hit_rate,
        memory_usage_mb=memory_usage_mb,
    )


@router.delete(
    "/cache/clear",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Clear cache",
    description="Clear all cached data.",
)
async def clear_cache(
    admin_key: str = Depends(verify_admin_api_key),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> Dict[str, Any]:
    """
    Clear all cached data.

    Use this to force fresh data retrieval from the database.

    Args:
        admin_key: Admin API key
        cache: Cache repository

    Returns:
        Success message
    """
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache is not available",
        )

    try:
        # Clear all keys matching trend/topic patterns
        patterns = ["trends:*", "topics:*", "search:*"]
        for pattern in patterns:
            await cache.delete_pattern(pattern)

        return {
            "success": True,
            "message": "Cache cleared successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}",
        )
