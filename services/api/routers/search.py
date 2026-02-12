"""
Search endpoints for semantic and keyword-based search across all content.

Provides unified search across trends, topics, and items using
both keyword matching and vector similarity.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.schemas.trends import TrendResponse, TopicResponse, MetricsResponse
from api.dependencies import (
    verify_api_key,
    get_trend_repository,
    get_topic_repository,
    get_vector_repository,
    get_cache_repository,
    get_semantic_search_service,
)
from trend_agent.storage.interfaces import (
    TrendRepository,
    TopicRepository,
    VectorRepository,
    CacheRepository,
)
from trend_agent.schemas import (
    Category,
    SourceType,
    SemanticSearchRequest as ServiceSearchRequest,
    SemanticSearchFilter,
)
from trend_agent.services.search import QdrantSemanticSearchService


router = APIRouter(prefix="/search", tags=["Search"])

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


class SemanticSearchRequest(BaseModel):
    """Request for semantic search."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    sources: Optional[List[str]] = Field(None, description="Filter by sources")
    language: Optional[str] = Field(None, description="Filter by language")
    limit: int = Field(20, ge=1, le=100, description="Number of results")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")
    search_type: str = Field("trends", description="Search type: trends, topics, or all")


class KeywordSearchRequest(BaseModel):
    """Request for keyword search."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    sources: Optional[List[str]] = Field(None, description="Filter by sources")
    language: Optional[str] = Field(None, description="Filter by language")
    limit: int = Field(20, ge=1, le=100, description="Number of results")
    search_type: str = Field("all", description="Search type: trends, topics, or all")


class SearchResult(BaseModel):
    """Unified search result."""

    type: str = Field(..., description="Result type: trend or topic")
    id: UUID = Field(..., description="Result ID")
    title: str = Field(..., description="Result title")
    summary: str = Field(..., description="Result summary")
    category: str = Field(..., description="Result category")
    score: float = Field(..., description="Relevance or similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchResponse(BaseModel):
    """Search results response."""

    results: List[SearchResult] = Field(..., description="Search results")
    total: int = Field(..., ge=0, description="Total number of results")
    query: str = Field(..., description="Original search query")
    search_type: str = Field(..., description="Search type used")


@router.post(
    "/semantic",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic search",
    description="Search using vector similarity across trends and topics.",
)
@limiter.limit("30/minute")  # Rate limit: 30 requests per minute
async def semantic_search(
    request: Request,
    search_request: SemanticSearchRequest,
    api_key: str = Depends(verify_api_key),
    trend_repo: TrendRepository = Depends(get_trend_repository),
    topic_repo: TopicRepository = Depends(get_topic_repository),
    vector_repo: Optional[VectorRepository] = Depends(get_vector_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> SearchResponse:
    """
    Semantic search using vector similarity.

    Converts the search query to a vector embedding and finds
    semantically similar trends and/or topics.

    Args:
        search_request: Search query and parameters
        api_key: API key (required)
        trend_repo: Trend repository
        topic_repo: Topic repository
        vector_repo: Vector repository for similarity search
        cache: Cache repository

    Returns:
        SearchResponse with semantically similar results

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

        # Build filters
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

        if search_request.language:
            filters.language = search_request.language

        # Create service search request
        service_request = ServiceSearchRequest(
            query=search_request.query,
            limit=search_request.limit,
            min_similarity=search_request.min_similarity,
            filters=filters,
        )

        # Perform semantic search
        trends = await search_service.search(service_request)

        # Convert trends to search results
        results = [
            SearchResult(
                type="trend",
                id=trend.id,
                title=trend.title,
                summary=trend.summary,
                category=trend.category.value,
                score=trend.score,
                metadata={
                    "sources": [s.value for s in trend.sources],
                    "language": trend.language,
                    "state": trend.state.value,
                    "rank": trend.rank,
                    "item_count": trend.item_count,
                }
            )
            for trend in trends
        ]

        return SearchResponse(
            results=results,
            total=len(results),
            query=search_request.query,
            search_type=search_request.search_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )


@router.post(
    "/keyword",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Keyword search",
    description="Search using keyword matching across trends and topics.",
)
@limiter.limit("60/minute")  # Rate limit: 60 requests per minute (less expensive than semantic)
async def keyword_search(
    request: Request,
    search_request: KeywordSearchRequest,
    api_key: str = Depends(verify_api_key),
    trend_repo: TrendRepository = Depends(get_trend_repository),
    topic_repo: TopicRepository = Depends(get_topic_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> SearchResponse:
    """
    Keyword-based search.

    Searches titles, summaries, and keywords for exact or fuzzy matches.

    Args:
        search_request: Search query and parameters
        api_key: API key (required)
        trend_repo: Trend repository
        topic_repo: Topic repository
        cache: Cache repository

    Returns:
        SearchResponse with matching results
    """
    query_lower = search_request.query.lower()
    results = []

    # Search trends if requested
    if search_request.search_type in ["trends", "all"]:
        from trend_agent.schemas import TrendFilter

        trend_filter = TrendFilter(
            category=Category(search_request.category) if search_request.category else None,
            sources=[SourceType(s) for s in search_request.sources] if search_request.sources else None,
            language=search_request.language,
            keywords=[search_request.query],
            limit=search_request.limit,
        )

        trends = await trend_repo.search(trend_filter)

        for trend in trends:
            # Check if query matches title, summary, or keywords
            if (
                query_lower in trend.title.lower()
                or query_lower in trend.summary.lower()
                or any(query_lower in kw.lower() for kw in trend.keywords)
            ):
                results.append(
                    SearchResult(
                        type="trend",
                        id=trend.id,
                        title=trend.title,
                        summary=trend.summary,
                        category=trend.category.value,
                        score=trend.score,
                        metadata={
                            "rank": trend.rank,
                            "state": trend.state.value,
                            "sources": [s.value for s in trend.sources],
                            "item_count": trend.item_count,
                        },
                    )
                )

    # Search topics if requested
    if search_request.search_type in ["topics", "all"]:
        topics = await topic_repo.search_by_keywords(
            keywords=[search_request.query],
            category=Category(search_request.category) if search_request.category else None,
            language=search_request.language,
            limit=search_request.limit,
        )

        for topic in topics:
            if (
                query_lower in topic.title.lower()
                or query_lower in topic.summary.lower()
                or any(query_lower in kw.lower() for kw in topic.keywords)
            ):
                results.append(
                    SearchResult(
                        type="topic",
                        id=topic.id,
                        title=topic.title,
                        summary=topic.summary,
                        category=topic.category.value,
                        score=topic.total_engagement.score,
                        metadata={
                            "sources": [s.value for s in topic.sources],
                            "item_count": topic.item_count,
                        },
                    )
                )

    # Sort by score and limit results
    results.sort(key=lambda x: x.score, reverse=True)
    results = results[:search_request.limit]

    return SearchResponse(
        results=results,
        total=len(results),
        query=search_request.query,
        search_type=search_request.search_type,
    )


@router.get(
    "/suggestions",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    summary="Get search suggestions",
    description="Get autocomplete suggestions for search queries.",
)
async def get_search_suggestions(
    query: str = Query(..., min_length=2, max_length=100, description="Partial search query"),
    limit: int = Query(10, ge=1, le=20, description="Number of suggestions"),
    api_key: str = Depends(verify_api_key),
    trend_repo: TrendRepository = Depends(get_trend_repository),
    topic_repo: TopicRepository = Depends(get_topic_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> List[str]:
    """
    Get autocomplete suggestions for search queries.

    Returns popular keywords and titles that match the partial query.

    Args:
        query: Partial search query
        limit: Number of suggestions to return
        api_key: API key (required)
        trend_repo: Trend repository
        topic_repo: Topic repository
        cache: Cache repository

    Returns:
        List of suggested search queries
    """
    cache_key = f"search:suggestions:{query.lower()}:{limit}"
    if cache:
        try:
            cached = await cache.get(cache_key)
            if cached:
                return cached
        except Exception:
            pass

    suggestions = set()
    query_lower = query.lower()

    # Get recent trends
    from trend_agent.schemas import TrendFilter

    trends = await trend_repo.get_top_trends(limit=50)

    # Extract matching keywords and titles
    for trend in trends:
        # Check title
        if query_lower in trend.title.lower():
            suggestions.add(trend.title)

        # Check keywords
        for kw in trend.keywords:
            if query_lower in kw.lower():
                suggestions.add(kw)

        if len(suggestions) >= limit:
            break

    # Convert to sorted list
    result = sorted(list(suggestions))[:limit]

    if cache:
        try:
            await cache.set(cache_key, result, ttl_seconds=600)  # 10 min
        except Exception:
            pass

    return result
