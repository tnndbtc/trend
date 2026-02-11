"""
Topic endpoints for retrieving clustered content items.

Topics are clusters of related content items before they're ranked into trends.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.schemas.trends import (
    TopicResponse,
    TopicListResponse,
    MetricsResponse,
)
from api.dependencies import (
    optional_api_key,
    get_topic_repository,
    get_cache_repository,
)
from trend_agent.storage.interfaces import (
    TopicRepository,
    CacheRepository,
)
from trend_agent.types import Category, SourceType


router = APIRouter(prefix="/topics", tags=["Topics"])


def topic_to_response(topic) -> TopicResponse:
    """Convert Topic domain model to TopicResponse API schema."""
    return TopicResponse(
        id=topic.id,
        title=topic.title,
        summary=topic.summary,
        category=topic.category.value,
        sources=[s.value for s in topic.sources],
        item_count=topic.item_count,
        total_engagement=MetricsResponse(**topic.total_engagement.dict()),
        first_seen=topic.first_seen,
        last_updated=topic.last_updated,
        language=topic.language,
        keywords=topic.keywords,
    )


@router.get(
    "",
    response_model=TopicListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all topics",
    description="Get a paginated list of topics with optional filtering.",
)
async def list_topics(
    limit: int = Query(20, ge=1, le=100, description="Number of topics to return"),
    offset: int = Query(0, ge=0, description="Number of topics to skip"),
    category: Optional[str] = Query(None, description="Filter by category"),
    source: Optional[str] = Query(None, description="Filter by source"),
    language: Optional[str] = Query(None, description="Filter by language code"),
    keywords: Optional[str] = Query(None, description="Filter by keywords (comma-separated)"),
    api_key: str = Depends(optional_api_key),
    topic_repo: TopicRepository = Depends(get_topic_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> TopicListResponse:
    """
    List topics with pagination and filtering.

    Topics are clusters of related content items that haven't been ranked yet.
    Use the trends endpoint to see ranked topics.

    Args:
        limit: Number of topics to return (1-100)
        offset: Number of topics to skip
        category: Filter by category
        source: Filter by source
        language: Filter by language code
        keywords: Filter by keywords (comma-separated)
        api_key: Optional API key
        topic_repo: Topic repository
        cache: Cache repository

    Returns:
        TopicListResponse with paginated topics
    """
    # Build cache key
    cache_key = f"topics:list:{category or 'all'}:{source or 'all'}:{language or 'all'}:{limit}:{offset}"
    if cache:
        try:
            cached = await cache.get(cache_key)
            if cached:
                return TopicListResponse(**cached)
        except Exception:
            pass

    # Parse filters
    category_filter = Category(category) if category else None
    source_filter = SourceType(source) if source else None
    keyword_list = keywords.split(",") if keywords else None

    # Fetch topics
    topics = await topic_repo.get_all(
        limit=limit,
        offset=offset,
        category=category_filter,
        language=language,
    )

    # Apply keyword filter if specified
    if keyword_list:
        topics = [
            t for t in topics
            if any(kw.lower() in " ".join(t.keywords).lower() for kw in keyword_list)
        ]

    # Apply source filter if specified
    if source_filter:
        topics = [t for t in topics if source_filter in t.sources]

    # Convert to response
    topic_responses = [topic_to_response(t) for t in topics]

    response = TopicListResponse(
        topics=topic_responses,
        total=len(topic_responses),
        limit=limit,
        offset=offset,
        has_more=len(topic_responses) >= limit,
    )

    if cache:
        try:
            await cache.set(cache_key, response.dict(), ttl_seconds=300)
        except Exception:
            pass

    return response


@router.get(
    "/{topic_id}",
    response_model=TopicResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single topic",
    description="Get detailed information about a specific topic by ID.",
)
async def get_topic(
    topic_id: UUID,
    api_key: str = Depends(optional_api_key),
    topic_repo: TopicRepository = Depends(get_topic_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> TopicResponse:
    """
    Get a single topic by ID.

    Args:
        topic_id: UUID of the topic
        api_key: Optional API key
        topic_repo: Topic repository
        cache: Cache repository

    Returns:
        TopicResponse with topic details

    Raises:
        HTTPException: 404 if topic not found
    """
    cache_key = f"topics:detail:{topic_id}"
    if cache:
        try:
            cached = await cache.get(cache_key)
            if cached:
                return TopicResponse(**cached)
        except Exception:
            pass

    topic = await topic_repo.get_by_id(topic_id)

    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic with ID {topic_id} not found",
        )

    response = topic_to_response(topic)

    if cache:
        try:
            await cache.set(cache_key, response.dict(), ttl_seconds=600)
        except Exception:
            pass

    return response


@router.get(
    "/{topic_id}/items",
    response_model=List[dict],
    status_code=status.HTTP_200_OK,
    summary="Get topic items",
    description="Get all content items that belong to a specific topic.",
)
async def get_topic_items(
    topic_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    api_key: str = Depends(optional_api_key),
    topic_repo: TopicRepository = Depends(get_topic_repository),
    cache: Optional[CacheRepository] = Depends(get_cache_repository),
) -> List[dict]:
    """
    Get items belonging to a topic.

    Returns all ProcessedItems that were clustered into this topic.

    Args:
        topic_id: UUID of the topic
        limit: Number of items to return
        offset: Number of items to skip
        api_key: Optional API key
        topic_repo: Topic repository
        cache: Cache repository

    Returns:
        List of items in the topic

    Raises:
        HTTPException: 404 if topic not found
    """
    # Check cache first
    cache_key = f"topics:items:{topic_id}:{limit}:{offset}"
    if cache:
        try:
            cached = await cache.get(cache_key)
            if cached:
                return cached
        except Exception:
            pass

    # Verify topic exists
    topic = await topic_repo.get(topic_id)
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Topic with ID {topic_id} not found",
        )

    # Get items for this topic
    items = await topic_repo.get_items_by_topic(
        topic_id=topic_id,
        limit=limit,
        offset=offset,
    )

    # Convert ProcessedItems to dict format
    items_dict = [
        {
            "id": str(item.id),
            "source": item.source.value,
            "source_id": item.source_id,
            "title": item.title,
            "content": item.content,
            "url": item.url,
            "author": item.author,
            "category": item.category.value,
            "language": item.language,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "processed_at": item.processed_at.isoformat(),
            "engagement": {
                "upvotes": item.engagement.upvotes,
                "downvotes": item.engagement.downvotes,
                "comments": item.engagement.comments,
                "shares": item.engagement.shares,
                "views": item.engagement.views,
                "score": item.engagement.score,
            },
            "keywords": item.keywords,
            "sentiment_score": item.sentiment_score,
        }
        for item in items
    ]

    # Cache the response
    if cache:
        try:
            await cache.set(cache_key, items_dict, ttl_seconds=600)  # 10 min
        except Exception:
            pass

    return items_dict


@router.post(
    "/search",
    response_model=TopicListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search topics",
    description="Search topics by keywords or semantic similarity.",
)
async def search_topics(
    query: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    category: Optional[str] = Query(None, description="Filter by category"),
    language: Optional[str] = Query(None, description="Filter by language"),
    api_key: str = Depends(optional_api_key),
    topic_repo: TopicRepository = Depends(get_topic_repository),
) -> TopicListResponse:
    """
    Search topics by keywords.

    Searches topic titles, summaries, and keywords for matches.

    Args:
        query: Search query string
        limit: Number of results to return
        category: Optional category filter
        language: Optional language filter
        api_key: Optional API key
        topic_repo: Topic repository

    Returns:
        TopicListResponse with matching topics
    """
    # Fetch matching topics
    topics = await topic_repo.search_by_keywords(
        keywords=[query],
        category=Category(category) if category else None,
        language=language,
        limit=limit,
    )

    topic_responses = [topic_to_response(t) for t in topics]

    return TopicListResponse(
        topics=topic_responses,
        total=len(topic_responses),
        limit=limit,
        offset=0,
        has_more=False,
    )
