"""
Deduplication module for processing pipeline.

This module provides duplicate detection and removal using embedding-based
similarity with configurable thresholds.
"""

import logging
from typing import Dict, List, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from trend_agent.intelligence.interfaces import BaseEmbeddingService
from trend_agent.processing.interfaces import BaseDeduplicator, BaseProcessingStage
from trend_agent.types import ProcessedItem, Topic, Trend, Metrics, SourceType

logger = logging.getLogger(__name__)


class EmbeddingDeduplicator(BaseDeduplicator):
    """
    Deduplicator that uses embedding similarity for duplicate detection.

    Uses cosine similarity between embeddings to identify duplicates
    with configurable thresholds.
    """

    def __init__(
        self,
        embedding_service: BaseEmbeddingService,
        default_threshold: float = 0.92,
    ):
        """
        Initialize deduplicator.

        Args:
            embedding_service: Service for generating embeddings
            default_threshold: Default similarity threshold (0-1)
        """
        self._embedding_service = embedding_service
        self._default_threshold = default_threshold

    async def find_duplicates(
        self, items: List[ProcessedItem], threshold: float = 0.92
    ) -> Dict[str, List[ProcessedItem]]:
        """
        Find duplicate items grouped by representative.

        Args:
            items: Items to check for duplicates
            threshold: Similarity threshold (0-1), default 0.92

        Returns:
            Dictionary mapping representative item source_id to duplicate groups

        Example:
            {
                "item1": [item1, item2, item3],  # item1 is representative
                "item5": [item5, item7],         # item5 is representative
            }
        """
        if not items or len(items) < 2:
            return {}

        # Generate embeddings for all items
        texts = [self._get_text_for_embedding(item) for item in items]
        embeddings = await self._embedding_service.embed_batch(texts)

        # Convert to numpy array for sklearn
        embeddings_array = np.array(embeddings)

        # Calculate pairwise similarities
        similarities = cosine_similarity(embeddings_array)

        # Find duplicate groups
        duplicate_groups: Dict[str, List[ProcessedItem]] = {}
        used_indices = set()

        for i in range(len(items)):
            if i in used_indices:
                continue

            # This item will be the representative
            representative = items[i]
            group = [representative]
            used_indices.add(i)

            # Find all duplicates of this item
            for j in range(i + 1, len(items)):
                if j in used_indices:
                    continue

                if similarities[i][j] > threshold:
                    group.append(items[j])
                    used_indices.add(j)

            # Only add to result if there are duplicates
            if len(group) > 1:
                duplicate_groups[representative.source_id] = group

        logger.info(
            f"Found {len(duplicate_groups)} duplicate groups "
            f"(threshold={threshold}, total_items={len(items)})"
        )

        return duplicate_groups

    async def remove_duplicates(
        self, items: List[ProcessedItem], threshold: float = 0.92
    ) -> List[ProcessedItem]:
        """
        Remove duplicate items, keeping only one from each group.

        Args:
            items: Items to deduplicate
            threshold: Similarity threshold (0-1), default 0.92

        Returns:
            Deduplicated items (keeps first occurrence from each group)
        """
        if not items or len(items) < 2:
            return items

        # Generate embeddings for all items
        texts = [self._get_text_for_embedding(item) for item in items]
        embeddings = await self._embedding_service.embed_batch(texts)

        # Convert to numpy array for sklearn
        embeddings_array = np.array(embeddings)

        # Calculate pairwise similarities
        similarities = cosine_similarity(embeddings_array)

        # Track which items to keep
        used_indices = set()
        unique_items = []

        for i in range(len(items)):
            if i in used_indices:
                continue

            # Keep this item (first occurrence)
            unique_items.append(items[i])
            used_indices.add(i)

            # Mark all duplicates as used
            for j in range(i + 1, len(items)):
                if similarities[i][j] > threshold:
                    used_indices.add(j)

        duplicates_removed = len(items) - len(unique_items)
        logger.info(
            f"Removed {duplicates_removed} duplicates "
            f"(kept {len(unique_items)}/{len(items)} items, threshold={threshold})"
        )

        return unique_items

    async def is_duplicate(
        self, item1: ProcessedItem, item2: ProcessedItem, threshold: float = 0.92
    ) -> bool:
        """
        Check if two items are duplicates.

        Args:
            item1: First item
            item2: Second item
            threshold: Similarity threshold (0-1), default 0.92

        Returns:
            True if items are duplicates (similarity > threshold)
        """
        # Generate embeddings
        text1 = self._get_text_for_embedding(item1)
        text2 = self._get_text_for_embedding(item2)

        embeddings = await self._embedding_service.embed_batch([text1, text2])

        # Calculate similarity
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

        is_dup = similarity > threshold

        logger.debug(
            f"Duplicate check: {item1.source_id} vs {item2.source_id} = "
            f"{similarity:.3f} ({'duplicate' if is_dup else 'unique'})"
        )

        return is_dup

    def _get_text_for_embedding(self, item: ProcessedItem) -> str:
        """
        Extract text from item for embedding generation.

        Args:
            item: Item to extract text from

        Returns:
            Text suitable for embedding

        Note:
            Prioritizes normalized text if available
        """
        # Use normalized title if available
        title = item.title_normalized or item.title

        # Use normalized content if available (limit to 500 chars for efficiency)
        content = ""
        if item.content_normalized:
            content = item.content_normalized[:500]
        elif item.content:
            content = item.content[:500]

        # Combine title and content
        text = f"{title} {content}".strip()

        return text if text else item.title


class DeduplicatorStage(BaseProcessingStage):
    """
    Processing stage that removes duplicate items.

    This stage uses embedding similarity to identify and remove duplicates,
    keeping only the first occurrence from each duplicate group.
    """

    def __init__(
        self,
        deduplicator: Optional[EmbeddingDeduplicator] = None,
        threshold: float = 0.92,
    ):
        """
        Initialize deduplicator stage.

        Args:
            deduplicator: EmbeddingDeduplicator instance (required)
            threshold: Similarity threshold for deduplication (0-1)
        """
        if deduplicator is None:
            raise ValueError("DeduplicatorStage requires an EmbeddingDeduplicator instance")

        self._deduplicator = deduplicator
        self._threshold = threshold

    async def process(self, items: List[ProcessedItem]) -> List[ProcessedItem]:
        """
        Remove duplicate items from the list.

        Args:
            items: Items to deduplicate

        Returns:
            Unique items (duplicates removed)
        """
        if not items:
            return items

        original_count = len(items)

        # Remove duplicates
        unique_items = await self._deduplicator.remove_duplicates(
            items, threshold=self._threshold
        )

        duplicates_removed = original_count - len(unique_items)

        logger.info(
            f"Deduplication: {original_count} items -> {len(unique_items)} unique "
            f"({duplicates_removed} duplicates removed, threshold={self._threshold})"
        )

        return unique_items

    async def validate(self, items: List[ProcessedItem]) -> bool:
        """
        Validate that no duplicates remain.

        Args:
            items: Items to validate

        Returns:
            True if no duplicates found above threshold

        Note:
            This is an expensive operation (O(n²)), use sparingly
        """
        # For validation, we check if any pairs are duplicates
        # This is expensive, so we only do it when explicitly requested
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if await self._deduplicator.is_duplicate(
                    items[i], items[j], threshold=self._threshold
                ):
                    logger.error(
                        f"Validation failed: found duplicate pair: "
                        f"{items[i].source_id} and {items[j].source_id}"
                    )
                    return False

        logger.info(f"Validation passed: no duplicates found among {len(items)} items")
        return True

    def get_stage_name(self) -> str:
        """
        Get the name of this processing stage.

        Returns:
            Stage name
        """
        return "deduplicator"


# ============================================================================
# Legacy Function (for backward compatibility)
# ============================================================================


async def deduplicate_legacy(
    topics: List,
    embedding_service: BaseEmbeddingService,
    threshold: float = 0.92,
    debug: bool = False,
) -> List:
    """
    Legacy deduplication function for backward compatibility.

    Args:
        topics: List of Topic objects
        embedding_service: Service for generating embeddings
        threshold: Cosine similarity threshold (default 0.92)
        debug: Print similarity scores for debugging (default False)

    Returns:
        List of unique topics

    Note:
        This is a legacy function maintained for backward compatibility.
        New code should use EmbeddingDeduplicator instead.
    """
    if not topics:
        return []

    deduplicator = EmbeddingDeduplicator(
        embedding_service=embedding_service,
        default_threshold=threshold,
    )

    # Convert topics to ProcessedItems (assuming they have similar structure)
    # This is a simplified conversion for backward compatibility
    items = topics  # Assuming topics are ProcessedItem-compatible

    unique_items = await deduplicator.remove_duplicates(items, threshold=threshold)

    if debug:
        duplicates_removed = len(topics) - len(unique_items)
        logger.info(
            f"Deduplication debug: removed {duplicates_removed} duplicates "
            f"(threshold={threshold})"
        )

    return unique_items


# ============================================================================
# Cross-Source Deduplication
# ============================================================================


class CrossSourceDeduplicator:
    """
    Advanced deduplicator that merges duplicate content across different sources.
    
    Instead of just removing duplicates, this class intelligently merges items
    from different sources, preserving all source attribution and aggregating
    engagement metrics.
    """
    
    def __init__(
        self,
        embedding_service: BaseEmbeddingService,
        threshold: float = 0.88,  # Slightly lower for cross-source (more lenient)
    ):
        """
        Initialize cross-source deduplicator.
        
        Args:
            embedding_service: Service for generating embeddings
            threshold: Similarity threshold for cross-source matching (default: 0.88)
        """
        self._embedding_service = embedding_service
        self._threshold = threshold
    
    async def merge_cross_source_items(
        self, items: List[ProcessedItem], threshold: Optional[float] = None
    ) -> List[ProcessedItem]:
        """
        Merge duplicate items across sources into unified items.
        
        Args:
            items: Items from different sources to deduplicate
            threshold: Optional override for similarity threshold
        
        Returns:
            List of merged items with multiple sources
        """
        if not items or len(items) < 2:
            return items
        
        threshold = threshold or self._threshold
        
        # Generate embeddings
        texts = [self._get_text_for_embedding(item) for item in items]
        embeddings = await self._embedding_service.embed_batch(texts)
        embeddings_array = np.array(embeddings)
        
        # Calculate similarities
        similarities = cosine_similarity(embeddings_array)
        
        # Group similar items
        merged_items = []
        used_indices = set()
        
        for i in range(len(items)):
            if i in used_indices:
                continue
            
            # Find all items similar to this one
            similar_group = [items[i]]
            used_indices.add(i)
            
            for j in range(i + 1, len(items)):
                if j in used_indices:
                    continue
                
                if similarities[i][j] > threshold:
                    similar_group.append(items[j])
                    used_indices.add(j)
            
            # Merge the group into a single item
            merged_item = self._merge_items(similar_group)
            merged_items.append(merged_item)
        
        sources_merged = len(items) - len(merged_items)
        logger.info(
            f"Cross-source deduplication: merged {sources_merged} items "
            f"({len(items)} → {len(merged_items)} items)"
        )
        
        return merged_items
    
    async def merge_cross_source_topics(
        self, topics: List[Topic], threshold: Optional[float] = None
    ) -> List[Topic]:
        """
        Merge duplicate topics across sources.
        
        Args:
            topics: Topics from different sources to deduplicate
            threshold: Optional override for similarity threshold
        
        Returns:
            List of merged topics
        """
        if not topics or len(topics) < 2:
            return topics
        
        threshold = threshold or self._threshold
        
        # Generate embeddings from topic summaries
        texts = [f"{topic.title} {topic.summary}" for topic in topics]
        embeddings = await self._embedding_service.embed_batch(texts)
        embeddings_array = np.array(embeddings)
        
        # Calculate similarities
        similarities = cosine_similarity(embeddings_array)
        
        # Group similar topics
        merged_topics = []
        used_indices = set()
        
        for i in range(len(topics)):
            if i in used_indices:
                continue
            
            # Find all topics similar to this one
            similar_group = [topics[i]]
            used_indices.add(i)
            
            for j in range(i + 1, len(topics)):
                if j in used_indices:
                    continue
                
                if similarities[i][j] > threshold:
                    similar_group.append(topics[j])
                    used_indices.add(j)
            
            # Merge the group
            merged_topic = self._merge_topics(similar_group)
            merged_topics.append(merged_topic)
        
        topics_merged = len(topics) - len(merged_topics)
        logger.info(
            f"Cross-source topic deduplication: merged {topics_merged} topics "
            f"({len(topics)} → {len(merged_topics)} topics)"
        )
        
        return merged_topics
    
    async def merge_cross_source_trends(
        self, trends: List[Trend], threshold: Optional[float] = None
    ) -> List[Trend]:
        """
        Merge duplicate trends across sources.
        
        Args:
            trends: Trends from different sources to deduplicate
            threshold: Optional override for similarity threshold
        
        Returns:
            List of merged trends
        """
        if not trends or len(trends) < 2:
            return trends
        
        threshold = threshold or self._threshold
        
        # Generate embeddings from trend summaries
        texts = [f"{trend.title} {trend.summary}" for trend in trends]
        embeddings = await self._embedding_service.embed_batch(texts)
        embeddings_array = np.array(embeddings)
        
        # Calculate similarities
        similarities = cosine_similarity(embeddings_array)
        
        # Group similar trends
        merged_trends = []
        used_indices = set()
        
        for i in range(len(trends)):
            if i in used_indices:
                continue
            
            # Find all trends similar to this one
            similar_group = [trends[i]]
            used_indices.add(i)
            
            for j in range(i + 1, len(trends)):
                if j in used_indices:
                    continue
                
                if similarities[i][j] > threshold:
                    similar_group.append(trends[j])
                    used_indices.add(j)
            
            # Merge the group
            merged_trend = self._merge_trends(similar_group)
            merged_trends.append(merged_trend)
        
        trends_merged = len(trends) - len(merged_trends)
        logger.info(
            f"Cross-source trend deduplication: merged {trends_merged} trends "
            f"({len(trends)} → {len(merged_trends)} trends)"
        )
        
        return merged_trends
    
    def _merge_items(self, items: List[ProcessedItem]) -> ProcessedItem:
        """
        Merge multiple items into a single representative item.
        
        Combines sources, aggregates metrics, and selects best content.
        
        Args:
            items: Items to merge (must have at least one)
        
        Returns:
            Merged item
        """
        if len(items) == 1:
            return items[0]
        
        # Use item with highest score as base
        items_sorted = sorted(items, key=lambda x: x.metrics.score, reverse=True)
        base_item = items_sorted[0]
        
        # Collect all unique sources
        sources = list(set(item.source for item in items))
        
        # Aggregate metrics
        total_metrics = Metrics(
            upvotes=sum(item.metrics.upvotes for item in items),
            downvotes=sum(item.metrics.downvotes for item in items),
            comments=sum(item.metrics.comments for item in items),
            shares=sum(item.metrics.shares for item in items),
            views=sum(item.metrics.views for item in items),
            score=sum(item.metrics.score for item in items),
        )
        
        # Create merged item (make a copy to avoid modifying original)
        from copy import deepcopy
        merged = deepcopy(base_item)
        
        # Update with merged data
        merged.metrics = total_metrics
        
        # Store all sources in metadata
        merged.metadata["cross_source_merged"] = True
        merged.metadata["source_count"] = len(sources)
        merged.metadata["sources"] = [s.value for s in sources]
        merged.metadata["merged_source_ids"] = [item.source_id for item in items]
        
        logger.debug(
            f"Merged {len(items)} items from {len(sources)} sources: {sources}"
        )
        
        return merged
    
    def _merge_topics(self, topics: List[Topic]) -> Topic:
        """
        Merge multiple topics into a single topic.
        
        Args:
            topics: Topics to merge
        
        Returns:
            Merged topic
        """
        if len(topics) == 1:
            return topics[0]
        
        # Use topic with highest item count as base
        topics_sorted = sorted(topics, key=lambda x: x.item_count, reverse=True)
        base_topic = topics_sorted[0]
        
        # Collect all unique sources
        all_sources = []
        for topic in topics:
            all_sources.extend(topic.sources)
        sources = list(set(all_sources))
        
        # Aggregate metrics
        total_metrics = Metrics(
            upvotes=sum(t.total_engagement.upvotes for t in topics),
            downvotes=sum(t.total_engagement.downvotes for t in topics),
            comments=sum(t.total_engagement.comments for t in topics),
            shares=sum(t.total_engagement.shares for t in topics),
            views=sum(t.total_engagement.views for t in topics),
            score=sum(t.total_engagement.score for t in topics),
        )
        
        # Merge keywords (unique)
        all_keywords = []
        for topic in topics:
            all_keywords.extend(topic.keywords)
        unique_keywords = list(set(all_keywords))
        
        # Create merged topic
        from copy import deepcopy
        merged = deepcopy(base_topic)
        
        merged.sources = sources
        merged.total_engagement = total_metrics
        merged.item_count = sum(t.item_count for t in topics)
        merged.keywords = unique_keywords[:10]  # Limit to top 10
        
        # Store merge metadata
        merged.metadata["cross_source_merged"] = True
        merged.metadata["source_count"] = len(sources)
        merged.metadata["merged_topic_count"] = len(topics)
        
        return merged
    
    def _merge_trends(self, trends: List[Trend]) -> Trend:
        """
        Merge multiple trends into a single trend.
        
        Args:
            trends: Trends to merge
        
        Returns:
            Merged trend
        """
        if len(trends) == 1:
            return trends[0]
        
        # Use trend with highest score as base
        trends_sorted = sorted(trends, key=lambda x: x.score, reverse=True)
        base_trend = trends_sorted[0]
        
        # Collect all unique sources
        all_sources = []
        for trend in trends:
            all_sources.extend(trend.sources)
        sources = list(set(all_sources))
        
        # Aggregate metrics
        total_metrics = Metrics(
            upvotes=sum(t.total_engagement.upvotes for t in trends),
            downvotes=sum(t.total_engagement.downvotes for t in trends),
            comments=sum(t.total_engagement.comments for t in trends),
            shares=sum(t.total_engagement.shares for t in trends),
            views=sum(t.total_engagement.views for t in trends),
            score=sum(t.total_engagement.score for t in trends),
        )
        
        # Merge keywords and key points
        all_keywords = []
        all_key_points = []
        for trend in trends:
            all_keywords.extend(trend.keywords)
            all_key_points.extend(trend.key_points)
        
        unique_keywords = list(set(all_keywords))
        unique_key_points = list(set(all_key_points))
        
        # Calculate aggregate velocity
        avg_velocity = sum(t.velocity for t in trends) / len(trends)
        
        # Create merged trend
        from copy import deepcopy
        merged = deepcopy(base_trend)
        
        merged.sources = sources
        merged.total_engagement = total_metrics
        merged.item_count = sum(t.item_count for t in trends)
        merged.keywords = unique_keywords[:10]  # Top 10
        merged.key_points = unique_key_points[:5]  # Top 5
        merged.velocity = avg_velocity
        
        # Recalculate score based on merged metrics
        merged.score = (
            total_metrics.upvotes * 1.0
            + total_metrics.comments * 2.0
            + total_metrics.shares * 3.0
        ) / max(1, merged.item_count)
        
        # Store merge metadata
        merged.metadata["cross_source_merged"] = True
        merged.metadata["source_count"] = len(sources)
        merged.metadata["merged_trend_count"] = len(trends)
        
        return merged
    
    def _get_text_for_embedding(self, item: ProcessedItem) -> str:
        """Extract text from item for embedding."""
        title = item.title_normalized or item.title
        content = ""
        if item.content_normalized:
            content = item.content_normalized[:500]
        elif item.content:
            content = item.content[:500]
        
        text = f"{title} {content}".strip()
        return text if text else item.title
