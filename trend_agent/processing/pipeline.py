"""
Processing pipeline orchestrator.

This module provides the main pipeline orchestrator that coordinates
all processing stages from raw items to ranked trends.
"""

import logging
import time
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from trend_agent.processing.interfaces import BasePipeline, ProcessingStage
from trend_agent.types import (
    PipelineConfig,
    PipelineResult,
    ProcessedItem,
    ProcessingStatus,
    RawItem,
    Trend,
)

logger = logging.getLogger(__name__)


class ProcessingPipeline(BasePipeline):
    """
    Main processing pipeline orchestrator.

    Coordinates the execution of all processing stages in sequence:
    1. Normalization (clean text, extract entities)
    2. Language Detection
    3. Deduplication (remove duplicates)
    4. Clustering (group into topics)
    5. Ranking (score and rank trends)

    The pipeline is composable - stages can be added/removed dynamically.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize processing pipeline.

        Args:
            config: Optional pipeline configuration
        """
        self._stages: List[ProcessingStage] = []
        self._config = config or PipelineConfig()

    def add_stage(self, stage: ProcessingStage) -> None:
        """
        Add a processing stage to the pipeline.

        Args:
            stage: The processing stage to add

        Note:
            Stages are executed in the order they are added
        """
        stage_name = stage.get_stage_name()
        logger.info(f"Adding stage to pipeline: {stage_name}")
        self._stages.append(stage)

    def remove_stage(self, stage_name: str) -> bool:
        """
        Remove a processing stage from the pipeline.

        Args:
            stage_name: Name of the stage to remove

        Returns:
            True if removed, False if not found
        """
        for i, stage in enumerate(self._stages):
            if stage.get_stage_name() == stage_name:
                self._stages.pop(i)
                logger.info(f"Removed stage from pipeline: {stage_name}")
                return True

        logger.warning(f"Stage not found in pipeline: {stage_name}")
        return False

    async def run(
        self, items: List[RawItem], config: Optional[PipelineConfig] = None
    ) -> PipelineResult:
        """
        Run the complete processing pipeline.

        Args:
            items: Raw items to process
            config: Optional pipeline configuration (overrides instance config)

        Returns:
            Pipeline execution result with statistics and trends

        Raises:
            ProcessingError: If pipeline execution fails critically
        """
        # Use provided config or instance config
        pipeline_config = config or self._config

        # Start timing
        start_time = time.time()
        started_at = datetime.utcnow()

        logger.info(
            f"Starting pipeline execution with {len(items)} raw items, "
            f"{len(self._stages)} stages"
        )

        # Initialize result
        result = PipelineResult(
            status=ProcessingStatus.IN_PROGRESS,
            items_collected=len(items),
            items_processed=0,
            items_deduplicated=0,
            topics_created=0,
            trends_created=0,
            duration_seconds=0.0,
            errors=[],
            started_at=started_at,
        )

        try:
            # Step 1: Convert RawItem to ProcessedItem
            processed_items = self._convert_to_processed_items(items)
            result.items_processed = len(processed_items)

            logger.info(f"Converted {len(processed_items)} items to ProcessedItem format")

            # Step 2: Run through all stages
            current_items = processed_items

            for stage in self._stages:
                stage_name = stage.get_stage_name()
                logger.info(f"Running stage: {stage_name}")

                try:
                    stage_start = time.time()

                    # Execute stage
                    current_items = await stage.process(current_items)

                    # Validate stage output (optional but recommended)
                    if hasattr(stage, "validate"):
                        is_valid = await stage.validate(current_items)
                        if not is_valid:
                            error_msg = f"Stage validation failed: {stage_name}"
                            logger.warning(error_msg)
                            result.errors.append(error_msg)

                    stage_duration = time.time() - stage_start
                    logger.info(
                        f"Stage {stage_name} completed in {stage_duration:.2f}s"
                    )

                except Exception as e:
                    error_msg = f"Stage {stage_name} failed: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    result.errors.append(error_msg)

                    # Decide whether to continue or fail
                    # For now, continue with partial results
                    continue

            # Step 3: Extract final results from metadata
            trends = self._extract_trends(current_items)

            # Update result statistics
            result.items_deduplicated = len(current_items)

            # Extract topics count from metadata if available
            if current_items and "_clustered_topics" in current_items[0].metadata:
                topics = current_items[0].metadata["_clustered_topics"]
                result.topics_created = len(topics)

            result.trends_created = len(trends)

            # Complete timing
            result.duration_seconds = time.time() - start_time
            result.completed_at = datetime.utcnow()

            # Determine final status
            if result.errors:
                result.status = ProcessingStatus.COMPLETED  # Completed with errors
                logger.warning(
                    f"Pipeline completed with {len(result.errors)} errors "
                    f"in {result.duration_seconds:.2f}s"
                )
            else:
                result.status = ProcessingStatus.COMPLETED
                logger.info(
                    f"Pipeline completed successfully in {result.duration_seconds:.2f}s"
                )

            # Store trends in result metadata
            result.metadata = {"trends": trends}

        except Exception as e:
            # Critical failure
            error_msg = f"Pipeline execution failed critically: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.status = ProcessingStatus.FAILED
            result.errors.append(error_msg)
            result.duration_seconds = time.time() - start_time
            result.completed_at = datetime.utcnow()

        return result

    def get_stages(self) -> List[str]:
        """
        Get names of all stages in the pipeline.

        Returns:
            List of stage names in execution order
        """
        return [stage.get_stage_name() for stage in self._stages]

    def _convert_to_processed_items(self, raw_items: List[RawItem]) -> List[ProcessedItem]:
        """
        Convert RawItem objects to ProcessedItem objects.

        Args:
            raw_items: List of raw items

        Returns:
            List of processed items (with normalized fields initialized)
        """
        processed_items = []

        for raw_item in raw_items:
            processed_item = ProcessedItem(
                id=uuid4(),
                source=raw_item.source,
                source_id=raw_item.source_id,
                url=raw_item.url,
                title=raw_item.title,
                title_normalized="",  # Will be filled by normalizer
                description=raw_item.description,
                content=raw_item.content,
                content_normalized=None,  # Will be filled by normalizer
                language="en",  # Default, will be detected
                author=raw_item.author,
                published_at=raw_item.published_at,
                collected_at=raw_item.collected_at,
                metrics=raw_item.metrics,
                category=None,  # Will be assigned during clustering
                embedding=None,  # Will be generated if needed
                metadata=raw_item.metadata.copy(),
            )
            processed_items.append(processed_item)

        return processed_items

    def _extract_trends(self, items: List[ProcessedItem]) -> List[Trend]:
        """
        Extract trends from processed items metadata.

        Args:
            items: Processed items with trends in metadata

        Returns:
            List of trends
        """
        if not items:
            return []

        # Trends should be in the first item's metadata
        trends = items[0].metadata.get("_ranked_trends", [])

        logger.info(f"Extracted {len(trends)} trends from pipeline results")

        return trends


# ============================================================================
# Pipeline Factory Functions
# ============================================================================


def create_standard_pipeline(
    embedding_service,
    llm_service=None,
    config: Optional[PipelineConfig] = None,
) -> ProcessingPipeline:
    """
    Create a standard processing pipeline with all stages.

    Args:
        embedding_service: Embedding service for deduplication and clustering
        llm_service: Optional LLM service for enhanced features
        config: Optional pipeline configuration

    Returns:
        Configured processing pipeline

    Example:
        >>> from tests.mocks.intelligence import MockEmbeddingService
        >>> embedding_svc = MockEmbeddingService()
        >>> pipeline = create_standard_pipeline(embedding_svc)
        >>> result = await pipeline.run(raw_items)
    """
    from trend_agent.processing.cluster import ClustererStage, HDBSCANClusterer
    from trend_agent.processing.deduplicate import (
        DeduplicatorStage,
        EmbeddingDeduplicator,
    )
    from trend_agent.processing.language import LanguageDetectorStage
    from trend_agent.processing.normalizer import NormalizerStage
    from trend_agent.processing.rank import RankerStage

    pipeline = ProcessingPipeline(config=config)

    # Use config values if available
    cfg = config or PipelineConfig()

    # Stage 1: Normalization
    normalizer_stage = NormalizerStage(extract_entities=False)  # Disable spaCy by default
    pipeline.add_stage(normalizer_stage)

    # Stage 2: Language Detection
    language_stage = LanguageDetectorStage()
    pipeline.add_stage(language_stage)

    # Stage 3: Deduplication
    deduplicator = EmbeddingDeduplicator(embedding_service)
    deduplicator_stage = DeduplicatorStage(
        deduplicator=deduplicator,
        threshold=cfg.deduplication_threshold,
    )
    pipeline.add_stage(deduplicator_stage)

    # Stage 4: Clustering
    clusterer = HDBSCANClusterer(
        embedding_service=embedding_service,
        llm_service=llm_service,
        min_cluster_size=cfg.min_cluster_size,
    )
    clusterer_stage = ClustererStage(
        clusterer=clusterer,
        min_cluster_size=cfg.min_cluster_size,
        distance_threshold=cfg.clustering_distance_threshold,
    )
    pipeline.add_stage(clusterer_stage)

    # Stage 5: Ranking
    ranker_stage = RankerStage(
        max_trends=cfg.max_trends_per_category,
        enable_source_diversity=cfg.source_diversity_enabled,
        max_percentage_per_source=cfg.max_percentage_per_source,
    )
    pipeline.add_stage(ranker_stage)

    logger.info(
        f"Created standard pipeline with {len(pipeline.get_stages())} stages: "
        f"{', '.join(pipeline.get_stages())}"
    )

    return pipeline


def create_minimal_pipeline(
    embedding_service,
    config: Optional[PipelineConfig] = None,
) -> ProcessingPipeline:
    """
    Create a minimal pipeline with only essential stages.

    Includes: Normalization, Deduplication, Clustering

    Args:
        embedding_service: Embedding service
        config: Optional pipeline configuration

    Returns:
        Configured minimal pipeline
    """
    from trend_agent.processing.cluster import ClustererStage, HDBSCANClusterer
    from trend_agent.processing.deduplicate import (
        DeduplicatorStage,
        EmbeddingDeduplicator,
    )
    from trend_agent.processing.normalizer import NormalizerStage

    pipeline = ProcessingPipeline(config=config)
    cfg = config or PipelineConfig()

    # Stage 1: Normalization
    pipeline.add_stage(NormalizerStage())

    # Stage 2: Deduplication
    deduplicator = EmbeddingDeduplicator(embedding_service)
    pipeline.add_stage(
        DeduplicatorStage(deduplicator=deduplicator, threshold=cfg.deduplication_threshold)
    )

    # Stage 3: Clustering
    clusterer = HDBSCANClusterer(embedding_service=embedding_service)
    pipeline.add_stage(
        ClustererStage(
            clusterer=clusterer,
            min_cluster_size=cfg.min_cluster_size,
            distance_threshold=cfg.clustering_distance_threshold,
        )
    )

    logger.info(f"Created minimal pipeline with {len(pipeline.get_stages())} stages")

    return pipeline
