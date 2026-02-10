"""
Intelligence layer for the Trend Intelligence Platform.

This package provides AI-powered analysis including embeddings,
LLM integration, semantic search, and trend detection.
"""

from trend_agent.intelligence.interfaces import (
    EmbeddingService,
    LLMService,
    SemanticSearchService,
    TrendDetector,
    TranslationService,
)

__all__ = [
    "EmbeddingService",
    "LLMService",
    "SemanticSearchService",
    "TrendDetector",
    "TranslationService",
]
