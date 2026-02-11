"""
AI Services for the Trend Intelligence Platform.

This package provides production-ready implementations of AI services:
- Embedding generation (OpenAI)
- LLM operations (OpenAI, Anthropic)
- Semantic search (Qdrant)
- Translation (OpenAI, LibreTranslate, DeepL)
"""

from trend_agent.services.embeddings import OpenAIEmbeddingService
from trend_agent.services.factory import (
    ServiceFactory,
    get_service_factory,
    close_global_factory,
)
from trend_agent.services.llm import AnthropicLLMService, OpenAILLMService
from trend_agent.services.search import QdrantSemanticSearchService

__all__ = [
    "OpenAIEmbeddingService",
    "OpenAILLMService",
    "AnthropicLLMService",
    "QdrantSemanticSearchService",
    "ServiceFactory",
    "get_service_factory",
    "close_global_factory",
]
