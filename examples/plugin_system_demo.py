"""
Plugin System Demo

This script demonstrates how to use the ingestion plugin system:
- Plugin discovery and loading
- Health monitoring
- Rate limiting
- Scheduled execution
- Manual triggering
"""

import asyncio
import logging
from datetime import datetime

from trend_agent.ingestion import (
    DefaultPluginManager,
    DefaultHealthChecker,
    InMemoryRateLimiter,
    DefaultScheduler,
    PluginRegistry,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def demo_plugin_discovery():
    """Demonstrate plugin discovery and loading."""
    logger.info("=" * 60)
    logger.info("PLUGIN DISCOVERY DEMO")
    logger.info("=" * 60)

    manager = DefaultPluginManager()

    # Load all plugins
    plugins = await manager.load_plugins()
    logger.info(f"Loaded {len(plugins)} plugins")

    # Get all plugin status
    all_status = await manager.get_all_plugin_status()

    for name, status in all_status.items():
        logger.info(f"\nPlugin: {name}")
        logger.info(f"  Version: {status['version']}")
        logger.info(f"  Description: {status['description']}")
        logger.info(f"  Source: {status['source_type']}")
        logger.info(f"  Schedule: {status['schedule']}")
        logger.info(f"  Rate Limit: {status['rate_limit']}/hour")
        logger.info(f"  Enabled: {status['enabled']}")


async def demo_manual_collection():
    """Demonstrate manual plugin execution."""
    logger.info("\n" + "=" * 60)
    logger.info("MANUAL COLLECTION DEMO")
    logger.info("=" * 60)

    # Get a plugin
    plugin = PluginRegistry.get_plugin("reddit")
    if not plugin:
        logger.warning("Reddit plugin not found")
        return

    logger.info(f"Collecting from {plugin.metadata.name}...")

    try:
        # Execute collection
        items = await plugin.collect()
        logger.info(f"Collected {len(items)} items")

        # Show first few items
        for i, item in enumerate(items[:3]):
            logger.info(f"\nItem {i+1}:")
            logger.info(f"  Title: {item.title}")
            logger.info(f"  URL: {item.url}")
            logger.info(f"  Published: {item.published_at}")
            logger.info(f"  Score: {item.metrics.score}")

    except Exception as e:
        logger.error(f"Collection failed: {e}")


async def demo_health_monitoring():
    """Demonstrate health monitoring."""
    logger.info("\n" + "=" * 60)
    logger.info("HEALTH MONITORING DEMO")
    logger.info("=" * 60)

    checker = DefaultHealthChecker(failure_threshold=3)

    # Simulate some plugin activity
    logger.info("Simulating plugin activity...")

    # Record some successes
    await checker.record_success("reddit")
    await checker.record_success("hackernews")

    # Record some failures
    await checker.record_failure("bbc", "Connection timeout")
    await checker.record_failure("bbc", "HTTP 500 error")

    # Check health of all plugins
    all_health = await checker.check_all_health()

    for name, health in all_health.items():
        logger.info(f"\nPlugin: {name}")
        logger.info(f"  Healthy: {health.is_healthy}")
        logger.info(f"  Total Runs: {health.total_runs}")
        logger.info(f"  Consecutive Failures: {health.consecutive_failures}")
        logger.info(f"  Success Rate: {health.success_rate:.1%}")
        if health.last_error:
            logger.info(f"  Last Error: {health.last_error}")


async def demo_rate_limiting():
    """Demonstrate rate limiting."""
    logger.info("\n" + "=" * 60)
    logger.info("RATE LIMITING DEMO")
    logger.info("=" * 60)

    limiter = InMemoryRateLimiter(default_limit=10, window_seconds=3600)

    plugin_name = "reddit"

    # Check initial quota
    remaining = await limiter.get_remaining_quota(plugin_name)
    logger.info(f"{plugin_name} quota: {remaining}/10 requests remaining")

    # Simulate some requests
    logger.info("\nSimulating 5 requests...")
    for i in range(5):
        can_run = await limiter.check_rate_limit(plugin_name)
        if can_run:
            await limiter.record_request(plugin_name)
            logger.info(f"  Request {i+1}: Allowed")
        else:
            logger.warning(f"  Request {i+1}: Rate limited!")

    # Check remaining quota
    remaining = await limiter.get_remaining_quota(plugin_name)
    logger.info(f"\nAfter 5 requests: {remaining}/10 remaining")


async def demo_scheduler():
    """Demonstrate scheduled plugin execution."""
    logger.info("\n" + "=" * 60)
    logger.info("SCHEDULER DEMO")
    logger.info("=" * 60)

    # Initialize components
    checker = DefaultHealthChecker()
    limiter = InMemoryRateLimiter()
    scheduler = DefaultScheduler(
        health_checker=checker,
        rate_limiter=limiter
    )

    await scheduler.start()

    try:
        # Schedule a plugin
        plugin = PluginRegistry.get_plugin("reddit")
        if plugin:
            logger.info(f"Scheduling {plugin.metadata.name}...")
            job_id = await scheduler.schedule_plugin(plugin, "*/30 * * * *")
            logger.info(f"  Job ID: {job_id}")

            # Get next run time
            next_run = await scheduler.get_next_run("reddit")
            logger.info(f"  Next run: {next_run}")

        # Trigger immediate execution
        logger.info("\nTriggering immediate execution...")
        task_id = await scheduler.trigger_now("reddit")
        logger.info(f"  Task ID: {task_id}")

        # Wait for execution
        logger.info("  Waiting for execution...")
        await asyncio.sleep(2)

        # Check health
        health = await checker.get_current_health("reddit")
        if health:
            logger.info(f"\n  Health Status:")
            logger.info(f"    Total Runs: {health.total_runs}")
            logger.info(f"    Healthy: {health.is_healthy}")

        # Get full schedule
        schedule = await scheduler.get_schedule()
        logger.info(f"\nScheduled plugins: {len(schedule)}")
        for name, next_time in schedule.items():
            logger.info(f"  {name}: next run at {next_time}")

    finally:
        await scheduler.shutdown()
        logger.info("\nScheduler shutdown")


async def demo_plugin_management():
    """Demonstrate plugin enable/disable."""
    logger.info("\n" + "=" * 60)
    logger.info("PLUGIN MANAGEMENT DEMO")
    logger.info("=" * 60)

    manager = DefaultPluginManager()

    plugin_name = "reddit"

    # Get initial status
    status = await manager.get_plugin_status(plugin_name)
    logger.info(f"{plugin_name} enabled: {status['enabled']}")

    # Disable plugin
    logger.info(f"\nDisabling {plugin_name}...")
    await manager.disable_plugin(plugin_name)

    status = await manager.get_plugin_status(plugin_name)
    logger.info(f"{plugin_name} enabled: {status['enabled']}")

    # Re-enable plugin
    logger.info(f"\nRe-enabling {plugin_name}...")
    await manager.enable_plugin(plugin_name)

    status = await manager.get_plugin_status(plugin_name)
    logger.info(f"{plugin_name} enabled: {status['enabled']}")


async def main():
    """Run all demos."""
    logger.info("Starting Plugin System Demo")
    logger.info("=" * 60)

    try:
        # Run demos
        await demo_plugin_discovery()
        await demo_manual_collection()
        await demo_health_monitoring()
        await demo_rate_limiting()
        await demo_scheduler()
        await demo_plugin_management()

        logger.info("\n" + "=" * 60)
        logger.info("Demo completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
