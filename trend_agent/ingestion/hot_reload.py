"""
Hot Reload System for dynamic crawler sources.

This module provides automatic hot-reloading of crawler sources when:
1. Database records are created/updated/deleted
2. Source configurations are modified via API
3. Manual reload is triggered

The system uses Django signals and background polling to detect changes.
"""

import logging
import asyncio
from typing import Optional, Set, Callable
from datetime import datetime, timedelta
from threading import Thread

logger = logging.getLogger(__name__)


class HotReloadManager:
    """
    Manages hot-reloading of dynamic crawler sources.

    Monitors database changes and reloads affected plugins without
    requiring application restart.
    """

    def __init__(self, dynamic_loader, check_interval: int = 60):
        """
        Initialize hot reload manager.

        Args:
            dynamic_loader: DynamicPluginLoader instance
            check_interval: Seconds between database checks (default: 60)
        """
        self.dynamic_loader = dynamic_loader
        self.check_interval = check_interval
        self._running = False
        self._reload_callbacks: Set[Callable] = set()
        self._last_check: Optional[datetime] = None
        self._source_timestamps: dict = {}  # source_id -> last_updated

    def register_reload_callback(self, callback: Callable):
        """
        Register a callback to be called when sources are reloaded.

        Args:
            callback: Async function to call after reload
        """
        self._reload_callbacks.add(callback)

    def unregister_reload_callback(self, callback: Callable):
        """Unregister a reload callback."""
        self._reload_callbacks.discard(callback)

    async def check_for_changes(self) -> Set[int]:
        """
        Check database for source changes since last check.

        Returns:
            Set of source IDs that have changed
        """
        try:
            import django
            import os
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
            django.setup()

            from web_interface.trends_viewer.models import CrawlerSource

            changed_sources = set()

            # Get all sources
            sources = CrawlerSource.objects.all()

            for source in sources:
                source_id = source.id
                last_updated = source.updated_at

                # Check if this is a new source or if it's been updated
                if source_id not in self._source_timestamps:
                    # New source
                    changed_sources.add(source_id)
                    self._source_timestamps[source_id] = last_updated
                    logger.info(f"Detected new source: {source.name} (ID: {source_id})")

                elif self._source_timestamps[source_id] < last_updated:
                    # Updated source
                    changed_sources.add(source_id)
                    self._source_timestamps[source_id] = last_updated
                    logger.info(f"Detected updated source: {source.name} (ID: {source_id})")

            # Check for deleted sources
            existing_ids = set(source.id for source in sources)
            deleted_ids = set(self._source_timestamps.keys()) - existing_ids

            for deleted_id in deleted_ids:
                changed_sources.add(deleted_id)
                del self._source_timestamps[deleted_id]
                logger.info(f"Detected deleted source (ID: {deleted_id})")

            return changed_sources

        except Exception as e:
            logger.error(f"Failed to check for source changes: {e}", exc_info=True)
            return set()

    async def reload_changed_sources(self, source_ids: Set[int]) -> dict:
        """
        Reload specific sources by ID.

        Args:
            source_ids: Set of source IDs to reload

        Returns:
            Dictionary with reload results
        """
        results = {
            'reloaded': [],
            'failed': [],
            'deleted': [],
        }

        for source_id in source_ids:
            try:
                # Check if source still exists
                import django
                import os
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
                django.setup()

                from web_interface.trends_viewer.models import CrawlerSource

                try:
                    source = CrawlerSource.objects.get(id=source_id)

                    # Reload source
                    success = await self.dynamic_loader.reload_source(source_id)

                    if success:
                        results['reloaded'].append(source_id)
                        logger.info(f"Successfully reloaded source {source_id}: {source.name}")
                    else:
                        results['failed'].append(source_id)
                        logger.warning(f"Failed to reload source {source_id}")

                except CrawlerSource.DoesNotExist:
                    # Source was deleted - unregister plugin
                    plugin_name = self.dynamic_loader._loaded_sources.get(source_id)
                    if plugin_name:
                        from trend_agent.ingestion.base import PluginRegistry
                        PluginRegistry.unregister(plugin_name)
                        del self.dynamic_loader._loaded_sources[source_id]
                        results['deleted'].append(source_id)
                        logger.info(f"Unregistered deleted source {source_id}")

            except Exception as e:
                logger.error(f"Failed to reload source {source_id}: {e}", exc_info=True)
                results['failed'].append(source_id)

        return results

    async def _run_check_loop(self):
        """Background loop that periodically checks for changes."""
        logger.info(f"Hot reload monitor started (check interval: {self.check_interval}s)")

        while self._running:
            try:
                # Check for changes
                changed_sources = await self.check_for_changes()

                if changed_sources:
                    logger.info(f"Found {len(changed_sources)} changed source(s)")

                    # Reload changed sources
                    results = await self.reload_changed_sources(changed_sources)

                    # Call callbacks
                    for callback in self._reload_callbacks:
                        try:
                            await callback(results)
                        except Exception as e:
                            logger.error(f"Reload callback failed: {e}", exc_info=True)

                    # Log summary
                    logger.info(
                        f"Reload complete - "
                        f"reloaded: {len(results['reloaded'])}, "
                        f"failed: {len(results['failed'])}, "
                        f"deleted: {len(results['deleted'])}"
                    )

                self._last_check = datetime.utcnow()

            except Exception as e:
                logger.error(f"Error in hot reload check loop: {e}", exc_info=True)

            # Sleep until next check
            await asyncio.sleep(self.check_interval)

        logger.info("Hot reload monitor stopped")

    def start(self):
        """Start the hot reload monitoring system."""
        if self._running:
            logger.warning("Hot reload manager is already running")
            return

        self._running = True

        # Start background task
        # Note: This should be called from an async context
        asyncio.create_task(self._run_check_loop())

        logger.info("Hot reload manager started")

    def stop(self):
        """Stop the hot reload monitoring system."""
        if not self._running:
            return

        self._running = False
        logger.info("Hot reload manager stopping...")

    def is_running(self) -> bool:
        """Check if hot reload manager is running."""
        return self._running

    async def trigger_manual_reload(self, source_id: Optional[int] = None) -> dict:
        """
        Manually trigger a reload.

        Args:
            source_id: Specific source to reload, or None for all

        Returns:
            Reload results dictionary
        """
        if source_id is not None:
            # Reload specific source
            logger.info(f"Manual reload triggered for source {source_id}")
            return await self.reload_changed_sources({source_id})
        else:
            # Reload all changed sources
            logger.info("Manual reload triggered for all changed sources")
            changed_sources = await self.check_for_changes()
            return await self.reload_changed_sources(changed_sources)


class DjangoSignalHandler:
    """
    Handles Django model signals for real-time reload triggers.

    This provides immediate reloading when sources are modified via
    Django admin or API, without waiting for the polling interval.
    """

    def __init__(self, hot_reload_manager: HotReloadManager):
        """
        Initialize signal handler.

        Args:
            hot_reload_manager: HotReloadManager instance
        """
        self.hot_reload_manager = hot_reload_manager
        self._signals_connected = False

    def connect_signals(self):
        """Connect Django signals for CrawlerSource model."""
        if self._signals_connected:
            return

        try:
            from django.db.models.signals import post_save, post_delete
            from django.dispatch import receiver
            import django
            import os

            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
            django.setup()

            from web_interface.trends_viewer.models import CrawlerSource

            @receiver(post_save, sender=CrawlerSource)
            def on_source_saved(sender, instance, created, **kwargs):
                """Trigger reload when source is saved."""
                action = "created" if created else "updated"
                logger.info(f"CrawlerSource {action}: {instance.name} (ID: {instance.id})")

                # Trigger async reload
                asyncio.create_task(
                    self.hot_reload_manager.trigger_manual_reload(instance.id)
                )

            @receiver(post_delete, sender=CrawlerSource)
            def on_source_deleted(sender, instance, **kwargs):
                """Trigger cleanup when source is deleted."""
                logger.info(f"CrawlerSource deleted: {instance.name} (ID: {instance.id})")

                # Trigger async reload
                asyncio.create_task(
                    self.hot_reload_manager.trigger_manual_reload(instance.id)
                )

            self._signals_connected = True
            logger.info("Django signals connected for hot reload")

        except Exception as e:
            logger.error(f"Failed to connect Django signals: {e}", exc_info=True)

    def disconnect_signals(self):
        """Disconnect Django signals."""
        # Django signals are global, so we can't really disconnect
        # Just mark as disconnected
        self._signals_connected = False


# Global instances
_hot_reload_manager: Optional[HotReloadManager] = None
_signal_handler: Optional[DjangoSignalHandler] = None


def get_hot_reload_manager(dynamic_loader) -> HotReloadManager:
    """
    Get the global hot reload manager instance.

    Args:
        dynamic_loader: DynamicPluginLoader instance

    Returns:
        HotReloadManager instance
    """
    global _hot_reload_manager
    if _hot_reload_manager is None:
        _hot_reload_manager = HotReloadManager(dynamic_loader)
    return _hot_reload_manager


def get_signal_handler(hot_reload_manager: HotReloadManager) -> DjangoSignalHandler:
    """
    Get the global signal handler instance.

    Args:
        hot_reload_manager: HotReloadManager instance

    Returns:
        DjangoSignalHandler instance
    """
    global _signal_handler
    if _signal_handler is None:
        _signal_handler = DjangoSignalHandler(hot_reload_manager)
    return _signal_handler


async def initialize_hot_reload(dynamic_loader, enable_signals: bool = True) -> HotReloadManager:
    """
    Initialize and start the hot reload system.

    Args:
        dynamic_loader: DynamicPluginLoader instance
        enable_signals: Whether to connect Django signals

    Returns:
        Running HotReloadManager instance
    """
    # Get manager
    manager = get_hot_reload_manager(dynamic_loader)

    # Connect signals if requested
    if enable_signals:
        signal_handler = get_signal_handler(manager)
        signal_handler.connect_signals()

    # Start manager
    manager.start()

    logger.info("Hot reload system initialized")
    return manager
