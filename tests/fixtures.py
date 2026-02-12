"""
Test fixtures and sample data for development and testing.

This module provides fixtures for creating test data across all layers.
"""

from datetime import datetime, timedelta
from uuid import uuid4

from trend_agent.schemas import (
    Category,
    Metrics,
    ProcessedItem,
    RawItem,
    SourceType,
    Topic,
    Trend,
    TrendState,
    PluginMetadata,
)


# ============================================================================
# Sample Metrics
# ============================================================================


def create_sample_metrics(
    upvotes: int = 100,
    comments: int = 50,
    views: int = 1000,
) -> Metrics:
    """Create sample metrics."""
    return Metrics(
        upvotes=upvotes,
        downvotes=10,
        comments=comments,
        shares=25,
        views=views,
        score=float(upvotes - 10 + comments * 0.5),
    )


# ============================================================================
# Sample Raw Items
# ============================================================================


def create_sample_raw_item(
    source: SourceType = SourceType.REDDIT,
    title: str = "Sample Trending Item",
) -> RawItem:
    """Create a sample raw item."""
    return RawItem(
        source=source,
        source_id=f"{source.value}_{uuid4().hex[:8]}",
        url="https://example.com/item/123",
        title=title,
        description="This is a sample trending item for testing purposes.",
        content="Full content of the sample item goes here. It contains various details about the trending topic.",
        author="sample_user",
        published_at=datetime.utcnow() - timedelta(hours=2),
        metrics=create_sample_metrics(),
    )


def create_sample_raw_items(count: int = 10) -> list[RawItem]:
    """Create multiple sample raw items."""
    sources = list(SourceType)
    titles = [
        "AI Model Breakthrough Announced",
        "New Climate Change Research Published",
        "Tech Company Releases Major Update",
        "Political Event Sparks Discussion",
        "Sports Team Wins Championship",
        "Entertainment Industry News",
        "Scientific Discovery Made",
        "Business Merger Completed",
        "Global News: International Summit",
        "Educational Reform Proposed",
    ]

    items = []
    for i in range(count):
        source = sources[i % len(sources)]
        title = titles[i % len(titles)]
        items.append(create_sample_raw_item(source=source, title=title))

    return items


# ============================================================================
# Sample Processed Items
# ============================================================================


def create_sample_processed_item(
    source: SourceType = SourceType.REDDIT,
    category: Category = Category.TECHNOLOGY,
) -> ProcessedItem:
    """Create a sample processed item."""
    title = f"Sample {category.value} Item"

    return ProcessedItem(
        id=uuid4(),
        source=source,
        source_id=f"{source.value}_{uuid4().hex[:8]}",
        url="https://example.com/item/123",
        title=title,
        title_normalized=title.lower().strip(),
        description="Normalized description of the item.",
        content="Normalized content of the item.",
        content_normalized="normalized content of the item.",
        language="en",
        published_at=datetime.utcnow() - timedelta(hours=2),
        collected_at=datetime.utcnow(),
        metrics=create_sample_metrics(),
        category=category,
        embedding=[0.1] * 1536,  # Fake embedding
    )


def create_sample_processed_items(count: int = 10) -> list[ProcessedItem]:
    """Create multiple sample processed items."""
    sources = list(SourceType)
    categories = list(Category)

    items = []
    for i in range(count):
        source = sources[i % len(sources)]
        category = categories[i % len(categories)]
        items.append(create_sample_processed_item(source=source, category=category))

    return items


# ============================================================================
# Sample Topics
# ============================================================================


def create_sample_topic(
    category: Category = Category.TECHNOLOGY,
    item_count: int = 5,
) -> Topic:
    """Create a sample topic."""
    return Topic(
        id=uuid4(),
        title=f"Sample {category.value} Topic",
        summary=f"This is a trending topic in {category.value.lower()} with {item_count} related items.",
        category=category,
        sources=[SourceType.REDDIT, SourceType.HACKERNEWS],
        item_count=item_count,
        total_engagement=create_sample_metrics(
            upvotes=500,
            comments=200,
            views=10000,
        ),
        first_seen=datetime.utcnow() - timedelta(hours=6),
        last_updated=datetime.utcnow(),
        keywords=["trending", "popular", category.value.lower()],
        embedding=[0.2] * 1536,
    )


def create_sample_topics(count: int = 5) -> list[Topic]:
    """Create multiple sample topics."""
    categories = list(Category)
    topics = []

    for i in range(count):
        category = categories[i % len(categories)]
        item_count = 3 + (i * 2)
        topics.append(create_sample_topic(category=category, item_count=item_count))

    return topics


# ============================================================================
# Sample Trends
# ============================================================================


def create_sample_trend(
    rank: int = 1,
    state: TrendState = TrendState.VIRAL,
    category: Category = Category.TECHNOLOGY,
) -> Trend:
    """Create a sample trend."""
    topic_id = uuid4()

    return Trend(
        id=uuid4(),
        topic_id=topic_id,
        rank=rank,
        title=f"Trending {category.value} Story #{rank}",
        summary=f"This is a {state.value} trend in {category.value.lower()}. It's gaining significant attention across multiple sources.",
        key_points=[
            f"Key point 1 about this {category.value.lower()} trend",
            f"Key point 2 highlighting important aspects",
            f"Key point 3 with additional context",
        ],
        category=category,
        state=state,
        score=100.0 - (rank * 5.0),
        sources=[SourceType.REDDIT, SourceType.HACKERNEWS, SourceType.TWITTER],
        item_count=10 + (rank * 2),
        total_engagement=create_sample_metrics(
            upvotes=1000 - (rank * 50),
            comments=500 - (rank * 20),
            views=50000 - (rank * 2000),
        ),
        velocity=10.0 - (rank * 0.5),
        first_seen=datetime.utcnow() - timedelta(hours=12),
        last_updated=datetime.utcnow(),
        peak_engagement_at=datetime.utcnow() - timedelta(hours=2),
        keywords=[
            "trending",
            "viral",
            category.value.lower(),
            "breaking",
        ],
        related_trend_ids=[],
    )


def create_sample_trends(count: int = 10) -> list[Trend]:
    """Create multiple sample trends."""
    categories = list(Category)
    states = list(TrendState)

    trends = []
    for i in range(count):
        rank = i + 1
        category = categories[i % len(categories)]
        state = states[i % len(states)]
        trends.append(create_sample_trend(rank=rank, state=state, category=category))

    return trends


# ============================================================================
# Sample Plugin Metadata
# ============================================================================


def create_sample_plugin_metadata(
    name: str = "sample_collector",
    source_type: SourceType = SourceType.REDDIT,
) -> PluginMetadata:
    """Create sample plugin metadata."""
    return PluginMetadata(
        name=name,
        version="1.0.0",
        author="Test Author",
        description=f"Sample collector for {source_type.value}",
        source_type=source_type,
        schedule="0 */6 * * *",  # Every 6 hours
        enabled=True,
        rate_limit=100,
        timeout_seconds=30,
        retry_count=3,
    )


# ============================================================================
# Fixture Collections
# ============================================================================


class Fixtures:
    """Collection of all fixtures for easy access."""

    @staticmethod
    def get_raw_items(count: int = 10) -> list[RawItem]:
        """Get sample raw items."""
        return create_sample_raw_items(count)

    @staticmethod
    def get_processed_items(count: int = 10) -> list[ProcessedItem]:
        """Get sample processed items."""
        return create_sample_processed_items(count)

    @staticmethod
    def get_topics(count: int = 5) -> list[Topic]:
        """Get sample topics."""
        return create_sample_topics(count)

    @staticmethod
    def get_trends(count: int = 10) -> list[Trend]:
        """Get sample trends."""
        return create_sample_trends(count)

    @staticmethod
    def get_plugin_metadata(name: str, source_type: SourceType) -> PluginMetadata:
        """Get sample plugin metadata."""
        return create_sample_plugin_metadata(name, source_type)


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # Example usage
    fixtures = Fixtures()

    print("Sample Raw Items:")
    raw_items = fixtures.get_raw_items(3)
    for item in raw_items:
        print(f"  - {item.title} ({item.source.value})")

    print("\nSample Topics:")
    topics = fixtures.get_topics(3)
    for topic in topics:
        print(f"  - {topic.title} ({topic.category.value})")

    print("\nSample Trends:")
    trends = fixtures.get_trends(5)
    for trend in trends:
        print(f"  #{trend.rank}: {trend.title} ({trend.state.value})")
