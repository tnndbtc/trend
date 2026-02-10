"""
Mock implementations for testing and parallel development.

These mocks allow different development sessions to work independently
without blocking on dependencies from other sessions.
"""

from tests.mocks.storage import (
    MockTrendRepository,
    MockTopicRepository,
    MockVectorRepository,
    MockCacheRepository,
)
from tests.mocks.intelligence import (
    MockEmbeddingService,
    MockLLMService,
    MockSemanticSearchService,
)
from tests.mocks.processing import (
    MockNormalizer,
    MockDeduplicator,
    MockClusterer,
    MockRanker,
)

__all__ = [
    "MockTrendRepository",
    "MockTopicRepository",
    "MockVectorRepository",
    "MockCacheRepository",
    "MockEmbeddingService",
    "MockLLMService",
    "MockSemanticSearchService",
    "MockNormalizer",
    "MockDeduplicator",
    "MockClusterer",
    "MockRanker",
]
