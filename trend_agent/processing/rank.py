"""
Ranking module for processing pipeline.

This module provides ranking and scoring of topics into trends using
composite scoring with engagement, velocity, and diversity metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from trend_agent.processing.interfaces import BaseRanker, BaseProcessingStage
from trend_agent.types import ProcessedItem, Topic, Trend, TrendState

logger = logging.getLogger(__name__)


class CompositeRanker(BaseRanker):
    """
    Ranker that uses composite scoring with engagement, recency, and velocity.

    Scoring factors:
    - Engagement metrics (upvotes, comments, shares, views)
    - Recency (boost for recent trends)
    - Velocity (rate of engagement growth)
    - Source diversity (bonus for multiple sources)
    """

    def __init__(
        self,
        engagement_weight: float = 0.5,
        recency_weight: float = 0.2,
        velocity_weight: float = 0.2,
        diversity_weight: float = 0.1,
    ):
        """
        Initialize composite ranker.

        Args:
            engagement_weight: Weight for engagement score (default: 0.5)
            recency_weight: Weight for recency score (default: 0.2)
            velocity_weight: Weight for velocity score (default: 0.2)
            diversity_weight: Weight for diversity score (default: 0.1)

        Note:
            Weights should sum to 1.0 for normalized scoring
        """
        self._engagement_weight = engagement_weight
        self._recency_weight = recency_weight
        self._velocity_weight = velocity_weight
        self._diversity_weight = diversity_weight

    async def rank(self, topics: List[Topic]) -> List[Trend]:
        """
        Rank topics into trends with composite scoring.

        Args:
            topics: Topics to rank

        Returns:
            Ranked trends (sorted by score descending)
        """
        if not topics:
            return []

        # Convert topics to trends with scores
        trends = []
        for topic in topics:
            score = await self.calculate_score(topic)

            # Create trend from topic
            trend = Trend(
                id=uuid4(),
                topic_id=topic.id,
                rank=0,  # Will be set after sorting
                title=topic.title,
                summary=topic.summary,
                key_points=[],  # TODO: extract key points
                category=topic.category,
                state=self._determine_trend_state(topic),
                score=score,
                sources=topic.sources,
                item_count=topic.item_count,
                total_engagement=topic.total_engagement,
                velocity=0.0,  # Will be calculated
                first_seen=topic.first_seen,
                last_updated=topic.last_updated,
                language=topic.language,
                keywords=topic.keywords,
                metadata=topic.metadata,
            )

            # Calculate velocity
            trend.velocity = await self.calculate_velocity(trend)

            trends.append(trend)

        # Sort by score descending
        trends.sort(key=lambda t: t.score, reverse=True)

        # Assign ranks
        for rank, trend in enumerate(trends, start=1):
            trend.rank = rank

        logger.info(f"Ranked {len(trends)} trends")

        return trends

    async def calculate_score(self, topic: Topic) -> float:
        """
        Calculate composite score for a topic.

        Args:
            topic: Topic to score

        Returns:
            Composite score (higher is better)

        Note:
            Score is normalized to 0-100 range for interpretability
        """
        # 1. Engagement score (based on metrics)
        engagement_score = self._calculate_engagement_score(topic)

        # 2. Recency score (boost recent topics)
        recency_score = self._calculate_recency_score(topic)

        # 3. Velocity score (estimate growth rate)
        velocity_score = self._estimate_velocity_score(topic)

        # 4. Diversity score (bonus for multiple sources)
        diversity_score = self._calculate_diversity_score(topic)

        # Composite score (weighted sum)
        composite_score = (
            (engagement_score * self._engagement_weight)
            + (recency_score * self._recency_weight)
            + (velocity_score * self._velocity_weight)
            + (diversity_score * self._diversity_weight)
        )

        # Normalize to 0-100 range
        normalized_score = min(100.0, max(0.0, composite_score))

        logger.debug(
            f"Topic '{topic.title[:50]}' scores: "
            f"engagement={engagement_score:.1f}, "
            f"recency={recency_score:.1f}, "
            f"velocity={velocity_score:.1f}, "
            f"diversity={diversity_score:.1f}, "
            f"composite={normalized_score:.1f}"
        )

        return normalized_score

    async def calculate_velocity(self, trend: Trend) -> float:
        """
        Calculate engagement velocity for a trend.

        Args:
            trend: Trend to analyze

        Returns:
            Velocity score (engagement per hour)

        Note:
            Velocity = total_engagement / time_span_hours
            Higher velocity indicates rapid growth
        """
        # Calculate time span in hours
        time_span = trend.last_updated - trend.first_seen
        hours = max(1.0, time_span.total_seconds() / 3600)

        # Calculate total engagement
        total_engagement = (
            trend.total_engagement.upvotes
            + trend.total_engagement.comments * 2  # Weight comments higher
            + trend.total_engagement.shares * 3  # Weight shares even higher
            + trend.total_engagement.views * 0.1  # Weight views lower
        )

        # Velocity = engagement per hour
        velocity = total_engagement / hours

        logger.debug(
            f"Trend '{trend.title[:50]}' velocity: "
            f"{velocity:.2f} engagement/hour "
            f"(timespan={hours:.1f}h, total_engagement={total_engagement})"
        )

        return velocity

    async def apply_source_diversity(
        self, trends: List[Trend], max_percentage: float = 0.20
    ) -> List[Trend]:
        """
        Apply source diversity rules to trends.

        Ensures no single source dominates the trend list by limiting
        the percentage of trends from any single source.

        Args:
            trends: Trends to filter
            max_percentage: Maximum percentage from single source (default: 0.20)

        Returns:
            Filtered trends with source diversity enforced

        Example:
            If max_percentage=0.20 and there are 10 trends, max 2 trends
            can be from the same source.
        """
        if not trends:
            return trends

        max_per_source = max(1, int(len(trends) * max_percentage))

        # Track source counts
        source_counts = {}
        filtered_trends = []

        for trend in trends:
            # Get primary source (first source in list)
            primary_source = trend.sources[0] if trend.sources else None

            if primary_source is None:
                # No source info, include it
                filtered_trends.append(trend)
                continue

            # Check if we've reached the limit for this source
            current_count = source_counts.get(primary_source, 0)

            if current_count < max_per_source:
                filtered_trends.append(trend)
                source_counts[primary_source] = current_count + 1
            else:
                logger.debug(
                    f"Filtered trend '{trend.title[:50]}' "
                    f"(source diversity: {primary_source} at limit)"
                )

        removed_count = len(trends) - len(filtered_trends)
        if removed_count > 0:
            logger.info(
                f"Applied source diversity: removed {removed_count} trends "
                f"(max {max_percentage*100:.0f}% per source)"
            )

        return filtered_trends

    def _calculate_engagement_score(self, topic: Topic) -> float:
        """
        Calculate engagement score from metrics.

        Args:
            topic: Topic with engagement metrics

        Returns:
            Engagement score (0-100)
        """
        # Weight different engagement types
        weighted_engagement = (
            topic.total_engagement.upvotes * 1.0
            + topic.total_engagement.comments * 2.0  # Comments worth more
            + topic.total_engagement.shares * 3.0  # Shares worth even more
            + topic.total_engagement.views * 0.1  # Views worth less
            + topic.total_engagement.score * 1.5  # Platform score
        )

        # Apply logarithmic scaling for better distribution
        import math

        score = math.log10(max(1, weighted_engagement)) * 10

        # Normalize to 0-100
        return min(100.0, score)

    def _calculate_recency_score(self, topic: Topic) -> float:
        """
        Calculate recency score (boost recent topics).

        Args:
            topic: Topic with timestamps

        Returns:
            Recency score (0-100)
        """
        now = datetime.utcnow()
        age = now - topic.last_updated

        # Decay function: recent = 100, decreases over time
        # Half-life of 24 hours
        half_life_hours = 24
        hours_old = age.total_seconds() / 3600

        import math

        score = 100 * math.exp(-0.693 * hours_old / half_life_hours)

        return max(0.0, score)

    def _estimate_velocity_score(self, topic: Topic) -> float:
        """
        Estimate velocity score from topic metrics.

        Args:
            topic: Topic to analyze

        Returns:
            Velocity score (0-100)
        """
        # Estimate velocity from time span and engagement
        time_span = topic.last_updated - topic.first_seen
        hours = max(1.0, time_span.total_seconds() / 3600)

        total_engagement = (
            topic.total_engagement.upvotes
            + topic.total_engagement.comments * 2
            + topic.total_engagement.shares * 3
        )

        velocity = total_engagement / hours

        # Apply logarithmic scaling
        import math

        score = math.log10(max(1, velocity)) * 15

        return min(100.0, score)

    def _calculate_diversity_score(self, topic: Topic) -> float:
        """
        Calculate diversity score (bonus for multiple sources).

        Args:
            topic: Topic with source information

        Returns:
            Diversity score (0-100)
        """
        num_sources = len(topic.sources)

        # Diminishing returns: 1 source = 20, 2 = 50, 3 = 70, 4+ = 100
        if num_sources == 1:
            return 20.0
        elif num_sources == 2:
            return 50.0
        elif num_sources == 3:
            return 70.0
        else:
            return 100.0

    def _determine_trend_state(self, topic: Topic) -> TrendState:
        """
        Determine trend state from topic metrics.

        Args:
            topic: Topic to analyze

        Returns:
            TrendState enum value
        """
        now = datetime.utcnow()
        age = now - topic.last_updated

        # Simple heuristics for trend state
        # In production, use historical data for accurate state detection

        if age < timedelta(hours=6):
            # Recent activity
            if topic.total_engagement.score > 1000:
                return TrendState.VIRAL
            else:
                return TrendState.EMERGING
        elif age < timedelta(days=1):
            return TrendState.SUSTAINED
        elif age < timedelta(days=3):
            return TrendState.DECLINING
        else:
            return TrendState.DEAD


class RankerStage(BaseProcessingStage):
    """
    Processing stage that ranks topics into trends.

    This stage converts topics to trends with ranking and scoring.
    """

    def __init__(
        self,
        ranker: Optional[CompositeRanker] = None,
        max_trends: Optional[int] = None,
        enable_source_diversity: bool = True,
        max_percentage_per_source: float = 0.20,
    ):
        """
        Initialize ranker stage.

        Args:
            ranker: CompositeRanker instance (creates new if None)
            max_trends: Maximum number of trends to return (None = unlimited)
            enable_source_diversity: Apply source diversity filtering
            max_percentage_per_source: Max percentage from single source (0-1)
        """
        self._ranker = ranker or CompositeRanker()
        self._max_trends = max_trends
        self._enable_source_diversity = enable_source_diversity
        self._max_percentage_per_source = max_percentage_per_source

    async def process(self, items: List[ProcessedItem]) -> List[ProcessedItem]:
        """
        Rank topics into trends.

        Note: This stage extracts topics from metadata and creates trends.
        The trends are stored back in metadata.

        Args:
            items: Items with topics in metadata

        Returns:
            Original items with trends in metadata
        """
        if not items:
            return items

        # Extract topics from metadata
        topics = items[0].metadata.get("_clustered_topics", [])

        if not topics:
            logger.warning("No topics found in metadata for ranking")
            return items

        # Rank topics into trends
        trends = await self._ranker.rank(topics)

        # Apply source diversity if enabled
        if self._enable_source_diversity:
            trends = await self._ranker.apply_source_diversity(
                trends, max_percentage=self._max_percentage_per_source
            )

        # Limit number of trends if specified
        if self._max_trends:
            trends = trends[: self._max_trends]

        # Store trends in metadata
        items[0].metadata["_ranked_trends"] = trends
        logger.info(f"Ranked {len(trends)} trends from {len(topics)} topics")

        return items

    async def validate(self, items: List[ProcessedItem]) -> bool:
        """
        Validate ranking results.

        Args:
            items: Items to validate

        Returns:
            True if trends were created and properly ranked
        """
        if not items:
            return True

        # Check if trends were created
        trends = items[0].metadata.get("_ranked_trends", [])
        if not trends:
            logger.error("Validation failed: no trends created during ranking")
            return False

        # Verify trends are sorted by rank (1, 2, 3, ...)
        for i in range(len(trends) - 1):
            if trends[i].rank < trends[i + 1].rank:
                continue
            logger.error(
                f"Validation failed: trends not properly ranked "
                f"(trend {i} has rank {trends[i].rank}, "
                f"trend {i+1} has rank {trends[i+1].rank})"
            )
            return False

        logger.info(f"Validation passed: {len(trends)} trends properly ranked")
        return True

    def get_stage_name(self) -> str:
        """
        Get the name of this processing stage.

        Returns:
            Stage name
        """
        return "ranker"


# ============================================================================
# Legacy Functions (for backward compatibility)
# ============================================================================


def score_topic(topic):
    """
    Calculate engagement score for a single topic based on metrics.

    Legacy function for backward compatibility.

    Args:
        topic: Topic object

    Returns:
        Engagement score
    """
    return (
        topic.metrics.get("upvotes", 0)
        + topic.metrics.get("comments", 0)
        + topic.metrics.get("score", 0)
    )


def rank_topics(topics):
    """
    Rank topics by their engagement scores in descending order.

    Legacy function for backward compatibility.

    Args:
        topics: List of Topic objects

    Returns:
        Sorted list of topics (highest score first)
    """
    return sorted(topics, key=score_topic, reverse=True)


def score_cluster(cluster):
    """
    Calculate engagement score for a cluster based on metrics.

    Legacy function for backward compatibility.

    Args:
        cluster: List of Topic objects

    Returns:
        Total engagement score
    """
    score = 0
    for t in cluster:
        score += t.metrics.get("upvotes", 0)
        score += t.metrics.get("comments", 0)
        score += t.metrics.get("score", 0)
    return score


def rank_clusters(clusters):
    """
    Rank clusters by their engagement scores in descending order.

    Legacy function for backward compatibility.

    Args:
        clusters: List of clusters

    Returns:
        Sorted list of clusters (highest score first)
    """
    return sorted(clusters, key=score_cluster, reverse=True)
