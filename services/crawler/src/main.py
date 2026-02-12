"""
Crawler Service - Data Collection from Multiple Sources

This service is responsible for:
- Collecting trends from multiple data sources (Reddit, HackerNews, News outlets)
- Running collectors on schedule via APScheduler
- Publishing collected data to the processing pipeline
- Managing collector plugins via the plugin system
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Dict, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CrawlerService:
    """Main crawler service that orchestrates data collection."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.plugin_manager = None
        self.running = False

    async def initialize(self):
        """Initialize the crawler service and load collector plugins."""
        logger.info("🚀 Initializing Crawler Service...")

        try:
            # Import here to avoid circular dependencies
            from trend_agent.ingestion.manager import DefaultPluginManager

            self.plugin_manager = DefaultPluginManager()
            await self.plugin_manager.load_plugins()

            plugins = self.plugin_manager.get_all_plugins()
            logger.info(f"✅ Loaded {len(plugins)} collector plugins: {list(plugins.keys())}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize plugin manager: {e}")
            raise

    async def run_collector(self, collector_name: str):
        """Run a specific collector and process results."""
        logger.info(f"▶️  Running collector: {collector_name}")

        try:
            collector = self.plugin_manager.get_plugin(collector_name)
            if not collector:
                logger.warning(f"⚠️  Collector not found: {collector_name}")
                return

            # Collect data
            results = await collector.collect_async()
            logger.info(f"✅ Collected {len(results)} items from {collector_name}")

            # Process and store results
            await self.process_results(collector_name, results)

        except Exception as e:
            logger.error(f"❌ Error running collector {collector_name}: {e}", exc_info=True)

    async def process_results(self, source: str, results: List[Dict]):
        """Process collected results and send to processing pipeline."""
        if not results:
            return

        logger.info(f"📊 Processing {len(results)} results from {source}")

        try:
            # Import storage repositories
            from trend_agent.storage.postgres import PostgreSQLTrendRepository
            from trend_agent.storage.redis import RedisCacheRepository

            # Initialize repositories
            trend_repo = PostgreSQLTrendRepository(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5433")),
                database=os.getenv("POSTGRES_DB", "trends"),
                user=os.getenv("POSTGRES_USER", "trend_user"),
                password=os.getenv("POSTGRES_PASSWORD", "trend_password"),
            )
            await trend_repo.connect()

            cache_repo = RedisCacheRepository(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6380")),
            )
            await cache_repo.connect()

            # Store each result
            for idx, item in enumerate(results):
                try:
                    # Create trend object
                    trend_data = {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "source": source,
                        "content": item.get("content", ""),
                        "metadata": item.get("metadata", {}),
                        "collected_at": datetime.utcnow(),
                    }

                    # Store in database
                    trend_id = await trend_repo.create(trend_data)

                    # Cache for quick access
                    await cache_repo.set(
                        f"trend:{source}:{idx}",
                        trend_data,
                        ttl=3600  # 1 hour
                    )

                    logger.debug(f"  ✓ Stored trend {trend_id}: {item.get('title', '')[:50]}...")

                except Exception as e:
                    logger.error(f"  ✗ Failed to store item {idx}: {e}")
                    continue

            await trend_repo.close()
            await cache_repo.close()

            logger.info(f"✅ Processed and stored {len(results)} trends from {source}")

        except Exception as e:
            logger.error(f"❌ Error processing results: {e}", exc_info=True)

    async def run_all_collectors(self):
        """Run all enabled collectors in parallel."""
        logger.info("🔄 Running all collectors...")

        collectors = self.plugin_manager.get_all_plugins()

        # Run collectors concurrently
        tasks = [self.run_collector(name) for name in collectors.keys()]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("✅ All collectors completed")

    def schedule_collectors(self):
        """Schedule collectors to run periodically."""
        logger.info("⏰ Scheduling collectors...")

        # Schedule collectors based on configuration
        schedules = {
            "reddit": "*/30 * * * *",      # Every 30 minutes
            "hackernews": "*/20 * * * *",  # Every 20 minutes
            "google_news": "0 * * * *",    # Every hour
            "guardian": "0 */2 * * *",     # Every 2 hours
            "bbc": "0 */2 * * *",          # Every 2 hours
            "reuters": "0 */2 * * *",      # Every 2 hours
            "ap_news": "0 */3 * * *",      # Every 3 hours
            "al_jazeera": "0 */3 * * *",   # Every 3 hours
        }

        for collector_name, cron_expr in schedules.items():
            self.scheduler.add_job(
                self.run_collector,
                trigger=CronTrigger.from_crontab(cron_expr),
                args=[collector_name],
                id=f"collector_{collector_name}",
                name=f"Collector: {collector_name}",
                replace_existing=True,
            )
            logger.info(f"  ✓ Scheduled {collector_name}: {cron_expr}")

        # Also schedule a full run every 6 hours
        self.scheduler.add_job(
            self.run_all_collectors,
            trigger=CronTrigger.from_crontab("0 */6 * * *"),
            id="all_collectors",
            name="All Collectors",
            replace_existing=True,
        )
        logger.info("  ✓ Scheduled full collector run: 0 */6 * * *")

        logger.info("✅ All collectors scheduled")

    async def start(self):
        """Start the crawler service."""
        logger.info("🚀 Starting Crawler Service...")

        # Initialize
        await self.initialize()

        # Schedule collectors
        self.schedule_collectors()

        # Start scheduler
        self.scheduler.start()
        logger.info("✅ Scheduler started")

        # Run an initial collection
        if os.getenv("RUN_ON_STARTUP", "true").lower() == "true":
            logger.info("🔄 Running initial collection...")
            await self.run_all_collectors()

        self.running = True
        logger.info("✅ Crawler Service is running")

        # Keep service running
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("🛑 Crawler Service cancelled")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the crawler service gracefully."""
        logger.info("🛑 Shutting down Crawler Service...")

        self.running = False

        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("✅ Scheduler stopped")

        logger.info("✅ Crawler Service shutdown complete")


async def main():
    """Main entry point for the crawler service."""
    crawler = CrawlerService()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        loop.create_task(crawler.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the crawler service
    try:
        await crawler.start()
    except Exception as e:
        logger.error(f"❌ Crawler service failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
