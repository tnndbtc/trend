"""
Ingestion layer interface contracts.

This module defines Protocol classes for plugin management, scheduling,
and health monitoring.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Protocol

from trend_agent.ingestion.base import CollectorPlugin
from trend_agent.schemas import PluginHealth, RawItem


class PluginManager(Protocol):
    """Interface for managing collector plugins."""

    async def load_plugins(self) -> List[CollectorPlugin]:
        """
        Discover and load all available plugins.

        Returns:
            List of loaded plugins
        """
        ...

    async def reload_plugin(self, name: str) -> bool:
        """
        Reload a specific plugin.

        Args:
            name: Name of the plugin to reload

        Returns:
            True if reloaded successfully
        """
        ...

    async def enable_plugin(self, name: str) -> bool:
        """
        Enable a plugin.

        Args:
            name: Name of the plugin to enable

        Returns:
            True if enabled successfully
        """
        ...

    async def disable_plugin(self, name: str) -> bool:
        """
        Disable a plugin.

        Args:
            name: Name of the plugin to disable

        Returns:
            True if disabled successfully
        """
        ...

    async def get_plugin_status(self, name: str) -> Optional[Dict]:
        """
        Get status information for a plugin.

        Args:
            name: Name of the plugin

        Returns:
            Status dictionary if found, None otherwise
        """
        ...

    async def get_all_plugin_status(self) -> Dict[str, Dict]:
        """
        Get status information for all plugins.

        Returns:
            Dictionary mapping plugin names to status
        """
        ...


class HealthChecker(Protocol):
    """Interface for monitoring plugin health."""

    async def check_health(self, plugin: CollectorPlugin) -> PluginHealth:
        """
        Check the health of a plugin.

        Args:
            plugin: The plugin to check

        Returns:
            Health status of the plugin
        """
        ...

    async def check_all_health(self) -> Dict[str, PluginHealth]:
        """
        Check health of all plugins.

        Returns:
            Dictionary mapping plugin names to health status
        """
        ...

    async def record_success(self, plugin_name: str) -> None:
        """
        Record a successful collection.

        Args:
            plugin_name: Name of the plugin
        """
        ...

    async def record_failure(self, plugin_name: str, error: str) -> None:
        """
        Record a failed collection.

        Args:
            plugin_name: Name of the plugin
            error: Error message
        """
        ...

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
        ...


class RateLimiter(Protocol):
    """Interface for rate limiting plugin requests."""

    async def check_rate_limit(self, plugin_name: str) -> bool:
        """
        Check if plugin can make a request.

        Args:
            plugin_name: Name of the plugin

        Returns:
            True if request is allowed, False if rate limited
        """
        ...

    async def record_request(self, plugin_name: str) -> None:
        """
        Record a request for rate limiting.

        Args:
            plugin_name: Name of the plugin
        """
        ...

    async def get_remaining_quota(self, plugin_name: str) -> int:
        """
        Get remaining request quota for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Number of requests remaining in current window
        """
        ...

    async def reset_quota(self, plugin_name: str) -> None:
        """
        Reset quota for a plugin.

        Args:
            plugin_name: Name of the plugin
        """
        ...


class Scheduler(Protocol):
    """Interface for scheduling plugin execution."""

    async def schedule_plugin(
        self, plugin: CollectorPlugin, cron_expression: str
    ) -> str:
        """
        Schedule a plugin for periodic execution.

        Args:
            plugin: The plugin to schedule
            cron_expression: Cron expression for scheduling

        Returns:
            Job ID for the scheduled task
        """
        ...

    async def unschedule_plugin(self, plugin_name: str) -> bool:
        """
        Remove a plugin from the schedule.

        Args:
            plugin_name: Name of the plugin to unschedule

        Returns:
            True if unscheduled successfully
        """
        ...

    async def trigger_now(self, plugin_name: str) -> str:
        """
        Trigger immediate execution of a plugin.

        Args:
            plugin_name: Name of the plugin to execute

        Returns:
            Task ID for the execution
        """
        ...

    async def get_next_run(self, plugin_name: str) -> Optional[datetime]:
        """
        Get next scheduled run time for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Next run datetime if scheduled, None otherwise
        """
        ...

    async def get_schedule(self) -> Dict[str, datetime]:
        """
        Get schedule for all plugins.

        Returns:
            Dictionary mapping plugin names to next run times
        """
        ...


# ============================================================================
# Abstract Base Classes
# ============================================================================


class BasePluginManager(ABC):
    """Abstract base class for plugin manager implementations."""

    @abstractmethod
    async def load_plugins(self) -> List[CollectorPlugin]:
        pass

    @abstractmethod
    async def reload_plugin(self, name: str) -> bool:
        pass

    @abstractmethod
    async def enable_plugin(self, name: str) -> bool:
        pass

    @abstractmethod
    async def disable_plugin(self, name: str) -> bool:
        pass

    @abstractmethod
    async def get_plugin_status(self, name: str) -> Optional[Dict]:
        pass

    @abstractmethod
    async def get_all_plugin_status(self) -> Dict[str, Dict]:
        pass


class BaseHealthChecker(ABC):
    """Abstract base class for health checker implementations."""

    @abstractmethod
    async def check_health(self, plugin: CollectorPlugin) -> PluginHealth:
        pass

    @abstractmethod
    async def check_all_health(self) -> Dict[str, PluginHealth]:
        pass

    @abstractmethod
    async def record_success(self, plugin_name: str) -> None:
        pass

    @abstractmethod
    async def record_failure(self, plugin_name: str, error: str) -> None:
        pass

    @abstractmethod
    async def get_health_history(
        self, plugin_name: str, hours: int = 24
    ) -> List[PluginHealth]:
        pass


class BaseRateLimiter(ABC):
    """Abstract base class for rate limiter implementations."""

    @abstractmethod
    async def check_rate_limit(self, plugin_name: str) -> bool:
        pass

    @abstractmethod
    async def record_request(self, plugin_name: str) -> None:
        pass

    @abstractmethod
    async def get_remaining_quota(self, plugin_name: str) -> int:
        pass

    @abstractmethod
    async def reset_quota(self, plugin_name: str) -> None:
        pass


class BaseScheduler(ABC):
    """Abstract base class for scheduler implementations."""

    @abstractmethod
    async def schedule_plugin(
        self, plugin: CollectorPlugin, cron_expression: str
    ) -> str:
        pass

    @abstractmethod
    async def unschedule_plugin(self, plugin_name: str) -> bool:
        pass

    @abstractmethod
    async def trigger_now(self, plugin_name: str) -> str:
        pass

    @abstractmethod
    async def get_next_run(self, plugin_name: str) -> Optional[datetime]:
        pass

    @abstractmethod
    async def get_schedule(self) -> Dict[str, datetime]:
        pass
