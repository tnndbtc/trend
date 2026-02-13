"""
Dynamic Plugin Loader for database-driven collector sources.

This module provides functionality to:
1. Load collector configurations from database (CrawlerSource model)
2. Dynamically instantiate collector plugins based on source type
3. Register dynamic plugins with PluginRegistry
4. Support hot-reloading when sources are updated
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import httpx

from trend_agent.ingestion.base import CollectorPlugin, PluginRegistry
from trend_agent.schemas import PluginMetadata, RawItem, SourceType, Metrics

logger = logging.getLogger(__name__)


class DynamicCollectorPlugin(CollectorPlugin):
    """
    Dynamically generated collector plugin from database configuration.

    This class wraps database-configured sources and makes them compatible
    with the CollectorPlugin interface.
    """

    def __init__(self, source_config: Dict[str, Any], collector_impl):
        """
        Initialize dynamic collector.

        Args:
            source_config: Configuration from CrawlerSource model
            collector_impl: Implementation function/class for collection
        """
        self.source_config = source_config
        self.collector_impl = collector_impl

        # Build metadata from source config
        self.metadata = PluginMetadata(
            name=source_config['name'],
            version="1.0",
            author=source_config.get('created_by', 'dynamic'),
            description=source_config.get('description', ''),
            source_type=SourceType(source_config['source_type']),
            schedule=source_config.get('schedule', '0 */4 * * *'),
            enabled=source_config.get('enabled', True),
            rate_limit=source_config.get('rate_limit'),
            timeout_seconds=source_config.get('timeout_seconds', 30),
            retry_count=source_config.get('retry_count', 3),
        )

        super().__init__()

    async def collect(self) -> List[RawItem]:
        """
        Collect data using the configured collector implementation.

        Returns:
            List of RawItem objects
        """
        try:
            # Call the collector implementation
            items = await self.collector_impl(self.source_config)
            return items
        except Exception as e:
            logger.error(f"Collection failed for {self.metadata.name}: {e}", exc_info=True)
            raise


class DynamicPluginLoader:
    """
    Factory for creating collector plugins from database configurations.

    Supports multiple source types:
    - RSS feeds
    - API-based sources (Twitter, Reddit, YouTube)
    - Custom plugins (user-provided code)
    """

    def __init__(self):
        """Initialize the dynamic plugin loader."""
        self._loaded_sources: Dict[int, str] = {}  # source_id -> plugin_name
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for making requests."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            )
        return self._http_client

    async def close(self):
        """Close resources."""
        if self._http_client:
            await self._http_client.aclose()

    def _create_rss_collector(self, config: Dict[str, Any]):
        """
        Create RSS feed collector implementation.

        Args:
            config: Source configuration

        Returns:
            Async collector function
        """
        async def collect_rss(cfg: Dict[str, Any]) -> List[RawItem]:
            """Collect items from RSS feed."""
            import feedparser
            from dateutil import parser as date_parser

            url = cfg.get('url')
            if not url:
                logger.error(f"RSS source {cfg['name']} missing URL")
                return []

            try:
                # Fetch RSS feed
                client = await self._get_http_client()

                # Apply custom headers if configured
                headers = cfg.get('custom_headers', {})

                response = await client.get(url, headers=headers)
                response.raise_for_status()

                # Parse RSS feed
                feed = feedparser.parse(response.text)

                items = []
                for entry in feed.entries:
                    # Extract data from RSS entry
                    try:
                        # Parse published date
                        published_at = datetime.utcnow()
                        if hasattr(entry, 'published'):
                            try:
                                published_at = date_parser.parse(entry.published)
                            except Exception:
                                pass

                        # Create RawItem
                        item = RawItem(
                            source=SourceType(cfg['source_type']),
                            source_id=entry.get('id', entry.get('link', '')),
                            url=entry.get('link', ''),
                            title=entry.get('title', ''),
                            description=entry.get('summary', ''),
                            content=entry.get('content', [{}])[0].get('value', '') if hasattr(entry, 'content') else '',
                            author=entry.get('author', ''),
                            published_at=published_at,
                            collected_at=datetime.utcnow(),
                            metrics=Metrics(),
                            metadata={
                                'source_name': cfg['name'],
                                'feed_title': feed.feed.get('title', ''),
                            },
                            language=cfg.get('language', 'en'),
                        )

                        items.append(item)

                    except Exception as e:
                        logger.warning(f"Failed to parse RSS entry: {e}")
                        continue

                logger.info(f"Collected {len(items)} items from RSS: {cfg['name']}")
                return items

            except Exception as e:
                logger.error(f"Failed to fetch RSS feed {url}: {e}", exc_info=True)
                return []

        return collect_rss

    def _create_api_collector(self, config: Dict[str, Any]):
        """
        Create API-based collector implementation.

        Args:
            config: Source configuration

        Returns:
            Async collector function
        """
        source_type = config['source_type']

        if source_type == 'reddit':
            return self._create_reddit_collector(config)
        elif source_type == 'twitter':
            return self._create_twitter_collector(config)
        elif source_type == 'youtube':
            return self._create_youtube_collector(config)
        else:
            # Generic API collector
            return self._create_generic_api_collector(config)

    def _create_reddit_collector(self, config: Dict[str, Any]):
        """Create Reddit API collector."""
        async def collect_reddit(cfg: Dict[str, Any]) -> List[RawItem]:
            """Collect from Reddit API."""
            try:
                client = await self._get_http_client()

                # Reddit URL (could be subreddit or specific endpoint)
                url = cfg.get('url', 'https://www.reddit.com/r/all/hot.json')

                # Apply API key if configured
                headers = cfg.get('custom_headers', {})
                if cfg.get('api_key'):
                    headers['Authorization'] = f"Bearer {cfg['api_key']}"

                response = await client.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                items = []

                # Parse Reddit response
                for post in data.get('data', {}).get('children', []):
                    post_data = post.get('data', {})

                    item = RawItem(
                        source=SourceType.REDDIT,
                        source_id=post_data.get('id', ''),
                        url=f"https://reddit.com{post_data.get('permalink', '')}",
                        title=post_data.get('title', ''),
                        description=post_data.get('selftext', ''),
                        author=post_data.get('author', ''),
                        published_at=datetime.fromtimestamp(post_data.get('created_utc', 0)),
                        collected_at=datetime.utcnow(),
                        metrics=Metrics(
                            upvotes=post_data.get('ups', 0),
                            downvotes=post_data.get('downs', 0),
                            comments=post_data.get('num_comments', 0),
                            score=post_data.get('score', 0),
                        ),
                        metadata={
                            'subreddit': post_data.get('subreddit', ''),
                            'source_name': cfg['name'],
                        },
                        language=cfg.get('language', 'en'),
                    )
                    items.append(item)

                logger.info(f"Collected {len(items)} items from Reddit: {cfg['name']}")
                return items

            except Exception as e:
                logger.error(f"Failed to collect from Reddit: {e}", exc_info=True)
                return []

        return collect_reddit

    def _create_twitter_collector(self, config: Dict[str, Any]):
        """Create Twitter API collector."""
        async def collect_twitter(cfg: Dict[str, Any]) -> List[RawItem]:
            """Collect from Twitter API."""
            logger.warning(f"Twitter collector for {cfg['name']} not yet implemented")
            # TODO: Implement Twitter API v2 integration
            return []

        return collect_twitter

    def _create_youtube_collector(self, config: Dict[str, Any]):
        """Create YouTube API collector."""
        async def collect_youtube(cfg: Dict[str, Any]) -> List[RawItem]:
            """Collect from YouTube API."""
            logger.warning(f"YouTube collector for {cfg['name']} not yet implemented")
            # TODO: Implement YouTube Data API integration
            return []

        return collect_youtube

    def _create_generic_api_collector(self, config: Dict[str, Any]):
        """Create generic API collector."""
        async def collect_generic(cfg: Dict[str, Any]) -> List[RawItem]:
            """Collect from generic API."""
            logger.info(f"Generic API collector for {cfg['name']}: {cfg.get('url')}")
            # TODO: Implement generic API collector
            return []

        return collect_generic

    def _create_custom_collector(self, config: Dict[str, Any]):
        """
        Create custom collector from user-provided code.

        Args:
            config: Source configuration with plugin_code

        Returns:
            Async collector function
        """
        async def collect_custom(cfg: Dict[str, Any]) -> List[RawItem]:
            """Execute custom collector code."""
            plugin_code = cfg.get('plugin_code', '')
            if not plugin_code:
                logger.error(f"Custom source {cfg['name']} has no plugin code")
                return []

            try:
                # Use the sandboxed execution environment
                from trend_agent.ingestion.sandbox import get_sandbox

                sandbox = get_sandbox(
                    timeout_seconds=cfg.get('timeout_seconds', 30),
                    max_memory_mb=100
                )

                logger.info(f"Executing custom plugin code for: {cfg['name']}")

                # Execute plugin code in sandbox
                items = await sandbox.execute_plugin_code(
                    code=plugin_code,
                    collect_function_name='collect',
                    config=cfg
                )

                logger.info(f"Collected {len(items)} items from custom plugin: {cfg['name']}")
                return items

            except Exception as e:
                logger.error(f"Failed to execute custom plugin {cfg['name']}: {e}", exc_info=True)
                return []

        return collect_custom

    def create_collector(self, config: Dict[str, Any]) -> Optional[CollectorPlugin]:
        """
        Create a collector plugin from configuration.

        Args:
            config: Source configuration dictionary

        Returns:
            CollectorPlugin instance or None if creation fails
        """
        source_type = config.get('source_type')

        try:
            # Select appropriate collector implementation based on source type
            if source_type in ['rss', 'google_news', 'bbc', 'reuters', 'ap_news', 'al_jazeera', 'guardian']:
                collector_impl = self._create_rss_collector(config)
            elif source_type in ['reddit', 'twitter', 'youtube']:
                collector_impl = self._create_api_collector(config)
            elif source_type == 'custom':
                collector_impl = self._create_custom_collector(config)
            else:
                logger.error(f"Unknown source type: {source_type}")
                return None

            # Create dynamic plugin
            plugin = DynamicCollectorPlugin(config, collector_impl)

            logger.info(f"Created dynamic collector: {plugin.metadata.name}")
            return plugin

        except Exception as e:
            logger.error(f"Failed to create collector for {config.get('name')}: {e}", exc_info=True)
            return None

    async def load_from_database(self) -> List[CollectorPlugin]:
        """
        Load all enabled sources from database and create collectors.

        Returns:
            List of created collector plugins
        """
        try:
            # Import Django models
            import django
            import os
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
            django.setup()

            from web_interface.trends_viewer.models import CrawlerSource

            # Query enabled sources
            sources = CrawlerSource.objects.filter(enabled=True)

            created_plugins = []

            for source in sources:
                # Convert Django model to dict
                config = {
                    'id': source.id,
                    'name': source.name,
                    'source_type': source.source_type,
                    'description': source.description,
                    'url': source.url,
                    'enabled': source.enabled,
                    'schedule': source.schedule,
                    'collection_interval_hours': source.collection_interval_hours,
                    'rate_limit': source.rate_limit,
                    'timeout_seconds': source.timeout_seconds,
                    'retry_count': source.retry_count,
                    'backoff_multiplier': source.backoff_multiplier,
                    'api_key': source.api_key,  # Will be decrypted by property
                    'oauth_config': source.oauth_config,
                    'custom_headers': source.custom_headers,
                    'category_filters': source.category_filters,
                    'keyword_filters': source.keyword_filters,
                    'language': source.language,
                    'content_filters': source.content_filters,
                    'plugin_code': source.plugin_code,
                    'config_json': source.config_json,
                    'created_by': source.created_by,
                }

                # Create collector
                plugin = self.create_collector(config)
                if plugin:
                    # Register with PluginRegistry
                    try:
                        # Check if already registered
                        existing = PluginRegistry.get_plugin(plugin.metadata.name)
                        if existing:
                            # Unregister old version
                            PluginRegistry.unregister(plugin.metadata.name)

                        # Register new version
                        PluginRegistry._instances[plugin.metadata.name] = plugin
                        PluginRegistry._plugins[plugin.metadata.name] = type(plugin)

                        created_plugins.append(plugin)
                        self._loaded_sources[source.id] = plugin.metadata.name

                        logger.info(f"Registered dynamic plugin: {plugin.metadata.name}")

                    except Exception as e:
                        logger.error(f"Failed to register plugin {plugin.metadata.name}: {e}")

            logger.info(f"Loaded {len(created_plugins)} dynamic collectors from database")
            return created_plugins

        except Exception as e:
            logger.error(f"Failed to load sources from database: {e}", exc_info=True)
            return []

    async def reload_source(self, source_id: int) -> bool:
        """
        Reload a specific source by ID.

        Args:
            source_id: Database ID of the source

        Returns:
            True if reloaded successfully
        """
        try:
            import django
            import os
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
            django.setup()

            from web_interface.trends_viewer.models import CrawlerSource

            # Get source
            source = CrawlerSource.objects.get(id=source_id)

            # Unregister old plugin if exists
            old_plugin_name = self._loaded_sources.get(source_id)
            if old_plugin_name:
                PluginRegistry.unregister(old_plugin_name)
                del self._loaded_sources[source_id]

            # Create new plugin if enabled
            if source.enabled:
                config = {
                    'id': source.id,
                    'name': source.name,
                    'source_type': source.source_type,
                    'description': source.description,
                    'url': source.url,
                    'enabled': source.enabled,
                    'schedule': source.schedule,
                    'rate_limit': source.rate_limit,
                    'timeout_seconds': source.timeout_seconds,
                    'retry_count': source.retry_count,
                    'api_key': source.api_key,
                    'custom_headers': source.custom_headers,
                    'language': source.language,
                    'config_json': source.config_json,
                }

                plugin = self.create_collector(config)
                if plugin:
                    PluginRegistry._instances[plugin.metadata.name] = plugin
                    PluginRegistry._plugins[plugin.metadata.name] = type(plugin)
                    self._loaded_sources[source_id] = plugin.metadata.name

                    logger.info(f"Reloaded source {source_id}: {plugin.metadata.name}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to reload source {source_id}: {e}", exc_info=True)
            return False


# Global instance
_dynamic_loader: Optional[DynamicPluginLoader] = None


def get_dynamic_loader() -> DynamicPluginLoader:
    """Get the global dynamic plugin loader instance."""
    global _dynamic_loader
    if _dynamic_loader is None:
        _dynamic_loader = DynamicPluginLoader()
    return _dynamic_loader
