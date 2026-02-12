"""
Intelligence layer interface contracts.

This module defines Protocol classes for AI-powered services including
embeddings, LLM, semantic search, trend detection, and translation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Tuple

from trend_agent.schemas import (
    ProcessedItem,
    SemanticSearchRequest,
    Topic,
    Trend,
    TrendState,
    VectorMatch,
)


class EmbeddingService(Protocol):
    """Interface for text embedding generation."""

    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        ...

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: Texts to embed

        Returns:
            List of embedding vectors
        """
        ...

    def get_dimension(self) -> int:
        """
        Get embedding vector dimension.

        Returns:
            Embedding dimension size
        """
        ...

    def get_model_name(self) -> str:
        """
        Get the name of the embedding model.

        Returns:
            Model name
        """
        ...


class LLMService(Protocol):
    """Interface for Large Language Model operations."""

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            **kwargs: Additional model-specific parameters

        Returns:
            Generated text
        """
        ...

    async def summarize(
        self, text: str, max_length: int = 200, style: str = "concise"
    ) -> str:
        """
        Summarize text.

        Args:
            text: Text to summarize
            max_length: Maximum summary length in characters
            style: Summary style (concise, detailed, bullet_points)

        Returns:
            Summary text
        """
        ...

    async def summarize_topics(
        self, topics: List[Topic], max_topics: int = 10
    ) -> List[str]:
        """
        Generate summaries for multiple topics.

        Args:
            topics: Topics to summarize
            max_topics: Maximum topics to process

        Returns:
            List of summaries
        """
        ...

    async def extract_key_points(self, text: str, max_points: int = 5) -> List[str]:
        """
        Extract key points from text.

        Args:
            text: Text to analyze
            max_points: Maximum key points to extract

        Returns:
            List of key points
        """
        ...

    async def analyze_trend(self, trend: Trend) -> Dict[str, Any]:
        """
        Perform deep analysis of a trend.

        Args:
            trend: Trend to analyze

        Returns:
            Analysis results including sentiment, topics, entities
        """
        ...

    async def generate_tags(self, text: str, max_tags: int = 10) -> List[str]:
        """
        Generate tags for text.

        Args:
            text: Text to tag
            max_tags: Maximum tags to generate

        Returns:
            List of tags
        """
        ...


class SemanticSearchService(Protocol):
    """Interface for semantic search operations."""

    async def search(self, request: SemanticSearchRequest) -> List[Trend]:
        """
        Perform semantic search for trends.

        Args:
            request: Search request with query and filters

        Returns:
            List of matching trends
        """
        ...

    async def search_similar(
        self, trend_id: str, limit: int = 10, min_similarity: float = 0.7
    ) -> List[Trend]:
        """
        Find trends similar to a given trend.

        Args:
            trend_id: ID of the trend to match
            limit: Maximum results to return
            min_similarity: Minimum similarity score

        Returns:
            List of similar trends
        """
        ...

    async def search_by_embedding(
        self, embedding: List[float], limit: int = 10, filters: Optional[Dict] = None
    ) -> List[VectorMatch]:
        """
        Search using a pre-computed embedding.

        Args:
            embedding: Query embedding vector
            limit: Maximum results to return
            filters: Optional metadata filters

        Returns:
            List of vector matches
        """
        ...


class TrendDetector(Protocol):
    """Interface for trend detection and state tracking."""

    async def detect_trends(self, topics: List[Topic]) -> List[Trend]:
        """
        Detect trends from topics.

        Args:
            topics: Topics to analyze

        Returns:
            Detected trends
        """
        ...

    async def update_trend_state(self, trend: Trend) -> TrendState:
        """
        Update the lifecycle state of a trend.

        Args:
            trend: Trend to update

        Returns:
            New trend state
        """
        ...

    async def detect_emerging(self, topics: List[Topic]) -> List[Trend]:
        """
        Detect emerging trends.

        Args:
            topics: Topics to analyze

        Returns:
            Emerging trends
        """
        ...

    async def detect_viral(self, trends: List[Trend]) -> List[Trend]:
        """
        Detect viral trends (rapid growth).

        Args:
            trends: Trends to analyze

        Returns:
            Viral trends
        """
        ...

    async def detect_declining(self, trends: List[Trend]) -> List[Trend]:
        """
        Detect declining trends.

        Args:
            trends: Trends to analyze

        Returns:
            Declining trends
        """
        ...

    async def calculate_momentum(self, trend: Trend) -> float:
        """
        Calculate trend momentum.

        Args:
            trend: Trend to analyze

        Returns:
            Momentum score
        """
        ...

    async def predict_peak(self, trend: Trend) -> Optional[Tuple[float, str]]:
        """
        Predict when a trend will peak.

        Args:
            trend: Trend to analyze

        Returns:
            Tuple of (hours_until_peak, confidence_level) or None
        """
        ...


class TranslationService(Protocol):
    """Interface for multi-language translation."""

    async def translate(
        self, text: str, target_language: str, source_language: Optional[str] = None
    ) -> str:
        """
        Translate text to target language.

        Args:
            text: Text to translate
            target_language: Target language code (ISO 639-1)
            source_language: Source language code (auto-detect if None)

        Returns:
            Translated text
        """
        ...

    async def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> List[str]:
        """
        Translate multiple texts.

        Args:
            texts: Texts to translate
            target_language: Target language code
            source_language: Source language code (auto-detect if None)

        Returns:
            List of translated texts
        """
        ...

    async def detect_language(self, text: str) -> str:
        """
        Detect the language of text.

        Args:
            text: Text to analyze

        Returns:
            ISO 639-1 language code
        """
        ...

    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported language codes.

        Returns:
            List of ISO 639-1 language codes
        """
        ...


class SentimentAnalyzer(Protocol):
    """Interface for sentiment analysis."""

    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment scores and classification
        """
        ...

    async def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for multiple texts.

        Args:
            texts: Texts to analyze

        Returns:
            List of sentiment analysis results
        """
        ...

    async def get_overall_sentiment(self, topic: Topic) -> str:
        """
        Get overall sentiment for a topic.

        Args:
            topic: Topic to analyze

        Returns:
            Sentiment label (positive, negative, neutral)
        """
        ...


# ============================================================================
# Abstract Base Classes
# ============================================================================


class BaseEmbeddingService(ABC):
    """Abstract base class for embedding service implementations."""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        pass


class BaseLLMService(ABC):
    """Abstract base class for LLM service implementations."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        pass

    @abstractmethod
    async def summarize(
        self, text: str, max_length: int = 200, style: str = "concise"
    ) -> str:
        pass

    @abstractmethod
    async def summarize_topics(
        self, topics: List[Topic], max_topics: int = 10
    ) -> List[str]:
        pass

    @abstractmethod
    async def extract_key_points(self, text: str, max_points: int = 5) -> List[str]:
        pass

    @abstractmethod
    async def analyze_trend(self, trend: Trend) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_tags(self, text: str, max_tags: int = 10) -> List[str]:
        pass


class BaseSemanticSearchService(ABC):
    """Abstract base class for semantic search implementations."""

    @abstractmethod
    async def search(self, request: SemanticSearchRequest) -> List[Trend]:
        pass

    @abstractmethod
    async def search_similar(
        self, trend_id: str, limit: int = 10, min_similarity: float = 0.7
    ) -> List[Trend]:
        pass

    @abstractmethod
    async def search_by_embedding(
        self, embedding: List[float], limit: int = 10, filters: Optional[Dict] = None
    ) -> List[VectorMatch]:
        pass


class BaseTrendDetector(ABC):
    """Abstract base class for trend detector implementations."""

    @abstractmethod
    async def detect_trends(self, topics: List[Topic]) -> List[Trend]:
        pass

    @abstractmethod
    async def update_trend_state(self, trend: Trend) -> TrendState:
        pass

    @abstractmethod
    async def detect_emerging(self, topics: List[Topic]) -> List[Trend]:
        pass

    @abstractmethod
    async def detect_viral(self, trends: List[Trend]) -> List[Trend]:
        pass

    @abstractmethod
    async def detect_declining(self, trends: List[Trend]) -> List[Trend]:
        pass

    @abstractmethod
    async def calculate_momentum(self, trend: Trend) -> float:
        pass

    @abstractmethod
    async def predict_peak(self, trend: Trend) -> Optional[Tuple[float, str]]:
        pass


class BaseTranslationService(ABC):
    """Abstract base class for translation service implementations."""

    @abstractmethod
    async def translate(
        self, text: str, target_language: str, source_language: Optional[str] = None
    ) -> str:
        pass

    @abstractmethod
    async def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> List[str]:
        pass

    @abstractmethod
    async def detect_language(self, text: str) -> str:
        pass

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        pass


# ============================================================================
# Exceptions
# ============================================================================


class IntelligenceError(Exception):
    """Base exception for intelligence operations."""

    pass


class EmbeddingError(IntelligenceError):
    """Exception for embedding generation failures."""

    pass


class LLMError(IntelligenceError):
    """Exception for LLM operation failures."""

    pass


class SearchError(IntelligenceError):
    """Exception for search operation failures."""

    pass


class TranslationError(IntelligenceError):
    """Exception for translation failures."""

    pass


class TrendDetectionError(IntelligenceError):
    """Exception for trend detection failures."""

    pass
