"""
Converters for transforming data between different stages.

This module provides utilities for converting between RawItem and ProcessedItem,
allowing collected data to be persisted before full processing.
"""

import re
from uuid import uuid4

from trend_agent.schemas import ProcessedItem, RawItem


def raw_to_processed(raw_item: RawItem) -> ProcessedItem:
    """
    Convert a RawItem to ProcessedItem with minimal processing.

    This function prepares collected items for database storage by adding
    required fields with default values. Full processing (normalization,
    language detection, categorization) happens later in the processing pipeline.

    Args:
        raw_item: The raw collected item

    Returns:
        ProcessedItem with minimal defaults

    Example:
        >>> raw = RawItem(source="reddit", source_id="abc123", ...)
        >>> processed = raw_to_processed(raw)
        >>> assert processed.title_normalized is not None
    """
    # Basic title normalization - just strip whitespace and collapse spaces
    title_normalized = re.sub(r'\s+', ' ', (raw_item.title or "").strip())

    # Basic content normalization if content exists
    content_normalized = None
    if raw_item.content:
        content_normalized = re.sub(r'\s+', ' ', raw_item.content.strip())

    return ProcessedItem(
        id=uuid4(),  # Generate new UUID
        source=raw_item.source,
        source_id=raw_item.source_id,
        url=raw_item.url,
        title=raw_item.title,
        title_normalized=title_normalized,
        description=raw_item.description,
        content=raw_item.content,
        content_normalized=content_normalized,
        language="en",  # Default to English, will be detected in processing pipeline
        author=raw_item.author,
        published_at=raw_item.published_at,
        collected_at=raw_item.collected_at,
        metrics=raw_item.metrics,
        category=None,  # Will be classified in processing pipeline
        embedding=None,  # Will be generated in processing pipeline
        metadata={
            **raw_item.metadata,
            "processing_status": "pending",  # Mark as needing full processing
            "minimal_processing": True,  # Flag that this was minimally processed
        },
    )


def batch_raw_to_processed(raw_items: list[RawItem]) -> list[ProcessedItem]:
    """
    Convert a batch of RawItems to ProcessedItems.

    Args:
        raw_items: List of raw items

    Returns:
        List of processed items with minimal defaults

    Example:
        >>> raws = [raw1, raw2, raw3]
        >>> processed = batch_raw_to_processed(raws)
        >>> assert len(processed) == len(raws)
    """
    return [raw_to_processed(item) for item in raw_items]
