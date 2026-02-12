"""
Scheduler for periodic plugin execution.

This module implements plugin scheduling using APScheduler,
supporting cron expressions, interval-based scheduling, and
on-demand execution.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from trend_agent.ingestion.base import CollectorPlugin, PluginRegistry
from trend_agent.ingestion.interfaces import BaseScheduler
from trend_agent.ingestion.converters import batch_raw_to_processed

logger = logging.getLogger(__name__)


class DefaultScheduler(BaseScheduler):
    """
    Default scheduler implementation using APScheduler.

    This class handles:
    - Periodic plugin execution based on cron expressions
    - On-demand plugin triggering
    - Schedule management
    - Job tracking

    Integrates with HealthChecker and RateLimiter for robust execution.
    """

    def __init__(
        self,
        health_checker=None,
        rate_limiter=None,
        storage_repo=None
    ):
        """
        Initialize the scheduler.

        Args:
            health_checker: Optional HealthChecker instance for tracking
            rate_limiter: Optional RateLimiter for enforcing limits
            storage_repo: Optional storage repository for persisting collected data
        """
        self.scheduler = AsyncIOScheduler()
        self.health_checker = health_checker
        self.rate_limiter = rate_limiter
        self.storage_repo = storage_repo

        # Track job IDs for each plugin
        self._plugin_jobs: Dict[str, str] = {}

        # Track active tasks
        self._active_tasks: Dict[str, asyncio.Task] = {}

        logger.info("Scheduler initialized")

    async def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    async def shutdown(self) -> None:
        """Shutdown the scheduler and cancel active tasks."""
        logger.info("Shutting down scheduler")

        # Cancel all active tasks
        for task_id, task in self._active_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled active task: {task_id}")

        # Shutdown scheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown complete")

    async def schedule_plugin(
        self, plugin: CollectorPlugin, cron_expression: str
    ) -> str:
        """
        Schedule a plugin for periodic execution.

        Args:
            plugin: The plugin to schedule
            cron_expression: Cron expression for scheduling (e.g., "0 * * * *" for hourly)

        Returns:
            Job ID for the scheduled task

        Example cron expressions:
            "0 * * * *" - Every hour
            "*/15 * * * *" - Every 15 minutes
            "0 0 * * *" - Daily at midnight
            "0 0 * * 0" - Weekly on Sunday
        """
        plugin_name = plugin.metadata.name

        # If already scheduled, remove old job
        if plugin_name in self._plugin_jobs:
            await self.unschedule_plugin(plugin_name)

        # Create cron trigger
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
        except Exception as e:
            logger.error(f"Invalid cron expression '{cron_expression}': {e}")
            raise ValueError(f"Invalid cron expression: {e}")

        # Add job to scheduler
        job = self.scheduler.add_job(
            self._execute_plugin,
            trigger=trigger,
            args=[plugin],
            id=f"plugin_{plugin_name}",
            name=f"Collect from {plugin_name}",
            replace_existing=True,
        )

        job_id = job.id
        self._plugin_jobs[plugin_name] = job_id

        logger.info(
            f"Scheduled plugin {plugin_name} with cron '{cron_expression}' (job_id: {job_id})"
        )

        return job_id

    async def unschedule_plugin(self, plugin_name: str) -> bool:
        """
        Remove a plugin from the schedule.

        Args:
            plugin_name: Name of the plugin to unschedule

        Returns:
            True if unscheduled successfully
        """
        if plugin_name not in self._plugin_jobs:
            logger.warning(f"Plugin {plugin_name} is not scheduled")
            return False

        job_id = self._plugin_jobs[plugin_name]

        try:
            self.scheduler.remove_job(job_id)
            del self._plugin_jobs[plugin_name]
            logger.info(f"Unscheduled plugin {plugin_name} (job_id: {job_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to unschedule plugin {plugin_name}: {e}")
            return False

    async def trigger_now(self, plugin_name: str) -> str:
        """
        Trigger immediate execution of a plugin.

        This creates a one-time task that executes immediately.

        Args:
            plugin_name: Name of the plugin to execute

        Returns:
            Task ID for the execution
        """
        plugin = PluginRegistry.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin {plugin_name} not found")

        # Generate unique task ID
        task_id = f"task_{plugin_name}_{uuid.uuid4().hex[:8]}"

        # Create and store task
        task = asyncio.create_task(
            self._execute_plugin(plugin),
            name=task_id
        )

        self._active_tasks[task_id] = task

        # Clean up task when done
        task.add_done_callback(lambda t: self._active_tasks.pop(task_id, None))

        logger.info(f"Triggered immediate execution of {plugin_name} (task_id: {task_id})")

        return task_id

    async def get_next_run(self, plugin_name: str) -> Optional[datetime]:
        """
        Get next scheduled run time for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Next run datetime if scheduled, None otherwise
        """
        if plugin_name not in self._plugin_jobs:
            return None

        job_id = self._plugin_jobs[plugin_name]

        try:
            job = self.scheduler.get_job(job_id)
            if job and job.next_run_time:
                return job.next_run_time
            return None
        except Exception as e:
            logger.error(f"Error getting next run time for {plugin_name}: {e}")
            return None

    async def get_schedule(self) -> Dict[str, datetime]:
        """
        Get schedule for all plugins.

        Returns:
            Dictionary mapping plugin names to next run times
        """
        schedule = {}

        for plugin_name, job_id in self._plugin_jobs.items():
            try:
                job = self.scheduler.get_job(job_id)
                if job and job.next_run_time:
                    schedule[plugin_name] = job.next_run_time
            except Exception as e:
                logger.error(f"Error getting schedule for {plugin_name}: {e}")

        return schedule

    async def _execute_plugin(self, plugin: CollectorPlugin) -> None:
        """
        Execute a plugin collection.

        This internal method handles:
        - Rate limiting
        - Plugin execution
        - Error handling
        - Health tracking
        - Data persistence

        Args:
            plugin: The plugin to execute
        """
        plugin_name = plugin.metadata.name
        logger.info(f"Executing plugin: {plugin_name}")

        try:
            # Check rate limit
            if self.rate_limiter:
                can_run = await self.rate_limiter.check_rate_limit(plugin_name)
                if not can_run:
                    logger.warning(f"Rate limit exceeded for {plugin_name}, skipping execution")
                    return

            # Record request
            if self.rate_limiter:
                await self.rate_limiter.record_request(plugin_name)

            # Execute collection with timeout
            timeout = plugin.metadata.timeout_seconds

            try:
                items = await asyncio.wait_for(
                    plugin.collect(),
                    timeout=timeout
                )

                logger.info(f"Plugin {plugin_name} collected {len(items)} items")

                # Validate items
                validated_items = []
                for item in items:
                    if await plugin.validate(item):
                        validated_items.append(item)
                    else:
                        logger.warning(f"Item validation failed for {plugin_name}: {item.source_id}")

                logger.info(f"Plugin {plugin_name} validated {len(validated_items)}/{len(items)} items")

                # Persist to storage if available
                if self.storage_repo and validated_items:
                    try:
                        # Convert RawItems to ProcessedItems with minimal processing
                        # Full processing will happen later in the processing pipeline
                        processed_items = batch_raw_to_processed(validated_items)

                        # Save to database (storage_repo should be ItemRepository)
                        for item in processed_items:
                            await self.storage_repo.save(item)

                        logger.info(f"Persisted {len(processed_items)} items from {plugin_name} to database")
                    except Exception as e:
                        logger.error(f"Failed to persist items from {plugin_name}: {e}", exc_info=True)

                # Call success hook
                await plugin.on_success(validated_items)

                # Record success in health checker
                if self.health_checker:
                    await self.health_checker.record_success(plugin_name)

            except asyncio.TimeoutError:
                error_msg = f"Plugin execution timed out after {timeout}s"
                logger.error(f"{plugin_name}: {error_msg}")

                await plugin.on_error(TimeoutError(error_msg))

                if self.health_checker:
                    await self.health_checker.record_failure(plugin_name, error_msg)

            except Exception as e:
                error_msg = f"Plugin execution failed: {str(e)}"
                logger.error(f"{plugin_name}: {error_msg}", exc_info=True)

                await plugin.on_error(e)

                if self.health_checker:
                    await self.health_checker.record_failure(plugin_name, error_msg)

        except Exception as e:
            # Catch-all for any unexpected errors
            logger.error(f"Unexpected error executing {plugin_name}: {e}", exc_info=True)

    def get_active_tasks(self) -> Dict[str, bool]:
        """
        Get status of active tasks.

        Returns:
            Dictionary mapping task IDs to completion status
        """
        return {
            task_id: task.done()
            for task_id, task in self._active_tasks.items()
        }

    async def schedule_all_plugins(self) -> Dict[str, str]:
        """
        Schedule all enabled plugins using their configured schedules.

        Returns:
            Dictionary mapping plugin names to job IDs
        """
        scheduled = {}

        for plugin in PluginRegistry.get_enabled_plugins():
            try:
                cron_expression = plugin.metadata.schedule
                job_id = await self.schedule_plugin(plugin, cron_expression)
                scheduled[plugin.metadata.name] = job_id
            except Exception as e:
                logger.error(
                    f"Failed to schedule plugin {plugin.metadata.name}: {e}",
                    exc_info=True
                )

        logger.info(f"Scheduled {len(scheduled)} plugins")
        return scheduled
