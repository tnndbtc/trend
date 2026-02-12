"""
Unit tests for KeyPointExtractor.

Tests key point extraction from trends using LLMs, including parsing,
validation, and fallback mechanisms.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

from trend_agent.services.key_points import (
    KeyPointExtractor,
    TopicKeyPointExtractor,
)
from trend_agent.schemas import (
    Trend,
    Topic,
    ProcessedItem,
    TrendState,
    Metrics,
    Category,
    SourceType,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    service = Mock()
    service.generate = AsyncMock()
    return service


@pytest.fixture
def mock_trend():
    """Create a mock trend for testing."""
    return Trend(
        id=uuid4(),
        topic_id=uuid4(),
        rank=1,
        title="AI Breakthrough in Natural Language Processing",
        summary="Researchers announce major advancement in NLP technology using new transformer architecture.",
        category=Category.TECHNOLOGY,
        state=TrendState.VIRAL,
        score=95.0,
        sources=[SourceType.REDDIT, SourceType.HACKERNEWS, SourceType.TWITTER],
        item_count=150,
        total_engagement=Metrics(
            upvotes=5000,
            comments=1200,
            shares=800,
            views=50000,
            score=10000.0,
        ),
        velocity=250.5,
        first_seen=datetime.utcnow() - timedelta(hours=12),
        last_updated=datetime.utcnow(),
        language="en",
        keywords=["AI", "NLP", "transformer", "machine learning"],
        metadata={},
    )


@pytest.fixture
def mock_topic():
    """Create a mock topic for testing."""
    return Topic(
        id=uuid4(),
        title="New Climate Report Released",
        summary="IPCC releases comprehensive climate assessment showing accelerating trends.",
        category=Category.SCIENCE,
        sources=[SourceType.BBC, SourceType.REUTERS],
        item_count=45,
        total_engagement=Metrics(upvotes=2000, comments=500),
        first_seen=datetime.utcnow() - timedelta(hours=6),
        last_updated=datetime.utcnow(),
        language="en",
        keywords=["climate", "IPCC", "environment"],
        metadata={},
    )


# ============================================================================
# Response Parsing Tests
# ============================================================================


class TestResponseParsing:
    """Tests for parsing LLM responses into key points."""

    @pytest.mark.asyncio
    async def test_parse_json_array_response(self, mock_llm_service):
        """Test parsing valid JSON array response."""
        extractor = KeyPointExtractor(mock_llm_service)

        response = '["First point", "Second point", "Third point"]'
        key_points = extractor._parse_response(response)

        assert len(key_points) == 3
        assert "First point" in key_points
        assert "Second point" in key_points
        assert "Third point" in key_points

    @pytest.mark.asyncio
    async def test_parse_json_with_extra_text(self, mock_llm_service):
        """Test parsing JSON array embedded in text."""
        extractor = KeyPointExtractor(mock_llm_service)

        response = '''Here are the key points:
        ["Point one", "Point two", "Point three"]
        These are the main findings.'''

        key_points = extractor._parse_response(response)

        assert len(key_points) == 3
        assert "Point one" in key_points

    @pytest.mark.asyncio
    async def test_parse_bullet_list_fallback(self, mock_llm_service):
        """Test fallback to bullet list parsing."""
        extractor = KeyPointExtractor(mock_llm_service)

        response = """
        - First important point about the trend
        - Second key finding from analysis
        - Third notable development
        """

        key_points = extractor._parse_response(response)

        assert len(key_points) >= 3
        assert any("First important point" in point for point in key_points)

    @pytest.mark.asyncio
    async def test_parse_numbered_list(self, mock_llm_service):
        """Test parsing numbered list."""
        extractor = KeyPointExtractor(mock_llm_service)

        response = """
        1. First key point here
        2. Second key point here
        3. Third key point here
        """

        key_points = extractor._parse_response(response)

        assert len(key_points) >= 3


# ============================================================================
# Validation Tests
# ============================================================================


class TestValidation:
    """Tests for key point validation."""

    @pytest.mark.asyncio
    async def test_validate_removes_short_points(self, mock_llm_service):
        """Test that very short points are removed."""
        extractor = KeyPointExtractor(mock_llm_service)

        key_points = [
            "This is a valid key point that is long enough.",
            "Short",
            "Another valid point that meets length requirements.",
        ]

        validated = extractor._validate_key_points(key_points)

        assert len(validated) == 2
        assert "Short" not in validated

    @pytest.mark.asyncio
    async def test_validate_adds_punctuation(self, mock_llm_service):
        """Test that missing punctuation is added."""
        extractor = KeyPointExtractor(mock_llm_service)

        key_points = [
            "This point has no punctuation",
            "This point has punctuation.",
        ]

        validated = extractor._validate_key_points(key_points)

        # Both should end with punctuation
        for point in validated:
            assert point[-1] in ".!?"

    @pytest.mark.asyncio
    async def test_validate_limits_to_max_points(self, mock_llm_service):
        """Test that points are limited to max_points."""
        extractor = KeyPointExtractor(mock_llm_service, max_points=3)

        key_points = [
            "First valid point here with sufficient length.",
            "Second valid point here with sufficient length.",
            "Third valid point here with sufficient length.",
            "Fourth valid point here with sufficient length.",
            "Fifth valid point here with sufficient length.",
        ]

        validated = extractor._validate_key_points(key_points)

        assert len(validated) <= 3

    @pytest.mark.asyncio
    async def test_validate_truncates_long_points(self, mock_llm_service):
        """Test that very long points are truncated."""
        extractor = KeyPointExtractor(mock_llm_service)

        long_point = "A" * 600  # Exceeds 500 char limit
        key_points = [long_point]

        validated = extractor._validate_key_points(key_points)

        assert len(validated) == 1
        assert len(validated[0]) <= 500
        assert validated[0].endswith("...")


# ============================================================================
# Extraction Tests
# ============================================================================


class TestExtraction:
    """Tests for key point extraction from trends."""

    @pytest.mark.asyncio
    async def test_extract_key_points_success(self, mock_llm_service, mock_trend):
        """Test successful key point extraction."""
        # Mock LLM response
        mock_llm_service.generate.return_value = (
            '["AI breakthrough uses novel transformer architecture", '
            '"Performance improvements of 40% over previous models", '
            '"Research team from MIT and Stanford collaboration"]'
        )

        extractor = KeyPointExtractor(mock_llm_service)
        key_points = await extractor.extract_key_points(mock_trend)

        assert len(key_points) >= 3
        assert mock_llm_service.generate.called
        assert any("transformer" in point.lower() for point in key_points)

    @pytest.mark.asyncio
    async def test_extract_key_points_with_items(
        self, mock_llm_service, mock_trend, mock_llm_service
    ):
        """Test extraction with related items."""
        mock_llm_service.generate.return_value = '["Point 1", "Point 2", "Point 3"]'

        items = [
            ProcessedItem(
                source=SourceType.REDDIT,
                source_id="abc123",
                url="https://example.com/1",
                title="Detailed article about the breakthrough",
                title_normalized="detailed article about the breakthrough",
                description="In-depth analysis of the new architecture",
                published_at=datetime.utcnow(),
                collected_at=datetime.utcnow(),
                metrics=Metrics(upvotes=100),
                metadata={},
            )
        ]

        extractor = KeyPointExtractor(mock_llm_service)
        key_points = await extractor.extract_key_points(mock_trend, items=items)

        assert len(key_points) >= 3
        # Verify items were included in context
        call_args = mock_llm_service.generate.call_args
        assert "Detailed article" in str(call_args)

    @pytest.mark.asyncio
    async def test_extract_key_points_llm_failure(self, mock_llm_service, mock_trend):
        """Test fallback when LLM fails."""
        # Mock LLM failure
        mock_llm_service.generate.side_effect = Exception("API error")

        extractor = KeyPointExtractor(mock_llm_service)
        key_points = await extractor.extract_key_points(mock_trend)

        # Should return fallback points
        assert len(key_points) >= 1
        # Fallback points should mention basic trend info
        assert any(
            "Technology" in point or "engagement" in point.lower()
            for point in key_points
        )

    @pytest.mark.asyncio
    async def test_extract_key_points_batch(self, mock_llm_service):
        """Test batch extraction for multiple trends."""
        mock_llm_service.generate.return_value = '["Point 1", "Point 2", "Point 3"]'

        trends = [
            Trend(
                id=uuid4(),
                topic_id=uuid4(),
                rank=i,
                title=f"Trend {i}",
                summary=f"Summary {i}",
                category=Category.TECHNOLOGY,
                state=TrendState.EMERGING,
                score=50.0,
                sources=[SourceType.REDDIT],
                item_count=10,
                total_engagement=Metrics(upvotes=100),
                velocity=10.0,
                first_seen=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                language="en",
                metadata={},
            )
            for i in range(3)
        ]

        extractor = KeyPointExtractor(mock_llm_service)
        results = await extractor.extract_key_points_batch(trends)

        assert len(results) == 3
        for trend_id, key_points in results.items():
            assert len(key_points) >= 1

    @pytest.mark.asyncio
    async def test_update_trend_key_points(self, mock_llm_service, mock_trend):
        """Test updating trend with key points in-place."""
        mock_llm_service.generate.return_value = '["Point 1", "Point 2"]'

        extractor = KeyPointExtractor(mock_llm_service)
        updated_trend = await extractor.update_trend_key_points(mock_trend)

        assert updated_trend.key_points == ["Point 1", "Point 2"]
        assert updated_trend.id == mock_trend.id


# ============================================================================
# Topic Extraction Tests
# ============================================================================


class TestTopicExtraction:
    """Tests for extracting key points from topics."""

    @pytest.mark.asyncio
    async def test_extract_from_topic(self, mock_llm_service, mock_topic):
        """Test extracting key points from a topic."""
        mock_llm_service.generate.return_value = (
            '["IPCC report shows accelerating warming", '
            '"Urgent action needed within next decade", '
            '"Report represents consensus of 200+ scientists"]'
        )

        extractor = TopicKeyPointExtractor(mock_llm_service, max_points=3)
        key_points = await extractor.extract_from_topic(mock_topic)

        assert len(key_points) <= 3
        assert any("IPCC" in point for point in key_points)

    @pytest.mark.asyncio
    async def test_extract_from_topic_failure(self, mock_llm_service, mock_topic):
        """Test fallback when extraction fails."""
        mock_llm_service.generate.side_effect = Exception("API error")

        extractor = TopicKeyPointExtractor(mock_llm_service)
        key_points = await extractor.extract_from_topic(mock_topic)

        # Should fall back to summary
        assert len(key_points) >= 1
        assert mock_topic.summary in key_points


# ============================================================================
# Context Building Tests
# ============================================================================


class TestContextBuilding:
    """Tests for building context from trends and items."""

    @pytest.mark.asyncio
    async def test_build_context_basic(self, mock_llm_service, mock_trend):
        """Test building basic context from trend."""
        extractor = KeyPointExtractor(mock_llm_service)
        context = await extractor._build_context(mock_trend)

        assert mock_trend.title in context
        assert mock_trend.summary in context
        assert mock_trend.category.value in context
        assert "AI" in context  # keyword

    @pytest.mark.asyncio
    async def test_build_context_with_items(self, mock_llm_service, mock_trend):
        """Test building context with related items."""
        items = [
            ProcessedItem(
                source=SourceType.REDDIT,
                source_id="123",
                url="https://example.com",
                title="Related article title",
                title_normalized="related article title",
                published_at=datetime.utcnow(),
                collected_at=datetime.utcnow(),
                metrics=Metrics(),
                metadata={},
            )
        ]

        extractor = KeyPointExtractor(mock_llm_service)
        context = await extractor._build_context(mock_trend, items=items)

        assert "Related Content:" in context
        assert "Related article title" in context
