"""
Plugin Manager implementation for collector plugins.

This module provides the concrete implementation of the PluginManager interface,
handling plugin discovery, lifecycle management, and status tracking.
"""

import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Optional

from trend_agent.ingestion.base import CollectorPlugin, PluginRegistry
from trend_agent.ingestion.interfaces import BasePluginManager

logger = logging.getLogger(__name__)


class DefaultPluginManager(BasePluginManager):
    """
    Default implementation of the PluginManager interface.

    This class manages the lifecycle of collector plugins, including:
    - Auto-discovery of plugins
    - Loading and reloading
    - Enabling/disabling plugins
    - Status tracking

    Attributes:
        plugin_dir: Directory containing plugin modules
        auto_discover: Whether to automatically discover plugins on init
    """

    def __init__(
        self,
        plugin_dir: Optional[str] = None,
        auto_discover: bool = True
    ):
        """
        Initialize the plugin manager.

        Args:
            plugin_dir: Path to directory containing plugin modules.
                       Defaults to trend_agent/collectors
            auto_discover: If True, automatically discover plugins on init
        """
        self.plugin_dir = plugin_dir or self._get_default_plugin_dir()
        self._status_cache: Dict[str, Dict] = {}

        if auto_discover:
            # Note: We can't call async methods in __init__, so we just prepare
            # The actual loading should be done via load_plugins()
            logger.info(f"Plugin manager initialized. Plugin directory: {self.plugin_dir}")

    def _get_default_plugin_dir(self) -> str:
        """Get the default plugin directory path."""
        # Assuming plugins are in trend_agent/collectors/
        current_file = Path(__file__)
        collectors_dir = current_file.parent.parent / "collectors"
        return str(collectors_dir)

    async def load_plugins(self) -> List[CollectorPlugin]:
        """
        Discover and load all available plugins.

        This method scans the plugin directory for Python modules,
        imports them, and registers any CollectorPlugin subclasses.

        Returns:
            List of loaded plugins
        """
        logger.info(f"Loading plugins from {self.plugin_dir}")

        plugin_dir = Path(self.plugin_dir)
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory {self.plugin_dir} does not exist")
            return []

        # Clear existing registry to avoid duplicates during reload
        # Note: In production, you might want to be more careful about this

        loaded_plugins = []

        # Discover all .py files in the plugin directory
        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                # Skip __init__.py and private modules
                continue

            try:
                # Import the module
                module_name = f"trend_agent.collectors.{plugin_file.stem}"
                module = importlib.import_module(module_name)

                # Find all CollectorPlugin subclasses in the module
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, CollectorPlugin)
                        and obj is not CollectorPlugin
                    ):
                        # The plugin should already be registered via @register_collector
                        # or we can register it here
                        plugin_instance = PluginRegistry.get_plugin(obj.metadata.name)
                        if plugin_instance:
                            loaded_plugins.append(plugin_instance)
                            logger.info(f"Loaded plugin: {obj.metadata.name}")

            except Exception as e:
                logger.error(f"Failed to load plugin from {plugin_file}: {e}", exc_info=True)

        logger.info(f"Successfully loaded {len(loaded_plugins)} plugins")
        return loaded_plugins

    async def reload_plugin(self, name: str) -> bool:
        """
        Reload a specific plugin.

        This is useful for hot-reloading plugins during development
        or when configuration changes.

        Args:
            name: Name of the plugin to reload

        Returns:
            True if reloaded successfully
        """
        logger.info(f"Reloading plugin: {name}")

        try:
            plugin = PluginRegistry.get_plugin(name)
            if not plugin:
                logger.warning(f"Plugin {name} not found in registry")
                return False

            # Get the module name from the plugin class
            module_name = plugin.__class__.__module__

            # Reload the module
            module = importlib.import_module(module_name)
            importlib.reload(module)

            # Unregister old instance
            PluginRegistry.unregister(name)

            # The module reload should trigger re-registration via decorators
            # Verify the plugin is re-registered
            new_plugin = PluginRegistry.get_plugin(name)
            if new_plugin:
                logger.info(f"Successfully reloaded plugin: {name}")
                return True
            else:
                logger.error(f"Plugin {name} not re-registered after reload")
                return False

        except Exception as e:
            logger.error(f"Failed to reload plugin {name}: {e}", exc_info=True)
            return False

    async def enable_plugin(self, name: str) -> bool:
        """
        Enable a plugin.

        Args:
            name: Name of the plugin to enable

        Returns:
            True if enabled successfully
        """
        logger.info(f"Enabling plugin: {name}")

        plugin = PluginRegistry.get_plugin(name)
        if not plugin:
            logger.warning(f"Plugin {name} not found")
            return False

        try:
            # Since PluginMetadata is frozen, we need to create a new instance
            # For now, we'll track enabled state in status cache
            # In production, you might want to persist this in a database
            self._status_cache[name] = {
                **self._status_cache.get(name, {}),
                "enabled": True
            }
            logger.info(f"Plugin {name} enabled")
            return True

        except Exception as e:
            logger.error(f"Failed to enable plugin {name}: {e}", exc_info=True)
            return False

    async def disable_plugin(self, name: str) -> bool:
        """
        Disable a plugin.

        Args:
            name: Name of the plugin to disable

        Returns:
            True if disabled successfully
        """
        logger.info(f"Disabling plugin: {name}")

        plugin = PluginRegistry.get_plugin(name)
        if not plugin:
            logger.warning(f"Plugin {name} not found")
            return False

        try:
            self._status_cache[name] = {
                **self._status_cache.get(name, {}),
                "enabled": False
            }
            logger.info(f"Plugin {name} disabled")
            return True

        except Exception as e:
            logger.error(f"Failed to disable plugin {name}: {e}", exc_info=True)
            return False

    async def get_plugin_status(self, name: str) -> Optional[Dict]:
        """
        Get status information for a plugin.

        Args:
            name: Name of the plugin

        Returns:
            Status dictionary if found, None otherwise
        """
        plugin = PluginRegistry.get_plugin(name)
        if not plugin:
            return None

        # Build status from metadata and cache
        cached_status = self._status_cache.get(name, {})

        return {
            "name": plugin.metadata.name,
            "version": plugin.metadata.version,
            "author": plugin.metadata.author,
            "description": plugin.metadata.description,
            "source_type": plugin.metadata.source_type,
            "schedule": plugin.metadata.schedule,
            "enabled": cached_status.get("enabled", plugin.metadata.enabled),
            "rate_limit": plugin.metadata.rate_limit,
            "timeout_seconds": plugin.metadata.timeout_seconds,
            "retry_count": plugin.metadata.retry_count,
        }

    async def get_all_plugin_status(self) -> Dict[str, Dict]:
        """
        Get status information for all plugins.

        Returns:
            Dictionary mapping plugin names to status
        """
        all_status = {}

        for plugin in PluginRegistry.get_all_plugins():
            status = await self.get_plugin_status(plugin.metadata.name)
            if status:
                all_status[plugin.metadata.name] = status

        return all_status

    def get_plugin(self, name: str) -> Optional[CollectorPlugin]:
        """
        Get a plugin instance by name.

        Args:
            name: Name of the plugin

        Returns:
            Plugin instance if found, None otherwise
        """
        return PluginRegistry.get_plugin(name)

    def get_enabled_plugins(self) -> List[CollectorPlugin]:
        """
        Get all enabled plugins.

        Returns:
            List of enabled plugin instances
        """
        enabled = []
        for plugin in PluginRegistry.get_all_plugins():
            status = self._status_cache.get(plugin.metadata.name, {})
            is_enabled = status.get("enabled", plugin.metadata.enabled)
            if is_enabled:
                enabled.append(plugin)
        return enabled
