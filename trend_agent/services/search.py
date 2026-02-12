"""
Qdrant Semantic Search Service implementation.

Provides production-ready semantic search using Qdrant vector database,
combining embedding generation, vector similarity search, and trend retrieval.
"""

import logging
import time
from typing import Dict, List, Optional
from uuid import UUID

from trend_agent.intelligence.interfaces import (
    BaseSemanticSearchService,
    SearchError,
)
from trend_agent.observability.metrics import (
    api_request_counter,
    api_request_duration,
)
from trend_agent.storage.interfaces import (
    TrendRepository,
    VectorRepository,
)
from trend_agent.schemas import (
    SemanticSearchRequest,
    Trend,
    TrendFilter,
    VectorMatch,
)

logger = logging.getLogger(__name__)


class QdrantSemanticSearchService(BaseSemanticSearchService):
    """
    Qdrant-based semantic search service for trend discovery.

    Combines vector similarity search with database queries to provide
    intelligent, context-aware trend search capabilities.

    Features:
    - Text-to-vector query conversion using embeddings
    - Similarity-based trend discovery
    - Metadata filtering (category, language, date, etc.)
    - Prometheus metrics integration
    - Error handling and logging

    Architecture:
        User Query → Embedding Service → Vector (1536-dim)
        Vector → Qdrant Search → VectorMatch (IDs + scores)
        IDs → Trend Repository → Full Trend Objects
        Filter & Rank → Return Results

    Example:
        ```python
        # Initialize dependencies
        embedding_service = OpenAIEmbeddingService(api_key="sk-...")
        vector_repo = QdrantVectorRepository(host="localhost", port=6333)
        trend_repo = PostgreSQLTrendRepository(db_url="postgresql://...")

        # Create search service
        search = QdrantSemanticSearchService(
            embedding_service=embedding_service,
            vector_repository=vector_repo,
            trend_repository=trend_repo,
        )

        # Semantic search
        request = SemanticSearchRequest(
            query="latest AI breakthroughs",
            limit=10,
            min_similarity=0.75,
        )
        trends = await search.search(request)

        # Find similar trends
        similar = await search.search_similar(
            trend_id="123e4567-e89b-12d3-a456-426614174000",
            limit=5,
        )
        ```
    """

    def __init__(
        self,
        embedding_service,  # Type: EmbeddingService
        vector_repository: VectorRepository,
        trend_repository: TrendRepository,
        default_limit: int = 20,
        default_min_similarity: float = 0.7,
    ):
        """
        Initialize Qdrant semantic search service.

        Args:
            embedding_service: Service for generating text embeddings
            vector_repository: Qdrant vector database repository
            trend_repository: PostgreSQL trend repository
            default_limit: Default maximum results to return
            default_min_similarity: Default minimum similarity threshold

        Raises:
            ValueError: If any required service is None
        """
        if not embedding_service:
            raise ValueError("embedding_service is required")
        if not vector_repository:
            raise ValueError("vector_repository is required")
        if not trend_repository:
            raise ValueError("trend_repository is required")

        self.embedding_service = embedding_service
        self.vector_repository = vector_repository
        self.trend_repository = trend_repository
        self.default_limit = default_limit
        self.default_min_similarity = default_min_similarity

        # Metrics tracking
        self._total_searches = 0
        self._total_results = 0

        logger.info(
            f"Initialized QdrantSemanticSearchService "
            f"(limit={default_limit}, min_similarity={default_min_similarity})"
        )

    async def search(self, request: SemanticSearchRequest) -> List[Trend]:
        """
        Perform semantic search for trends using natural language query.

        This method:
        1. Converts query text to embedding vector
        2. Searches Qdrant for similar vectors
        3. Fetches full Trend objects from database
        4. Applies metadata filters
        5. Returns ranked results

        Args:
            request: Search request with query and optional filters

        Returns:
            List of matching trends, ranked by similarity

        Raises:
            SearchError: If search operation fails
        """
        start_time = time.time()

        try:
            # Validate query
            if not request.query or not request.query.strip():
                raise SearchError("Search query cannot be empty")

            logger.info(
                f"Semantic search: query='{request.query[:50]}...' "
                f"limit={request.limit} min_similarity={request.min_similarity}"
            )

            # Step 1: Generate embedding from query text
            try:
                query_embedding = await self.embedding_service.embed(request.query)
            except Exception as e:
                logger.error(f"Failed to generate query embedding: {e}")
                raise SearchError(f"Embedding generation failed: {e}") from e

            # Step 2: Build metadata filters for vector search
            vector_filters = self._build_vector_filters(request.filters)

            # Step 3: Search vector database
            try:
                vector_matches = await self.vector_repository.search(
                    vector=query_embedding,
                    limit=request.limit * 2,  # Fetch extra to account for filtering
                    filters=vector_filters,
                    min_score=request.min_similarity,
                )
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                raise SearchError(f"Vector search failed: {e}") from e

            if not vector_matches:
                logger.info("No vector matches found")
                duration = time.time() - start_time
                self._record_metrics("search", duration, 0, 200)
                return []

            logger.debug(f"Found {len(vector_matches)} vector matches")

            # Step 4: Fetch full Trend objects from database
            trends = await self._fetch_trends_by_ids(vector_matches, request.filters)

            # Step 5: Apply limit (after database filtering)
            trends = trends[: request.limit]

            # Update metrics
            duration = time.time() - start_time
            self._record_metrics("search", duration, len(trends), 200)
            self._total_searches += 1
            self._total_results += len(trends)

            logger.info(
                f"Semantic search completed: {len(trends)} results in {duration:.2f}s"
            )

            return trends

        except SearchError:
            # Re-raise SearchError as-is
            duration = time.time() - start_time
            self._record_metrics("search", duration, 0, 500)
            raise
        except Exception as e:
            # Wrap unexpected errors
            duration = time.time() - start_time
            self._record_metrics("search", duration, 0, 500)
            logger.error(f"Unexpected search error: {e}")
            raise SearchError(f"Search failed: {e}") from e

    async def search_similar(
        self, trend_id: str, limit: int = 10, min_similarity: float = 0.7
    ) -> List[Trend]:
        """
        Find trends similar to a given trend.

        This method retrieves the embedding of the specified trend and
        searches for other trends with similar embeddings.

        Args:
            trend_id: ID of the trend to match
            limit: Maximum results to return
            min_similarity: Minimum similarity score (0-1)

        Returns:
            List of similar trends, excluding the query trend itself

        Raises:
            SearchError: If search operation fails or trend not found
        """
        start_time = time.time()

        try:
            logger.info(
                f"Similarity search: trend_id={trend_id} "
                f"limit={limit} min_similarity={min_similarity}"
            )

            # Step 1: Get the trend's embedding from vector database
            try:
                vector_result = await self.vector_repository.get(trend_id)
                if not vector_result:
                    raise SearchError(f"Trend {trend_id} not found in vector database")

                trend_embedding, metadata = vector_result
            except Exception as e:
                logger.error(f"Failed to retrieve trend embedding: {e}")
                raise SearchError(f"Trend retrieval failed: {e}") from e

            # Step 2: Search for similar vectors
            try:
                vector_matches = await self.vector_repository.search(
                    vector=trend_embedding,
                    limit=limit + 1,  # +1 to account for the trend itself
                    min_score=min_similarity,
                )
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                raise SearchError(f"Vector search failed: {e}") from e

            # Step 3: Remove the query trend itself from results
            vector_matches = [m for m in vector_matches if m.id != trend_id]

            # Apply limit after filtering
            vector_matches = vector_matches[:limit]

            if not vector_matches:
                logger.info("No similar trends found")
                duration = time.time() - start_time
                self._record_metrics("search_similar", duration, 0, 200)
                return []

            logger.debug(f"Found {len(vector_matches)} similar vector matches")

            # Step 4: Fetch full Trend objects
            trends = await self._fetch_trends_by_ids(vector_matches)

            # Update metrics
            duration = time.time() - start_time
            self._record_metrics("search_similar", duration, len(trends), 200)
            self._total_searches += 1
            self._total_results += len(trends)

            logger.info(
                f"Similarity search completed: {len(trends)} results in {duration:.2f}s"
            )

            return trends

        except SearchError:
            duration = time.time() - start_time
            self._record_metrics("search_similar", duration, 0, 500)
            raise
        except Exception as e:
            duration = time.time() - start_time
            self._record_metrics("search_similar", duration, 0, 500)
            logger.error(f"Unexpected similarity search error: {e}")
            raise SearchError(f"Similarity search failed: {e}") from e

    async def search_by_embedding(
        self, embedding: List[float], limit: int = 10, filters: Optional[Dict] = None
    ) -> List[VectorMatch]:
        """
        Search using a pre-computed embedding vector.

        This low-level method performs direct vector search without
        text-to-embedding conversion or trend object fetching. Useful
        for advanced use cases or when embeddings are already available.

        Args:
            embedding: Pre-computed query embedding vector
            limit: Maximum results to return
            filters: Optional metadata filters

        Returns:
            List of vector matches with IDs and similarity scores

        Raises:
            SearchError: If search operation fails
        """
        start_time = time.time()

        try:
            # Validate embedding
            if not embedding:
                raise SearchError("Embedding vector cannot be empty")

            expected_dim = self.embedding_service.get_dimension()
            if len(embedding) != expected_dim:
                raise SearchError(
                    f"Embedding dimension mismatch: expected {expected_dim}, "
                    f"got {len(embedding)}"
                )

            logger.info(
                f"Embedding search: dimension={len(embedding)} "
                f"limit={limit} filters={filters is not None}"
            )

            # Search vector database
            try:
                vector_matches = await self.vector_repository.search(
                    vector=embedding,
                    limit=limit,
                    filters=filters,
                    min_score=0.0,  # No minimum score for raw embedding search
                )
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                raise SearchError(f"Vector search failed: {e}") from e

            # Update metrics
            duration = time.time() - start_time
            self._record_metrics(
                "search_by_embedding", duration, len(vector_matches), 200
            )
            self._total_searches += 1
            self._total_results += len(vector_matches)

            logger.info(
                f"Embedding search completed: {len(vector_matches)} results in {duration:.2f}s"
            )

            return vector_matches

        except SearchError:
            duration = time.time() - start_time
            self._record_metrics("search_by_embedding", duration, 0, 500)
            raise
        except Exception as e:
            duration = time.time() - start_time
            self._record_metrics("search_by_embedding", duration, 0, 500)
            logger.error(f"Unexpected embedding search error: {e}")
            raise SearchError(f"Embedding search failed: {e}") from e

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _build_vector_filters(
        self, trend_filter: Optional[TrendFilter]
    ) -> Optional[Dict]:
        """
        Convert TrendFilter to Qdrant metadata filters.

        Maps high-level trend filters to Qdrant's metadata filter format.

        Args:
            trend_filter: Optional trend filter criteria

        Returns:
            Dictionary of metadata filters for Qdrant, or None
        """
        if not trend_filter:
            return None

        filters = {}

        # Map TrendFilter fields to metadata fields
        if trend_filter.category:
            filters["category"] = trend_filter.category.value

        if trend_filter.language:
            filters["language"] = trend_filter.language

        if trend_filter.state:
            filters["state"] = trend_filter.state.value

        # Note: Date and score filters are typically handled by the
        # trend repository, not the vector database, as Qdrant is
        # optimized for vector similarity, not range queries

        return filters if filters else None

    async def _fetch_trends_by_ids(
        self,
        vector_matches: List[VectorMatch],
        filters: Optional[TrendFilter] = None,
    ) -> List[Trend]:
        """
        Fetch full Trend objects from database using vector match IDs.

        This method:
        1. Extracts trend IDs from vector matches
        2. Fetches trends from PostgreSQL
        3. Applies additional filters (date, score, etc.)
        4. Preserves similarity-based ranking

        Args:
            vector_matches: List of vector search results
            filters: Optional additional filters to apply

        Returns:
            List of Trend objects, ranked by similarity score
        """
        if not vector_matches:
            return []

        # Extract trend IDs from vector matches
        trend_ids = [UUID(match.id) for match in vector_matches]

        # Fetch trends from database
        trends = []
        for trend_id in trend_ids:
            try:
                trend = await self.trend_repository.get(trend_id)
                if trend:
                    trends.append(trend)
                else:
                    logger.warning(
                        f"Trend {trend_id} found in vector DB but not in PostgreSQL"
                    )
            except Exception as e:
                logger.error(f"Failed to fetch trend {trend_id}: {e}")
                # Continue with other trends

        # Apply additional filters if provided
        if filters:
            trends = self._apply_trend_filters(trends, filters)

        # Preserve ranking from vector similarity
        # (Trends are already in the correct order based on trend_ids order)

        return trends

    def _apply_trend_filters(
        self, trends: List[Trend], filters: TrendFilter
    ) -> List[Trend]:
        """
        Apply TrendFilter criteria to a list of trends.

        Filters that couldn't be applied at the vector level (date ranges,
        score ranges, keyword matching) are applied here.

        Args:
            trends: List of trends to filter
            filters: Filter criteria

        Returns:
            Filtered list of trends
        """
        filtered = trends

        # Score range filters
        if filters.min_score is not None:
            filtered = [t for t in filtered if t.score >= filters.min_score]

        if filters.max_score is not None:
            filtered = [t for t in filtered if t.score <= filters.max_score]

        # Date range filters
        if filters.date_from:
            filtered = [t for t in filtered if t.last_updated >= filters.date_from]

        if filters.date_to:
            filtered = [t for t in filtered if t.last_updated <= filters.date_to]

        # Keyword filters (check if any keyword appears in title or keywords list)
        if filters.keywords:
            filtered = [
                t
                for t in filtered
                if any(
                    kw.lower() in t.title.lower()
                    or any(kw.lower() in tk.lower() for tk in t.keywords)
                    for kw in filters.keywords
                )
            ]

        # Source filters (check if trend has any of the requested sources)
        if filters.sources:
            filtered = [
                t for t in filtered if any(src in t.sources for src in filters.sources)
            ]

        return filtered

    def _record_metrics(
        self, operation: str, duration: float, result_count: int, status_code: int
    ):
        """Record Prometheus metrics for search operations."""
        try:
            api_request_duration.labels(
                method="SEARCH", endpoint=f"semantic_search_{operation}"
            ).observe(duration)

            api_request_counter.labels(
                method="SEARCH",
                endpoint=f"semantic_search_{operation}",
                status_code=status_code,
            ).inc()

            logger.debug(
                f"Metrics recorded: {operation} duration={duration:.2f}s "
                f"results={result_count} status={status_code}"
            )
        except Exception as e:
            logger.warning(f"Failed to record metrics: {e}")

    def get_stats(self) -> Dict:
        """
        Get search service statistics.

        Returns:
            Dictionary with search statistics
        """
        avg_results = (
            self._total_results / self._total_searches if self._total_searches > 0 else 0
        )

        return {
            "total_searches": self._total_searches,
            "total_results": self._total_results,
            "avg_results_per_search": round(avg_results, 2),
            "embedding_model": self.embedding_service.get_model_name(),
            "embedding_dimension": self.embedding_service.get_dimension(),
            "default_limit": self.default_limit,
            "default_min_similarity": self.default_min_similarity,
        }

    async def close(self):
        """Clean up resources (if needed)."""
        logger.info(
            f"Closing QdrantSemanticSearchService "
            f"(total_searches={self._total_searches}, "
            f"total_results={self._total_results})"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
