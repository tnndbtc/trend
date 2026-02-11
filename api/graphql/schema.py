"""
GraphQL Schema for Trend Intelligence Platform.

Provides GraphQL API alongside REST for flexible querying.
"""

import strawberry
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from trend_agent.types import TrendState, Category, SourceType


# ============================================================================
# GraphQL Types
# ============================================================================


@strawberry.type
class MetricsType:
    """Engagement metrics."""

    upvotes: int
    downvotes: int
    comments: int
    shares: int
    views: int
    score: float


@strawberry.type
class TrendType:
    """Trend object for GraphQL."""

    id: strawberry.ID
    topic_id: strawberry.ID
    rank: int
    title: str
    summary: str
    key_points: List[str]
    category: str
    state: str
    score: float
    sources: List[str]
    item_count: int
    velocity: float
    first_seen: datetime
    last_updated: datetime
    language: str
    keywords: List[str]


@strawberry.type
class TopicType:
    """Topic object for GraphQL."""

    id: strawberry.ID
    title: str
    summary: str
    category: str
    sources: List[str]
    item_count: int
    first_seen: datetime
    last_updated: datetime
    language: str
    keywords: List[str]


@strawberry.type
class SearchResultType:
    """Search result for GraphQL."""

    type: str
    id: strawberry.ID
    title: str
    summary: str
    category: str
    score: float


# ============================================================================
# Input Types
# ============================================================================


@strawberry.input
class TrendFilterInput:
    """Filter criteria for trends."""

    category: Optional[str] = None
    state: Optional[str] = None
    language: Optional[str] = None
    min_score: Optional[float] = None
    limit: int = 20


@strawberry.input
class SearchInput:
    """Search input parameters."""

    query: str
    limit: int = 20
    min_similarity: float = 0.7


# ============================================================================
# Queries
# ============================================================================


@strawberry.type
class Query:
    """GraphQL query root."""

    @strawberry.field
    async def trends(
        self,
        filter: Optional[TrendFilterInput] = None,
    ) -> List[TrendType]:
        """
        Get list of trends with optional filtering.

        Args:
            filter: Optional filter criteria

        Returns:
            List of trends
        """
        from api.dependencies import get_trend_repository
        from trend_agent.types import TrendFilter

        # Get repository
        trend_repo = get_trend_repository()

        # Build filter
        trend_filter = TrendFilter(
            category=Category(filter.category) if filter and filter.category else None,
            state=TrendState(filter.state) if filter and filter.state else None,
            language=filter.language if filter else None,
            min_score=filter.min_score if filter else None,
            limit=filter.limit if filter else 20,
        )

        # Fetch trends
        trends = await trend_repo.search(trend_filter)

        # Convert to GraphQL types
        return [
            TrendType(
                id=strawberry.ID(str(t.id)),
                topic_id=strawberry.ID(str(t.topic_id)),
                rank=t.rank,
                title=t.title,
                summary=t.summary,
                key_points=t.key_points,
                category=t.category.value,
                state=t.state.value,
                score=t.score,
                sources=[s.value for s in t.sources],
                item_count=t.item_count,
                velocity=t.velocity,
                first_seen=t.first_seen,
                last_updated=t.last_updated,
                language=t.language,
                keywords=t.keywords,
            )
            for t in trends
        ]

    @strawberry.field
    async def trend(self, id: strawberry.ID) -> Optional[TrendType]:
        """
        Get a specific trend by ID.

        Args:
            id: Trend UUID

        Returns:
            Trend or None
        """
        from api.dependencies import get_trend_repository
        from uuid import UUID

        trend_repo = get_trend_repository()
        trend = await trend_repo.get(UUID(id))

        if not trend:
            return None

        return TrendType(
            id=strawberry.ID(str(trend.id)),
            topic_id=strawberry.ID(str(trend.topic_id)),
            rank=trend.rank,
            title=trend.title,
            summary=trend.summary,
            key_points=trend.key_points,
            category=trend.category.value,
            state=trend.state.value,
            score=trend.score,
            sources=[s.value for s in trend.sources],
            item_count=trend.item_count,
            velocity=trend.velocity,
            first_seen=trend.first_seen,
            last_updated=trend.last_updated,
            language=trend.language,
            keywords=trend.keywords,
        )

    @strawberry.field
    async def search(self, input: SearchInput) -> List[SearchResultType]:
        """
        Semantic search across trends.

        Args:
            input: Search parameters

        Returns:
            List of search results
        """
        from api.dependencies import (
            get_trend_repository,
            get_vector_repository,
            get_semantic_search_service,
        )
        from trend_agent.types import SemanticSearchRequest

        trend_repo = get_trend_repository()
        vector_repo = get_vector_repository()

        if not vector_repo:
            return []

        # Get search service
        search_service = await get_semantic_search_service(trend_repo, vector_repo)

        # Create search request
        request = SemanticSearchRequest(
            query=input.query,
            limit=input.limit,
            min_similarity=input.min_similarity,
        )

        # Perform search
        trends = await search_service.search(request)

        # Convert to GraphQL types
        return [
            SearchResultType(
                type="trend",
                id=strawberry.ID(str(t.id)),
                title=t.title,
                summary=t.summary,
                category=t.category.value,
                score=t.score,
            )
            for t in trends
        ]


# ============================================================================
# Mutations
# ============================================================================


@strawberry.type
class Mutation:
    """GraphQL mutation root."""

    @strawberry.field
    async def trigger_collection(self, plugin_name: Optional[str] = None) -> str:
        """
        Trigger data collection.

        Args:
            plugin_name: Optional specific plugin to collect from

        Returns:
            Status message
        """
        from trend_agent.tasks.collection import (
            collect_from_plugin_task,
            collect_all_plugins_task,
        )

        if plugin_name:
            task = collect_from_plugin_task.delay(plugin_name)
            return f"Collection started for {plugin_name}: {task.id}"
        else:
            task = collect_all_plugins_task.delay()
            return f"Collection started for all plugins: {task.id}"


# ============================================================================
# Schema
# ============================================================================


schema = strawberry.Schema(query=Query, mutation=Mutation)
