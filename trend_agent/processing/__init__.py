"""
Processing pipeline module for Trend Intelligence Platform.

This module provides composable processing stages for transforming raw items
into ranked trends through normalization, deduplication, clustering, and ranking.

Main Components:
- ProcessingPipeline: Orchestrator for running all stages
- NormalizerStage: Text normalization and entity extraction
- LanguageDetectorStage: Language detection
- DeduplicatorStage: Duplicate removal using embeddings
- ClustererStage: Topic clustering using HDBSCAN
- RankerStage: Trend ranking with composite scoring

Usage:
    >>> from trend_agent.processing import create_standard_pipeline
    >>> from tests.mocks.intelligence import MockEmbeddingService
    >>>
    >>> embedding_svc = MockEmbeddingService()
    >>> pipeline = create_standard_pipeline(embedding_svc)
    >>> result = await pipeline.run(raw_items)
    >>> trends = result.metadata["trends"]
"""

# Pipeline orchestrator
from trend_agent.processing.pipeline import (
    ProcessingPipeline,
    create_standard_pipeline,
    create_minimal_pipeline,
)

# Individual stage implementations
from trend_agent.processing.normalizer import NormalizerStage, TextNormalizer
from trend_agent.processing.language import (
    LanguageDetectorStage,
    LanguageDetector,
    is_cjk,
    is_rtl,
    get_language_family,
)
from trend_agent.processing.deduplicate import (
    DeduplicatorStage,
    EmbeddingDeduplicator,
)
from trend_agent.processing.cluster import (
    ClustererStage,
    HDBSCANClusterer,
)
from trend_agent.processing.rank import (
    RankerStage,
    CompositeRanker,
)

# Re-export exceptions for convenience
from trend_agent.processing.interfaces import (
    ProcessingError,
    NormalizationError,
    DeduplicationError,
    ClusteringError,
    RankingError,
)

__all__ = [
    # Pipeline
    "ProcessingPipeline",
    "create_standard_pipeline",
    "create_minimal_pipeline",
    # Stages
    "NormalizerStage",
    "LanguageDetectorStage",
    "DeduplicatorStage",
    "ClustererStage",
    "RankerStage",
    # Core implementations
    "TextNormalizer",
    "LanguageDetector",
    "EmbeddingDeduplicator",
    "HDBSCANClusterer",
    "CompositeRanker",
    # Utilities
    "is_cjk",
    "is_rtl",
    "get_language_family",
    # Exceptions
    "ProcessingError",
    "NormalizationError",
    "DeduplicationError",
    "ClusteringError",
    "RankingError",
]
