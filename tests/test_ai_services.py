"""
Unit tests for AI services.

Tests the OpenAI embedding service, LLM services (OpenAI and Anthropic),
and the semantic search service.
"""

import asyncio
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from trend_agent.services.embeddings import OpenAIEmbeddingService
from trend_agent.services.llm import OpenAILLMService, AnthropicLLMService
from trend_agent.services.search import (
    QdrantSemanticSearchService,
    SemanticSearchRequest,
    SemanticSearchFilter,
)
from trend_agent.schemas import Trend, TrendState, Category, SourceType, Metrics
from datetime import datetime, timedelta


# ============================================================================
# Test Fixtures
# ============================================================================


def create_sample_trend(
    trend_id: Optional[str] = None,
    title: str = "Test Trend",
    category: Category = Category.TECHNOLOGY,
) -> Trend:
    """Create a sample trend for testing."""
    return Trend(
        id=uuid4() if trend_id is None else trend_id,
        topic_id=uuid4(),
        rank=1,
        title=title,
        summary="Test summary for the trend",
        key_points=["Point 1", "Point 2", "Point 3"],
        category=category,
        state=TrendState.VIRAL,
        score=95.5,
        sources=[SourceType.REDDIT, SourceType.HACKERNEWS],
        item_count=10,
        total_engagement=Metrics(
            upvotes=1000,
            downvotes=10,
            comments=200,
            shares=50,
            views=10000,
            score=1190.0,
        ),
        velocity=15.5,
        first_seen=datetime.utcnow() - timedelta(hours=6),
        last_updated=datetime.utcnow(),
        peak_engagement_at=datetime.utcnow() - timedelta(hours=2),
        keywords=["test", "trending", "technology"],
        related_trend_ids=[],
    )


# ============================================================================
# OpenAI Embedding Service Tests
# ============================================================================


@pytest.mark.asyncio
class TestOpenAIEmbeddingService:
    """Tests for OpenAIEmbeddingService."""

    @patch("openai.AsyncOpenAI")
    async def test_embed_single_text(self, mock_openai_class):
        """Test embedding a single text."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_response.usage = MagicMock(total_tokens=100)
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAIEmbeddingService(api_key="test-key")

        result = await service.embed("Hello world")

        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)
        assert mock_client.embeddings.create.called

    @patch("openai.AsyncOpenAI")
    async def test_embed_batch(self, mock_openai_class):
        """Test embedding multiple texts in batch."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
            MagicMock(embedding=[0.3] * 1536),
        ]
        mock_response.usage = MagicMock(total_tokens=300)
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAIEmbeddingService(api_key="test-key")

        texts = ["Hello", "World", "Test"]
        results = await service.embed_batch(texts)

        assert len(results) == 3
        assert all(len(emb) == 1536 for emb in results)

    @patch("openai.AsyncOpenAI")
    async def test_embed_batch_splits_large_batches(self, mock_openai_class):
        """Test that large batches are split into multiple API calls."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Create mock embeddings for each call
        mock_response.data = [MagicMock(embedding=[0.1] * 1536) for _ in range(100)]
        mock_response.usage = MagicMock(total_tokens=1000)
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAIEmbeddingService(
            api_key="test-key",
            max_batch_size=100,
        )

        # Create 250 texts (should split into 3 batches: 100, 100, 50)
        texts = [f"Text {i}" for i in range(250)]
        results = await service.embed_batch(texts)

        assert len(results) == 250
        # Should be called 3 times (100, 100, 50)
        assert mock_client.embeddings.create.call_count == 3

    @patch("openai.AsyncOpenAI")
    async def test_cost_tracking(self, mock_openai_class):
        """Test cost tracking for embeddings."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_response.usage = MagicMock(total_tokens=1000)
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAIEmbeddingService(
            api_key="test-key",
            model="text-embedding-3-small",
        )

        await service.embed("Hello world")

        stats = service.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_tokens"] == 1000
        assert stats["total_cost_usd"] > 0

    @patch("openai.AsyncOpenAI")
    async def test_model_configuration(self, mock_openai_class):
        """Test different embedding model configurations."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Test text-embedding-3-small
        service_small = OpenAIEmbeddingService(
            api_key="test-key",
            model="text-embedding-3-small",
        )
        assert service_small.model == "text-embedding-3-small"
        assert service_small.dimension == 1536

        # Test text-embedding-3-large
        service_large = OpenAIEmbeddingService(
            api_key="test-key",
            model="text-embedding-3-large",
        )
        assert service_large.model == "text-embedding-3-large"
        assert service_large.dimension == 3072

    @patch("openai.AsyncOpenAI")
    async def test_retry_on_failure(self, mock_openai_class):
        """Test retry logic on API failure."""
        mock_client = MagicMock()

        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_response.usage = MagicMock(total_tokens=100)

        mock_client.embeddings.create = AsyncMock(
            side_effect=[
                Exception("API Error"),  # First call fails
                mock_response,  # Second call succeeds
            ]
        )
        mock_openai_class.return_value = mock_client

        service = OpenAIEmbeddingService(
            api_key="test-key",
            max_retries=3,
        )

        result = await service.embed("Hello")
        assert len(result) == 1536

        # Should be called twice (1 failure + 1 success)
        assert mock_client.embeddings.create.call_count == 2


# ============================================================================
# OpenAI LLM Service Tests
# ============================================================================


@pytest.mark.asyncio
class TestOpenAILLMService:
    """Tests for OpenAILLMService."""

    @patch("openai.AsyncOpenAI")
    async def test_generate(self, mock_openai_class):
        """Test text generation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Generated text response"))
        ]
        mock_response.usage = MagicMock(prompt_tokens=50, completion_tokens=20)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAILLMService(api_key="test-key")

        result = await service.generate("Test prompt")
        assert result == "Generated text response"

    @patch("openai.AsyncOpenAI")
    async def test_summarize_concise(self, mock_openai_class):
        """Test concise summarization."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="This is a concise summary."))
        ]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=30)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAILLMService(api_key="test-key")

        result = await service.summarize(
            "Long text to summarize...",
            max_length=100,
            style="concise",
        )
        assert "summary" in result.lower()

    @patch("openai.AsyncOpenAI")
    async def test_extract_key_points(self, mock_openai_class):
        """Test key point extraction."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="- First key point\n- Second key point\n- Third key point"
                )
            )
        ]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=40)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAILLMService(api_key="test-key")

        result = await service.extract_key_points("Long text...", num_points=3)

        assert isinstance(result, list)
        assert len(result) >= 1

    @patch("openai.AsyncOpenAI")
    async def test_generate_tags(self, mock_openai_class):
        """Test tag generation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="ai, machine learning, technology"))
        ]
        mock_response.usage = MagicMock(prompt_tokens=80, completion_tokens=20)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAILLMService(api_key="test-key")

        result = await service.generate_tags("Text about AI and ML", num_tags=3)

        assert isinstance(result, list)
        assert len(result) >= 1

    @patch("openai.AsyncOpenAI")
    async def test_analyze_trend(self, mock_openai_class):
        """Test trend analysis."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        analysis_json = """
        {
            "sentiment": "positive",
            "urgency": "high",
            "impact_score": 8.5,
            "predicted_trajectory": "rising"
        }
        """
        mock_response.choices = [MagicMock(message=MagicMock(content=analysis_json))]
        mock_response.usage = MagicMock(prompt_tokens=150, completion_tokens=50)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAILLMService(api_key="test-key")

        result = await service.analyze_trend(
            title="AI Breakthrough",
            description="Major AI advancement",
            metrics={"upvotes": 1000, "comments": 200},
        )

        assert isinstance(result, dict)
        assert "sentiment" in result or "positive" in str(result).lower()

    @patch("openai.AsyncOpenAI")
    async def test_cost_tracking(self, mock_openai_class):
        """Test cost tracking for LLM calls."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAILLMService(
            api_key="test-key",
            model="gpt-4-turbo",
        )

        await service.generate("Test prompt")

        stats = service.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_input_tokens"] == 100
        assert stats["total_output_tokens"] == 50
        assert stats["total_cost_usd"] > 0


# ============================================================================
# Anthropic LLM Service Tests
# ============================================================================


@pytest.mark.asyncio
class TestAnthropicLLMService:
    """Tests for AnthropicLLMService."""

    @patch("anthropic.AsyncAnthropic")
    async def test_generate(self, mock_anthropic_class):
        """Test text generation with Anthropic."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Generated response from Claude")]
        mock_response.usage = MagicMock(input_tokens=50, output_tokens=30)
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_client

        service = AnthropicLLMService(api_key="test-key")

        result = await service.generate("Test prompt")
        assert result == "Generated response from Claude"

    @patch("anthropic.AsyncAnthropic")
    async def test_summarize(self, mock_anthropic_class):
        """Test summarization with Claude."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Claude's summary of the text")]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=40)
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_client

        service = AnthropicLLMService(api_key="test-key")

        result = await service.summarize("Long text...", style="concise")
        assert "summary" in result.lower() or "Claude" in result

    @patch("anthropic.AsyncAnthropic")
    async def test_model_configuration(self, mock_anthropic_class):
        """Test different Claude model configurations."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Test Claude Sonnet
        service_sonnet = AnthropicLLMService(
            api_key="test-key",
            model="claude-3-sonnet-20240229",
        )
        assert "sonnet" in service_sonnet.model

        # Test Claude Opus
        service_opus = AnthropicLLMService(
            api_key="test-key",
            model="claude-3-opus-20240229",
        )
        assert "opus" in service_opus.model


# ============================================================================
# Semantic Search Service Tests
# ============================================================================


@pytest.mark.asyncio
class TestQdrantSemanticSearchService:
    """Tests for QdrantSemanticSearchService."""

    async def test_search_basic(self):
        """Test basic semantic search."""
        # Mock dependencies
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(
            return_value=[
                {"id": str(uuid4()), "score": 0.95},
                {"id": str(uuid4()), "score": 0.90},
            ]
        )

        mock_trend_repo = MagicMock()
        trends = [
            create_sample_trend(title="AI Breakthrough"),
            create_sample_trend(title="Tech Innovation"),
        ]
        mock_trend_repo.get_by_ids = AsyncMock(return_value=trends)

        service = QdrantSemanticSearchService(
            embedding_service=mock_embedding_service,
            vector_repository=mock_vector_repo,
            trend_repository=mock_trend_repo,
        )

        request = SemanticSearchRequest(
            query="AI developments",
            limit=10,
        )

        results = await service.search(request)

        assert len(results) == 2
        assert all(isinstance(t, Trend) for t in results)
        assert mock_embedding_service.embed.called
        assert mock_vector_repo.search.called

    async def test_search_with_filters(self):
        """Test search with metadata filters."""
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(return_value=[])

        mock_trend_repo = MagicMock()
        mock_trend_repo.get_by_ids = AsyncMock(return_value=[])

        service = QdrantSemanticSearchService(
            embedding_service=mock_embedding_service,
            vector_repository=mock_vector_repo,
            trend_repository=mock_trend_repo,
        )

        # Search with category filter
        request = SemanticSearchRequest(
            query="tech news",
            limit=10,
            filters=SemanticSearchFilter(
                category=Category.TECHNOLOGY,
                min_score=80.0,
            ),
        )

        await service.search(request)

        # Verify search was called with filters
        assert mock_vector_repo.search.called
        call_kwargs = mock_vector_repo.search.call_args[1]
        assert "filters" in call_kwargs

    async def test_find_similar(self):
        """Test finding similar trends."""
        mock_embedding_service = MagicMock()

        mock_vector_repo = MagicMock()
        mock_vector_repo.get_by_id = AsyncMock(
            return_value={"id": "test-id", "vector": [0.1] * 1536}
        )
        mock_vector_repo.search = AsyncMock(
            return_value=[
                {"id": str(uuid4()), "score": 0.85},
            ]
        )

        mock_trend_repo = MagicMock()
        trends = [create_sample_trend(title="Similar Trend")]
        mock_trend_repo.get_by_ids = AsyncMock(return_value=trends)

        service = QdrantSemanticSearchService(
            embedding_service=mock_embedding_service,
            vector_repository=mock_vector_repo,
            trend_repository=mock_trend_repo,
        )

        trend_id = uuid4()
        results = await service.find_similar(trend_id, limit=5)

        assert len(results) >= 0
        assert mock_vector_repo.get_by_id.called

    async def test_search_by_embedding(self):
        """Test direct search by embedding vector."""
        mock_embedding_service = MagicMock()

        mock_vector_repo = MagicMock()
        mock_vector_repo.search = AsyncMock(
            return_value=[{"id": str(uuid4()), "score": 0.92}]
        )

        mock_trend_repo = MagicMock()
        trends = [create_sample_trend(title="Matched Trend")]
        mock_trend_repo.get_by_ids = AsyncMock(return_value=trends)

        service = QdrantSemanticSearchService(
            embedding_service=mock_embedding_service,
            vector_repository=mock_vector_repo,
            trend_repository=mock_trend_repo,
        )

        embedding = [0.1] * 1536
        results = await service.search_by_embedding(embedding, limit=10)

        assert len(results) >= 0
        assert mock_vector_repo.search.called
        # Should NOT call embedding service for pre-computed embedding
        assert not mock_embedding_service.embed.called


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
