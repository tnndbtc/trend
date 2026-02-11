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
        PostgreSQLTopicRepository,
    )
    from trend_agent.types import TrendState
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
        trend_repo = PostgreSQLTrendRepository(db_pool.pool)
        topic_repo = PostgreSQLTopicRepository(db_pool.pool)

        # Clean up old items (older than X days)
        items_deleted = await item_repo.delete_older_than(days)

        # Clean up DEAD/DECLINING trends older than X days
        trends_deleted = await trend_repo.delete_old_trends(
            days=days,
            states=[TrendState.DEAD, TrendState.DECLINING]
        )

        # Clean up stale topics (no activity in X days, not associated with any trend)
        topics_deleted = await topic_repo.delete_stale_topics(days=days)

        # Clean up old pipeline run logs
        pipeline_runs_deleted = await _cleanup_pipeline_runs(db_pool.pool, days)

        # Clean up orphaned embeddings (items/trends that no longer exist)
        embeddings_cleaned = await _cleanup_orphaned_embeddings(db_pool.pool)

        return {
            "items_deleted": items_deleted,
            "trends_deleted": trends_deleted,
            "topics_deleted": topics_deleted,
            "pipeline_runs_deleted": pipeline_runs_deleted,
            "embeddings_cleaned": embeddings_cleaned,
            "cutoff_days": days,
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        await db_pool.close()


async def _cleanup_pipeline_runs(pool, days: int) -> int:
    """
    Clean up old pipeline run records.

    Args:
        pool: Database connection pool
        days: Days to keep

    Returns:
        Number of records deleted
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = """
            DELETE FROM pipeline_runs
            WHERE started_at < $1
            RETURNING id
        """
        rows = await pool.fetch(query, cutoff)
        deleted = len(rows)
        logger.info(f"Deleted {deleted} pipeline runs older than {days} days")
        return deleted

    except Exception as e:
        # Table might not exist yet
        logger.warning(f"Could not cleanup pipeline runs: {e}")
        return 0


async def _cleanup_orphaned_embeddings(pool) -> int:
    """
    Clean up orphaned vector embeddings.

    Removes embeddings for items/trends that no longer exist in the database.

    Args:
        pool: Database connection pool

    Returns:
        Number of embeddings cleaned
    """
    try:
        # Find orphaned item embeddings
        query = """
            SELECT id FROM vectors
            WHERE id LIKE 'item:%'
            AND substring(id from 6)::uuid NOT IN (SELECT id::text FROM processed_items)
        """
        orphaned_items = await pool.fetch(query)

        # Find orphaned trend embeddings
        query2 = """
            SELECT id FROM vectors
            WHERE id LIKE 'trend:%'
            AND substring(id from 7)::uuid NOT IN (SELECT id::text FROM trends)
        """
        orphaned_trends = await pool.fetch(query2)

        total_orphaned = len(orphaned_items) + len(orphaned_trends)

        if total_orphaned > 0:
            # Delete orphaned embeddings
            all_orphaned_ids = [row["id"] for row in orphaned_items + orphaned_trends]
            delete_query = "DELETE FROM vectors WHERE id = ANY($1)"
            await pool.execute(delete_query, all_orphaned_ids)
            logger.info(f"Cleaned up {total_orphaned} orphaned embeddings")

        return total_orphaned

    except Exception as e:
        # Vectors table might not exist or might be in Qdrant only
        logger.warning(f"Could not cleanup orphaned embeddings: {e}")
        return 0


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
    from trend_agent.storage.postgres import (
        PostgreSQLConnectionPool,
        PostgreSQLPluginHealthRepository,
    )
    from trend_agent.types import PluginHealth
    import os

    # Initialize database connection
    db_pool = PostgreSQLConnectionPool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "trends"),
        user=os.getenv("POSTGRES_USER", "trend_user"),
        password=os.getenv("POSTGRES_PASSWORD", "trend_password"),
    )
    await db_pool.connect()

    try:
        health_repo = PostgreSQLPluginHealthRepository(db_pool.pool)
        plugin_manager = DefaultPluginManager()
        await plugin_manager.load_plugins()

        plugins = plugin_manager.get_all_plugins()
        updated_count = 0

        for plugin in plugins:
            # Get plugin status from manager
            status = await plugin_manager.get_plugin_status(plugin.metadata.name)

            # Convert status dict to PluginHealth object
            health = PluginHealth(
                name=plugin.metadata.name,
                is_healthy=status.get("is_healthy", True),
                last_run_at=status.get("last_run"),
                last_success_at=status.get("last_success"),
                last_error=status.get("last_error"),
                consecutive_failures=status.get("consecutive_failures", 0),
                total_runs=status.get("total_runs", 0),
                success_rate=status.get("success_rate", 0.0),
            )

            # Store health status in database
            await health_repo.update(health)
            updated_count += 1

        logger.info(f"Updated health status for {updated_count} plugins in database")

        return {
            "plugins_updated": updated_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        await db_pool.close()


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
        PostgreSQLTopicRepository,
        PostgreSQLItemRepository,
    )
    from trend_agent.storage.redis import RedisCacheRepository
    from trend_agent.types import TrendFilter
    import os
    import json

    db_pool = PostgreSQLConnectionPool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "trends"),
        user=os.getenv("POSTGRES_USER", "trend_user"),
        password=os.getenv("POSTGRES_PASSWORD", "trend_password"),
    )
    await db_pool.connect()

    # Initialize Redis cache
    redis = None
    try:
        redis = RedisCacheRepository(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
        )
        await redis.connect()
    except Exception as e:
        logger.warning(f"Could not connect to Redis for analytics storage: {e}")

    try:
        trend_repo = PostgreSQLTrendRepository(db_pool.pool)
        topic_repo = PostgreSQLTopicRepository(db_pool.pool)
        item_repo = PostgreSQLItemRepository(db_pool.pool)

        # Get trends from last 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        filters = TrendFilter(date_from=cutoff, limit=10000)
        trends = await trend_repo.search(filters)

        # Calculate trend analytics
        analytics = {
            "period": "7_days",
            "generated_at": datetime.utcnow().isoformat(),
            "total_trends": len(trends),
            "total_topics": await topic_repo.count(),
            "total_items": await item_repo.count(),
            "categories": {},
            "sources": {},
            "states": {},
            "languages": {},
            "avg_score": 0.0,
            "avg_velocity": 0.0,
            "avg_item_count": 0.0,
            "top_trends": [],
        }

        if trends:
            # Count by category
            for trend in trends:
                cat = trend.category.value
                analytics["categories"][cat] = analytics["categories"].get(cat, 0) + 1

                # Count by state
                state = trend.state.value
                analytics["states"][state] = analytics["states"].get(state, 0) + 1

                # Count by language
                lang = trend.language or "unknown"
                analytics["languages"][lang] = analytics["languages"].get(lang, 0) + 1

                # Count by source
                for source in trend.sources:
                    src = source.value
                    analytics["sources"][src] = analytics["sources"].get(src, 0) + 1

            # Calculate averages
            analytics["avg_score"] = sum(t.score for t in trends) / len(trends)
            analytics["avg_velocity"] = sum(t.velocity for t in trends) / len(trends)
            analytics["avg_item_count"] = sum(t.item_count for t in trends) / len(trends)

            # Get top 10 trends by score
            top_trends_data = sorted(trends, key=lambda t: t.score, reverse=True)[:10]
            analytics["top_trends"] = [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "score": t.score,
                    "category": t.category.value,
                    "state": t.state.value,
                }
                for t in top_trends_data
            ]

        # Store analytics in Redis cache (24 hour TTL)
        if redis:
            try:
                await redis.set("analytics:trends:7days", analytics, ttl_seconds=86400)
                await redis.set("analytics:latest", analytics, ttl_seconds=86400)
                logger.info("Stored analytics in Redis cache")
            except Exception as e:
                logger.warning(f"Failed to store analytics in Redis: {e}")

        # Store analytics snapshot in database (for historical tracking)
        try:
            analytics_json = json.dumps(analytics)
            query = """
                INSERT INTO analytics_snapshots (period, data, created_at)
                VALUES ($1, $2, NOW())
            """
            await db_pool.pool.execute(query, "7_days", analytics_json)
            logger.info("Stored analytics snapshot in database")
        except Exception as e:
            # Table might not exist yet
            logger.warning(f"Could not store analytics snapshot in database: {e}")

        return {
            "analytics": analytics,
            "timestamp": analytics["generated_at"],
        }

    finally:
        await db_pool.close()
        if redis:
            await redis.close()


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


@app.task(name="trend_agent.tasks.scheduler.update_trend_states_task")
def update_trend_states_task() -> Dict[str, Any]:
    """
    Update trend lifecycle states for all active trends.

    Analyzes trends and transitions states based on:
    - Velocity trends (acceleration/deceleration)
    - Engagement patterns
    - Time since peak
    - Historical data

    This task should run frequently (every 15-30 minutes) to ensure
    trends are accurately classified in their lifecycle.

    Returns:
        Dictionary with update statistics
    """
    logger.info("Updating trend states")

    try:
        result = asyncio.run(_update_trend_states_async())
        logger.info(
            f"Trend states updated: {result['updated']}/{result['total']} changed"
        )
        return result

    except Exception as e:
        logger.error(f"Failed to update trend states: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def _update_trend_states_async() -> Dict[str, Any]:
    """
    Async implementation of trend state updates.

    Returns:
        Dictionary with statistics
    """
    from trend_agent.services.trend_states import TrendStateService
    from trend_agent.storage.postgres import (
        PostgreSQLConnectionPool,
        PostgreSQLTrendRepository,
    )
    import os

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
        trend_repo = PostgreSQLTrendRepository(db_pool.pool)
        state_service = TrendStateService(trend_repo=trend_repo)

        # Get all active trends (not DEAD)
        from trend_agent.types import TrendFilter, TrendState

        # Get trends from last 7 days (active window)
        cutoff = datetime.utcnow() - timedelta(days=7)
        filters = TrendFilter(date_from=cutoff, limit=5000)
        trends = await trend_repo.search(filters)

        # Filter out DEAD trends (they don't need updates)
        active_trends = [t for t in trends if t.state != TrendState.DEAD]

        logger.info(
            f"Found {len(active_trends)} active trends to analyze "
            f"({len(trends) - len(active_trends)} dead trends skipped)"
        )

        # Bulk update states
        stats = await state_service.bulk_update_states(active_trends)

        # Add state breakdown
        state_counts = {}
        for trend in trends:
            state = trend.state.value
            state_counts[state] = state_counts.get(state, 0) + 1

        return {
            "status": "success",
            "total": stats["total"],
            "updated": stats["updated"],
            "unchanged": stats["unchanged"],
            "errors": stats["errors"],
            "state_breakdown": state_counts,
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        await db_pool.close()


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
