"""
Mock intelligence implementations for testing.

These mocks provide simple implementations of AI services
for use during development and testing.
"""

import hashlib
import random
from typing import Any, Dict, List, Optional

from trend_agent.intelligence.interfaces import (
    BaseEmbeddingService,
    BaseLLMService,
    BaseSemanticSearchService,
)
from trend_agent.types import (
    SemanticSearchRequest,
    Topic,
    Trend,
    VectorMatch,
)


class MockEmbeddingService(BaseEmbeddingService):
    """Mock embedding service that generates deterministic fake embeddings."""

    def __init__(self, dimension: int = 1536):
        self._dimension = dimension
        self._model_name = "mock-embedding-model"

    async def embed(self, text: str) -> List[float]:
        """Generate a deterministic fake embedding based on text hash."""
        # Use text hash as seed for reproducibility
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        random.seed(seed)

        # Generate random normalized vector
        vector = [random.gauss(0, 1) for _ in range(self._dimension)]

        # Normalize
        magnitude = sum(x * x for x in vector) ** 0.5
        if magnitude > 0:
            vector = [x / magnitude for x in vector]

        return vector

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return [await self.embed(text) for text in texts]

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension

    def get_model_name(self) -> str:
        """Get model name."""
        return self._model_name


class MockLLMService(BaseLLMService):
    """Mock LLM service that generates simple fake responses."""

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Generate fake text response."""
        return f"Mock LLM response to: {prompt[:100]}..."

    async def summarize(
        self, text: str, max_length: int = 200, style: str = "concise"
    ) -> str:
        """Generate fake summary."""
        words = text.split()[:30]
        return " ".join(words) + "... [Mock summary]"

    async def summarize_topics(
        self, topics: List[Topic], max_topics: int = 10
    ) -> List[str]:
        """Generate fake summaries for topics."""
        return [
            f"Summary of {topic.title[:50]}... [Mock summary]"
            for topic in topics[:max_topics]
        ]

    async def extract_key_points(self, text: str, max_points: int = 5) -> List[str]:
        """Extract fake key points."""
        return [
            f"Key point {i+1}: Mock key point from text"
            for i in range(min(max_points, 3))
        ]

    async def analyze_trend(self, trend: Trend) -> Dict[str, Any]:
        """Perform fake trend analysis."""
        return {
            "sentiment": "positive",
            "sentiment_score": 0.75,
            "topics": ["topic1", "topic2", "topic3"],
            "entities": {
                "people": ["Person A", "Person B"],
                "organizations": ["Org A"],
                "locations": ["Location A"],
            },
            "summary": f"Mock analysis of {trend.title}",
        }

    async def generate_tags(self, text: str, max_tags: int = 10) -> List[str]:
        """Generate fake tags."""
        common_tags = [
            "technology",
            "news",
            "trending",
            "viral",
            "popular",
            "breaking",
            "update",
            "analysis",
        ]
        return common_tags[:max_tags]


class MockSemanticSearchService(BaseSemanticSearchService):
    """Mock semantic search service."""

    def __init__(
        self,
        embedding_service: Optional[MockEmbeddingService] = None,
        trend_repo: Optional[Any] = None,
    ):
        self._embedding_service = embedding_service or MockEmbeddingService()
        self._trend_repo = trend_repo

    async def search(self, request: SemanticSearchRequest) -> List[Trend]:
        """Perform fake semantic search."""
        # In a real implementation, this would:
        # 1. Generate query embedding
        # 2. Search vector DB
        # 3. Fetch full trend objects
        # 4. Apply filters

        # For mock, return empty list
        return []

    async def search_similar(
        self, trend_id: str, limit: int = 10, min_similarity: float = 0.7
    ) -> List[Trend]:
        """Find fake similar trends."""
        # In real implementation, would fetch trend embedding and search
        return []

    async def search_by_embedding(
        self, embedding: List[float], limit: int = 10, filters: Optional[Dict] = None
    ) -> List[VectorMatch]:
        """Search using fake embedding."""
        # Generate some fake results
        fake_results = [
            VectorMatch(
                id=f"trend_{i}",
                score=0.95 - (i * 0.05),
                metadata={"category": "Technology", "source": "reddit"},
            )
            for i in range(min(limit, 5))
        ]
        return fake_results
