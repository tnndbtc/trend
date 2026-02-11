"""
Celery task queue configuration for the Trend Intelligence Platform.

This module configures Celery for distributed task execution including:
- Data collection tasks
- Processing pipeline tasks
- Scheduled periodic tasks
- Task monitoring and error handling

The Celery app uses RabbitMQ as the message broker and Redis as the result backend.
"""

import os
import logging
from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Celery configuration
class CeleryConfig:
    """Celery configuration class."""

    # Broker settings
    broker_url = os.getenv(
        "CELERY_BROKER_URL",
        "amqp://guest:guest@localhost:5672//"
    )
    result_backend = os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/1"
    )

    # Task settings
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    timezone = "UTC"
    enable_utc = True

    # Task execution settings
    task_acks_late = True  # Acknowledge task after completion
    task_reject_on_worker_lost = True  # Requeue tasks if worker crashes
    task_track_started = True  # Track when tasks start
    worker_prefetch_multiplier = 1  # Fetch one task at a time (for long-running tasks)
    worker_max_tasks_per_child = 1000  # Restart worker after N tasks (prevent memory leaks)

    # Task result settings
    result_expires = 3600  # Keep results for 1 hour
    result_persistent = True  # Persist results

    # Task routing
    task_default_queue = "default"
    task_default_exchange = "default"
    task_default_routing_key = "default"

    # Define task queues
    task_queues = (
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("collection", Exchange("collection"), routing_key="collection.#"),
        Queue("processing", Exchange("processing"), routing_key="processing.#"),
        Queue("priority", Exchange("priority"), routing_key="priority.#", priority=10),
    )

    # Task routes
    task_routes = {
        "trend_agent.tasks.collection.*": {
            "queue": "collection",
            "routing_key": "collection.data",
        },
        "trend_agent.tasks.processing.*": {
            "queue": "processing",
            "routing_key": "processing.pipeline",
        },
    }

    # Beat schedule (periodic tasks)
    beat_schedule = {
        # Collect from all plugins every hour
        "collect-all-hourly": {
            "task": "trend_agent.tasks.collection.collect_all_plugins_task",
            "schedule": crontab(minute=0),  # Every hour at :00
            "options": {"queue": "collection"},
        },
        # Collect from high-frequency sources every 15 minutes
        "collect-high-frequency": {
            "task": "trend_agent.tasks.collection.collect_high_frequency_task",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
            "options": {"queue": "collection"},
        },
        # Process collected items every 30 minutes
        "process-items": {
            "task": "trend_agent.tasks.processing.process_pending_items_task",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
            "options": {"queue": "processing"},
        },
        # Cleanup old data daily at 3 AM
        "cleanup-daily": {
            "task": "trend_agent.tasks.scheduler.cleanup_old_data_task",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3:00 AM
            "options": {"queue": "default"},
        },
        # Health check every 5 minutes
        "health-check": {
            "task": "trend_agent.tasks.scheduler.health_check_task",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
            "options": {"queue": "default"},
        },
        # Update trend states every 20 minutes
        "update-trend-states": {
            "task": "trend_agent.tasks.scheduler.update_trend_states_task",
            "schedule": crontab(minute="*/20"),  # Every 20 minutes
            "options": {"queue": "processing"},
        },
    }

    # Logging
    worker_hijack_root_logger = False
    worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
    worker_task_log_format = "[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s"


# Create Celery app
app = Celery("trend_agent")
app.config_from_object(CeleryConfig)

# Auto-discover tasks from all task modules
app.autodiscover_tasks([
    "trend_agent.tasks.collection",
    "trend_agent.tasks.processing",
    "trend_agent.tasks.scheduler",
])


# Celery signals for monitoring
@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery configuration."""
    logger.info(f"Request: {self.request!r}")
    return {"status": "ok", "worker": self.request.hostname}


# Event handlers
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks after Celery is configured."""
    logger.info("Celery periodic tasks configured")


@app.on_after_finalize.connect
def setup_task_monitoring(sender, **kwargs):
    """Setup task monitoring after Celery is finalized."""
    logger.info("Celery app finalized and ready")


# Task error handler
class TaskErrorHandler:
    """Centralized task error handling."""

    @staticmethod
    def handle_task_failure(task_id: str, exception: Exception, traceback: str):
        """
        Handle task failure.

        Args:
            task_id: ID of the failed task
            exception: Exception that caused the failure
            traceback: Traceback string
        """
        logger.error(
            f"Task {task_id} failed with exception: {exception}\n"
            f"Traceback: {traceback}"
        )

        # Send alert notification (async in background)
        try:
            import asyncio
            from trend_agent.services.alerts import get_alert_service, AlertSeverity

            alert_service = get_alert_service()

            async def send_failure_alert():
                await alert_service.send_alert(
                    title=f"Task Failure: {task_id}",
                    message=f"Task failed with exception: {str(exception)}\n\nTraceback:\n{traceback}",
                    severity=AlertSeverity.ERROR,
                    metadata={"task_id": task_id, "exception_type": type(exception).__name__},
                )

            # Run alert in new event loop (since we're in Celery context)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(send_failure_alert())

        except Exception as e:
            logger.warning(f"Failed to send alert for task failure: {e}")

        # Record failure in database for analytics
        try:
            import asyncio
            from trend_agent.storage.postgres import PostgreSQLConnectionPool
            import os

            async def record_failure():
                db_pool = PostgreSQLConnectionPool(
                    host=os.getenv("POSTGRES_HOST", "localhost"),
                    port=int(os.getenv("POSTGRES_PORT", "5432")),
                    database=os.getenv("POSTGRES_DB", "trends"),
                    user=os.getenv("POSTGRES_USER", "trend_user"),
                    password=os.getenv("POSTGRES_PASSWORD", "trend_password"),
                )
                await db_pool.connect()

                try:
                    query = """
                        INSERT INTO task_failures (task_id, exception, traceback, created_at)
                        VALUES ($1, $2, $3, NOW())
                    """
                    await db_pool.pool.execute(query, task_id, str(exception), traceback)
                finally:
                    await db_pool.close()

            # Run in event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(record_failure())

        except Exception as e:
            logger.warning(f"Failed to record task failure in database: {e}")


# Utility functions

def get_active_tasks():
    """
    Get list of currently active tasks.

    Returns:
        List of active task information
    """
    inspect = app.control.inspect()
    active = inspect.active()
    return active if active else {}


def get_scheduled_tasks():
    """
    Get list of scheduled periodic tasks.

    Returns:
        List of scheduled tasks
    """
    inspect = app.control.inspect()
    scheduled = inspect.scheduled()
    return scheduled if scheduled else {}


def get_registered_tasks():
    """
    Get list of all registered tasks.

    Returns:
        List of registered task names
    """
    inspect = app.control.inspect()
    registered = inspect.registered()
    return registered if registered else {}


def cancel_task(task_id: str):
    """
    Cancel a running or pending task.

    Args:
        task_id: ID of the task to cancel
    """
    app.control.revoke(task_id, terminate=True)
    logger.info(f"Task {task_id} cancelled")


def purge_queue(queue_name: str = "default"):
    """
    Purge all tasks from a queue.

    Args:
        queue_name: Name of the queue to purge
    """
    app.control.purge()
    logger.info(f"Queue {queue_name} purged")


# Export
__all__ = [
    "app",
    "CeleryConfig",
    "debug_task",
    "get_active_tasks",
    "get_scheduled_tasks",
    "get_registered_tasks",
    "cancel_task",
    "purge_queue",
    "TaskErrorHandler",
]
