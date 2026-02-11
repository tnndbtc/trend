"""
PostgreSQL repository implementations.

This module provides asyncpg-based implementations of the storage interfaces
for PostgreSQL database operations.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg
from asyncpg import Pool

from trend_agent.storage.interfaces import (
    BaseTrendRepository,
    ConnectionError,
    IntegrityError,
    ItemRepository,
    NotFoundError,
    StorageError,
    TopicRepository,
)
from trend_agent.types import (
    Category,
    Metrics,
    PluginHealth,
    ProcessedItem,
    SourceType,
    Topic,
    Trend,
    TrendFilter,
    TrendState,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Connection Pool Management
# ============================================================================


class PostgreSQLConnectionPool:
    """
    Manages PostgreSQL connection pool lifecycle.

    This class handles the creation and cleanup of asyncpg connection pools,
    providing a single shared pool for all repository instances.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "trends",
        user: str = "trend_user",
        password: str = "trend_password",
        min_size: int = 10,
        max_size: int = 20,
    ):
        """
        Initialize connection pool configuration.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            min_size: Minimum pool size
            max_size: Maximum pool size
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_size = min_size
        self.max_size = max_size
        self._pool: Optional[Pool] = None

    async def connect(self) -> Pool:
        """
        Create and return a connection pool.

        Returns:
            asyncpg connection pool

        Raises:
            ConnectionError: If connection fails
        """
        if self._pool is not None:
            return self._pool

        try:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=60,
            )
            logger.info(
                f"PostgreSQL connection pool created: {self.host}:{self.port}/{self.database}"
            )
            return self._pool
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise ConnectionError(f"Database connection failed: {e}")

    async def close(self):
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")

    @property
    def pool(self) -> Optional[Pool]:
        """Get the current pool instance."""
        return self._pool


# ============================================================================
# Helper Functions
# ============================================================================


def _metrics_to_jsonb(metrics: Metrics) -> str:
    """Convert Metrics to JSONB-compatible JSON string."""
    return json.dumps(metrics.dict())


def _jsonb_to_metrics(jsonb_data: str) -> Metrics:
    """Convert JSONB string to Metrics object."""
    if isinstance(jsonb_data, str):
        data = json.loads(jsonb_data)
    else:
        data = jsonb_data
    return Metrics(**data)


def _row_to_trend(row: asyncpg.Record) -> Trend:
    """Convert database row to Trend object."""
    return Trend(
        id=row["id"],
        topic_id=row["topic_id"],
        rank=row["rank"],
        title=row["title"],
        summary=row["summary"],
        key_points=row["key_points"] or [],
        category=Category(row["category"]),
        state=TrendState(row["state"]),
        score=row["score"],
        sources=[SourceType(s) for s in row["sources"]],
        item_count=row["item_count"],
        velocity=row["velocity"],
        language=row["language"],
        keywords=row["keywords"] or [],
        related_trend_ids=row["related_trend_ids"] or [],
        total_engagement=_jsonb_to_metrics(row["total_engagement"]),
        first_seen=row["first_seen"],
        last_updated=row["last_updated"],
        peak_engagement_at=row.get("peak_engagement_at"),
        metadata=row["metadata"] or {},
    )


def _row_to_topic(row: asyncpg.Record) -> Topic:
    """Convert database row to Topic object."""
    return Topic(
        id=row["id"],
        title=row["title"],
        summary=row["summary"],
        category=Category(row["category"]),
        sources=[SourceType(s) for s in row["sources"]],
        item_count=row["item_count"],
        language=row["language"],
        keywords=row["keywords"] or [],
        total_engagement=_jsonb_to_metrics(row["total_engagement"]),
        first_seen=row["first_seen"],
        last_updated=row["last_updated"],
        metadata=row["metadata"] or {},
    )


def _row_to_processed_item(row: asyncpg.Record) -> ProcessedItem:
    """Convert database row to ProcessedItem object."""
    # Parse metadata if it's a JSON string
    metadata = row["metadata"]
    if isinstance(metadata, str):
        metadata = json.loads(metadata) if metadata else {}
    elif metadata is None:
        metadata = {}

    return ProcessedItem(
        id=row["id"],
        source=SourceType(row["source"]),
        source_id=row["source_id"],
        url=row["url"],
        title=row["title"],
        title_normalized=row["title_normalized"],
        description=row.get("description"),
        content=row.get("content"),
        content_normalized=row.get("content_normalized"),
        language=row["language"],
        author=row.get("author"),
        category=Category(row["category"]) if row.get("category") else None,
        metrics=_jsonb_to_metrics(row["metrics"]),
        published_at=row["published_at"],
        collected_at=row["collected_at"],
        metadata=metadata,
    )


# ============================================================================
# Repository Implementations
# ============================================================================


class PostgreSQLTrendRepository(BaseTrendRepository):
    """PostgreSQL implementation of TrendRepository."""

    def __init__(self, pool: Pool):
        """
        Initialize repository with a connection pool.

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def save(self, trend: Trend) -> UUID:
        """
        Save a trend to the database.

        Args:
            trend: The trend to save

        Returns:
            UUID of the saved trend

        Raises:
            StorageError: If save operation fails
        """
        try:
            query = """
                INSERT INTO trends (
                    id, topic_id, rank, title, summary, key_points, category,
                    state, score, sources, item_count, velocity, language,
                    keywords, related_trend_ids, total_engagement,
                    first_seen, last_updated, peak_engagement_at, metadata
                ) VALUES (
                    COALESCE($1, uuid_generate_v4()), $2, $3, $4, $5, $6, $7,
                    $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                )
                ON CONFLICT (id) DO UPDATE SET
                    rank = EXCLUDED.rank,
                    title = EXCLUDED.title,
                    summary = EXCLUDED.summary,
                    key_points = EXCLUDED.key_points,
                    state = EXCLUDED.state,
                    score = EXCLUDED.score,
                    sources = EXCLUDED.sources,
                    item_count = EXCLUDED.item_count,
                    velocity = EXCLUDED.velocity,
                    keywords = EXCLUDED.keywords,
                    related_trend_ids = EXCLUDED.related_trend_ids,
                    total_engagement = EXCLUDED.total_engagement,
                    peak_engagement_at = EXCLUDED.peak_engagement_at,
                    metadata = EXCLUDED.metadata
                RETURNING id
            """

            sources_array = [s.value for s in trend.sources]
            engagement_json = _metrics_to_jsonb(trend.total_engagement)

            trend_id = await self.pool.fetchval(
                query,
                trend.id,
                trend.topic_id,
                trend.rank,
                trend.title,
                trend.summary,
                trend.key_points,
                trend.category.value,
                trend.state.value,
                trend.score,
                sources_array,
                trend.item_count,
                trend.velocity,
                trend.language,
                trend.keywords,
                trend.related_trend_ids,
                engagement_json,
                trend.first_seen,
                trend.last_updated,
                trend.peak_engagement_at,
                json.dumps(trend.metadata),
            )

            logger.debug(f"Saved trend {trend_id}: {trend.title}")
            return trend_id

        except Exception as e:
            logger.error(f"Failed to save trend: {e}")
            raise StorageError(f"Failed to save trend: {e}")

    async def get(self, trend_id: UUID) -> Optional[Trend]:
        """
        Retrieve a trend by ID.

        Args:
            trend_id: UUID of the trend

        Returns:
            The trend if found, None otherwise
        """
        try:
            query = "SELECT * FROM trends WHERE id = $1"
            row = await self.pool.fetchrow(query, trend_id)

            if row is None:
                return None

            return _row_to_trend(row)

        except Exception as e:
            logger.error(f"Failed to get trend {trend_id}: {e}")
            raise StorageError(f"Failed to get trend: {e}")

    async def search(self, filters: TrendFilter) -> List[Trend]:
        """
        Search trends with filters.

        Args:
            filters: Search filter criteria

        Returns:
            List of matching trends
        """
        try:
            # Build dynamic query based on filters
            conditions = []
            params = []
            param_count = 0

            if filters.category:
                param_count += 1
                conditions.append(f"category = ${param_count}")
                params.append(filters.category.value)

            if filters.sources:
                param_count += 1
                source_values = [s.value for s in filters.sources]
                conditions.append(f"sources && ${param_count}")
                params.append(source_values)

            if filters.state:
                param_count += 1
                conditions.append(f"state = ${param_count}")
                params.append(filters.state.value)

            if filters.min_score is not None:
                param_count += 1
                conditions.append(f"score >= ${param_count}")
                params.append(filters.min_score)

            if filters.max_score is not None:
                param_count += 1
                conditions.append(f"score <= ${param_count}")
                params.append(filters.max_score)

            if filters.language:
                param_count += 1
                conditions.append(f"language = ${param_count}")
                params.append(filters.language)

            if filters.date_from:
                param_count += 1
                conditions.append(f"first_seen >= ${param_count}")
                params.append(filters.date_from)

            if filters.date_to:
                param_count += 1
                conditions.append(f"first_seen <= ${param_count}")
                params.append(filters.date_to)

            if filters.keywords:
                param_count += 1
                conditions.append(f"keywords && ${param_count}")
                params.append(filters.keywords)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f"""
                SELECT * FROM trends
                WHERE {where_clause}
                ORDER BY rank, score DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            params.extend([filters.limit, filters.offset])

            rows = await self.pool.fetch(query, *params)
            return [_row_to_trend(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to search trends: {e}")
            raise StorageError(f"Failed to search trends: {e}")

    async def update(self, trend_id: UUID, updates: Dict[str, Any]) -> bool:
        """
        Update a trend.

        Args:
            trend_id: UUID of the trend to update
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if not found
        """
        try:
            # Build dynamic update query
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")

                # Handle special types
                if key == "total_engagement" and isinstance(value, Metrics):
                    params.append(_metrics_to_jsonb(value))
                elif key in ("category", "state"):
                    params.append(value.value if hasattr(value, "value") else value)
                elif key == "sources" and isinstance(value, list):
                    params.append([s.value if hasattr(s, "value") else s for s in value])
                elif key == "metadata":
                    params.append(json.dumps(value))
                else:
                    params.append(value)

            if not set_clauses:
                return False

            set_clause = ", ".join(set_clauses)
            param_count += 1
            query = f"""
                UPDATE trends
                SET {set_clause}
                WHERE id = ${param_count}
            """
            params.append(trend_id)

            result = await self.pool.execute(query, *params)
            updated = result.split()[-1] == "1"

            if updated:
                logger.debug(f"Updated trend {trend_id}")

            return updated

        except Exception as e:
            logger.error(f"Failed to update trend {trend_id}: {e}")
            raise StorageError(f"Failed to update trend: {e}")

    async def delete(self, trend_id: UUID) -> bool:
        """
        Delete a trend.

        Args:
            trend_id: UUID of the trend to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            query = "DELETE FROM trends WHERE id = $1"
            result = await self.pool.execute(query, trend_id)
            deleted = result.split()[-1] == "1"

            if deleted:
                logger.debug(f"Deleted trend {trend_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete trend {trend_id}: {e}")
            raise StorageError(f"Failed to delete trend: {e}")

    async def get_top_trends(
        self,
        limit: int = 10,
        category: Optional[str] = None,
        date_from: Optional[datetime] = None,
    ) -> List[Trend]:
        """
        Get top-ranked trends.

        Args:
            limit: Maximum number of trends to return
            category: Optional category filter
            date_from: Optional date filter

        Returns:
            List of top trends ordered by rank
        """
        try:
            # Use the database function for optimized query
            query = "SELECT * FROM get_top_trends_by_category($1, $2, $3)"
            rows = await self.pool.fetch(query, category, limit, date_from)

            # Fetch full trend details for each result
            trend_ids = [row["id"] for row in rows]
            if not trend_ids:
                return []

            detail_query = "SELECT * FROM trends WHERE id = ANY($1) ORDER BY rank, score DESC"
            detail_rows = await self.pool.fetch(detail_query, trend_ids)

            return [_row_to_trend(row) for row in detail_rows]

        except Exception as e:
            logger.error(f"Failed to get top trends: {e}")
            raise StorageError(f"Failed to get top trends: {e}")

    async def count(self, filters: Optional[TrendFilter] = None) -> int:
        """
        Count trends matching filters.

        Args:
            filters: Optional search filter criteria

        Returns:
            Number of matching trends
        """
        try:
            if filters is None:
                # Count all trends
                query = "SELECT COUNT(*) FROM trends"
                return await self.pool.fetchval(query)

            # Build dynamic query based on filters (same logic as search)
            conditions = []
            params = []
            param_count = 0

            if filters.category:
                param_count += 1
                conditions.append(f"category = ${param_count}")
                params.append(filters.category.value)

            if filters.sources:
                param_count += 1
                source_values = [s.value for s in filters.sources]
                conditions.append(f"sources && ${param_count}")
                params.append(source_values)

            if filters.state:
                param_count += 1
                conditions.append(f"state = ${param_count}")
                params.append(filters.state.value)

            if filters.min_score is not None:
                param_count += 1
                conditions.append(f"score >= ${param_count}")
                params.append(filters.min_score)

            if filters.max_score is not None:
                param_count += 1
                conditions.append(f"score <= ${param_count}")
                params.append(filters.max_score)

            if filters.language:
                param_count += 1
                conditions.append(f"language = ${param_count}")
                params.append(filters.language)

            if filters.date_from:
                param_count += 1
                conditions.append(f"first_seen >= ${param_count}")
                params.append(filters.date_from)

            if filters.date_to:
                param_count += 1
                conditions.append(f"first_seen <= ${param_count}")
                params.append(filters.date_to)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f"SELECT COUNT(*) FROM trends WHERE {where_clause}"

            return await self.pool.fetchval(query, *params)

        except Exception as e:
            logger.error(f"Failed to count trends: {e}")
            raise StorageError(f"Failed to count trends: {e}")

    async def delete_old_trends(
        self,
        days: int,
        states: Optional[List[TrendState]] = None
    ) -> int:
        """
        Delete old trends in specific states.

        Args:
            days: Delete trends older than this many days
            states: Optional list of states to filter (e.g., DEAD, DECLINING)

        Returns:
            Number of trends deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            if states:
                # Delete trends in specific states older than cutoff
                state_values = [s.value for s in states]
                query = """
                    DELETE FROM trends
                    WHERE last_updated < $1
                    AND state = ANY($2)
                    RETURNING id
                """
                rows = await self.pool.fetch(query, cutoff_date, state_values)
            else:
                # Delete all trends older than cutoff
                query = """
                    DELETE FROM trends
                    WHERE last_updated < $1
                    RETURNING id
                """
                rows = await self.pool.fetch(query, cutoff_date)

            deleted = len(rows)
            logger.info(f"Deleted {deleted} trends older than {days} days (states: {states})")
            return deleted

        except Exception as e:
            logger.error(f"Failed to delete old trends: {e}")
            raise StorageError(f"Failed to delete old trends: {e}")


class PostgreSQLTopicRepository:
    """PostgreSQL implementation of TopicRepository."""

    def __init__(self, pool: Pool):
        """
        Initialize repository with a connection pool.

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def save(self, topic: Topic) -> UUID:
        """
        Save a topic to the database.

        Args:
            topic: The topic to save

        Returns:
            UUID of the saved topic
        """
        try:
            query = """
                INSERT INTO topics (
                    id, title, summary, category, sources, item_count,
                    language, keywords, total_engagement, first_seen,
                    last_updated, metadata
                ) VALUES (
                    COALESCE($1, uuid_generate_v4()), $2, $3, $4, $5, $6,
                    $7, $8, $9, $10, $11, $12
                )
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    summary = EXCLUDED.summary,
                    sources = EXCLUDED.sources,
                    item_count = EXCLUDED.item_count,
                    keywords = EXCLUDED.keywords,
                    total_engagement = EXCLUDED.total_engagement,
                    metadata = EXCLUDED.metadata
                RETURNING id
            """

            sources_array = [s.value for s in topic.sources]
            engagement_json = _metrics_to_jsonb(topic.total_engagement)

            topic_id = await self.pool.fetchval(
                query,
                topic.id,
                topic.title,
                topic.summary,
                topic.category.value,
                sources_array,
                topic.item_count,
                topic.language,
                topic.keywords,
                engagement_json,
                topic.first_seen,
                topic.last_updated,
                json.dumps(topic.metadata),
            )

            logger.debug(f"Saved topic {topic_id}: {topic.title}")
            return topic_id

        except Exception as e:
            logger.error(f"Failed to save topic: {e}")
            raise StorageError(f"Failed to save topic: {e}")

    async def get(self, topic_id: UUID) -> Optional[Topic]:
        """
        Retrieve a topic by ID.

        Args:
            topic_id: UUID of the topic

        Returns:
            The topic if found, None otherwise
        """
        try:
            query = "SELECT * FROM topics WHERE id = $1"
            row = await self.pool.fetchrow(query, topic_id)

            if row is None:
                return None

            return _row_to_topic(row)

        except Exception as e:
            logger.error(f"Failed to get topic {topic_id}: {e}")
            raise StorageError(f"Failed to get topic: {e}")

    async def search(
        self,
        category: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Topic]:
        """
        Search topics with filters.

        Args:
            category: Optional category filter
            language: Optional language filter
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            List of matching topics
        """
        try:
            conditions = []
            params = []
            param_count = 0

            if category:
                param_count += 1
                conditions.append(f"category = ${param_count}")
                params.append(category)

            if language:
                param_count += 1
                conditions.append(f"language = ${param_count}")
                params.append(language)

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            query = f"""
                SELECT * FROM topics
                WHERE {where_clause}
                ORDER BY last_updated DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            params.extend([limit, offset])

            rows = await self.pool.fetch(query, *params)
            return [_row_to_topic(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to search topics: {e}")
            raise StorageError(f"Failed to search topics: {e}")

    async def update(self, topic_id: UUID, updates: Dict[str, Any]) -> bool:
        """
        Update a topic.

        Args:
            topic_id: UUID of the topic to update
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if not found
        """
        try:
            set_clauses = []
            params = []
            param_count = 0

            for key, value in updates.items():
                param_count += 1
                set_clauses.append(f"{key} = ${param_count}")

                if key == "total_engagement" and isinstance(value, Metrics):
                    params.append(_metrics_to_jsonb(value))
                elif key == "category":
                    params.append(value.value if hasattr(value, "value") else value)
                elif key == "sources" and isinstance(value, list):
                    params.append([s.value if hasattr(s, "value") else s for s in value])
                elif key == "metadata":
                    params.append(json.dumps(value))
                else:
                    params.append(value)

            if not set_clauses:
                return False

            set_clause = ", ".join(set_clauses)
            param_count += 1
            query = f"""
                UPDATE topics
                SET {set_clause}
                WHERE id = ${param_count}
            """
            params.append(topic_id)

            result = await self.pool.execute(query, *params)
            return result.split()[-1] == "1"

        except Exception as e:
            logger.error(f"Failed to update topic {topic_id}: {e}")
            raise StorageError(f"Failed to update topic: {e}")

    async def delete(self, topic_id: UUID) -> bool:
        """
        Delete a topic.

        Args:
            topic_id: UUID of the topic to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            query = "DELETE FROM topics WHERE id = $1"
            result = await self.pool.execute(query, topic_id)
            return result.split()[-1] == "1"

        except Exception as e:
            logger.error(f"Failed to delete topic {topic_id}: {e}")
            raise StorageError(f"Failed to delete topic: {e}")

    async def get_by_keyword(self, keyword: str, limit: int = 10) -> List[Topic]:
        """
        Get topics containing a specific keyword.

        Args:
            keyword: Keyword to search for
            limit: Maximum results to return

        Returns:
            List of matching topics
        """
        try:
            query = """
                SELECT * FROM topics
                WHERE $1 = ANY(keywords)
                   OR title ILIKE '%' || $1 || '%'
                   OR summary ILIKE '%' || $1 || '%'
                ORDER BY last_updated DESC
                LIMIT $2
            """
            rows = await self.pool.fetch(query, keyword, limit)
            return [_row_to_topic(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to search topics by keyword '{keyword}': {e}")
            raise StorageError(f"Failed to search topics by keyword: {e}")

    async def count(self) -> int:
        """
        Count total topics.

        Returns:
            Total number of topics
        """
        try:
            query = "SELECT COUNT(*) FROM topics"
            return await self.pool.fetchval(query)

        except Exception as e:
            logger.error(f"Failed to count topics: {e}")
            raise StorageError(f"Failed to count topics: {e}")

    async def get_items_by_topic(
        self,
        topic_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[ProcessedItem]:
        """
        Get all items belonging to a topic.

        Args:
            topic_id: UUID of the topic
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            List of ProcessedItem objects ordered by added_at DESC
        """
        try:
            query = """
                SELECT pi.*
                FROM processed_items pi
                INNER JOIN topic_items ti ON ti.item_id = pi.id
                WHERE ti.topic_id = $1
                ORDER BY ti.added_at DESC
                LIMIT $2 OFFSET $3
            """
            rows = await self.pool.fetch(query, topic_id, limit, offset)
            return [_row_to_processed_item(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get items for topic {topic_id}: {e}")
            raise StorageError(f"Failed to get items for topic: {e}")

    async def delete_stale_topics(self, days: int) -> int:
        """
        Delete stale topics that have no recent activity.

        Deletes topics that:
        - Have not been updated in X days
        - Are not associated with any active trend

        Args:
            days: Delete topics not updated in this many days

        Returns:
            Number of topics deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            query = """
                DELETE FROM topics
                WHERE last_updated < $1
                AND id NOT IN (
                    SELECT DISTINCT topic_id
                    FROM trends
                    WHERE state IN ('emerging', 'viral', 'sustained')
                )
                RETURNING id
            """
            rows = await self.pool.fetch(query, cutoff_date)
            deleted = len(rows)
            logger.info(f"Deleted {deleted} stale topics older than {days} days")
            return deleted

        except Exception as e:
            logger.error(f"Failed to delete stale topics: {e}")
            raise StorageError(f"Failed to delete stale topics: {e}")


class PostgreSQLItemRepository:
    """PostgreSQL implementation of ItemRepository."""

    def __init__(self, pool: Pool):
        """
        Initialize repository with a connection pool.

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def save(self, item: ProcessedItem) -> UUID:
        """
        Save a processed item to the database.

        Args:
            item: The item to save

        Returns:
            UUID of the saved item
        """
        try:
            query = """
                INSERT INTO processed_items (
                    id, source, source_id, url, title, title_normalized,
                    description, content, content_normalized, language,
                    author, category, metrics, published_at, collected_at, metadata
                ) VALUES (
                    COALESCE($1, uuid_generate_v4()), $2, $3, $4, $5, $6,
                    $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
                )
                ON CONFLICT (source, source_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    title_normalized = EXCLUDED.title_normalized,
                    description = EXCLUDED.description,
                    content = EXCLUDED.content,
                    content_normalized = EXCLUDED.content_normalized,
                    category = EXCLUDED.category,
                    metrics = EXCLUDED.metrics,
                    metadata = EXCLUDED.metadata
                RETURNING id
            """

            metrics_json = _metrics_to_jsonb(item.metrics)
            category_val = item.category.value if item.category else None

            item_id = await self.pool.fetchval(
                query,
                item.id,
                item.source.value,
                item.source_id,
                str(item.url),
                item.title,
                item.title_normalized,
                item.description,
                item.content,
                item.content_normalized,
                item.language,
                item.author,
                category_val,
                metrics_json,
                item.published_at,
                item.collected_at,
                json.dumps(item.metadata),
            )

            logger.debug(f"Saved item {item_id} from {item.source.value}")
            return item_id

        except Exception as e:
            logger.error(f"Failed to save item: {e}")
            raise StorageError(f"Failed to save item: {e}")

    async def save_batch(self, items: List[ProcessedItem]) -> List[UUID]:
        """
        Save multiple items in a batch.

        Args:
            items: List of items to save

        Returns:
            List of saved item IDs
        """
        try:
            # Use executemany for batch insert
            item_ids = []
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for item in items:
                        item_id = await self.save(item)
                        item_ids.append(item_id)

            logger.debug(f"Saved batch of {len(item_ids)} items")
            return item_ids

        except Exception as e:
            logger.error(f"Failed to save item batch: {e}")
            raise StorageError(f"Failed to save item batch: {e}")

    async def get(self, item_id: UUID) -> Optional[ProcessedItem]:
        """
        Retrieve an item by ID.

        Args:
            item_id: UUID of the item

        Returns:
            The item if found, None otherwise
        """
        try:
            query = "SELECT * FROM processed_items WHERE id = $1"
            row = await self.pool.fetchrow(query, item_id)

            if row is None:
                return None

            return _row_to_processed_item(row)

        except Exception as e:
            logger.error(f"Failed to get item {item_id}: {e}")
            raise StorageError(f"Failed to get item: {e}")

    async def get_by_source_id(
        self, source: str, source_id: str
    ) -> Optional[ProcessedItem]:
        """
        Retrieve an item by source and source ID.

        Args:
            source: Source type
            source_id: ID from the source system

        Returns:
            The item if found, None otherwise
        """
        try:
            query = "SELECT * FROM processed_items WHERE source = $1 AND source_id = $2"
            row = await self.pool.fetchrow(query, source, source_id)

            if row is None:
                return None

            return _row_to_processed_item(row)

        except Exception as e:
            logger.error(f"Failed to get item by source {source}/{source_id}: {e}")
            raise StorageError(f"Failed to get item by source: {e}")

    async def exists(self, source: str, source_id: str) -> bool:
        """
        Check if an item exists by source and source ID.

        Args:
            source: Source type
            source_id: ID from the source system

        Returns:
            True if exists, False otherwise
        """
        try:
            query = "SELECT EXISTS(SELECT 1 FROM processed_items WHERE source = $1 AND source_id = $2)"
            return await self.pool.fetchval(query, source, source_id)

        except Exception as e:
            logger.error(f"Failed to check item existence {source}/{source_id}: {e}")
            raise StorageError(f"Failed to check item existence: {e}")

    async def delete_older_than(self, days: int) -> int:
        """
        Delete items older than specified days.

        Args:
            days: Number of days

        Returns:
            Number of items deleted
        """
        try:
            # Use the database function
            result = await self.pool.fetchval("SELECT cleanup_old_items($1)", days)
            logger.info(f"Deleted {result} items older than {days} days")
            return result

        except Exception as e:
            logger.error(f"Failed to delete old items: {e}")
            raise StorageError(f"Failed to delete old items: {e}")

    async def get_pending_items(
        self,
        limit: int = 1000,
        hours_back: int = 24
    ) -> List[ProcessedItem]:
        """
        Get items that need full processing.

        Fetches items that were minimally processed during collection
        and need to go through the full processing pipeline.

        Args:
            limit: Maximum number of items to return
            hours_back: Only get items from last N hours

        Returns:
            List of ProcessedItem objects needing processing

        Raises:
            StorageError: If query fails
        """
        try:
            query = """
                SELECT *
                FROM processed_items
                WHERE
                    collected_at > NOW() - INTERVAL '%s hours'
                    AND (
                        metadata->>'processing_status' = 'pending'
                        OR metadata->>'minimal_processing' = 'true'
                    )
                    AND content_normalized IS NULL
                ORDER BY collected_at DESC
                LIMIT $1
            """
            rows = await self.pool.fetch(query % hours_back, limit)

            items = [_row_to_processed_item(row) for row in rows]
            logger.info(f"Retrieved {len(items)} pending items for processing")
            return items

        except Exception as e:
            logger.error(f"Failed to get pending items: {e}")
            raise StorageError(f"Failed to get pending items: {e}")

    async def count(self) -> int:
        """
        Count total items.

        Returns:
            Total number of processed items
        """
        try:
            query = "SELECT COUNT(*) FROM processed_items"
            return await self.pool.fetchval(query)

        except Exception as e:
            logger.error(f"Failed to count items: {e}")
            raise StorageError(f"Failed to count items: {e}")

    async def get_items_without_embeddings(self, limit: int = 100) -> List[ProcessedItem]:
        """
        Get items that don't have embeddings yet.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of ProcessedItem objects without embeddings
        """
        try:
            query = """
                SELECT *
                FROM processed_items
                WHERE
                    embedding IS NULL
                    OR ARRAY_LENGTH(embedding, 1) IS NULL
                ORDER BY collected_at DESC
                LIMIT $1
            """
            rows = await self.pool.fetch(query, limit)
            return [_row_to_processed_item(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get items without embeddings: {e}")
            raise StorageError(f"Failed to get items without embeddings: {e}")


# ============================================================================
# Plugin Health Repository
# ============================================================================


class PostgreSQLPluginHealthRepository:
    """PostgreSQL implementation of Plugin Health Repository."""

    def __init__(self, pool: Pool):
        """
        Initialize repository with a connection pool.

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def get(self, plugin_name: str) -> Optional[PluginHealth]:
        """
        Get plugin health status by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginHealth object if found, None otherwise
        """
        try:
            query = "SELECT * FROM plugin_health WHERE name = $1"
            row = await self.pool.fetchrow(query, plugin_name)

            if row is None:
                return None

            return PluginHealth(
                name=row["name"],
                is_healthy=row["is_healthy"],
                last_run_at=row["last_run_at"],
                last_success_at=row["last_success_at"],
                last_error=row["last_error"],
                consecutive_failures=row["consecutive_failures"],
                total_runs=row["total_runs"],
                success_rate=row["success_rate"],
            )

        except Exception as e:
            logger.error(f"Failed to get plugin health for '{plugin_name}': {e}")
            raise StorageError(f"Failed to get plugin health: {e}")

    async def get_all(self) -> List[PluginHealth]:
        """
        Get all plugin health statuses.

        Returns:
            List of all PluginHealth objects
        """
        try:
            query = "SELECT * FROM plugin_health ORDER BY name"
            rows = await self.pool.fetch(query)

            return [
                PluginHealth(
                    name=row["name"],
                    is_healthy=row["is_healthy"],
                    last_run_at=row["last_run_at"],
                    last_success_at=row["last_success_at"],
                    last_error=row["last_error"],
                    consecutive_failures=row["consecutive_failures"],
                    total_runs=row["total_runs"],
                    success_rate=row["success_rate"],
                )
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get all plugin health: {e}")
            raise StorageError(f"Failed to get all plugin health: {e}")

    async def update(self, health: PluginHealth) -> None:
        """
        Update or insert plugin health status.

        Args:
            health: PluginHealth object with updated data
        """
        try:
            query = """
                INSERT INTO plugin_health (
                    name, is_healthy, last_run_at, last_success_at, last_error,
                    consecutive_failures, total_runs, success_rate, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, NOW()
                )
                ON CONFLICT (name) DO UPDATE SET
                    is_healthy = EXCLUDED.is_healthy,
                    last_run_at = EXCLUDED.last_run_at,
                    last_success_at = EXCLUDED.last_success_at,
                    last_error = EXCLUDED.last_error,
                    consecutive_failures = EXCLUDED.consecutive_failures,
                    total_runs = EXCLUDED.total_runs,
                    success_rate = EXCLUDED.success_rate,
                    updated_at = NOW()
            """

            await self.pool.execute(
                query,
                health.name,
                health.is_healthy,
                health.last_run_at,
                health.last_success_at,
                health.last_error,
                health.consecutive_failures,
                health.total_runs,
                health.success_rate,
            )

            logger.debug(f"Updated plugin health for '{health.name}'")

        except Exception as e:
            logger.error(f"Failed to update plugin health for '{health.name}': {e}")
            raise StorageError(f"Failed to update plugin health: {e}")

    async def delete(self, plugin_name: str) -> bool:
        """
        Delete plugin health status.

        Args:
            plugin_name: Name of the plugin

        Returns:
            True if deleted, False if not found
        """
        try:
            query = "DELETE FROM plugin_health WHERE name = $1"
            result = await self.pool.execute(query, plugin_name)

            # asyncpg returns "DELETE N" where N is number of rows deleted
            deleted = int(result.split()[-1]) > 0
            if deleted:
                logger.debug(f"Deleted plugin health for '{plugin_name}'")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete plugin health for '{plugin_name}': {e}")
            raise StorageError(f"Failed to delete plugin health: {e}")


