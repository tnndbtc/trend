"""
Admin endpoints for system management and configuration.

Provides authenticated endpoints for managing collector plugins,
triggering manual operations, and viewing system metrics.
Requires admin API key for access.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import math

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
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
from api.schemas.source import (
    CrawlerSourceCreate,
    CrawlerSourceUpdate,
    CrawlerSourceResponse,
    CrawlerSourceList,
    SourceTestResponse,
    CollectionTriggerRequest as SourceCollectionTriggerRequest,
    CollectionTriggerResponse as SourceCollectionTriggerResponse,
    SourceValidationRequest,
    SourceValidationResponse,
    SourceHealthMetrics,
    SourceFilter,
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


def _get_crawler_source_model():
    """
    Lazy import of Django CrawlerSource model.

    This avoids importing Django at module level, which could cause
    circular dependencies and startup issues.
    """
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
    django.setup()

    from web_interface.trends_viewer.models import CrawlerSource
    return CrawlerSource


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


# ============================================================================
# Crawler Source Management Endpoints
# ============================================================================


def _source_to_response(source) -> CrawlerSourceResponse:
    """Convert Django model to Pydantic response schema."""
    return CrawlerSourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type,
        description=source.description,
        url=source.url,
        enabled=source.enabled,
        schedule=source.schedule,
        collection_interval_hours=source.collection_interval_hours,
        rate_limit=source.rate_limit,
        timeout_seconds=source.timeout_seconds,
        retry_count=source.retry_count,
        backoff_multiplier=source.backoff_multiplier,
        api_key_set=bool(source.api_key_encrypted),
        oauth_config=source.oauth_config,
        custom_headers=source.custom_headers,
        category_filters=source.category_filters,
        keyword_filters=source.keyword_filters,
        language=source.language,
        content_filters=source.content_filters,
        has_custom_code=bool(source.plugin_code),
        config_json=source.config_json,
        health_status=source.health_status,
        last_collection=source.last_collection,
        last_error=source.last_error,
        consecutive_failures=source.consecutive_failures,
        total_collections=source.total_collections,
        successful_collections=source.successful_collections,
        total_items_collected=source.total_items_collected,
        success_rate=source.success_rate,
        created_at=source.created_at,
        updated_at=source.updated_at,
        created_by=source.created_by,
    )


@router.get(
    "/sources",
    response_model=CrawlerSourceList,
    status_code=status.HTTP_200_OK,
    summary="List all crawler sources",
    description="Get a paginated list of all crawler sources with optional filtering.",
)
async def list_sources(
    admin_key: str = Depends(verify_admin_api_key),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    health_status: Optional[str] = Query(None, description="Filter by health status"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
) -> CrawlerSourceList:
    """
    List all crawler sources with filtering and pagination.

    Args:
        admin_key: Admin API key
        enabled: Filter by enabled/disabled
        source_type: Filter by source type
        health_status: Filter by health status
        search: Search term for name/description
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        CrawlerSourceList with paginated results
    """
    # Get model lazily
    CrawlerSource = _get_crawler_source_model()

    # Build query
    queryset = CrawlerSource.objects.all()

    # Apply filters
    if enabled is not None:
        queryset = queryset.filter(enabled=enabled)
    if source_type:
        queryset = queryset.filter(source_type=source_type)
    if health_status:
        queryset = queryset.filter(health_status=health_status)
    if search:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    # Get total count
    total = queryset.count()

    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    # Get paginated results
    sources = list(queryset[offset:offset + page_size])

    # Convert to response models
    source_responses = [_source_to_response(source) for source in sources]

    return CrawlerSourceList(
        sources=source_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/sources",
    response_model=CrawlerSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new crawler source",
    description="Create a new crawler source with the specified configuration.",
)
async def create_source(
    source_data: CrawlerSourceCreate,
    admin_key: str = Depends(verify_admin_api_key),
) -> CrawlerSourceResponse:
    """
    Create a new crawler source.

    Args:
        source_data: Source configuration
        admin_key: Admin API key

    Returns:
        Created CrawlerSourceResponse

    Raises:
        HTTPException: 400 if validation fails or source already exists
    """
    # Get model lazily
    CrawlerSource = _get_crawler_source_model()

    # Check if source with same name exists
    if CrawlerSource.objects.filter(name=source_data.name).exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source with name '{source_data.name}' already exists",
        )

    try:
        # Create new source
        source = CrawlerSource(
            name=source_data.name,
            source_type=source_data.source_type.value,
            description=source_data.description or "",
            url=source_data.url or "",
            enabled=source_data.enabled,
            schedule=source_data.schedule,
            collection_interval_hours=source_data.collection_interval_hours,
            rate_limit=source_data.rate_limit,
            timeout_seconds=source_data.timeout_seconds,
            retry_count=source_data.retry_count,
            backoff_multiplier=source_data.backoff_multiplier,
            oauth_config=source_data.oauth_config,
            custom_headers=source_data.custom_headers,
            category_filters=source_data.category_filters,
            keyword_filters=source_data.keyword_filters,
            language=source_data.language,
            content_filters=source_data.content_filters,
            plugin_code=source_data.plugin_code or "",
            config_json=source_data.config_json,
            created_by=source_data.created_by or "api",
        )

        # Set API key if provided (will be encrypted)
        if source_data.api_key:
            source.api_key = source_data.api_key

        # Save to database (triggers validation)
        source.save()

        return _source_to_response(source)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create source: {str(e)}",
        )


@router.get(
    "/sources/{source_id}",
    response_model=CrawlerSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get crawler source details",
    description="Get detailed information about a specific crawler source.",
)
async def get_source(
    source_id: int,
    admin_key: str = Depends(verify_admin_api_key),
) -> CrawlerSourceResponse:
    """
    Get details for a specific source.

    Args:
        source_id: Source ID
        admin_key: Admin API key

    Returns:
        CrawlerSourceResponse

    Raises:
        HTTPException: 404 if source not found
    """
    # Get model lazily
    CrawlerSource = _get_crawler_source_model()

    try:
        source = CrawlerSource.objects.get(id=source_id)
        return _source_to_response(source)
    except CrawlerSource.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {source_id} not found",
        )


@router.put(
    "/sources/{source_id}",
    response_model=CrawlerSourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update crawler source",
    description="Update an existing crawler source configuration.",
)
async def update_source(
    source_id: int,
    source_data: CrawlerSourceUpdate,
    admin_key: str = Depends(verify_admin_api_key),
) -> CrawlerSourceResponse:
    """
    Update an existing source.

    Args:
        source_id: Source ID to update
        source_data: Updated configuration (partial updates supported)
        admin_key: Admin API key

    Returns:
        Updated CrawlerSourceResponse

    Raises:
        HTTPException: 404 if source not found, 400 if validation fails
    """
    # Get model lazily
    CrawlerSource = _get_crawler_source_model()

    try:
        source = CrawlerSource.objects.get(id=source_id)
    except CrawlerSource.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {source_id} not found",
        )

    try:
        # Update fields (only non-None values)
        update_data = source_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == 'source_type' and value:
                value = value.value  # Convert enum to string
            if field == 'api_key' and value:
                # Handle API key encryption
                source.api_key = value
                continue
            setattr(source, field, value)

        # Save with validation
        source.save()

        return _source_to_response(source)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update source: {str(e)}",
        )


@router.delete(
    "/sources/{source_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Delete crawler source",
    description="Delete a crawler source from the system.",
)
async def delete_source(
    source_id: int,
    admin_key: str = Depends(verify_admin_api_key),
) -> Dict[str, Any]:
    """
    Delete a source.

    Args:
        source_id: Source ID to delete
        admin_key: Admin API key

    Returns:
        Success message

    Raises:
        HTTPException: 404 if source not found
    """
    # Get model lazily
    CrawlerSource = _get_crawler_source_model()

    try:
        source = CrawlerSource.objects.get(id=source_id)
        source_name = source.name
        source.delete()

        return {
            "success": True,
            "message": f"Source '{source_name}' deleted successfully",
        }
    except CrawlerSource.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {source_id} not found",
        )


@router.post(
    "/sources/{source_id}/test",
    response_model=SourceTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Test source connection",
    description="Test the connection to a crawler source.",
)
async def test_source(
    source_id: int,
    admin_key: str = Depends(verify_admin_api_key),
) -> SourceTestResponse:
    """
    Test connection to a source.

    Args:
        source_id: Source ID to test
        admin_key: Admin API key

    Returns:
        SourceTestResponse with test results

    Raises:
        HTTPException: 404 if source not found
    """
    # Get model lazily
    CrawlerSource = _get_crawler_source_model()

    try:
        source = CrawlerSource.objects.get(id=source_id)
    except CrawlerSource.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {source_id} not found",
        )

    # Test connection
    success, message = source.test_connection()

    return SourceTestResponse(
        success=success,
        message=message,
        timestamp=datetime.utcnow(),
    )


@router.post(
    "/sources/trigger",
    response_model=SourceCollectionTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger source collection",
    description="Manually trigger collection from specific sources.",
)
async def trigger_source_collection(
    request: SourceCollectionTriggerRequest,
    background_tasks: BackgroundTasks,
    admin_key: str = Depends(verify_admin_api_key),
) -> SourceCollectionTriggerResponse:
    """
    Trigger manual collection from sources.

    Args:
        request: Collection trigger request with source IDs
        background_tasks: FastAPI background tasks
        admin_key: Admin API key

    Returns:
        SourceCollectionTriggerResponse with status

    Raises:
        HTTPException: 400 if validation fails
    """
    # Get model lazily
    CrawlerSource = _get_crawler_source_model()

    triggered = []
    skipped = []
    errors = {}

    for source_id in request.source_ids:
        try:
            source = CrawlerSource.objects.get(id=source_id)

            if not source.enabled and not request.force:
                skipped.append(source_id)
                continue

            # TODO: Integrate with actual collection system
            # For now, just mark as triggered
            triggered.append(source_id)

            # In production, would:
            # 1. Create Celery task
            # 2. Pass source configuration to collector
            # 3. Run collection asynchronously

        except CrawlerSource.DoesNotExist:
            errors[source_id] = f"Source {source_id} not found"
        except Exception as e:
            errors[source_id] = str(e)

    message = f"Triggered collection for {len(triggered)} source(s)"
    if skipped:
        message += f", skipped {len(skipped)} disabled source(s)"
    if errors:
        message += f", {len(errors)} error(s)"

    return SourceCollectionTriggerResponse(
        triggered=triggered,
        skipped=skipped,
        errors=errors,
        message=message,
    )


@router.post(
    "/sources/validate",
    response_model=SourceValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate source configuration",
    description="Validate source configuration without creating/saving.",
)
async def validate_source(
    request: SourceValidationRequest,
    admin_key: str = Depends(verify_admin_api_key),
) -> SourceValidationResponse:
    """
    Validate source configuration.

    Args:
        request: Validation request with source data
        admin_key: Admin API key

    Returns:
        SourceValidationResponse with validation results
    """
    # Get model lazily
    CrawlerSource = _get_crawler_source_model()

    errors = []
    warnings = []

    source_data = request.source_data

    # Check for required fields based on source type
    if source_data.source_type.value in ['rss', 'google_news', 'bbc', 'reuters', 'ap_news', 'al_jazeera', 'guardian']:
        if not source_data.url:
            errors.append("URL is required for this source type")

    if source_data.source_type.value == 'custom':
        if not source_data.plugin_code:
            errors.append("Plugin code is required for custom source type")

    # Check for existing source with same name
    if CrawlerSource.objects.filter(name=source_data.name).exists():
        errors.append(f"Source with name '{source_data.name}' already exists")

    # Warnings
    if not source_data.rate_limit:
        warnings.append("Rate limit not set - unlimited requests allowed")

    if not source_data.api_key and source_data.source_type.value in ['twitter', 'youtube']:
        warnings.append(f"{source_data.source_type.value} usually requires API authentication")

    return SourceValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.get(
    "/sources/{source_id}/health",
    response_model=SourceHealthMetrics,
    status_code=status.HTTP_200_OK,
    summary="Get source health metrics",
    description="Get detailed health and performance metrics for a source.",
)
async def get_source_health(
    source_id: int,
    admin_key: str = Depends(verify_admin_api_key),
) -> SourceHealthMetrics:
    """
    Get detailed health metrics for a source.

    Args:
        source_id: Source ID
        admin_key: Admin API key

    Returns:
        SourceHealthMetrics with detailed metrics

    Raises:
        HTTPException: 404 if source not found
    """
    # Get model lazily
    CrawlerSource = _get_crawler_source_model()

    try:
        source = CrawlerSource.objects.get(id=source_id)
    except CrawlerSource.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID {source_id} not found",
        )

    # Calculate health score (0-100)
    health_score = 0.0
    if source.total_collections > 0:
        # Success rate contributes 60%
        health_score += source.success_rate * 0.6

        # Recency contributes 20%
        if source.last_collection:
            from django.utils import timezone
            hours_since_last = (timezone.now() - source.last_collection).total_seconds() / 3600
            recency_score = max(0, 100 - (hours_since_last / 24) * 10)  # Decay over days
            health_score += recency_score * 0.2

        # No consecutive failures contributes 20%
        if source.consecutive_failures == 0:
            health_score += 20

    # Calculate average items per collection
    items_per_collection = 0.0
    if source.total_collections > 0:
        items_per_collection = source.total_items_collected / source.total_collections

    return SourceHealthMetrics(
        source_id=source.id,
        source_name=source.name,
        health_status=source.health_status,  # type: ignore
        uptime_percentage=source.success_rate,
        avg_collection_time_seconds=0.0,  # TODO: Track this metric
        items_per_collection=items_per_collection,
        last_24h_collections=0,  # TODO: Query collection runs
        error_rate_24h=0.0,  # TODO: Calculate from recent collections
        current_health_score=health_score,
    )
