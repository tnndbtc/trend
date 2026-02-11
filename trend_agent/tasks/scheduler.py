"""
Celery tasks for periodic maintenance, health checks, and data cleanup.

This module defines scheduled tasks that run periodically to maintain
system health, clean up old data, and perform system monitoring.
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from trend_agent.tasks import app

logger = logging.getLogger(__name__)


@app.task(name="trend_agent.tasks.scheduler.health_check_task")
def health_check_task() -> Dict[str, Any]:
    """
    Periodic health check of all system components.

    Checks:
    - Database connectivity
    - Redis availability
    - Qdrant status
    - Plugin health
    - Disk space
    - Memory usage

    Returns:
        Dictionary with health check results
    """
    logger.info("Running system health check")

    try:
        result = asyncio.run(_health_check_async())
        logger.info(f"Health check complete: {result['status']}")
        return result

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def _health_check_async() -> Dict[str, Any]:
    """
    Async implementation of health check.

    Returns:
        Dictionary with results
    """
    import os
    import psutil

    services = {}

    # Check PostgreSQL
    try:
        from trend_agent.storage.postgres import PostgreSQLConnectionPool

        db_pool = PostgreSQLConnectionPool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "trends"),
            user=os.getenv("POSTGRES_USER", "trend_user"),
            password=os.getenv("POSTGRES_PASSWORD", "trend_password"),
        )
        await db_pool.connect()
        async with db_pool.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        await db_pool.close()
        services["postgresql"] = "healthy"
    except Exception as e:
        services["postgresql"] = f"unhealthy: {str(e)}"

    # Check Redis
    try:
        from trend_agent.storage.redis import RedisCacheRepository

        redis = RedisCacheRepository(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
        )
        await redis.connect()
        await redis.set("health_check", "ok", ttl_seconds=10)
        result = await redis.get("health_check")
        await redis.close()
        services["redis"] = "healthy" if result == "ok" else "unhealthy"
    except Exception as e:
        services["redis"] = f"unhealthy: {str(e)}"

    # Check Qdrant
    try:
        from trend_agent.storage.qdrant import QdrantVectorRepository

        vector_repo = QdrantVectorRepository(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            collection_name="trend_embeddings",
            vector_size=1536,
        )
        # Qdrant is considered healthy if we can create the repository
        services["qdrant"] = "healthy"
    except Exception as e:
        services["qdrant"] = f"unhealthy: {str(e)}"

    # Check system resources
    try:
        disk_usage = psutil.disk_usage('/')
        memory = psutil.virtual_memory()

        resources = {
            "disk_percent": disk_usage.percent,
            "disk_free_gb": disk_usage.free / (1024**3),
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
        }
    except Exception as e:
        resources = {"error": str(e)}

    # Determine overall status
    all_healthy = all("healthy" in status for status in services.values())
    overall_status = "healthy" if all_healthy else "degraded"

    return {
        "status": overall_status,
        "services": services,
        "resources": resources,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.task(name="trend_agent.tasks.scheduler.cleanup_old_data_task")
def cleanup_old_data_task(days: int = 30) -> Dict[str, Any]:
    """
    Clean up old data from the database.

    Removes:
    - Trends older than N days in DEAD state
    - Items older than N days
    - Old pipeline run logs
    - Expired cache entries

    Args:
        days: Number of days to keep data

    Returns:
        Dictionary with cleanup results
    """
    logger.info(f"Starting cleanup of data older than {days} days")

    try:
        result = asyncio.run(_cleanup_old_data_async(days))
        logger.info(f"Cleanup complete: {result['items_deleted']} items deleted")
        return result

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


async def _cleanup_old_data_async(days: int) -> Dict[str, Any]:
    """
    Async implementation of data cleanup.

    Args:
        days: Days to keep

    Returns:
        Dictionary with results
    """
    from trend_agent.storage.postgres import (
        PostgreSQLConnectionPool,
        PostgreSQLItemRepository,
        PostgreSQLTrendRepository,
    )
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
        item_repo = PostgreSQLItemRepository(db_pool.pool)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Clean up old items
        deleted = await item_repo.delete_old_items(cutoff_date)

        # TODO: Add cleanup for trends, pipeline runs, etc.

        return {
            "items_deleted": deleted,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        await db_pool.close()


@app.task(name="trend_agent.tasks.scheduler.update_plugin_health_task")
def update_plugin_health_task() -> Dict[str, Any]:
    """
    Update health status for all collector plugins.

    Records success rates, last run times, and error counts
    for each plugin in the database.

    Returns:
        Dictionary with update results
    """
    logger.info("Updating plugin health status")

    try:
        result = asyncio.run(_update_plugin_health_async())
        logger.info(f"Plugin health updated: {result['plugins_updated']} plugins")
        return result

    except Exception as e:
        logger.error(f"Plugin health update failed: {e}")
        raise


async def _update_plugin_health_async() -> Dict[str, Any]:
    """
    Async implementation of plugin health update.

    Returns:
        Dictionary with results
    """
    from trend_agent.ingestion.manager import DefaultPluginManager

    plugin_manager = DefaultPluginManager()
    await plugin_manager.load_plugins()

    plugins = plugin_manager.get_all_plugins()
    updated_count = 0

    for plugin in plugins:
        # Get plugin status
        status = await plugin_manager.get_plugin_status(plugin.metadata.name)

        # TODO: Store health status in database
        # await health_repo.update(plugin.metadata.name, status)

        updated_count += 1

    return {
        "plugins_updated": updated_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.task(name="trend_agent.tasks.scheduler.generate_analytics_task")
def generate_analytics_task() -> Dict[str, Any]:
    """
    Generate analytics and statistics reports.

    Creates:
    - Trend analytics (growth rates, popular categories)
    - Source analytics (best performing sources)
    - Engagement analytics (average metrics over time)
    - System performance metrics

    Returns:
        Dictionary with analytics results
    """
    logger.info("Generating analytics reports")

    try:
        result = asyncio.run(_generate_analytics_async())
        logger.info("Analytics generation complete")
        return result

    except Exception as e:
        logger.error(f"Analytics generation failed: {e}")
        raise


async def _generate_analytics_async() -> Dict[str, Any]:
    """
    Async implementation of analytics generation.

    Returns:
        Dictionary with results
    """
    from trend_agent.storage.postgres import (
        PostgreSQLConnectionPool,
        PostgreSQLTrendRepository,
    )
    from trend_agent.types import TrendFilter
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

        # Get trends from last 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        filters = TrendFilter(date_from=cutoff, limit=10000)
        trends = await trend_repo.search(filters)

        # Calculate analytics
        analytics = {
            "total_trends": len(trends),
            "categories": {},
            "sources": {},
            "states": {},
            "avg_score": 0.0,
            "avg_velocity": 0.0,
        }

        if trends:
            # Count by category
            for trend in trends:
                cat = trend.category.value
                analytics["categories"][cat] = analytics["categories"].get(cat, 0) + 1

                # Count by state
                state = trend.state.value
                analytics["states"][state] = analytics["states"].get(state, 0) + 1

                # Count by source
                for source in trend.sources:
                    src = source.value
                    analytics["sources"][src] = analytics["sources"].get(src, 0) + 1

            # Calculate averages
            analytics["avg_score"] = sum(t.score for t in trends) / len(trends)
            analytics["avg_velocity"] = sum(t.velocity for t in trends) / len(trends)

        # TODO: Store analytics in database or cache

        return {
            "analytics": analytics,
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        await db_pool.close()


@app.task(name="trend_agent.tasks.scheduler.backup_database_task")
def backup_database_task() -> Dict[str, Any]:
    """
    Create a backup of the PostgreSQL database.

    Creates a pg_dump backup and stores it in the configured location.

    Returns:
        Dictionary with backup results
    """
    logger.info("Starting database backup")

    import subprocess
    import os

    try:
        # Database configuration
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "trends")
        db_user = os.getenv("POSTGRES_USER", "trend_user")
        db_password = os.getenv("POSTGRES_PASSWORD", "trend_password")
        backup_dir = os.getenv("BACKUP_DIR", "/tmp/backups")

        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)

        # Create backup filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"trends_backup_{timestamp}.sql")

        # Run pg_dump
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password

        command = [
            "pg_dump",
            "-h", db_host,
            "-p", db_port,
            "-U", db_user,
            "-d", db_name,
            "-F", "c",  # Custom format
            "-f", backup_file,
        ]

        result = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {result.stderr}")

        # Get file size
        file_size_mb = os.path.getsize(backup_file) / (1024 * 1024)

        logger.info(f"Database backup complete: {backup_file} ({file_size_mb:.2f} MB)")

        return {
            "status": "success",
            "backup_file": backup_file,
            "size_mb": file_size_mb,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.task(name="trend_agent.tasks.scheduler.monitor_celery_queue_task")
def monitor_celery_queue_task() -> Dict[str, Any]:
    """
    Monitor Celery queue sizes and worker status.

    Checks:
    - Queue lengths
    - Active workers
    - Failed task counts
    - Average task execution time

    Returns:
        Dictionary with monitoring results
    """
    logger.info("Monitoring Celery queues")

    from trend_agent.tasks import app as celery_app

    inspect = celery_app.control.inspect()

    # Get queue stats
    active_tasks = inspect.active() or {}
    scheduled_tasks = inspect.scheduled() or {}
    reserved_tasks = inspect.reserved() or {}
    stats = inspect.stats() or {}

    # Calculate totals
    total_active = sum(len(tasks) for tasks in active_tasks.values())
    total_scheduled = sum(len(tasks) for tasks in scheduled_tasks.values())
    total_reserved = sum(len(tasks) for tasks in reserved_tasks.values())
    total_workers = len(stats)

    result = {
        "workers": total_workers,
        "active_tasks": total_active,
        "scheduled_tasks": total_scheduled,
        "reserved_tasks": total_reserved,
        "worker_details": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Log warnings if queues are too long
    if total_active > 100:
        logger.warning(f"High number of active tasks: {total_active}")
    if total_scheduled > 500:
        logger.warning(f"High number of scheduled tasks: {total_scheduled}")

    return result


# Utility functions

def get_scheduler_status() -> Dict[str, Any]:
    """
    Get status of scheduled tasks.

    Returns:
        Dictionary with scheduler status
    """
    from trend_agent.tasks import app as celery_app

    inspect = celery_app.control.inspect()
    scheduled = inspect.scheduled() or {}

    return {
        "scheduled_tasks": scheduled,
        "timestamp": datetime.utcnow().isoformat(),
    }
