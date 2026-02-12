"""
Clustering module for processing pipeline.

This module provides clustering of ProcessedItems into Topics using HDBSCAN
for density-based clustering with automatic cluster number detection.
"""

import logging
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

import hdbscan
import numpy as np

from trend_agent.intelligence.interfaces import BaseEmbeddingService, BaseLLMService
from trend_agent.processing.interfaces import BaseClusterer, BaseProcessingStage
from trend_agent.schemas import Category, Metrics, ProcessedItem, SourceType, Topic

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
        cluster_selection_epsilon: float = 0.0,
        cluster_selection_method: str = "eom",
        prediction_data: bool = True,
    ):
        """
        Initialize HDBSCAN clusterer.

        Args:
            embedding_service: Service for generating embeddings
            llm_service: Optional LLM service for category assignment
            min_cluster_size: Minimum items per cluster (default: 2)
            min_samples: Minimum samples for core point (default: 1)
            cluster_selection_epsilon: Distance threshold for cluster merging (default: 0.0)
            cluster_selection_method: Method for selecting clusters: 'eom' or 'leaf' (default: 'eom')
            prediction_data: Whether to generate prediction data for soft clustering (default: True)
        """
        self._embedding_service = embedding_service
        self._llm_service = llm_service
        self._min_cluster_size = min_cluster_size
        self._min_samples = min_samples
        self._cluster_selection_epsilon = cluster_selection_epsilon
        self._cluster_selection_method = cluster_selection_method
        self._prediction_data = prediction_data
        self._last_clusterer = None  # Store last clusterer for analysis

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

        # Perform HDBSCAN clustering with advanced features
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=self._min_samples,
            metric="euclidean",  # Use euclidean for normalized embeddings
            cluster_selection_method=self._cluster_selection_method,
            cluster_selection_epsilon=self._cluster_selection_epsilon,
            prediction_data=self._prediction_data,  # Enable soft clustering
        )

        cluster_labels = clusterer.fit_predict(embeddings_array)

        # Store clusterer for advanced analysis
        self._last_clusterer = clusterer

        # Get cluster membership probabilities (soft clustering)
        probabilities = clusterer.probabilities_

        # Get outlier scores
        outlier_scores = clusterer.outlier_scores_

        logger.info(
            f"HDBSCAN clustering complete: {len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)} "
            f"clusters found, {sum(cluster_labels == -1)} outliers"
        )

        # Group items by cluster with metadata
        clusters: dict[int, List[ProcessedItem]] = {}
        cluster_metadata: dict[int, dict] = {}

        for item, label, prob, outlier_score in zip(
            items, cluster_labels, probabilities, outlier_scores
        ):
            if label not in clusters:
                clusters[label] = []
                cluster_metadata[label] = {
                    "probabilities": [],
                    "outlier_scores": [],
                }

            clusters[label].append(item)
            cluster_metadata[label]["probabilities"].append(float(prob))
            cluster_metadata[label]["outlier_scores"].append(float(outlier_score))

        # Create topics from clusters with advanced metadata
        topics = []
        for label, cluster_items in clusters.items():
            metadata = cluster_metadata[label]

            # Calculate cluster quality metrics
            avg_probability = np.mean(metadata["probabilities"])
            avg_outlier_score = np.mean(metadata["outlier_scores"])

            if label == -1:
                # Noise cluster - optionally split or group
                logger.info(
                    f"Found {len(cluster_items)} noise items (cluster -1, "
                    f"avg_outlier_score={avg_outlier_score:.3f})"
                )
                # For now, create a single "miscellaneous" topic
                if cluster_items:
                    topic = await self._create_topic_from_items(cluster_items, label)
                    topic.title = "Miscellaneous"
                    topic.category = Category.OTHER
                    topic.metadata.update({
                        "cluster_id": label,
                        "avg_membership_probability": avg_probability,
                        "avg_outlier_score": avg_outlier_score,
                        "is_noise_cluster": True,
                    })
                    topics.append(topic)
            else:
                topic = await self._create_topic_from_items(cluster_items, label)
                topic.metadata.update({
                    "cluster_id": label,
                    "avg_membership_probability": avg_probability,
                    "avg_outlier_score": avg_outlier_score,
                    "is_noise_cluster": False,
                })

                logger.debug(
                    f"Cluster {label}: {len(cluster_items)} items, "
                    f"prob={avg_probability:.3f}, outlier={avg_outlier_score:.3f}"
                )

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

    def get_cluster_persistence(self, cluster_id: int) -> Optional[float]:
        """
        Get persistence score for a cluster.

        Persistence indicates cluster stability - higher values mean
        more stable/persistent clusters.

        Args:
            cluster_id: Cluster label to analyze

        Returns:
            Persistence score (0-1) or None if not available
        """
        if self._last_clusterer is None:
            logger.warning("No clusterer available for persistence analysis")
            return None

        try:
            # Get condensed tree
            condensed_tree = self._last_clusterer.condensed_tree_

            # Find cluster in condensed tree
            cluster_data = condensed_tree[condensed_tree["child"] == cluster_id]

            if len(cluster_data) == 0:
                return None

            # Persistence is the lambda value range
            lambda_birth = cluster_data["lambda_val"].min()
            lambda_death = cluster_data["lambda_val"].max()
            persistence = lambda_death - lambda_birth

            return float(persistence)

        except Exception as e:
            logger.warning(f"Failed to compute persistence for cluster {cluster_id}: {e}")
            return None

    def get_cluster_stability(self, cluster_id: int) -> Optional[float]:
        """
        Get stability score for a cluster.

        Stability scores help determine cluster quality and robustness.

        Args:
            cluster_id: Cluster label to analyze

        Returns:
            Stability score or None if not available
        """
        if self._last_clusterer is None:
            logger.warning("No clusterer available for stability analysis")
            return None

        try:
            # Get cluster tree
            cluster_tree = self._last_clusterer.cluster_persistence_

            # Find stability for this cluster
            if hasattr(cluster_tree, "iloc"):
                # Pandas DataFrame
                cluster_row = cluster_tree[cluster_tree.index == cluster_id]
                if not cluster_row.empty:
                    return float(cluster_row.iloc[0])
            elif isinstance(cluster_tree, dict):
                return cluster_tree.get(cluster_id)

            return None

        except Exception as e:
            logger.warning(f"Failed to compute stability for cluster {cluster_id}: {e}")
            return None

    def get_clustering_quality_metrics(self) -> Dict[str, float]:
        """
        Get overall clustering quality metrics.

        Returns:
            Dictionary with quality metrics including:
            - num_clusters: Number of clusters found
            - num_outliers: Number of outlier points
            - avg_cluster_size: Average cluster size
            - outlier_ratio: Ratio of outliers to total points
            - avg_probability: Average membership probability
        """
        if self._last_clusterer is None:
            logger.warning("No clusterer available for quality analysis")
            return {}

        try:
            labels = self._last_clusterer.labels_
            probabilities = self._last_clusterer.probabilities_

            num_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            num_outliers = sum(labels == -1)
            total_points = len(labels)

            # Calculate cluster sizes
            cluster_sizes = []
            for label in set(labels):
                if label != -1:
                    cluster_sizes.append(sum(labels == label))

            return {
                "num_clusters": num_clusters,
                "num_outliers": num_outliers,
                "total_points": total_points,
                "avg_cluster_size": np.mean(cluster_sizes) if cluster_sizes else 0,
                "outlier_ratio": num_outliers / total_points if total_points > 0 else 0,
                "avg_probability": float(np.mean(probabilities)),
                "min_probability": float(np.min(probabilities)),
                "max_probability": float(np.max(probabilities)),
            }

        except Exception as e:
            logger.error(f"Failed to compute clustering quality metrics: {e}")
            return {}

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


# ============================================================================
# Legacy Function (for backward compatibility)
# ============================================================================


def cluster(topics: List, categories: List[str]) -> tuple[List[List], List[str]]:
    """
    Simple category-based clustering for Django management commands.

    Distributes topics across predefined categories using simple keyword matching.
    This is a simplified version for backward compatibility with the old collect_trends.py.

    Args:
        topics: List of Topic-like objects with 'title' and 'description' attributes
        categories: List of category names to cluster topics into

    Returns:
        Tuple of (clusters, cluster_category_names) where:
        - clusters: List of lists, each containing topics for that category
        - cluster_category_names: List of category names corresponding to each cluster

    Note:
        This is a simplified function for backward compatibility.
        For proper clustering, use HDBSCANClusterer with async/await.
    """
    if not topics:
        return [], []

    if not categories:
        # No categories provided, put all topics in one "General" cluster
        return [topics], ["General"]

    # Create empty cluster for each category
    category_clusters = {cat: [] for cat in categories}

    # Simple keyword-based assignment
    # Try to match topics to categories based on keywords in title/description
    category_keywords = {
        "Technology": ["ai", "tech", "software", "app", "code", "programming", "data", "cloud", "api"],
        "Business": ["company", "business", "startup", "funding", "market", "economy", "stock"],
        "Science": ["research", "study", "science", "discovery", "experiment", "paper"],
        "Politics": ["government", "politics", "election", "policy", "law", "congress"],
        "Entertainment": ["movie", "music", "game", "entertainment", "tv", "show", "video"],
        "Sports": ["sport", "game", "team", "player", "match", "championship"],
        "Health": ["health", "medical", "disease", "treatment", "doctor", "hospital"],
        "General": [],  # Catch-all
    }

    for topic in topics:
        # Get topic text
        title = getattr(topic, 'title', '') or ''
        description = getattr(topic, 'description', '') or ''
        text = f"{title} {description}".lower()

        # Try to match to a category
        matched = False
        for category in categories:
            if category in category_keywords:
                keywords = category_keywords[category]
                if any(keyword in text for keyword in keywords):
                    category_clusters[category].append(topic)
                    matched = True
                    break

        # If no match, assign to first category or "General" if it exists
        if not matched:
            if "General" in category_clusters:
                category_clusters["General"].append(topic)
            elif categories:
                category_clusters[categories[0]].append(topic)

    # Convert dict to lists (filter out empty clusters)
    clusters = []
    cluster_names = []

    for category in categories:
        if category_clusters[category]:  # Only include non-empty clusters
            clusters.append(category_clusters[category])
            cluster_names.append(category)

    # If no topics were assigned to any category, put them all in the first category
    if not clusters and topics:
        clusters = [topics]
        cluster_names = [categories[0] if categories else "General"]

    logger.info(
        f"Category clustering: {len(topics)} topics -> {len(clusters)} categories, "
        f"distribution: {[(name, len(cluster)) for name, cluster in zip(cluster_names, clusters)]}"
    )

    return clusters, cluster_names
