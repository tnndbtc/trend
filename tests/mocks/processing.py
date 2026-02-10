"""
Mock processing implementations for testing.

These mocks provide simple implementations of processing stages
for use during development and testing.
"""

from typing import Dict, List
from uuid import uuid4

from trend_agent.processing.interfaces import (
    BaseClusterer,
    BaseDeduplicator,
    BaseNormalizer,
    BaseRanker,
)
from trend_agent.types import (
    Category,
    Metrics,
    ProcessedItem,
    SourceType,
    Topic,
    Trend,
    TrendState,
)


class MockNormalizer(BaseNormalizer):
    """Mock normalizer that performs basic text cleaning."""

    async def normalize_text(self, text: str) -> str:
        """Basic text normalization."""
        # Simple normalization: strip, lowercase, remove extra spaces
        normalized = " ".join(text.strip().split())
        return normalized

    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract fake entities."""
        return {
            "people": ["Mock Person"],
            "organizations": ["Mock Org"],
            "locations": ["Mock Location"],
            "dates": ["2024-01-15"],
        }

    async def clean_html(self, html: str) -> str:
        """Basic HTML cleaning."""
        # Very simple HTML stripping
        import re

        text = re.sub(r"<[^>]+>", "", html)
        return await self.normalize_text(text)


class MockDeduplicator(BaseDeduplicator):
    """Mock deduplicator that uses simple string matching."""

    async def find_duplicates(
        self, items: List[ProcessedItem], threshold: float = 0.92
    ) -> Dict[str, List[ProcessedItem]]:
        """Find duplicates using title matching."""
        duplicates: Dict[str, List[ProcessedItem]] = {}

        for i, item1 in enumerate(items):
            group_id = str(item1.id or f"item_{i}")

            for item2 in items[i + 1 :]:
                # Simple similarity check: exact title match
                if item1.title.lower() == item2.title.lower():
                    if group_id not in duplicates:
                        duplicates[group_id] = [item1]
                    duplicates[group_id].append(item2)

        return duplicates

    async def remove_duplicates(
        self, items: List[ProcessedItem], threshold: float = 0.92
    ) -> List[ProcessedItem]:
        """Remove duplicates, keeping first occurrence."""
        seen_titles = set()
        unique_items = []

        for item in items:
            title_lower = item.title.lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_items.append(item)

        return unique_items

    async def is_duplicate(
        self, item1: ProcessedItem, item2: ProcessedItem, threshold: float = 0.92
    ) -> bool:
        """Check if two items are duplicates."""
        return item1.title.lower() == item2.title.lower()


class MockClusterer(BaseClusterer):
    """Mock clusterer that groups by category."""

    async def cluster(
        self,
        items: List[ProcessedItem],
        min_cluster_size: int = 2,
        distance_threshold: float = 0.3,
    ) -> List[Topic]:
        """Cluster items by category."""
        # Group items by category
        category_groups: Dict[Category, List[ProcessedItem]] = {}

        for item in items:
            category = item.category or Category.OTHER
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(item)

        # Create topics from groups
        topics = []
        for category, group_items in category_groups.items():
            if len(group_items) >= min_cluster_size:
                # Aggregate metrics
                total_upvotes = sum(item.metrics.upvotes for item in group_items)
                total_comments = sum(item.metrics.comments for item in group_items)
                total_score = sum(item.metrics.score for item in group_items)

                # Get unique sources
                sources = list(set(item.source for item in group_items))

                # Create topic
                topic = Topic(
                    id=uuid4(),
                    title=f"{category.value} Topic",
                    summary=f"Topic about {category.value.lower()} with {len(group_items)} items",
                    category=category,
                    sources=sources,
                    item_count=len(group_items),
                    total_engagement=Metrics(
                        upvotes=total_upvotes,
                        comments=total_comments,
                        score=total_score,
                    ),
                    first_seen=min(item.collected_at for item in group_items),
                    last_updated=max(item.collected_at for item in group_items),
                    language=group_items[0].language,
                    keywords=await self.extract_keywords(None, max_keywords=5),  # type: ignore
                )
                topics.append(topic)

        return topics

    async def assign_category(self, topic: Topic) -> str:
        """Assign category to topic."""
        return topic.category.value

    async def extract_keywords(
        self, topic: Topic, max_keywords: int = 10
    ) -> List[str]:
        """Extract fake keywords."""
        common_keywords = [
            "trending",
            "popular",
            "viral",
            "breaking",
            "news",
            "update",
            "latest",
            "technology",
            "innovation",
            "development",
        ]
        return common_keywords[:max_keywords]


class MockRanker(BaseRanker):
    """Mock ranker that ranks by engagement score."""

    async def rank(self, topics: List[Topic]) -> List[Trend]:
        """Rank topics into trends."""
        # Calculate scores
        scored_topics = []
        for topic in topics:
            score = await self.calculate_score(topic)
            scored_topics.append((topic, score))

        # Sort by score descending
        scored_topics.sort(key=lambda x: x[1], reverse=True)

        # Create trends
        trends = []
        for rank, (topic, score) in enumerate(scored_topics, start=1):
            trend = Trend(
                id=uuid4(),
                topic_id=topic.id or uuid4(),
                rank=rank,
                title=topic.title,
                summary=topic.summary,
                key_points=[
                    f"Key point {i+1}" for i in range(min(3, topic.item_count))
                ],
                category=topic.category,
                state=TrendState.EMERGING,
                score=score,
                sources=topic.sources,
                item_count=topic.item_count,
                total_engagement=topic.total_engagement,
                velocity=0.0,
                first_seen=topic.first_seen,
                last_updated=topic.last_updated,
                language=topic.language,
                keywords=topic.keywords,
            )
            trends.append(trend)

        return trends

    async def calculate_score(self, topic: Topic) -> float:
        """Calculate simple engagement score."""
        metrics = topic.total_engagement
        score = (
            metrics.upvotes * 1.0
            + metrics.comments * 2.0
            + metrics.views * 0.01
            + metrics.score * 0.5
        )
        return score

    async def calculate_velocity(self, trend: Trend) -> float:
        """Calculate fake velocity."""
        # In real implementation, would compare engagement over time
        return 5.0  # Mock velocity

    async def apply_source_diversity(
        self, trends: List[Trend], max_percentage: float = 0.20
    ) -> List[Trend]:
        """Apply source diversity filtering."""
        # In real implementation, would filter based on source distribution
        # For mock, just return all trends
        return trends
