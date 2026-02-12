"""
Base classes for data collection plugins.

This module defines the abstract interface that all data collectors must implement,
enabling a plugin-based architecture for data ingestion.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type

from trend_agent.schemas import PluginMetadata, RawItem


class CollectorPlugin(ABC):
    """
    Abstract base class for data collection plugins.

    All data collectors must inherit from this class and implement
    the required methods. The plugin registry will automatically
    discover and register subclasses.
    """

    # Plugin metadata (must be overridden by subclasses)
    metadata: PluginMetadata

    def __init__(self):
        """Initialize the collector plugin."""
        if not hasattr(self, "metadata"):
            raise NotImplementedError(
                f"{self.__class__.__name__} must define 'metadata' attribute"
            )

    @abstractmethod
    async def collect(self) -> List[RawItem]:
        """
        Collect data from the source.

        Returns:
            List of raw items collected from the source

        Raises:
            CollectionError: If collection fails
        """
        pass

    async def validate(self, item: RawItem) -> bool:
        """
        Validate a raw item.

        Default implementation accepts all items. Override for
        custom validation logic.

        Args:
            item: The item to validate

        Returns:
            True if item is valid, False otherwise
        """
        return True

    async def on_success(self, items: List[RawItem]) -> None:
        """
        Hook called after successful collection.

        Override to implement custom post-collection logic.

        Args:
            items: The items that were collected
        """
        pass

    async def on_error(self, error: Exception) -> None:
        """
        Hook called when collection fails.

        Override to implement custom error handling.

        Args:
            error: The exception that occurred
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} ({self.metadata.name})>"


class PluginRegistry:
    """
    Registry for auto-discovering and managing collector plugins.

    This class maintains a registry of all available collector plugins
    and provides methods for accessing them.
    """

    _plugins: Dict[str, Type[CollectorPlugin]] = {}
    _instances: Dict[str, CollectorPlugin] = {}

    @classmethod
    def register(cls, plugin_class: Type[CollectorPlugin]) -> None:
        """
        Register a plugin class.

        Args:
            plugin_class: The plugin class to register

        Raises:
            ValueError: If plugin name is already registered
        """
        # Instantiate to get metadata
        try:
            instance = plugin_class()
            name = instance.metadata.name
        except Exception as e:
            raise ValueError(
                f"Failed to register plugin {plugin_class.__name__}: {e}"
            )

        if name in cls._plugins:
            raise ValueError(f"Plugin '{name}' is already registered")

        cls._plugins[name] = plugin_class
        cls._instances[name] = instance

    @classmethod
    def get_plugin(cls, name: str) -> Optional[CollectorPlugin]:
        """
        Get a plugin instance by name.

        Args:
            name: Name of the plugin

        Returns:
            Plugin instance if found, None otherwise
        """
        return cls._instances.get(name)

    @classmethod
    def get_all_plugins(cls) -> List[CollectorPlugin]:
        """
        Get all registered plugin instances.

        Returns:
            List of all plugin instances
        """
        return list(cls._instances.values())

    @classmethod
    def get_enabled_plugins(cls) -> List[CollectorPlugin]:
        """
        Get all enabled plugin instances.

        Returns:
            List of enabled plugin instances
        """
        return [p for p in cls._instances.values() if p.metadata.enabled]

    @classmethod
    def get_plugin_names(cls) -> List[str]:
        """
        Get names of all registered plugins.

        Returns:
            List of plugin names
        """
        return list(cls._plugins.keys())

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Unregister a plugin by name.

        Args:
            name: Name of the plugin to unregister

        Returns:
            True if unregistered, False if not found
        """
        if name in cls._plugins:
            del cls._plugins[name]
            del cls._instances[name]
            return True
        return False

    @classmethod
    def clear(cls) -> None:
        """Clear all registered plugins."""
        cls._plugins.clear()
        cls._instances.clear()


def register_collector(plugin_class: Type[CollectorPlugin]) -> Type[CollectorPlugin]:
    """
    Decorator for auto-registering collector plugins.

    Usage:
        @register_collector
        class MyCollector(CollectorPlugin):
            ...

    Args:
        plugin_class: The plugin class to register

    Returns:
        The plugin class (unchanged)
    """
    PluginRegistry.register(plugin_class)
    return plugin_class


class CollectionError(Exception):
    """Exception raised when data collection fails."""

    pass


class ValidationError(Exception):
    """Exception raised when item validation fails."""

    pass
