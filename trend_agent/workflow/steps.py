"""
Built-in Workflow Steps for Trend Intelligence Pipeline.

Provides pre-built steps for common operations:
- Data collection
- Deduplication
- Language detection
- Clustering
- Ranking
- Summarization
"""

import logging
from typing import List, Optional

from trend_agent.workflow.interface import (
    WorkflowStep,
    WorkflowContext,
    StepResult,
    StepStatus,
)
from trend_agent.schemas import RawItem, Topic, Trend

logger = logging.getLogger(__name__)


class CollectDataStep(WorkflowStep):
    """
    Collect data from configured sources.

    Inputs:
        - plugin_names: List of plugin names to collect from (optional)

    Outputs:
        - items: List of collected RawItems
        - item_count: Number of items collected
    """

    def __init__(
        self,
        name: str = "collect_data",
        description: str = "Collect data from sources",
        plugin_names: Optional[List[str]] = None,
    ):
        super().__init__(name, description, retry_count=2)
        self.plugin_names = plugin_names

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute data collection."""
        from trend_agent.ingestion.manager import DefaultPluginManager

        try:
            # Get plugin names from context if not provided
            plugin_names = self.plugin_names or context.inputs.get("plugin_names")

            # Initialize plugin manager
            plugin_manager = DefaultPluginManager()
            await plugin_manager.load_plugins()

            # Collect items
            items: List[RawItem] = []

            if plugin_names:
                # Collect from specific plugins
                for plugin_name in plugin_names:
                    plugin_items = await plugin_manager.collect_from_plugin(plugin_name)
                    items.extend(plugin_items)
            else:
                # Collect from all plugins
                items = await plugin_manager.collect_all()

            logger.info(f"Collected {len(items)} items")

            return StepResult(
                status=StepStatus.COMPLETED,
                outputs={
                    "items": items,
                    "item_count": len(items),
                },
                metadata={"plugin_count": len(plugin_names or plugin_manager.get_all_plugins())},
            )

        except Exception as e:
            logger.error(f"Data collection failed: {e}", exc_info=True)
            return StepResult(
                status=StepStatus.FAILED,
                error=str(e),
            )


class DeduplicateStep(WorkflowStep):
    """
    Deduplicate items using semantic similarity.

    Inputs:
        - items: List of RawItems

    Outputs:
        - items: Deduplicated list of RawItems
        - removed_count: Number of duplicates removed
    """

    def __init__(
        self,
        name: str = "deduplicate",
        description: str = "Remove duplicate items",
        similarity_threshold: float = 0.85,
    ):
        super().__init__(name, description)
        self.similarity_threshold = similarity_threshold

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute deduplication."""
        try:
            items: List[RawItem] = context.outputs.get("items", [])

            if not items:
                return StepResult(
                    status=StepStatus.COMPLETED,
                    outputs={"items": [], "removed_count": 0},
                )

            from trend_agent.processing.dedup import SemanticDeduplicator
            from trend_agent.storage.qdrant import QdrantVectorRepository

            # Initialize deduplicator
            vector_repo = QdrantVectorRepository(
                collection_name="deduplication_temp",
                vector_size=1536,
            )

            deduplicator = SemanticDeduplicator(
                vector_repository=vector_repo,
                similarity_threshold=self.similarity_threshold,
            )

            # Deduplicate
            original_count = len(items)
            unique_items = await deduplicator.deduplicate(items)
            removed_count = original_count - len(unique_items)

            logger.info(f"Removed {removed_count} duplicates from {original_count} items")

            return StepResult(
                status=StepStatus.COMPLETED,
                outputs={
                    "items": unique_items,
                    "removed_count": removed_count,
                },
                metadata={
                    "original_count": original_count,
                    "unique_count": len(unique_items),
                    "duplicate_rate": removed_count / original_count if original_count > 0 else 0,
                },
            )

        except Exception as e:
            logger.error(f"Deduplication failed: {e}", exc_info=True)
            return StepResult(
                status=StepStatus.FAILED,
                error=str(e),
            )


class DetectLanguageStep(WorkflowStep):
    """
    Detect language for each item.

    Inputs:
        - items: List of RawItems

    Outputs:
        - items: RawItems with language detected
    """

    def __init__(
        self,
        name: str = "detect_language",
        description: str = "Detect language of items",
    ):
        super().__init__(name, description)

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute language detection."""
        try:
            items: List[RawItem] = context.outputs.get("items", [])

            from trend_agent.services.language import LanguageDetectionService

            language_service = LanguageDetectionService()

            # Detect language for each item
            for item in items:
                if not item.language:
                    item.language = await language_service.detect(item.title or item.text or "")

            logger.info(f"Detected languages for {len(items)} items")

            return StepResult(
                status=StepStatus.COMPLETED,
                outputs={"items": items},
            )

        except Exception as e:
            logger.error(f"Language detection failed: {e}", exc_info=True)
            return StepResult(
                status=StepStatus.FAILED,
                error=str(e),
            )


class ClusterItemsStep(WorkflowStep):
    """
    Cluster items into topics using HDBSCAN.

    Inputs:
        - items: List of RawItems

    Outputs:
        - topics: List of Topics
        - topic_count: Number of topics created
    """

    def __init__(
        self,
        name: str = "cluster_items",
        description: str = "Cluster items into topics",
        min_cluster_size: int = 3,
    ):
        super().__init__(name, description)
        self.min_cluster_size = min_cluster_size

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute clustering."""
        try:
            items: List[RawItem] = context.outputs.get("items", [])

            if len(items) < self.min_cluster_size:
                logger.warning(f"Not enough items to cluster ({len(items)} < {self.min_cluster_size})")
                return StepResult(
                    status=StepStatus.COMPLETED,
                    outputs={"topics": [], "topic_count": 0},
                )

            from trend_agent.processing.cluster import HDBSCANClusterer
            from trend_agent.storage.qdrant import QdrantVectorRepository

            # Initialize clusterer
            vector_repo = QdrantVectorRepository(
                collection_name="clustering_temp",
                vector_size=1536,
            )

            clusterer = HDBSCANClusterer(
                vector_repository=vector_repo,
                min_cluster_size=self.min_cluster_size,
            )

            # Cluster items
            topics = await clusterer.cluster(items)

            logger.info(f"Created {len(topics)} topics from {len(items)} items")

            return StepResult(
                status=StepStatus.COMPLETED,
                outputs={
                    "topics": topics,
                    "topic_count": len(topics),
                },
                metadata={
                    "item_count": len(items),
                    "cluster_rate": len(topics) / len(items) if len(items) > 0 else 0,
                },
            )

        except Exception as e:
            logger.error(f"Clustering failed: {e}", exc_info=True)
            return StepResult(
                status=StepStatus.FAILED,
                error=str(e),
            )


class RankTopicsStep(WorkflowStep):
    """
    Rank topics to create trends.

    Inputs:
        - topics: List of Topics

    Outputs:
        - trends: List of ranked Trends
        - trend_count: Number of trends created
    """

    def __init__(
        self,
        name: str = "rank_topics",
        description: str = "Rank topics to create trends",
        top_n: int = 100,
    ):
        super().__init__(name, description)
        self.top_n = top_n

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute ranking."""
        try:
            topics: List[Topic] = context.outputs.get("topics", [])

            if not topics:
                return StepResult(
                    status=StepStatus.COMPLETED,
                    outputs={"trends": [], "trend_count": 0},
                )

            from trend_agent.processing.rank import CompositeRanker

            # Initialize ranker
            ranker = CompositeRanker()

            # Rank topics
            trends = await ranker.rank(topics)

            # Limit to top N
            trends = trends[:self.top_n]

            logger.info(f"Ranked {len(topics)} topics, created {len(trends)} trends")

            return StepResult(
                status=StepStatus.COMPLETED,
                outputs={
                    "trends": trends,
                    "trend_count": len(trends),
                },
                metadata={
                    "topic_count": len(topics),
                    "average_score": sum(t.score for t in trends) / len(trends) if trends else 0,
                },
            )

        except Exception as e:
            logger.error(f"Ranking failed: {e}", exc_info=True)
            return StepResult(
                status=StepStatus.FAILED,
                error=str(e),
            )


class GenerateSummariesStep(WorkflowStep):
    """
    Generate summaries for trends using LLM.

    Inputs:
        - trends: List of Trends

    Outputs:
        - trends: Trends with generated summaries
    """

    def __init__(
        self,
        name: str = "generate_summaries",
        description: str = "Generate summaries for trends",
    ):
        super().__init__(name, description, retry_count=1)

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute summary generation."""
        try:
            trends: List[Trend] = context.outputs.get("trends", [])

            if not trends:
                return StepResult(
                    status=StepStatus.COMPLETED,
                    outputs={"trends": []},
                )

            from trend_agent.services.summarization import LLMSummarizationService

            # Initialize summarizer
            summarizer = LLMSummarizationService()

            # Generate summaries
            for trend in trends:
                if not trend.summary:
                    # Collect texts from topic items
                    texts = [item.title or item.text for item in trend.items]
                    trend.summary = await summarizer.summarize(texts)

            logger.info(f"Generated summaries for {len(trends)} trends")

            return StepResult(
                status=StepStatus.COMPLETED,
                outputs={"trends": trends},
            )

        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            return StepResult(
                status=StepStatus.FAILED,
                error=str(e),
            )


class PersistTrendsStep(WorkflowStep):
    """
    Persist trends to database.

    Inputs:
        - trends: List of Trends

    Outputs:
        - saved_count: Number of trends saved
    """

    def __init__(
        self,
        name: str = "persist_trends",
        description: str = "Save trends to database",
    ):
        super().__init__(name, description, retry_count=2)

    async def execute(self, context: WorkflowContext) -> StepResult:
        """Execute trend persistence."""
        try:
            trends: List[Trend] = context.outputs.get("trends", [])

            if not trends:
                return StepResult(
                    status=StepStatus.COMPLETED,
                    outputs={"saved_count": 0},
                )

            from trend_agent.storage.postgres import PostgreSQLConnectionPool
            from trend_agent.storage.repositories.trends import TrendRepository

            # Initialize repository
            db_pool = PostgreSQLConnectionPool()
            await db_pool.connect()

            trend_repo = TrendRepository(db_pool)

            # Save trends
            saved_count = 0
            for trend in trends:
                await trend_repo.save(trend)
                saved_count += 1

            logger.info(f"Saved {saved_count} trends to database")

            return StepResult(
                status=StepStatus.COMPLETED,
                outputs={"saved_count": saved_count},
            )

        except Exception as e:
            logger.error(f"Trend persistence failed: {e}", exc_info=True)
            return StepResult(
                status=StepStatus.FAILED,
                error=str(e),
            )
