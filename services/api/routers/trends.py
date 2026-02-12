"""
Trend endpoints for retrieving and searching trending topics.

Provides REST API endpoints for accessing trend data including
list, detail, search, and statistics operations.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

logger = logging.getLogger(__name__)

from api.schemas.trends import (
    TrendResponse,
    TrendListResponse,
    TrendSearchRequest,
    SimilarTrendsRequest,
    TrendStatsResponse,
    MetricsResponse,
    TopicResponse,
)
from api.dependencies import (
    verify_api_key,
    optional_api_key,
    get_trend_repository,
    get_vector_repository,
    get_cache_repository,
    get_semantic_search_service,
    pagination_params,
)
from trend_agent.storage.interfaces import (
    TrendRepository,
    VectorRepository,
    CacheRepository,
)
from trend_agent.schemas import (
    Category,
    TrendState,
    SourceType,
    TrendFilter,
    SemanticSearchRequest as ServiceSearchRequest,
    SemanticSearchFilter,
)
from trend_agent.services.search import QdrantSemanticSearchService


router = APIRouter(prefix="/trends", tags=["Trends"])


def trend_to_response(trend) -> TrendResponse:
    """Convert Trend domain model to TrendResponse API schema."""
    return TrendResponse(
        id=trend.id,
        topic_id=trend.topic_id,
        rank=trend.rank,
        title=trend.title,
        summary=trend.summary,
        key_points=trend.key_points,
        category=trend.category.value,
        state=trend.state.value,
        score=trend.score,
        sources=[s.value for s in trend.sources],
        item_count=trend.item_count,
        total_engagement=MetricsResponse(**trend.total_engagement.dict()),
        velocity=trend.velocity,
        first_seen=trend.first_seen,
        last_updated=trend.last_updated,
        peak_engagement_at=trend.peak_engagement_at,
        language=trend.language,
        keywords=trend.keywords,
        related_trend_ids=trend.related_trend_ids,
    )


@router.get(
    "",
    response_model=TrendListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all trends",
    description="Get a paginated list of trends with optional filtering by category, source, state, etc.",
)
async def list_trends(
    limit: int = Query(20, ge=1, le=100, description="Number of trends to return"),
    offset: int = Query(0, ge=0, description="Number of trends to skip"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source"),
    state: Optional[str] = Query(None, description="Filter by trend state"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum score"),
    api_key: str = Depends(optional_api_key),
    trend_repo: TrendRepository = Depends(get_trend_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> TrendListResponse:
    """
    List trends with pagination and filtering.

    Returns a paginated list of trends sorted by rank (highest first).
    Supports filtering by category, source, state, language, and minimum score.

    Args:
        limit: Number of trends to return (1-100)
        offset: Number of trends to skip
        category: Filter by category (Technology, Politics, etc.)
        source: Filter by source (reddit, hackernews, etc.)
        state: Filter by trend state (emerging, viral, sustained, declining)
        language: Filter by language code (ISO 639-1, e.g., "en", "es")
        min_score: Minimum trend score (0-100)
        api_key: Optional API key for authentication
        trend_repo: Trend repository dependency
        cache: Cache repository dependency

    Returns:
        TrendListResponse with paginated trends
    """
    # Build filter
    filters = TrendFilter(
        category=Category(category) if category else None,
        sources=[SourceType(source)] if source else None,
        state=TrendState(state) if state else None,
        language=language,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )

    # Try cache first
    cache_key = f"trends:list:{hash(filters.json())}"
    if cache:
        try:
            cached = await cache.get(cache_key)
            if cached:
                return TrendListResponse(**cached)
        except Exception:
            pass  # Continue without cache

    # Fetch from database
    trends = await trend_repo.search(filters)
    total = len(trends)  # TODO: Add count method to repository

    # Convert to response models
    trend_responses = [trend_to_response(t) for t in trends]

    response = TrendListResponse(
        trends=trend_responses,
        total=total,
        limit=limit,
        offset=offset,
        has_more=total > (offset + limit),
    )

    # Cache response
    if cache:
        try:
            await cache.set(cache_key, response.dict(), ttl_seconds=300)  # 5 min cache
        except Exception:
            pass

    return response


@router.get(
    "/top",
    response_model=TrendListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get top trends",
    description="Get the highest-ranked trends across all categories or within a specific category.",
)
async def get_top_trends(
    limit: int = Query(10, ge=1, le=50, description="Number of top trends to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    api_key: str = Depends(optional_api_key),
    trend_repo: TrendRepository = Depends(get_trend_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> TrendListResponse:
    """
    Get top-ranked trends.

    Returns the highest-scored trends, optionally filtered by category.
    Results are sorted by rank (1 = highest).

    Args:
        limit: Number of top trends to return (1-50)
        category: Optional category filter
        api_key: Optional API key
        trend_repo: Trend repository
        cache: Cache repository

    Returns:
        TrendListResponse with top trends
    """
    cache_key = f"trends:top:{category or 'all'}:{limit}"
    if cache:
        try:
            cached = await cache.get(cache_key)
            if cached:
                return TrendListResponse(**cached)
        except Exception:
            pass

    trends = await trend_repo.get_top_trends(
        limit=limit,
        category=Category(category) if category else None,
    )

    trend_responses = [trend_to_response(t) for t in trends]

    response = TrendListResponse(
        trends=trend_responses,
        total=len(trend_responses),
        limit=limit,
        offset=0,
        has_more=False,
    )

    if cache:
        try:
            await cache.set(cache_key, response.dict(), ttl_seconds=300)
        except Exception:
            pass

    return response


@router.get(
    "/{trend_id}",
    response_model=TrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single trend",
    description="Get detailed information about a specific trend by ID.",
)
async def get_trend(
    trend_id: UUID,
    api_key: str = Depends(optional_api_key),
    trend_repo: TrendRepository = Depends(get_trend_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> TrendResponse:
    """
    Get a single trend by ID.

    Args:
        trend_id: UUID of the trend
        api_key: Optional API key
        trend_repo: Trend repository
        cache: Cache repository

    Returns:
        TrendResponse with trend details

    Raises:
        HTTPException: 404 if trend not found
    """
    cache_key = f"trends:detail:{trend_id}"
    if cache:
        try:
            cached = await cache.get(cache_key)
            if cached:
                return TrendResponse(**cached)
        except Exception:
            pass

    trend = await trend_repo.get_by_id(trend_id)

    if trend is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trend with ID {trend_id} not found",
        )

    response = trend_to_response(trend)

    if cache:
        try:
            await cache.set(cache_key, response.dict(), ttl_seconds=600)  # 10 min
        except Exception:
            pass

    return response


@router.post(
    "/search",
    response_model=TrendListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search trends",
    description="Semantic search for trends using vector similarity.",
)
async def search_trends(
    search_request: TrendSearchRequest,
    api_key: str = Depends(verify_api_key),
    trend_repo: TrendRepository = Depends(get_trend_repository),
    vector_repo: Optional[VectorRepository] = Depends(get_vector_repository),
) -> TrendListResponse:
    """
    Semantic search for trends.

    Uses vector similarity search to find trends semantically similar to the query.
    Requires an embedding service to be configured.

    Args:
        search_request: Search query and filters
        api_key: API key (required)
        trend_repo: Trend repository
        vector_repo: Vector repository for semantic search

    Returns:
        TrendListResponse with matching trends

    Raises:
        HTTPException: 503 if vector search is unavailable
    """
    if vector_repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic search is currently unavailable. Vector database not connected.",
        )

    try:
        # Get semantic search service
        from api.dependencies import get_semantic_search_service as get_search_svc
        search_service = await get_search_svc(trend_repo, vector_repo)

        # Build filters from request
        filters = SemanticSearchFilter()

        if search_request.category:
            try:
                filters.category = Category(search_request.category)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {search_request.category}"
                )

        if search_request.sources:
            try:
                filters.sources = [SourceType(s) for s in search_request.sources]
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid source: {str(e)}"
                )

        if search_request.state:
            try:
                filters.state = TrendState(search_request.state)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid state: {search_request.state}"
                )

        if search_request.language:
            filters.language = search_request.language

        if search_request.min_score:
            filters.min_score = search_request.min_score

        if search_request.date_from:
            filters.date_from = search_request.date_from

        if search_request.date_to:
            filters.date_to = search_request.date_to

        # Create service search request
        service_request = ServiceSearchRequest(
            query=search_request.query,
            limit=search_request.limit,
            min_similarity=search_request.min_similarity,
            filters=filters,
        )

        # Perform semantic search
        trends = await search_service.search(service_request)

        # Convert to response models
        trend_responses = [trend_to_response(t) for t in trends]

        return TrendListResponse(
            trends=trend_responses,
            total=len(trend_responses),
            limit=search_request.limit,
            offset=0,
            has_more=False,  # Semantic search doesn't use offset pagination
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trend semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trend semantic search failed: {str(e)}"
        )


@router.get(
    "/{trend_id}/similar",
    response_model=TrendListResponse,
    status_code=status.HTTP_200_OK,
    summary="Find similar trends",
    description="Find trends similar to a specific trend using vector similarity.",
)
async def get_similar_trends(
    trend_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Number of similar trends"),
    min_similarity: float = Query(0.7, ge=0.0, le=1.0, description="Minimum similarity score"),
    api_key: str = Depends(optional_api_key),
    trend_repo: TrendRepository = Depends(get_trend_repository),
    vector_repo: Optional[VectorRepository] = Depends(get_vector_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> TrendListResponse:
    """
    Find similar trends to a given trend.

    Uses vector similarity to find related trends.

    Args:
        trend_id: UUID of the reference trend
        limit: Number of similar trends to return
        min_similarity: Minimum similarity score (0.0-1.0)
        api_key: Optional API key
        trend_repo: Trend repository
        vector_repo: Vector repository
        cache: Cache repository

    Returns:
        TrendListResponse with similar trends

    Raises:
        HTTPException: 404 if trend not found, 503 if vector search unavailable
    """
    # Get the source trend
    trend = await trend_repo.get(trend_id)
    if trend is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trend with ID {trend_id} not found",
        )

    if vector_repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Similarity search is currently unavailable. Vector database not connected.",
        )

    try:
        # Check cache first
        cache_key = f"trends:similar:{trend_id}:{limit}:{min_similarity}"
        if cache:
            try:
                cached = await cache.get(cache_key)
                if cached:
                    return TrendListResponse(**cached)
            except Exception:
                pass

        # Get the trend's vector from vector repository
        vector_id = f"trend:{trend_id}"
        vector_data = await vector_repo.get(vector_id)

        if vector_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vector embedding not found for trend {trend_id}. The trend may not have been indexed yet.",
            )

        trend_vector, _ = vector_data

        # Search for similar vectors
        matches = await vector_repo.search(
            vector=trend_vector,
            limit=limit + 1,  # +1 to account for the source trend itself
            min_score=min_similarity,
        )

        # Filter out the source trend and extract trend IDs
        similar_trend_ids = [
            UUID(match.id.replace("trend:", ""))
            for match in matches
            if match.id != vector_id
        ][:limit]

        # Fetch full trend data
        similar_trends = []
        for tid in similar_trend_ids:
            t = await trend_repo.get(tid)
            if t:
                similar_trends.append(t)

        # Convert to response models
        trend_responses = [trend_to_response(t) for t in similar_trends]

        response = TrendListResponse(
            trends=trend_responses,
            total=len(trend_responses),
            limit=limit,
            offset=0,
            has_more=False,
        )

        # Cache the response
        if cache:
            try:
                await cache.set(cache_key, response.dict(), ttl_seconds=600)  # 10 min
            except Exception:
                pass

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar trends search failed for {trend_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find similar trends: {str(e)}"
        )


@router.get(
    "/stats/overview",
    response_model=TrendStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get trend statistics",
    description="Get aggregate statistics about trends including counts by category, state, and source.",
)
async def get_trend_stats(
    api_key: str = Depends(optional_api_key),
    trend_repo: TrendRepository = Depends(get_trend_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> TrendStatsResponse:
    """
    Get trend statistics and analytics.

    Returns aggregate statistics including:
    - Total trends, topics, and items
    - Breakdown by category, state, and source
    - Average engagement metrics

    Args:
        api_key: Optional API key
        trend_repo: Trend repository
        cache: Cache repository

    Returns:
        TrendStatsResponse with statistics
    """
    cache_key = "trends:stats:overview"
    if cache:
        try:
            cached = await cache.get(cache_key)
            if cached:
                return TrendStatsResponse(**cached)
        except Exception:
            pass

    # Fetch all trends (consider pagination for large datasets)
    all_trends = await trend_repo.search(TrendFilter(limit=10000))

    # Calculate statistics
    total_trends = len(all_trends)
    total_topics = len(set(t.topic_id for t in all_trends))
    total_items = sum(t.item_count for t in all_trends)

    # Group by category
    trends_by_category = {}
    for trend in all_trends:
        cat = trend.category.value
        trends_by_category[cat] = trends_by_category.get(cat, 0) + 1

    # Group by state
    trends_by_state = {}
    for trend in all_trends:
        st = trend.state.value
        trends_by_state[st] = trends_by_state.get(st, 0) + 1

    # Group by source (count unique sources per trend)
    trends_by_source = {}
    for trend in all_trends:
        for source in trend.sources:
            src = source.value
            trends_by_source[src] = trends_by_source.get(src, 0) + 1

    # Calculate average engagement
    if total_trends > 0:
        avg_upvotes = sum(t.total_engagement.upvotes for t in all_trends) // total_trends
        avg_comments = sum(t.total_engagement.comments for t in all_trends) // total_trends
        avg_views = sum(t.total_engagement.views for t in all_trends) // total_trends
        avg_score = sum(t.total_engagement.score for t in all_trends) / total_trends
    else:
        avg_upvotes = avg_comments = avg_views = 0
        avg_score = 0.0

    response = TrendStatsResponse(
        total_trends=total_trends,
        total_topics=total_topics,
        total_items=total_items,
        trends_by_category=trends_by_category,
        trends_by_state=trends_by_state,
        trends_by_source=trends_by_source,
        average_engagement=MetricsResponse(
            upvotes=avg_upvotes,
            comments=avg_comments,
            views=avg_views,
            score=avg_score,
        ),
    )

    if cache:
        try:
            await cache.set(cache_key, response.dict(), ttl_seconds=600)  # 10 min
        except Exception:
            pass

    return response
