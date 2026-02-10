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
from trend_agent.types import ProcessedItem

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
