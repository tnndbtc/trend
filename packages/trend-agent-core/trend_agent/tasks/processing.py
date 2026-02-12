"""
Celery tasks for processing collected data through the pipeline.

This module defines tasks for running the processing pipeline on raw items,
generating trends, and storing results in the database.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from celery import Task

from trend_agent.tasks import app
from trend_agent.schemas import ProcessedItem, Trend, Topic

logger = logging.getLogger(__name__)


class ProcessingTask(Task):
    """Base class for processing tasks with error handling."""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 2}
    retry_backoff = True
    retry_backoff_max = 900  # 15 minutes
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(
            f"Processing task {task_id} failed: {exc}\n"
            f"Args: {args}\n"
            f"Kwargs: {kwargs}\n"
            f"Info: {einfo}"
        )


@app.task(base=ProcessingTask, name="trend_agent.tasks.processing.process_pending_items_task")
def process_pending_items_task(limit: int = 1000) -> Dict[str, Any]:
    """
    Process pending items through the pipeline.

    Fetches unprocessed items from the database, runs them through
    the processing pipeline, and saves the resulting trends.

    Args:
        limit: Maximum number of items to process in one batch

    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting processing of up to {limit} pending items")

    try:
        result = asyncio.run(_process_pending_items_async(limit))
        logger.info(
            f"Processing complete: {result['trends_created']} trends created "
            f"from {result['items_processed']} items"
        )
        return result

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise


async def _process_pending_items_async(limit: int) -> Dict[str, Any]:
    """
    Async implementation of processing pending items.

    Args:
        limit: Maximum items to process

    Returns:
        Dictionary with results
    """
    from trend_agent.storage.postgres import (
        PostgreSQLConnectionPool,
        PostgreSQLItemRepository,
        PostgreSQLTrendRepository,
        PostgreSQLTopicRepository,
    )
    from trend_agent.storage.qdrant import QdrantVectorRepository
    from trend_agent.processing import create_standard_pipeline
    import os

    # Check if we should use real AI services
    use_real_services = os.getenv("USE_REAL_AI_SERVICES", "false").lower() in ("true", "1", "yes")
    llm_provider = os.getenv("LLM_PROVIDER", "openai")

    # Connect to database
    db_pool = PostgreSQLConnectionPool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "trends"),
        user=os.getenv("POSTGRES_USER", "trend_user"),
        password=os.getenv("POSTGRES_PASSWORD", "trend_password"),
    )
    await db_pool.connect()

    try:
        # Get pending items (items collected in last 24 hours that haven't been processed)
        item_repo = PostgreSQLItemRepository(db_pool.pool)

        # Fetch items that need full processing from the database
        pending_items = await item_repo.get_pending_items(limit=limit, hours_back=24)

        if not pending_items:
            logger.info("No pending items to process")
            return {
                "items_processed": 0,
                "trends_created": 0,
                "topics_created": 0,
                "duration_seconds": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Initialize AI services (real or mock based on configuration)
        if use_real_services:
            logger.info(f"Using real AI services (LLM provider: {llm_provider})")
            from trend_agent.services import ServiceFactory
            service_factory = ServiceFactory()
            embedding_service = service_factory.get_embedding_service()
            llm_service = service_factory.get_llm_service(provider=llm_provider)
        else:
            logger.info("Using mock AI services for testing")
            from tests.mocks.intelligence import MockEmbeddingService, MockLLMService
            embedding_service = MockEmbeddingService()
            llm_service = MockLLMService()
            service_factory = None

        # Initialize vector repository for storing embeddings
        vector_repo = QdrantVectorRepository(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            collection_name="trend_items"
        )

        # Create and run pipeline
        pipeline = create_standard_pipeline(embedding_service, llm_service)
        start_time = datetime.utcnow()

        # Convert ProcessedItems to RawItems for pipeline
        from trend_agent.schemas import RawItem, SourceType

        raw_items = [
            RawItem(
                source=item.source,
                source_id=item.source_id,
                url=item.url,
                title=item.title,
                description=item.description,
                content=item.content,
                author=item.author,
                published_at=item.published_at,
                collected_at=item.collected_at,
                metrics=item.metrics,
                metadata=item.metadata,
            )
            for item in pending_items[:limit]
        ]

        pipeline_result = await pipeline.run(raw_items)

        # Extract processed items with enrichments from pipeline
        # Pipeline stores processed items in metadata
        processed_with_enrichments = pipeline_result.metadata.get('processed_items', [])

        # Update items in database with enriched data (normalized text, language, category, etc.)
        items_updated = 0
        embeddings_saved = 0

        for enriched_item in processed_with_enrichments:
            # Update the item in the database with enriched data
            await item_repo.save(enriched_item)
            items_updated += 1

            # Save embeddings to Qdrant if available
            if enriched_item.embedding:
                try:
                    await vector_repo.upsert(
                        id=str(enriched_item.id),
                        vector=enriched_item.embedding,
                        payload={
                            "source": enriched_item.source.value,
                            "source_id": enriched_item.source_id,
                            "title": enriched_item.title,
                            "language": enriched_item.language,
                            "category": enriched_item.category.value if enriched_item.category else None,
                            "published_at": enriched_item.published_at.isoformat(),
                        }
                    )
                    embeddings_saved += 1
                except Exception as e:
                    logger.warning(f"Failed to save embedding for item {enriched_item.id}: {e}")

        # Extract trends from pipeline result
        trends: List[Trend] = pipeline_result.metadata.get("trends", [])
        topics: List[Topic] = pipeline_result.metadata.get("_clustered_topics", [])

        # Save trends to database
        trend_repo = PostgreSQLTrendRepository(db_pool.pool)
        topic_repo = PostgreSQLTopicRepository(db_pool.pool)

        trends_saved = 0
        topics_saved = 0

        # Save topics first
        for topic in topics:
            await topic_repo.save(topic)
            topics_saved += 1

        # Save trends
        for trend in trends:
            await trend_repo.save(trend)
            trends_saved += 1

        duration = (datetime.utcnow() - start_time).total_seconds()

        return {
            "items_processed": len(pending_items),
            "items_updated": items_updated,
            "embeddings_saved": embeddings_saved,
            "topics_created": topics_saved,
            "trends_created": trends_saved,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat(),
            "pipeline_status": pipeline_result.status.value,
        }

    finally:
        # Clean up resources
        if service_factory:
            await service_factory.close()
        await db_pool.close()


@app.task(base=ProcessingTask, name="trend_agent.tasks.processing.reprocess_trends_task")
def reprocess_trends_task(hours: int = 24) -> Dict[str, Any]:
    """
    Reprocess existing trends to update scores and rankings.

    Useful for updating trend states (emerging, viral, sustained, declining)
    and recalculating scores based on new engagement data.

    Args:
        hours: Reprocess trends from last N hours

    Returns:
        Dictionary with reprocessing results
    """
    logger.info(f"Reprocessing trends from last {hours} hours")

    try:
        result = asyncio.run(_reprocess_trends_async(hours))
        logger.info(f"Reprocessing complete: {result['trends_updated']} trends updated")
        return result

    except Exception as e:
        logger.error(f"Reprocessing failed: {e}")
        raise


async def _reprocess_trends_async(hours: int) -> Dict[str, Any]:
    """
    Async implementation of trend reprocessing.

    Args:
        hours: Hours to look back

    Returns:
        Dictionary with results
    """
    from trend_agent.storage.postgres import (
        PostgreSQLConnectionPool,
        PostgreSQLTrendRepository,
    )
    from trend_agent.schemas import TrendFilter
    import os

    db_pool = PostgreSQLConnectionPool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "trends"),
        user=os.getenv("POSTGRES_USER", "trend_user"),
        password=os.getenv("POSTGRES_PASSWORD", "trend_password"),
    )
    await db_pool.connect()

    try:
        trend_repo = PostgreSQLTrendRepository(db_pool.pool)

        # Get recent trends
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        filters = TrendFilter(
            date_from=cutoff,
            limit=1000,
        )

        trends = await trend_repo.search(filters)
        updated_count = 0

        # TODO: Implement trend state update logic
        # For now, just count
        for trend in trends:
            # Update trend state based on velocity, engagement, etc.
            # await trend_repo.update(trend)
            updated_count += 1

        return {
            "trends_updated": updated_count,
            "hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        await db_pool.close()


@app.task(base=ProcessingTask, name="trend_agent.tasks.processing.generate_embeddings_task")
def generate_embeddings_task(item_ids: Optional[List[str]] = None, limit: int = 100) -> Dict[str, Any]:
    """
    Generate embeddings for items that don't have them yet.

    Args:
        item_ids: Optional list of specific item IDs to process
        limit: Maximum number of items to process if item_ids not specified

    Returns:
        Dictionary with results
    """
    logger.info(f"Generating embeddings for {len(item_ids) if item_ids else limit} items")

    try:
        result = asyncio.run(_generate_embeddings_async(item_ids, limit))
        logger.info(f"Embedding generation complete: {result['embeddings_created']} embeddings")
        return result

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise


async def _generate_embeddings_async(item_ids: Optional[List[str]], limit: int) -> Dict[str, Any]:
    """
    Async implementation of embedding generation.

    Args:
        item_ids: Optional item IDs
        limit: Max items to process

    Returns:
        Dictionary with results
    """
    from trend_agent.storage.postgres import (
        PostgreSQLConnectionPool,
        PostgreSQLItemRepository,
    )
    from trend_agent.storage.qdrant import QdrantVectorRepository
    import os

    # Check if we should use real AI services
    use_real_services = os.getenv("USE_REAL_AI_SERVICES", "false").lower() in ("true", "1", "yes")

    # Connect to databases
    db_pool = PostgreSQLConnectionPool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "trends"),
        user=os.getenv("POSTGRES_USER", "trend_user"),
        password=os.getenv("POSTGRES_PASSWORD", "trend_password"),
    )
    await db_pool.connect()

    vector_repo = QdrantVectorRepository(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
        collection_name="trend_embeddings",
        vector_size=1536,
    )

    try:
        item_repo = PostgreSQLItemRepository(db_pool.pool)

        # Get items without embeddings
        # TODO: Add method to get items without embeddings
        items = []

        if not items:
            return {
                "embeddings_created": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Initialize embedding service (real or mock)
        if use_real_services:
            logger.info("Using real OpenAI embedding service")
            from trend_agent.services import ServiceFactory
            service_factory = ServiceFactory()
            embedding_service = service_factory.get_embedding_service()
        else:
            logger.info("Using mock embedding service for testing")
            from tests.mocks.intelligence import MockEmbeddingService
            embedding_service = MockEmbeddingService()
            service_factory = None

        embeddings_created = 0

        for item in items[:limit]:
            # Generate embedding
            text = f"{item.title} {item.description or ''}"
            embedding = await embedding_service.generate_embedding(text)

            # Store in vector database
            await vector_repo.upsert(
                id=str(item.id),
                vector=embedding,
                metadata={
                    "item_id": str(item.id),
                    "source": item.source.value,
                    "category": item.category.value if item.category else None,
                    "language": item.language,
                },
            )

            embeddings_created += 1

        return {
            "embeddings_created": embeddings_created,
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        # Clean up resources
        if service_factory:
            await service_factory.close()
        await db_pool.close()


@app.task(name="trend_agent.tasks.processing.test_pipeline_task")
def test_pipeline_task(sample_size: int = 10) -> Dict[str, Any]:
    """
    Test the processing pipeline with sample data.

    Useful for debugging and validating pipeline configuration.

    Args:
        sample_size: Number of sample items to process

    Returns:
        Dictionary with test results
    """
    logger.info(f"Testing pipeline with {sample_size} sample items")

    try:
        result = asyncio.run(_test_pipeline_async(sample_size))
        logger.info("Pipeline test complete")
        return result

    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def _test_pipeline_async(sample_size: int) -> Dict[str, Any]:
    """
    Async implementation of pipeline test.

    Args:
        sample_size: Number of sample items

    Returns:
        Dictionary with results
    """
    from trend_agent.processing import create_standard_pipeline
    from trend_agent.schemas import RawItem, SourceType, Metrics
    from pydantic import HttpUrl
    import os

    # Check if we should use real AI services
    use_real_services = os.getenv("USE_REAL_AI_SERVICES", "false").lower() in ("true", "1", "yes")
    llm_provider = os.getenv("LLM_PROVIDER", "openai")

    # Create sample items
    raw_items = []
    for i in range(sample_size):
        item = RawItem(
            source=SourceType.REDDIT,
            source_id=f"test_{i}",
            url=HttpUrl(f"https://example.com/test_{i}"),
            title=f"Test Item {i}",
            description=f"This is test item number {i}",
            published_at=datetime.utcnow(),
            metrics=Metrics(upvotes=100 * i, comments=10 * i, score=float(100 * i)),
        )
        raw_items.append(item)

    # Initialize AI services (real or mock)
    if use_real_services:
        logger.info(f"Testing pipeline with real AI services (LLM: {llm_provider})")
        from trend_agent.services import ServiceFactory
        service_factory = ServiceFactory()
        embedding_service = service_factory.get_embedding_service()
        llm_service = service_factory.get_llm_service(provider=llm_provider)
    else:
        logger.info("Testing pipeline with mock AI services")
        from tests.mocks.intelligence import MockEmbeddingService, MockLLMService
        embedding_service = MockEmbeddingService()
        llm_service = MockLLMService()
        service_factory = None

    try:
        # Run pipeline
        pipeline = create_standard_pipeline(embedding_service, llm_service)

        start_time = datetime.utcnow()
        result = await pipeline.run(raw_items)
        duration = (datetime.utcnow() - start_time).total_seconds()

        trends = result.metadata.get("trends", [])

        return {
            "success": True,
            "items_processed": result.items_collected,
            "trends_created": result.trends_created,
            "duration_seconds": duration,
            "status": result.status.value,
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        # Clean up resources
        if service_factory:
            await service_factory.close()


# Utility functions

def get_processing_status() -> Dict[str, Any]:
    """
    Get status of processing tasks.

    Returns:
        Dictionary with task status information
    """
    from trend_agent.tasks import get_active_tasks, get_scheduled_tasks

    active = get_active_tasks()
    scheduled = get_scheduled_tasks()

    # Filter for processing tasks only
    processing_active = {}
    for worker, tasks in (active or {}).items():
        processing_tasks = [
            t for t in tasks
            if "processing" in t.get("name", "")
        ]
        if processing_tasks:
            processing_active[worker] = processing_tasks

    return {
        "active_tasks": processing_active,
        "scheduled_tasks": scheduled,
        "timestamp": datetime.utcnow().isoformat(),
    }
