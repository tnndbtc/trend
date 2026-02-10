"""
Health monitoring for collector plugins.

This module provides health checking and tracking for collector plugins,
monitoring success rates, failures, and overall plugin health status.
"""

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from trend_agent.ingestion.base import CollectorPlugin, PluginRegistry
from trend_agent.ingestion.interfaces import BaseHealthChecker
from trend_agent.types import PluginHealth

logger = logging.getLogger(__name__)


class DefaultHealthChecker(BaseHealthChecker):
    """
    Default implementation of the HealthChecker interface.

    This class monitors plugin health by tracking:
    - Successful and failed collection attempts
    - Last run times
    - Consecutive failure counts
    - Success rates over time
    - Health history

    The health data can be stored in-memory or backed by Redis for persistence.
    """

    def __init__(
        self,
        max_history_size: int = 1000,
        health_check_interval: int = 60,
        failure_threshold: int = 3
    ):
        """
        Initialize the health checker.

        Args:
            max_history_size: Maximum number of health snapshots to keep per plugin
            health_check_interval: Interval in seconds between health checks
            failure_threshold: Number of consecutive failures before marking unhealthy
        """
        self.max_history_size = max_history_size
        self.health_check_interval = health_check_interval
        self.failure_threshold = failure_threshold

        # In-memory storage for health data
        # In production, this should be backed by Redis or a database
        self._health_data: Dict[str, PluginHealth] = {}
        self._health_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_history_size)
        )

        # Lock for thread-safe updates
        self._lock = asyncio.Lock()

        logger.info(
            f"Health checker initialized with failure threshold: {failure_threshold}"
        )

    async def check_health(self, plugin: CollectorPlugin) -> PluginHealth:
        """
        Check the health of a plugin.

        This method evaluates the plugin's current health based on:
        - Recent run history
        - Consecutive failures
        - Success rate

        Args:
            plugin: The plugin to check

        Returns:
            Health status of the plugin
        """
        plugin_name = plugin.metadata.name

        async with self._lock:
            # Get or create health data
            if plugin_name not in self._health_data:
                self._health_data[plugin_name] = PluginHealth(
                    name=plugin_name,
                    is_healthy=True,
                    last_run_at=None,
                    last_success_at=None,
                    last_error=None,
                    consecutive_failures=0,
                    total_runs=0,
                    success_rate=1.0,
                )

            health = self._health_data[plugin_name]

            # Determine if healthy based on consecutive failures
            is_healthy = health.consecutive_failures < self.failure_threshold

            # Update health status (return a new instance since PluginHealth is not frozen)
            health.is_healthy = is_healthy

            return health

    async def check_all_health(self) -> Dict[str, PluginHealth]:
        """
        Check health of all plugins.

        Returns:
            Dictionary mapping plugin names to health status
        """
        all_health = {}

        for plugin in PluginRegistry.get_all_plugins():
            health = await self.check_health(plugin)
            all_health[plugin.metadata.name] = health

        return all_health

    async def record_success(self, plugin_name: str) -> None:
        """
        Record a successful collection.

        This updates the health metrics and resets consecutive failures.

        Args:
            plugin_name: Name of the plugin
        """
        logger.debug(f"Recording success for plugin: {plugin_name}")

        async with self._lock:
            # Get or create health data
            if plugin_name not in self._health_data:
                self._health_data[plugin_name] = PluginHealth(
                    name=plugin_name,
                    is_healthy=True,
                    last_run_at=None,
                    last_success_at=None,
                    last_error=None,
                    consecutive_failures=0,
                    total_runs=0,
                    success_rate=1.0,
                )

            health = self._health_data[plugin_name]

            # Update metrics
            now = datetime.utcnow()
            health.last_run_at = now
            health.last_success_at = now
            health.consecutive_failures = 0
            health.total_runs += 1
            health.is_healthy = True

            # Recalculate success rate
            # For simplicity, we'll use recent history if available
            recent_history = list(self._health_history[plugin_name])
            if recent_history:
                successes = sum(1 for h in recent_history if h.consecutive_failures == 0)
                health.success_rate = successes / len(recent_history)
            else:
                # Use all-time rate (simplified)
                health.success_rate = min(1.0, health.success_rate + 0.01)

            # Store snapshot in history
            self._store_health_snapshot(plugin_name, health)

            logger.info(
                f"Plugin {plugin_name} success recorded. "
                f"Success rate: {health.success_rate:.2%}"
            )

    async def record_failure(self, plugin_name: str, error: str) -> None:
        """
        Record a failed collection.

        This updates the health metrics and increments consecutive failures.

        Args:
            plugin_name: Name of the plugin
            error: Error message
        """
        logger.warning(f"Recording failure for plugin {plugin_name}: {error}")

        async with self._lock:
            # Get or create health data
            if plugin_name not in self._health_data:
                self._health_data[plugin_name] = PluginHealth(
                    name=plugin_name,
                    is_healthy=True,
                    last_run_at=None,
                    last_success_at=None,
                    last_error=None,
                    consecutive_failures=0,
                    total_runs=0,
                    success_rate=1.0,
                )

            health = self._health_data[plugin_name]

            # Update metrics
            now = datetime.utcnow()
            health.last_run_at = now
            health.last_error = error
            health.consecutive_failures += 1
            health.total_runs += 1

            # Check if unhealthy
            health.is_healthy = health.consecutive_failures < self.failure_threshold

            # Recalculate success rate
            recent_history = list(self._health_history[plugin_name])
            if recent_history:
                successes = sum(1 for h in recent_history if h.consecutive_failures == 0)
                health.success_rate = successes / len(recent_history)
            else:
                # Decrease success rate
                health.success_rate = max(0.0, health.success_rate - 0.01)

            # Store snapshot in history
            self._store_health_snapshot(plugin_name, health)

            logger.error(
                f"Plugin {plugin_name} failure recorded. "
                f"Consecutive failures: {health.consecutive_failures}, "
                f"Is healthy: {health.is_healthy}"
            )

    async def get_health_history(
        self, plugin_name: str, hours: int = 24
    ) -> List[PluginHealth]:
        """
        Get health history for a plugin.

        Args:
            plugin_name: Name of the plugin
            hours: Number of hours of history to retrieve

        Returns:
            List of health snapshots
        """
        async with self._lock:
            if plugin_name not in self._health_history:
                return []

            # Filter history by time window
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            history = []

            for health_snapshot in self._health_history[plugin_name]:
                if health_snapshot.last_run_at and health_snapshot.last_run_at >= cutoff_time:
                    history.append(health_snapshot)

            return history

    def _store_health_snapshot(self, plugin_name: str, health: PluginHealth) -> None:
        """
        Store a snapshot of health data in history.

        Args:
            plugin_name: Name of the plugin
            health: Current health status
        """
        # Create a copy of the health data for the snapshot
        snapshot = PluginHealth(
            name=health.name,
            is_healthy=health.is_healthy,
            last_run_at=health.last_run_at,
            last_success_at=health.last_success_at,
            last_error=health.last_error,
            consecutive_failures=health.consecutive_failures,
            total_runs=health.total_runs,
            success_rate=health.success_rate,
        )

        self._health_history[plugin_name].append(snapshot)

    async def get_current_health(self, plugin_name: str) -> Optional[PluginHealth]:
        """
        Get current health status for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Current health status or None if not found
        """
        async with self._lock:
            return self._health_data.get(plugin_name)

    async def reset_health(self, plugin_name: str) -> bool:
        """
        Reset health metrics for a plugin.

        Useful for recovery after fixing issues.

        Args:
            plugin_name: Name of the plugin

        Returns:
            True if reset successfully
        """
        logger.info(f"Resetting health metrics for plugin: {plugin_name}")

        async with self._lock:
            if plugin_name in self._health_data:
                self._health_data[plugin_name] = PluginHealth(
                    name=plugin_name,
                    is_healthy=True,
                    last_run_at=None,
                    last_success_at=None,
                    last_error=None,
                    consecutive_failures=0,
                    total_runs=0,
                    success_rate=1.0,
                )
                # Clear history
                self._health_history[plugin_name].clear()
                return True

            return False

    def get_unhealthy_plugins(self) -> List[str]:
        """
        Get list of unhealthy plugin names.

        Returns:
            List of plugin names that are currently unhealthy
        """
        return [
            name
            for name, health in self._health_data.items()
            if not health.is_healthy
        ]
