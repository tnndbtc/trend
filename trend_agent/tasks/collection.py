"""
Celery tasks for data collection from various sources.

This module defines tasks for collecting data from collector plugins,
managing rate limits, handling failures, and storing raw items.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from celery import Task, group, chain

from trend_agent.tasks import app
from trend_agent.types import RawItem, SourceType

logger = logging.getLogger(__name__)


class CollectionTask(Task):
    """Base class for collection tasks with error handling."""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(
            f"Collection task {task_id} failed: {exc}\n"
            f"Args: {args}\n"
            f"Kwargs: {kwargs}\n"
            f"Info: {einfo}"
        )
        # TODO: Send alert, update health checker


@app.task(base=CollectionTask, name="trend_agent.tasks.collection.collect_from_plugin_task")
def collect_from_plugin_task(plugin_name: str) -> Dict[str, Any]:
    """
    Collect data from a specific plugin.

    Args:
        plugin_name: Name of the plugin to collect from

    Returns:
        Dictionary with collection results

    Raises:
        ValueError: If plugin not found or disabled
    """
    logger.info(f"Starting collection from plugin: {plugin_name}")

    try:
        # Run async collection in sync context
        result = asyncio.run(_collect_from_plugin_async(plugin_name))
        logger.info(
            f"Collection complete for {plugin_name}: "
            f"{result['items_collected']} items collected"
        )
        return result

    except Exception as e:
        logger.error(f"Collection failed for {plugin_name}: {e}")
        raise


async def _collect_from_plugin_async(plugin_name: str) -> Dict[str, Any]:
    """
    Async implementation of plugin collection.

    Args:
        plugin_name: Name of the plugin

    Returns:
        Dictionary with results
    """
    from trend_agent.ingestion.manager import DefaultPluginManager
    from trend_agent.storage.postgres import (
        PostgreSQLConnectionPool,
        PostgreSQLItemRepository,
    )
    import os

    # Initialize plugin manager
    plugin_manager = DefaultPluginManager()
    await plugin_manager.load_plugins()

    # Get the plugin
    plugin = plugin_manager.get_plugin(plugin_name)
    if plugin is None:
        raise ValueError(f"Plugin '{plugin_name}' not found")

    # Check if enabled
    status = await plugin_manager.get_plugin_status(plugin_name)
    if not status.get("enabled", True):
        raise ValueError(f"Plugin '{plugin_name}' is disabled")

    # Collect data
    start_time = datetime.utcnow()
    raw_items = await plugin.collect()

    # Connect to database
    db_pool = PostgreSQLConnectionPool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "trends"),
        user=os.getenv("POSTGRES_USER", "trend_user"),
        password=os.getenv("POSTGRES_PASSWORD", "trend_password"),
    )
    await db_pool.connect()

    # Save items
    try:
        item_repo = PostgreSQLItemRepository(db_pool.pool)
        saved_count = 0

        for raw_item in raw_items:
            # Convert RawItem to ProcessedItem
            from trend_agent.types import ProcessedItem

            processed_item = ProcessedItem(
                source=raw_item.source,
                source_id=raw_item.source_id,
                url=raw_item.url,
                title=raw_item.title,
                title_normalized=raw_item.title,  # Will be normalized in processing
                description=raw_item.description,
                content=raw_item.content,
                author=raw_item.author,
                published_at=raw_item.published_at,
                collected_at=raw_item.collected_at,
                metrics=raw_item.metrics,
                metadata=raw_item.metadata,
            )

            await item_repo.save(processed_item)
            saved_count += 1

        duration = (datetime.utcnow() - start_time).total_seconds()

        return {
            "plugin_name": plugin_name,
            "items_collected": len(raw_items),
            "items_saved": saved_count,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        await db_pool.close()


@app.task(base=CollectionTask, name="trend_agent.tasks.collection.collect_all_plugins_task")
def collect_all_plugins_task() -> Dict[str, Any]:
    """
    Collect data from all enabled plugins.

    This task creates subtasks for each plugin and runs them in parallel.

    Returns:
        Dictionary with overall collection results
    """
    logger.info("Starting collection from all plugins")

    try:
        result = asyncio.run(_collect_all_plugins_async())
        logger.info(
            f"Collection complete from all plugins: "
            f"{result['total_items']} items collected from "
            f"{result['plugins_run']} plugins"
        )
        return result

    except Exception as e:
        logger.error(f"Collection from all plugins failed: {e}")
        raise


async def _collect_all_plugins_async() -> Dict[str, Any]:
    """
    Async implementation of collecting from all plugins.

    Returns:
        Dictionary with results
    """
    from trend_agent.ingestion.manager import DefaultPluginManager

    # Initialize plugin manager
    plugin_manager = DefaultPluginManager()
    await plugin_manager.load_plugins()

    # Get all enabled plugins
    all_plugins = plugin_manager.get_all_plugins()
    enabled_plugins = []

    for plugin in all_plugins:
        status = await plugin_manager.get_plugin_status(plugin.metadata.name)
        if status.get("enabled", True):
            enabled_plugins.append(plugin.metadata.name)

    logger.info(f"Found {len(enabled_plugins)} enabled plugins")

    # Create subtasks for each plugin
    # Note: Using Celery's group to run in parallel
    job = group(
        collect_from_plugin_task.s(plugin_name)
        for plugin_name in enabled_plugins
    )

    # Execute tasks (this is synchronous from the task perspective)
    # The group will be executed by Celery workers
    result = job.apply_async()

    # Wait for all tasks to complete (with timeout)
    results = result.get(timeout=600)  # 10 minute timeout

    # Aggregate results
    total_items = sum(r.get("items_collected", 0) for r in results)
    total_saved = sum(r.get("items_saved", 0) for r in results)

    return {
        "plugins_run": len(enabled_plugins),
        "total_items": total_items,
        "total_saved": total_saved,
        "timestamp": datetime.utcnow().isoformat(),
        "plugin_results": results,
    }


@app.task(base=CollectionTask, name="trend_agent.tasks.collection.collect_high_frequency_task")
def collect_high_frequency_task() -> Dict[str, Any]:
    """
    Collect from high-frequency sources (Reddit, HackerNews, Twitter).

    These sources update frequently and should be checked more often.

    Returns:
        Dictionary with collection results
    """
    logger.info("Starting high-frequency collection")

    high_frequency_plugins = ["reddit", "hackernews"]

    try:
        # Create subtasks for high-frequency plugins
        job = group(
            collect_from_plugin_task.s(plugin_name)
            for plugin_name in high_frequency_plugins
        )

        result = job.apply_async()
        results = result.get(timeout=300)  # 5 minute timeout

        total_items = sum(r.get("items_collected", 0) for r in results)

        logger.info(f"High-frequency collection complete: {total_items} items")

        return {
            "plugins_run": len(high_frequency_plugins),
            "total_items": total_items,
            "timestamp": datetime.utcnow().isoformat(),
            "plugin_results": results,
        }

    except Exception as e:
        logger.error(f"High-frequency collection failed: {e}")
        raise


@app.task(base=CollectionTask, name="trend_agent.tasks.collection.collect_and_process_task")
def collect_and_process_task(plugin_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Collect data and immediately trigger processing.

    This is a chained task that collects data then processes it.

    Args:
        plugin_name: Optional specific plugin name, or None for all

    Returns:
        Dictionary with collection and processing results
    """
    logger.info(f"Starting collect-and-process for: {plugin_name or 'all plugins'}")

    from trend_agent.tasks.processing import process_pending_items_task

    # Create a chain: collect -> process
    if plugin_name:
        job = chain(
            collect_from_plugin_task.s(plugin_name),
            process_pending_items_task.s()
        )
    else:
        job = chain(
            collect_all_plugins_task.s(),
            process_pending_items_task.s()
        )

    # Execute the chain
    result = job.apply_async()
    final_result = result.get(timeout=900)  # 15 minute timeout

    logger.info("Collect-and-process complete")

    return {
        "status": "completed",
        "result": final_result,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.task(name="trend_agent.tasks.collection.test_plugin_task")
def test_plugin_task(plugin_name: str) -> Dict[str, Any]:
    """
    Test a plugin without saving data.

    Useful for debugging and validating plugin configuration.

    Args:
        plugin_name: Name of the plugin to test

    Returns:
        Dictionary with test results
    """
    logger.info(f"Testing plugin: {plugin_name}")

    try:
        result = asyncio.run(_test_plugin_async(plugin_name))
        logger.info(f"Plugin test complete for {plugin_name}")
        return result

    except Exception as e:
        logger.error(f"Plugin test failed for {plugin_name}: {e}")
        return {
            "plugin_name": plugin_name,
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def _test_plugin_async(plugin_name: str) -> Dict[str, Any]:
    """
    Async implementation of plugin test.

    Args:
        plugin_name: Name of the plugin

    Returns:
        Dictionary with test results
    """
    from trend_agent.ingestion.manager import DefaultPluginManager

    plugin_manager = DefaultPluginManager()
    await plugin_manager.load_plugins()

    plugin = plugin_manager.get_plugin(plugin_name)
    if plugin is None:
        raise ValueError(f"Plugin '{plugin_name}' not found")

    # Try to collect (but don't save)
    start_time = datetime.utcnow()
    raw_items = await plugin.collect()
    duration = (datetime.utcnow() - start_time).total_seconds()

    # Analyze collected items
    sample_item = raw_items[0] if raw_items else None

    return {
        "plugin_name": plugin_name,
        "success": True,
        "items_collected": len(raw_items),
        "duration_seconds": duration,
        "sample_item": {
            "title": sample_item.title if sample_item else None,
            "source": sample_item.source.value if sample_item else None,
        } if sample_item else None,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Utility functions for task monitoring

def get_collection_status() -> Dict[str, Any]:
    """
    Get status of collection tasks.

    Returns:
        Dictionary with task status information
    """
    from trend_agent.tasks import get_active_tasks, get_scheduled_tasks

    active = get_active_tasks()
    scheduled = get_scheduled_tasks()

    # Filter for collection tasks only
    collection_active = {}
    for worker, tasks in (active or {}).items():
        collection_tasks = [
            t for t in tasks
            if "collection" in t.get("name", "")
        ]
        if collection_tasks:
            collection_active[worker] = collection_tasks

    return {
        "active_tasks": collection_active,
        "scheduled_tasks": scheduled,
        "timestamp": datetime.utcnow().isoformat(),
    }
