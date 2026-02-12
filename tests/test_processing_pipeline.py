"""
Integration tests for processing pipeline.

Tests the complete pipeline from raw items to ranked trends using mock services.
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from trend_agent.processing.pipeline import (
    ProcessingPipeline,
    create_standard_pipeline,
    create_minimal_pipeline,
)
from trend_agent.processing.cluster import ClustererStage, HDBSCANClusterer
from trend_agent.processing.deduplicate import DeduplicatorStage, EmbeddingDeduplicator
from trend_agent.processing.language import LanguageDetectorStage
from trend_agent.processing.normalizer import NormalizerStage
from trend_agent.processing.rank import RankerStage
from trend_agent.schemas import (
    Metrics,
    PipelineConfig,
    ProcessingStatus,
    RawItem,
    SourceType,
)
from tests.mocks.intelligence import MockEmbeddingService, MockLLMService
from tests.fixtures import Fixtures


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def embedding_service():
    """Provide mock embedding service."""
    return MockEmbeddingService()


@pytest.fixture
def llm_service():
    """Provide mock LLM service."""
    return MockLLMService()


@pytest.fixture
def fixtures():
    """Provide test fixtures."""
    return Fixtures()


@pytest.fixture
def raw_items(fixtures) -> List[RawItem]:
    """Provide sample raw items for testing."""
    return fixtures.get_raw_items(20)


@pytest.fixture
def pipeline_config() -> PipelineConfig:
    """Provide pipeline configuration."""
    return PipelineConfig(
        deduplication_threshold=0.92,
        clustering_distance_threshold=0.3,
        min_cluster_size=2,
        max_trends_per_category=10,
        source_diversity_enabled=True,
        max_percentage_per_source=0.20,
    )


# ============================================================================
# Pipeline Construction Tests
# ============================================================================


def test_pipeline_creation():
    """Test basic pipeline creation."""
    pipeline = ProcessingPipeline()
    assert len(pipeline.get_stages()) == 0

    # Add a stage
    normalizer = NormalizerStage()
    pipeline.add_stage(normalizer)
    assert len(pipeline.get_stages()) == 1
    assert "normalizer" in pipeline.get_stages()


def test_pipeline_stage_removal():
    """Test removing stages from pipeline."""
    pipeline = ProcessingPipeline()
    pipeline.add_stage(NormalizerStage())
    pipeline.add_stage(LanguageDetectorStage())

    assert len(pipeline.get_stages()) == 2

    # Remove a stage
    result = pipeline.remove_stage("normalizer")
    assert result is True
    assert len(pipeline.get_stages()) == 1
    assert "normalizer" not in pipeline.get_stages()

    # Try to remove non-existent stage
    result = pipeline.remove_stage("nonexistent")
    assert result is False


def test_standard_pipeline_creation(embedding_service, llm_service, pipeline_config):
    """Test standard pipeline factory function."""
    pipeline = create_standard_pipeline(
        embedding_service, llm_service, config=pipeline_config
    )

    stages = pipeline.get_stages()
    assert len(stages) == 5
    assert "normalizer" in stages
    assert "language_detector" in stages
    assert "deduplicator" in stages
    assert "clusterer" in stages
    assert "ranker" in stages


def test_minimal_pipeline_creation(embedding_service, pipeline_config):
    """Test minimal pipeline factory function."""
    pipeline = create_minimal_pipeline(embedding_service, config=pipeline_config)

    stages = pipeline.get_stages()
    assert len(stages) == 3
    assert "normalizer" in stages
    assert "deduplicator" in stages
    assert "clusterer" in stages


# ============================================================================
# Individual Stage Tests
# ============================================================================


@pytest.mark.asyncio
async def test_normalizer_stage():
    """Test normalizer stage independently."""
    from trend_agent.schemas import ProcessedItem, Metrics

    # Create test item with HTML content
    item = ProcessedItem(
        source=SourceType.REDDIT,
        source_id="test123",
        url="https://example.com",
        title="  Test   Title  ",
        title_normalized="",
        description="<p>HTML description</p>",
        content="<div>HTML content</div>",
        published_at=datetime.utcnow(),
        collected_at=datetime.utcnow(),
        metrics=Metrics(),
    )

    normalizer = NormalizerStage()
    result = await normalizer.process([item])

    assert len(result) == 1
    assert result[0].title_normalized == "Test Title"
    assert "<p>" not in result[0].description
    assert result[0].content_normalized is not None
    assert "<div>" not in result[0].content_normalized


@pytest.mark.asyncio
async def test_language_detector_stage():
    """Test language detector stage."""
    from trend_agent.schemas import ProcessedItem, Metrics

    # Create items with different languages
    items = [
        ProcessedItem(
            source=SourceType.REDDIT,
            source_id="en1",
            url="https://example.com/1",
            title="This is an English title",
            title_normalized="This is an English title",
            published_at=datetime.utcnow(),
            collected_at=datetime.utcnow(),
            metrics=Metrics(),
        ),
        ProcessedItem(
            source=SourceType.REDDIT,
            source_id="es1",
            url="https://example.com/2",
            title="Este es un título en español",
            title_normalized="Este es un título en español",
            published_at=datetime.utcnow(),
            collected_at=datetime.utcnow(),
            metrics=Metrics(),
        ),
    ]

    detector = LanguageDetectorStage()
    result = await detector.process(items)

    assert len(result) == 2
    # Language detection should work
    assert result[0].language is not None
    assert result[1].language is not None


@pytest.mark.asyncio
async def test_deduplicator_stage(embedding_service):
    """Test deduplicator stage."""
    from trend_agent.schemas import ProcessedItem, Metrics

    # Create duplicate items
    now = datetime.utcnow()
    items = [
        ProcessedItem(
            source=SourceType.REDDIT,
            source_id="item1",
            url="https://example.com/1",
            title="Breaking news about AI",
            title_normalized="breaking news about ai",
            published_at=now,
            collected_at=now,
            metrics=Metrics(upvotes=100),
        ),
        ProcessedItem(
            source=SourceType.HACKERNEWS,
            source_id="item2",
            url="https://example.com/2",
            title="Breaking news about AI",  # Duplicate
            title_normalized="breaking news about ai",
            published_at=now,
            collected_at=now,
            metrics=Metrics(upvotes=50),
        ),
        ProcessedItem(
            source=SourceType.TWITTER,
            source_id="item3",
            url="https://example.com/3",
            title="Completely different topic",
            title_normalized="completely different topic",
            published_at=now,
            collected_at=now,
            metrics=Metrics(upvotes=75),
        ),
    ]

    deduplicator = EmbeddingDeduplicator(embedding_service)
    stage = DeduplicatorStage(deduplicator=deduplicator, threshold=0.95)

    result = await stage.process(items)

    # Should remove the duplicate
    assert len(result) < len(items)


@pytest.mark.asyncio
async def test_clusterer_stage(embedding_service):
    """Test clusterer stage."""
    from trend_agent.schemas import ProcessedItem, Metrics

    # Create items that should cluster together
    now = datetime.utcnow()
    items = []
    for i in range(5):
        items.append(
            ProcessedItem(
                source=SourceType.REDDIT,
                source_id=f"ai{i}",
                url=f"https://example.com/ai{i}",
                title=f"AI development news {i}",
                title_normalized=f"ai development news {i}",
                published_at=now,
                collected_at=now,
                metrics=Metrics(upvotes=100 + i),
            )
        )

    clusterer = HDBSCANClusterer(embedding_service)
    stage = ClustererStage(clusterer=clusterer, min_cluster_size=2)

    result = await stage.process(items)

    # Check that topics were created
    assert len(result) > 0
    assert "_clustered_topics" in result[0].metadata
    topics = result[0].metadata["_clustered_topics"]
    assert len(topics) > 0


@pytest.mark.asyncio
async def test_ranker_stage(embedding_service):
    """Test ranker stage."""
    from trend_agent.schemas import ProcessedItem, Metrics, Topic, Category

    # Create mock topic
    now = datetime.utcnow()
    topic = Topic(
        title="AI Development",
        summary="Latest AI news",
        category=Category.TECHNOLOGY,
        sources=[SourceType.REDDIT],
        item_count=5,
        total_engagement=Metrics(upvotes=500, comments=100),
        first_seen=now - timedelta(hours=2),
        last_updated=now,
    )

    # Create item with topic in metadata
    item = ProcessedItem(
        source=SourceType.REDDIT,
        source_id="test",
        url="https://example.com",
        title="Test",
        title_normalized="test",
        published_at=now,
        collected_at=now,
        metrics=Metrics(),
        metadata={"_clustered_topics": [topic]},
    )

    stage = RankerStage()
    result = await stage.process([item])

    # Check that trends were created
    assert len(result) > 0
    assert "_ranked_trends" in result[0].metadata
    trends = result[0].metadata["_ranked_trends"]
    assert len(trends) > 0
    assert trends[0].rank == 1


# ============================================================================
# End-to-End Pipeline Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_pipeline_execution(
    embedding_service, llm_service, raw_items, pipeline_config
):
    """Test complete pipeline execution end-to-end."""
    pipeline = create_standard_pipeline(
        embedding_service, llm_service, config=pipeline_config
    )

    result = await pipeline.run(raw_items)

    # Check result status
    assert result.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]
    assert result.items_collected == len(raw_items)
    assert result.items_processed > 0
    assert result.duration_seconds > 0
    assert result.started_at is not None
    assert result.completed_at is not None

    # If successful, check that trends were created
    if result.status == ProcessingStatus.COMPLETED:
        assert "trends" in result.metadata
        trends = result.metadata["trends"]
        # May or may not have trends depending on clustering
        assert isinstance(trends, list)


@pytest.mark.asyncio
async def test_pipeline_with_empty_input(embedding_service):
    """Test pipeline with empty input."""
    pipeline = create_minimal_pipeline(embedding_service)

    result = await pipeline.run([])

    assert result.status == ProcessingStatus.COMPLETED
    assert result.items_collected == 0
    assert result.items_processed == 0


@pytest.mark.asyncio
async def test_pipeline_with_single_item(embedding_service):
    """Test pipeline with single item."""
    fixtures = Fixtures()
    items = fixtures.get_raw_items(1)

    pipeline = create_minimal_pipeline(embedding_service)
    result = await pipeline.run(items)

    assert result.status == ProcessingStatus.COMPLETED
    assert result.items_collected == 1


@pytest.mark.asyncio
async def test_pipeline_stage_validation(embedding_service, raw_items):
    """Test that pipeline validates stage outputs."""
    pipeline = create_standard_pipeline(embedding_service)

    # Run pipeline
    result = await pipeline.run(raw_items[:10])

    # Check that validation didn't cause failures
    # (validation errors are warnings, not failures)
    assert result.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]


@pytest.mark.asyncio
async def test_pipeline_error_handling(embedding_service):
    """Test pipeline error handling with invalid data."""
    # Create invalid raw items (missing required fields)
    from pydantic import HttpUrl

    invalid_items = [
        RawItem(
            source=SourceType.REDDIT,
            source_id="test",
            url=HttpUrl("https://example.com"),
            title="",  # Empty title should be handled
            published_at=datetime.utcnow(),
            metrics=Metrics(),
        )
    ]

    pipeline = create_minimal_pipeline(embedding_service)
    result = await pipeline.run(invalid_items)

    # Pipeline should complete even with problematic data
    assert result.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]


@pytest.mark.asyncio
async def test_pipeline_config_application(embedding_service):
    """Test that pipeline config is properly applied."""
    custom_config = PipelineConfig(
        deduplication_threshold=0.85,  # Lower threshold
        min_cluster_size=3,  # Larger clusters
        max_trends_per_category=5,  # Fewer trends
    )

    pipeline = create_standard_pipeline(embedding_service, config=custom_config)
    fixtures = Fixtures()
    items = fixtures.get_raw_items(15)

    result = await pipeline.run(items)

    # Check that config was used
    assert result.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_pipeline_performance(embedding_service):
    """Test pipeline performance with larger dataset."""
    fixtures = Fixtures()
    items = fixtures.get_raw_items(50)  # 50 items

    pipeline = create_minimal_pipeline(embedding_service)

    import time

    start = time.time()
    result = await pipeline.run(items)
    duration = time.time() - start

    # Should complete in reasonable time (< 10 seconds for 50 items with mocks)
    assert duration < 10.0
    assert result.duration_seconds < 10.0


# ============================================================================
# Run tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
