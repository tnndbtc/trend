"""
Processing layer interface contracts.

This module defines Protocol classes for the data processing pipeline,
including normalization, deduplication, clustering, and ranking stages.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Protocol

from trend_agent.types import (
    PipelineConfig,
    PipelineResult,
    ProcessedItem,
    RawItem,
    Topic,
    Trend,
)


class ProcessingStage(Protocol):
    """
    Interface for a processing pipeline stage.

    Each stage accepts a list of items and returns a processed list.
    Stages should be stateless and composable.
    """

    async def process(self, items: List[ProcessedItem]) -> List[ProcessedItem]:
        """
        Process a batch of items.

        Args:
            items: Items to process

        Returns:
            Processed items

        Raises:
            ProcessingError: If processing fails
        """
        ...

    async def validate(self, items: List[ProcessedItem]) -> bool:
        """
        Validate processed items.

        Args:
            items: Items to validate

        Returns:
            True if all items are valid
        """
        ...

    def get_stage_name(self) -> str:
        """
        Get the name of this processing stage.

        Returns:
            Stage name
        """
        ...


class Pipeline(Protocol):
    """Interface for the processing pipeline orchestrator."""

    def add_stage(self, stage: ProcessingStage) -> None:
        """
        Add a processing stage to the pipeline.

        Args:
            stage: The processing stage to add
        """
        ...

    def remove_stage(self, stage_name: str) -> bool:
        """
        Remove a processing stage from the pipeline.

        Args:
            stage_name: Name of the stage to remove

        Returns:
            True if removed, False if not found
        """
        ...

    async def run(
        self, items: List[RawItem], config: Optional[PipelineConfig] = None
    ) -> PipelineResult:
        """
        Run the complete processing pipeline.

        Args:
            items: Raw items to process
            config: Optional pipeline configuration

        Returns:
            Pipeline execution result
        """
        ...

    def get_stages(self) -> List[str]:
        """
        Get names of all stages in the pipeline.

        Returns:
            List of stage names in execution order
        """
        ...


class Normalizer(Protocol):
    """Interface for text normalization."""

    async def normalize_text(self, text: str) -> str:
        """
        Normalize text content.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        ...

    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary of entity types to entity lists
        """
        ...

    async def clean_html(self, html: str) -> str:
        """
        Clean HTML content.

        Args:
            html: HTML content

        Returns:
            Clean text without HTML tags
        """
        ...


class LanguageDetector(Protocol):
    """Interface for language detection."""

    async def detect(self, text: str) -> str:
        """
        Detect language of text.

        Args:
            text: Text to analyze

        Returns:
            ISO 639-1 language code
        """
        ...

    async def detect_batch(self, texts: List[str]) -> List[str]:
        """
        Detect languages for multiple texts.

        Args:
            texts: Texts to analyze

        Returns:
            List of ISO 639-1 language codes
        """
        ...

    def get_confidence(self) -> float:
        """
        Get confidence score of last detection.

        Returns:
            Confidence score (0-1)
        """
        ...


class Deduplicator(Protocol):
    """Interface for duplicate detection."""

    async def find_duplicates(
        self, items: List[ProcessedItem], threshold: float = 0.92
    ) -> Dict[str, List[ProcessedItem]]:
        """
        Find duplicate items.

        Args:
            items: Items to check for duplicates
            threshold: Similarity threshold (0-1)

        Returns:
            Dictionary mapping representative item IDs to duplicate groups
        """
        ...

    async def remove_duplicates(
        self, items: List[ProcessedItem], threshold: float = 0.92
    ) -> List[ProcessedItem]:
        """
        Remove duplicate items, keeping only one from each group.

        Args:
            items: Items to deduplicate
            threshold: Similarity threshold (0-1)

        Returns:
            Deduplicated items
        """
        ...

    async def is_duplicate(
        self, item1: ProcessedItem, item2: ProcessedItem, threshold: float = 0.92
    ) -> bool:
        """
        Check if two items are duplicates.

        Args:
            item1: First item
            item2: Second item
            threshold: Similarity threshold (0-1)

        Returns:
            True if items are duplicates
        """
        ...


class Clusterer(Protocol):
    """Interface for clustering items into topics."""

    async def cluster(
        self,
        items: List[ProcessedItem],
        min_cluster_size: int = 2,
        distance_threshold: float = 0.3,
    ) -> List[Topic]:
        """
        Cluster items into topics.

        Args:
            items: Items to cluster
            min_cluster_size: Minimum items per cluster
            distance_threshold: Maximum distance for clustering

        Returns:
            List of topics (clusters)
        """
        ...

    async def assign_category(self, topic: Topic) -> str:
        """
        Assign a category to a topic.

        Args:
            topic: Topic to categorize

        Returns:
            Category name
        """
        ...

    async def extract_keywords(self, topic: Topic, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords from a topic.

        Args:
            topic: Topic to analyze
            max_keywords: Maximum keywords to extract

        Returns:
            List of keywords
        """
        ...


class Ranker(Protocol):
    """Interface for ranking and scoring trends."""

    async def rank(self, topics: List[Topic]) -> List[Trend]:
        """
        Rank topics into trends.

        Args:
            topics: Topics to rank

        Returns:
            Ranked trends
        """
        ...

    async def calculate_score(self, topic: Topic) -> float:
        """
        Calculate score for a topic.

        Args:
            topic: Topic to score

        Returns:
            Composite score
        """
        ...

    async def calculate_velocity(self, trend: Trend) -> float:
        """
        Calculate engagement velocity for a trend.

        Args:
            trend: Trend to analyze

        Returns:
            Velocity score
        """
        ...

    async def apply_source_diversity(
        self, trends: List[Trend], max_percentage: float = 0.20
    ) -> List[Trend]:
        """
        Apply source diversity rules to trends.

        Args:
            trends: Trends to filter
            max_percentage: Maximum percentage from single source

        Returns:
            Filtered trends
        """
        ...


# ============================================================================
# Abstract Base Classes
# ============================================================================


class BasePipeline(ABC):
    """Abstract base class for pipeline implementations."""

    @abstractmethod
    def add_stage(self, stage: ProcessingStage) -> None:
        pass

    @abstractmethod
    def remove_stage(self, stage_name: str) -> bool:
        pass

    @abstractmethod
    async def run(
        self, items: List[RawItem], config: Optional[PipelineConfig] = None
    ) -> PipelineResult:
        pass

    @abstractmethod
    def get_stages(self) -> List[str]:
        pass


class BaseProcessingStage(ABC):
    """Abstract base class for processing stage implementations."""

    @abstractmethod
    async def process(self, items: List[ProcessedItem]) -> List[ProcessedItem]:
        pass

    async def validate(self, items: List[ProcessedItem]) -> bool:
        """Default validation accepts all items."""
        return True

    @abstractmethod
    def get_stage_name(self) -> str:
        pass


class BaseNormalizer(ABC):
    """Abstract base class for normalizer implementations."""

    @abstractmethod
    async def normalize_text(self, text: str) -> str:
        pass

    @abstractmethod
    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        pass

    @abstractmethod
    async def clean_html(self, html: str) -> str:
        pass


class BaseDeduplicator(ABC):
    """Abstract base class for deduplicator implementations."""

    @abstractmethod
    async def find_duplicates(
        self, items: List[ProcessedItem], threshold: float = 0.92
    ) -> Dict[str, List[ProcessedItem]]:
        pass

    @abstractmethod
    async def remove_duplicates(
        self, items: List[ProcessedItem], threshold: float = 0.92
    ) -> List[ProcessedItem]:
        pass

    @abstractmethod
    async def is_duplicate(
        self, item1: ProcessedItem, item2: ProcessedItem, threshold: float = 0.92
    ) -> bool:
        pass


class BaseClusterer(ABC):
    """Abstract base class for clusterer implementations."""

    @abstractmethod
    async def cluster(
        self,
        items: List[ProcessedItem],
        min_cluster_size: int = 2,
        distance_threshold: float = 0.3,
    ) -> List[Topic]:
        pass

    @abstractmethod
    async def assign_category(self, topic: Topic) -> str:
        pass

    @abstractmethod
    async def extract_keywords(self, topic: Topic, max_keywords: int = 10) -> List[str]:
        pass


class BaseRanker(ABC):
    """Abstract base class for ranker implementations."""

    @abstractmethod
    async def rank(self, topics: List[Topic]) -> List[Trend]:
        pass

    @abstractmethod
    async def calculate_score(self, topic: Topic) -> float:
        pass

    @abstractmethod
    async def calculate_velocity(self, trend: Trend) -> float:
        pass

    @abstractmethod
    async def apply_source_diversity(
        self, trends: List[Trend], max_percentage: float = 0.20
    ) -> List[Trend]:
        pass


# ============================================================================
# Exceptions
# ============================================================================


class ProcessingError(Exception):
    """Base exception for processing operations."""

    pass


class NormalizationError(ProcessingError):
    """Exception for normalization failures."""

    pass


class DeduplicationError(ProcessingError):
    """Exception for deduplication failures."""

    pass


class ClusteringError(ProcessingError):
    """Exception for clustering failures."""

    pass


class RankingError(ProcessingError):
    """Exception for ranking failures."""

    pass
