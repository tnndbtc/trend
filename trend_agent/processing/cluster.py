"""
Clustering module for processing pipeline.

This module provides clustering of ProcessedItems into Topics using HDBSCAN
for density-based clustering with automatic cluster number detection.
"""

import logging
from collections import Counter
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

import hdbscan
import numpy as np

from trend_agent.intelligence.interfaces import BaseEmbeddingService, BaseLLMService
from trend_agent.processing.interfaces import BaseClusterer, BaseProcessingStage
from trend_agent.types import Category, Metrics, ProcessedItem, SourceType, Topic

logger = logging.getLogger(__name__)


class HDBSCANClusterer(BaseClusterer):
    """
    Clusterer that uses HDBSCAN for density-based clustering.

    HDBSCAN (Hierarchical Density-Based Spatial Clustering of Applications with Noise)
    automatically determines the number of clusters and handles varying density well.
    """

    def __init__(
        self,
        embedding_service: BaseEmbeddingService,
        llm_service: Optional[BaseLLMService] = None,
        min_cluster_size: int = 2,
        min_samples: int = 1,
    ):
        """
        Initialize HDBSCAN clusterer.

        Args:
            embedding_service: Service for generating embeddings
            llm_service: Optional LLM service for category assignment
            min_cluster_size: Minimum items per cluster (default: 2)
            min_samples: Minimum samples for core point (default: 1)
        """
        self._embedding_service = embedding_service
        self._llm_service = llm_service
        self._min_cluster_size = min_cluster_size
        self._min_samples = min_samples

    async def cluster(
        self,
        items: List[ProcessedItem],
        min_cluster_size: int = 2,
        distance_threshold: float = 0.3,
    ) -> List[Topic]:
        """
        Cluster items into topics using HDBSCAN.

        Args:
            items: Items to cluster
            min_cluster_size: Minimum items per cluster
            distance_threshold: Maximum distance for clustering (used for epsilon)

        Returns:
            List of topics (clusters)

        Note:
            - Items with cluster label -1 are considered noise and grouped separately
            - Each cluster becomes a Topic with aggregated metadata
        """
        if not items:
            return []

        if len(items) < min_cluster_size:
            logger.info(
                f"Too few items ({len(items)}) for clustering. "
                "Creating single topic."
            )
            return [await self._create_topic_from_items(items, 0)]

        # Generate embeddings for all items
        texts = [self._get_text_for_embedding(item) for item in items]
        embeddings = await self._embedding_service.embed_batch(texts)

        # Convert to numpy array
        embeddings_array = np.array(embeddings)

        # Perform HDBSCAN clustering
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=self._min_samples,
            metric="euclidean",  # Use euclidean for normalized embeddings
            cluster_selection_method="eom",  # Excess of mass (default)
        )

        cluster_labels = clusterer.fit_predict(embeddings_array)

        # Group items by cluster
        clusters: dict[int, List[ProcessedItem]] = {}
        for item, label in zip(items, cluster_labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(item)

        # Create topics from clusters
        topics = []
        for label, cluster_items in clusters.items():
            if label == -1:
                # Noise cluster - optionally split or group
                logger.info(f"Found {len(cluster_items)} noise items (cluster -1)")
                # For now, create a single "miscellaneous" topic
                if cluster_items:
                    topic = await self._create_topic_from_items(cluster_items, label)
                    topic.title = "Miscellaneous"
                    topic.category = Category.OTHER
                    topics.append(topic)
            else:
                topic = await self._create_topic_from_items(cluster_items, label)
                topics.append(topic)

        logger.info(
            f"Clustered {len(items)} items into {len(topics)} topics "
            f"(min_cluster_size={min_cluster_size})"
        )

        return topics

    async def assign_category(self, topic: Topic) -> str:
        """
        Assign a category to a topic using LLM.

        Args:
            topic: Topic to categorize

        Returns:
            Category name

        Note:
            Falls back to heuristic assignment if LLM service not available
        """
        if self._llm_service:
            try:
                # Use LLM to assign category
                prompt = f"""Analyze this topic and assign it to one of these categories:
{', '.join([c.value for c in Category])}

Topic: {topic.title}
Summary: {topic.summary}
Keywords: {', '.join(topic.keywords[:5])}

Respond with only the category name."""

                category_name = await self._llm_service.generate(
                    prompt, max_tokens=50, temperature=0.3
                )

                # Validate category
                category_name = category_name.strip()
                for cat in Category:
                    if cat.value.lower() in category_name.lower():
                        return cat.value

            except Exception as e:
                logger.warning(f"LLM category assignment failed: {e}")

        # Fallback: use keyword-based heuristic
        return self._assign_category_heuristic(topic)

    async def extract_keywords(
        self, topic: Topic, max_keywords: int = 10
    ) -> List[str]:
        """
        Extract keywords from a topic using TF-IDF or LLM.

        Args:
            topic: Topic to analyze
            max_keywords: Maximum keywords to extract

        Returns:
            List of keywords

        Note:
            Uses simple frequency-based extraction if LLM not available
        """
        # For now, use simple word frequency
        # In production, use TF-IDF or LLM extraction
        text = f"{topic.title} {topic.summary}".lower()

        # Remove common words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "is",
            "are",
            "was",
            "were",
            "to",
            "in",
            "on",
            "at",
            "for",
            "of",
            "with",
            "by",
        }

        # Extract words
        words = text.split()
        word_freq = Counter(
            [w for w in words if len(w) > 3 and w not in stop_words]
        )

        # Get top keywords
        keywords = [word for word, _ in word_freq.most_common(max_keywords)]

        return keywords

    async def _create_topic_from_items(
        self, items: List[ProcessedItem], cluster_id: int
    ) -> Topic:
        """
        Create a Topic from a cluster of items.

        Args:
            items: Items in the cluster
            cluster_id: Cluster identifier

        Returns:
            Topic object with aggregated metadata
        """
        # Aggregate metrics
        total_upvotes = sum(item.metrics.upvotes for item in items)
        total_downvotes = sum(item.metrics.downvotes for item in items)
        total_comments = sum(item.metrics.comments for item in items)
        total_shares = sum(item.metrics.shares for item in items)
        total_views = sum(item.metrics.views for item in items)
        total_score = sum(item.metrics.score for item in items)

        total_engagement = Metrics(
            upvotes=total_upvotes,
            downvotes=total_downvotes,
            comments=total_comments,
            shares=total_shares,
            views=total_views,
            score=total_score,
        )

        # Get unique sources
        sources = list(set(item.source for item in items))

        # Get most common language
        languages = [item.language for item in items]
        language = Counter(languages).most_common(1)[0][0] if languages else "en"

        # Get most common category
        categories = [item.category for item in items if item.category]
        category = (
            Counter(categories).most_common(1)[0][0] if categories else Category.OTHER
        )

        # Create title from most engaged item
        items_sorted = sorted(items, key=lambda x: x.metrics.score, reverse=True)
        title = items_sorted[0].title_normalized or items_sorted[0].title

        # Create summary from top items
        summary_texts = []
        for item in items_sorted[:3]:
            text = item.title_normalized or item.title
            if text and text not in summary_texts:
                summary_texts.append(text)

        summary = " | ".join(summary_texts[:3])

        # Get time range
        first_seen = min(item.published_at for item in items)
        last_updated = max(item.published_at for item in items)

        # Create topic
        topic = Topic(
            id=uuid4(),
            title=title,
            summary=summary,
            category=category,
            sources=sources,
            item_count=len(items),
            total_engagement=total_engagement,
            first_seen=first_seen,
            last_updated=last_updated,
            language=language,
            keywords=[],  # Will be populated later
            metadata={"cluster_id": cluster_id},
        )

        # Extract keywords
        topic.keywords = await self.extract_keywords(topic)

        return topic

    def _get_text_for_embedding(self, item: ProcessedItem) -> str:
        """
        Extract text from item for embedding generation.

        Args:
            item: Item to extract text from

        Returns:
            Text suitable for embedding
        """
        # Use normalized title if available
        title = item.title_normalized or item.title

        # Use normalized content if available (limit to 500 chars)
        content = ""
        if item.content_normalized:
            content = item.content_normalized[:500]
        elif item.content:
            content = item.content[:500]

        # Combine title and content
        text = f"{title} {content}".strip()

        return text if text else item.title

    def _assign_category_heuristic(self, topic: Topic) -> str:
        """
        Assign category using keyword-based heuristics.

        Args:
            topic: Topic to categorize

        Returns:
            Category name
        """
        text = f"{topic.title} {topic.summary}".lower()

        # Category keywords
        category_keywords = {
            Category.TECHNOLOGY: [
                "tech",
                "software",
                "ai",
                "computer",
                "app",
                "code",
                "programming",
                "internet",
                "digital",
            ],
            Category.POLITICS: [
                "election",
                "government",
                "president",
                "congress",
                "vote",
                "political",
                "senator",
                "law",
            ],
            Category.ENTERTAINMENT: [
                "movie",
                "film",
                "music",
                "celebrity",
                "actor",
                "show",
                "netflix",
                "entertainment",
            ],
            Category.SPORTS: [
                "game",
                "team",
                "player",
                "football",
                "basketball",
                "soccer",
                "sports",
                "championship",
            ],
            Category.SCIENCE: [
                "research",
                "study",
                "scientist",
                "discovery",
                "science",
                "experiment",
                "space",
                "astronomy",
            ],
            Category.BUSINESS: [
                "company",
                "business",
                "market",
                "stock",
                "economy",
                "finance",
                "ceo",
                "startup",
            ],
            Category.HEALTH: [
                "health",
                "medical",
                "doctor",
                "disease",
                "hospital",
                "vaccine",
                "covid",
                "medicine",
            ],
        }

        # Count keyword matches
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            category_scores[category] = score

        # Get category with highest score
        if max(category_scores.values()) > 0:
            best_category = max(category_scores, key=category_scores.get)
            return best_category.value

        return Category.OTHER.value


class ClustererStage(BaseProcessingStage):
    """
    Processing stage that clusters items into topics.

    This stage uses HDBSCAN to cluster similar items together,
    creating Topic objects from the clusters.
    """

    def __init__(
        self,
        clusterer: Optional[HDBSCANClusterer] = None,
        min_cluster_size: int = 2,
        distance_threshold: float = 0.3,
    ):
        """
        Initialize clusterer stage.

        Args:
            clusterer: HDBSCANClusterer instance (required)
            min_cluster_size: Minimum items per cluster
            distance_threshold: Maximum distance for clustering
        """
        if clusterer is None:
            raise ValueError("ClustererStage requires an HDBSCANClusterer instance")

        self._clusterer = clusterer
        self._min_cluster_size = min_cluster_size
        self._distance_threshold = distance_threshold

    async def process(self, items: List[ProcessedItem]) -> List[ProcessedItem]:
        """
        Cluster items into topics.

        Note: This stage doesn't modify the input items directly.
        Instead, it creates Topic objects stored in metadata.
        The items are returned unchanged.

        Args:
            items: Items to cluster

        Returns:
            Original items (unchanged)

        Note:
            Topics are stored in a special metadata key for later retrieval
        """
        if not items:
            return items

        # Perform clustering
        topics = await self._clusterer.cluster(
            items,
            min_cluster_size=self._min_cluster_size,
            distance_threshold=self._distance_threshold,
        )

        # Store topics in first item's metadata (temporary solution)
        # In production, this would be passed through a different channel
        if items and topics:
            items[0].metadata["_clustered_topics"] = topics
            logger.info(f"Created {len(topics)} topics from {len(items)} items")

        return items

    async def validate(self, items: List[ProcessedItem]) -> bool:
        """
        Validate clustering results.

        Args:
            items: Items to validate

        Returns:
            True if topics were created
        """
        if not items:
            return True

        # Check if topics were created
        has_topics = "_clustered_topics" in items[0].metadata
        if not has_topics:
            logger.error("Validation failed: no topics created during clustering")
            return False

        topics = items[0].metadata["_clustered_topics"]
        logger.info(f"Validation passed: {len(topics)} topics created")
        return True

    def get_stage_name(self) -> str:
        """
        Get the name of this processing stage.

        Returns:
            Stage name
        """
        return "clusterer"
