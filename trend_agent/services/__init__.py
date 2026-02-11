"""
AI Services for the Trend Intelligence Platform.

This package provides production-ready implementations of AI services:
- Embedding generation (OpenAI)
- LLM operations (OpenAI, Anthropic)
- Semantic search (Qdrant)
- Translation (OpenAI, LibreTranslate, DeepL)
- Trend state management (lifecycle tracking)
- Alert notifications (Email, Slack)
"""

from trend_agent.services.embeddings import OpenAIEmbeddingService
from trend_agent.services.factory import (
    ServiceFactory,
    get_service_factory,
    close_global_factory,
)
from trend_agent.services.llm import AnthropicLLMService, OpenAILLMService
from trend_agent.services.search import QdrantSemanticSearchService
from trend_agent.services.trend_states import TrendStateService, get_trend_state_service
from trend_agent.services.alerts import AlertService, get_alert_service
from trend_agent.services.key_points import KeyPointExtractor, TopicKeyPointExtractor, get_key_point_extractor

__all__ = [
    "OpenAIEmbeddingService",
    "OpenAILLMService",
    "AnthropicLLMService",
    "QdrantSemanticSearchService",
    "TrendStateService",
    "get_trend_state_service",
    "AlertService",
    "get_alert_service",
    "KeyPointExtractor",
    "TopicKeyPointExtractor",
    "get_key_point_extractor",
    "ServiceFactory",
    "get_service_factory",
    "close_global_factory",
]
