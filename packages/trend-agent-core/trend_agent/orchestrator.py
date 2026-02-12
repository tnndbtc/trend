"""
Integration orchestrator for the complete pipeline flow.

This module provides high-level functions to orchestrate the complete
data flow: collection → processing → storage → API availability.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from trend_agent.services import ServiceFactory
from trend_agent.storage.postgres import (
    PostgreSQLConnectionPool,
    PostgreSQLItemRepository,
    PostgreSQLTrendRepository,
    PostgreSQLTopicRepository,
)
from trend_agent.storage.qdrant import QdrantVectorRepository
from trend_agent.storage.redis import RedisCacheRepository
from trend_agent.ingestion.manager import DefaultPluginManager
from trend_agent.ingestion.converters import batch_raw_to_processed
from trend_agent.processing import create_standard_pipeline
from trend_agent.schemas import ProcessedItem, Trend, Topic

logger = logging.getLogger(__name__)


class TrendIntelligenceOrchestrator:
    """
    Main orchestrator for the trend intelligence platform.

    This class coordinates all components of the system:
    - Data collection from various sources
    - Processing through the pipeline
    - Storage in PostgreSQL, Qdrant, and Redis
    - Making data available via API
    """

    def __init__(
        self,
        postgres_config: Optional[Dict[str, Any]] = None,
        qdrant_config: Optional[Dict[str, Any]] = None,
        redis_config: Optional[Dict[str, Any]] = None,
        use_real_ai_services: bool = True,
        llm_provider: str = "openai",
    ):
        """
        Initialize the orchestrator with storage configurations.

        Args:
            postgres_config: PostgreSQL connection config
            qdrant_config: Qdrant connection config
            redis_config: Redis connection config
            use_real_ai_services: Use real AI services (True) or mocks (False)
            llm_provider: LLM provider to use ("openai" or "anthropic")
        """
        # Use environment variables as defaults
        self.postgres_config = postgres_config or {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5433")),
            "database": os.getenv("POSTGRES_DB", "trends"),
            "user": os.getenv("POSTGRES_USER", "trend_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "trend_password"),
        }

        self.qdrant_config = qdrant_config or {
            "host": os.getenv("QDRANT_HOST", "localhost"),
            "port": int(os.getenv("QDRANT_PORT", "6333")),
        }

        self.redis_config = redis_config or {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6380")),
            "password": os.getenv("REDIS_PASSWORD", None),
        }

        # Storage components (initialized on connect)
        self.db_pool: Optional[PostgreSQLConnectionPool] = None
        self.item_repo: Optional[PostgreSQLItemRepository] = None
        self.trend_repo: Optional[PostgreSQLTrendRepository] = None
        self.topic_repo: Optional[PostgreSQLTopicRepository] = None
        self.vector_repo: Optional[QdrantVectorRepository] = None
        self.cache_repo: Optional[RedisCacheRepository] = None

        # Processing components
        self.plugin_manager: Optional[DefaultPluginManager] = None

        # AI Services
        self.use_real_ai_services = use_real_ai_services
        self.llm_provider = llm_provider
        self.service_factory: Optional[ServiceFactory] = None

        logger.info(
            f"TrendIntelligenceOrchestrator initialized "
            f"(real_services={use_real_ai_services}, llm_provider={llm_provider})"
        )

    async def connect(self):
        """Connect to all storage backends and initialize AI services."""
        logger.info("Connecting to storage backends...")

        # PostgreSQL
        self.db_pool = PostgreSQLConnectionPool(**self.postgres_config)
        await self.db_pool.connect()
        self.item_repo = PostgreSQLItemRepository(self.db_pool.pool)
        self.trend_repo = PostgreSQLTrendRepository(self.db_pool.pool)
        self.topic_repo = PostgreSQLTopicRepository(self.db_pool.pool)
        logger.info("✅ PostgreSQL connected")

        # Qdrant
        self.vector_repo = QdrantVectorRepository(
            host=self.qdrant_config["host"],
            port=self.qdrant_config["port"],
            collection_name="trend_items",
        )
        logger.info("✅ Qdrant connected")

        # Redis
        self.cache_repo = RedisCacheRepository(
            host=self.redis_config["host"],
            port=self.redis_config["port"],
            password=self.redis_config["password"],
        )
        await self.cache_repo.connect()
        logger.info("✅ Redis connected")

        # Plugin Manager
        self.plugin_manager = DefaultPluginManager()
        await self.plugin_manager.load_plugins()
        logger.info("✅ Plugin manager initialized")

        # AI Services
        if self.use_real_ai_services:
            self.service_factory = ServiceFactory()
            logger.info(f"✅ AI service factory initialized (LLM provider: {self.llm_provider})")
        else:
            logger.info("✅ Using mock AI services for testing")

        logger.info("All storage backends and services connected successfully")

    async def disconnect(self):
        """Disconnect from all storage backends and clean up services."""
        logger.info("Disconnecting from storage backends...")

        if self.db_pool:
            await self.db_pool.close()
        if self.cache_repo:
            await self.cache_repo.close()
        if self.vector_repo:
            self.vector_repo.client.close()
        if self.service_factory:
            await self.service_factory.close()

        logger.info("Disconnected from all storage backends and services")

    async def collect_from_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """
        Collect data from a specific plugin and save to database.

        Args:
            plugin_name: Name of the plugin to collect from

        Returns:
            Dictionary with collection results
        """
        if not self.plugin_manager or not self.item_repo:
            raise RuntimeError("Orchestrator not connected. Call connect() first.")

        logger.info(f"Collecting from plugin: {plugin_name}")
        start_time = datetime.utcnow()

        # Get the plugin
        plugin = self.plugin_manager.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin '{plugin_name}' not found")

        # Collect raw items
        raw_items = await plugin.collect()
        logger.info(f"Collected {len(raw_items)} items from {plugin_name}")

        # Convert to processed items with minimal processing
        processed_items = batch_raw_to_processed(raw_items)

        # Save to database
        saved_count = 0
        for item in processed_items:
            await self.item_repo.save(item)
            saved_count += 1

        duration = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "plugin_name": plugin_name,
            "items_collected": len(raw_items),
            "items_saved": saved_count,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"Collection complete: {result}")
        return result

    async def collect_from_all_plugins(self) -> Dict[str, Any]:
        """
        Collect data from all enabled plugins.

        Returns:
            Dictionary with aggregated results
        """
        if not self.plugin_manager:
            raise RuntimeError("Orchestrator not connected. Call connect() first.")

        logger.info("Collecting from all enabled plugins...")
        start_time = datetime.utcnow()

        all_plugins = self.plugin_manager.get_all_plugins()
        results = []

        for plugin in all_plugins:
            try:
                status = await self.plugin_manager.get_plugin_status(plugin.metadata.name)
                if status.get("enabled", True):
                    result = await self.collect_from_plugin(plugin.metadata.name)
                    results.append(result)
            except Exception as e:
                logger.error(f"Failed to collect from {plugin.metadata.name}: {e}")
                results.append({
                    "plugin_name": plugin.metadata.name,
                    "error": str(e),
                    "items_collected": 0,
                    "items_saved": 0,
                })

        total_items = sum(r.get("items_collected", 0) for r in results)
        total_saved = sum(r.get("items_saved", 0) for r in results)
        duration = (datetime.utcnow() - start_time).total_seconds()

        summary = {
            "plugins_run": len(results),
            "total_items_collected": total_items,
            "total_items_saved": total_saved,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat(),
            "plugin_results": results,
        }

        logger.info(f"Collection complete from all plugins: {summary}")
        return summary

    async def process_pending_items(self, limit: int = 1000) -> Dict[str, Any]:
        """
        Process pending items through the pipeline.

        Args:
            limit: Maximum number of items to process

        Returns:
            Dictionary with processing results
        """
        if not self.item_repo:
            raise RuntimeError("Orchestrator not connected. Call connect() first.")

        logger.info(f"Processing up to {limit} pending items...")
        start_time = datetime.utcnow()

        # Get pending items
        pending_items = await self.item_repo.get_pending_items(limit=limit, hours_back=24)

        if not pending_items:
            logger.info("No pending items to process")
            return {
                "items_processed": 0,
                "items_updated": 0,
                "embeddings_saved": 0,
                "topics_created": 0,
                "trends_created": 0,
                "duration_seconds": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        logger.info(f"Found {len(pending_items)} pending items")

        # Get AI services (real or mock)
        if self.use_real_ai_services and self.service_factory:
            logger.info(f"Using real AI services (LLM provider: {self.llm_provider})")
            embedding_service = self.service_factory.get_embedding_service()
            llm_service = self.service_factory.get_llm_service(provider=self.llm_provider)
        else:
            logger.info("Using mock AI services for testing")
            from tests.mocks.intelligence import MockEmbeddingService, MockLLMService
            embedding_service = MockEmbeddingService()
            llm_service = MockLLMService()

        # Create pipeline
        pipeline = create_standard_pipeline(embedding_service, llm_service)

        # Convert to RawItems for pipeline
        from trend_agent.schemas import RawItem
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
            for item in pending_items
        ]

        # Run pipeline
        pipeline_result = await pipeline.run(raw_items)

        # Extract processed items from metadata (pipeline stores them there)
        processed_with_enrichments = pipeline_result.metadata.get('processed_items', [])

        # Update items and save embeddings
        items_updated = 0
        embeddings_saved = 0

        for enriched_item in processed_with_enrichments:
            await self.item_repo.save(enriched_item)
            items_updated += 1

            if enriched_item.embedding and self.vector_repo:
                try:
                    await self.vector_repo.upsert(
                        id=str(enriched_item.id),
                        vector=enriched_item.embedding,
                        payload={
                            "source": enriched_item.source.value,
                            "title": enriched_item.title,
                            "language": enriched_item.language,
                        }
                    )
                    embeddings_saved += 1
                except Exception as e:
                    logger.warning(f"Failed to save embedding: {e}")

        # Save topics and trends
        topics = pipeline_result.metadata.get("_clustered_topics", [])
        trends = pipeline_result.metadata.get("trends", [])

        topics_saved = 0
        for topic in topics:
            await self.topic_repo.save(topic)
            topics_saved += 1

        trends_saved = 0
        for trend in trends:
            await self.trend_repo.save(trend)
            trends_saved += 1

        duration = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "items_processed": len(pending_items),
            "items_updated": items_updated,
            "embeddings_saved": embeddings_saved,
            "topics_created": topics_saved,
            "trends_created": trends_saved,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat(),
            "pipeline_status": pipeline_result.status.value,
        }

        logger.info(f"Processing complete: {result}")
        return result

    async def run_full_pipeline(self, plugin_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the complete pipeline: collect → process → store.

        Args:
            plugin_name: Optional specific plugin, or None for all plugins

        Returns:
            Dictionary with complete pipeline results
        """
        logger.info("=" * 80)
        logger.info("RUNNING FULL PIPELINE")
        logger.info("=" * 80)
        start_time = datetime.utcnow()

        # Step 1: Collection
        if plugin_name:
            collection_result = await self.collect_from_plugin(plugin_name)
        else:
            collection_result = await self.collect_from_all_plugins()

        logger.info(f"✅ Collection complete: {collection_result.get('total_items_saved', collection_result.get('items_saved'))} items saved")

        # Step 2: Processing
        processing_result = await self.process_pending_items(limit=1000)

        logger.info(f"✅ Processing complete: {processing_result['trends_created']} trends created")

        duration = (datetime.utcnow() - start_time).total_seconds()

        result = {
            "status": "completed",
            "collection": collection_result,
            "processing": processing_result,
            "total_duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info("=" * 80)
        logger.info(f"FULL PIPELINE COMPLETE in {duration:.2f}s")
        logger.info("=" * 80)

        return result


# Convenience functions for quick usage

async def run_collection(plugin_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick helper to run collection.

    Args:
        plugin_name: Optional plugin name, or None for all

    Returns:
        Collection results
    """
    orchestrator = TrendIntelligenceOrchestrator()
    await orchestrator.connect()
    try:
        if plugin_name:
            return await orchestrator.collect_from_plugin(plugin_name)
        else:
            return await orchestrator.collect_from_all_plugins()
    finally:
        await orchestrator.disconnect()


async def run_processing(limit: int = 1000) -> Dict[str, Any]:
    """
    Quick helper to run processing.

    Args:
        limit: Max items to process

    Returns:
        Processing results
    """
    orchestrator = TrendIntelligenceOrchestrator()
    await orchestrator.connect()
    try:
        return await orchestrator.process_pending_items(limit=limit)
    finally:
        await orchestrator.disconnect()


async def run_full_pipeline(plugin_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick helper to run the full pipeline.

    Args:
        plugin_name: Optional plugin name

    Returns:
        Complete pipeline results
    """
    orchestrator = TrendIntelligenceOrchestrator()
    await orchestrator.connect()
    try:
        return await orchestrator.run_full_pipeline(plugin_name=plugin_name)
    finally:
        await orchestrator.disconnect()
