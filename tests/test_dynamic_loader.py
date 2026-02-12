"""
Unit tests for dynamic plugin loader.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from trend_agent.ingestion.dynamic_loader import (
    DynamicPluginLoader,
    DynamicCollectorPlugin,
)
from trend_agent.schemas import RawItem, SourceType, Metrics


class TestDynamicPluginLoader:
    """Test cases for dynamic plugin loader."""

    @pytest.fixture
    def loader(self):
        """Create loader instance."""
        return DynamicPluginLoader()

    @pytest.fixture
    def rss_config(self):
        """Sample RSS source configuration."""
        return {
            'id': 1,
            'name': 'Test RSS Feed',
            'source_type': 'rss',
            'description': 'Test RSS feed',
            'url': 'https://example.com/feed.rss',
            'enabled': True,
            'schedule': '0 */2 * * *',
            'rate_limit': 60,
            'timeout_seconds': 30,
            'retry_count': 3,
            'language': 'en',
            'custom_headers': {},
            'config_json': {},
        }

    def test_create_rss_collector(self, loader, rss_config):
        """Test creating RSS collector."""
        collector_impl = loader._create_rss_collector(rss_config)
        assert callable(collector_impl)

    def test_create_collector(self, loader, rss_config):
        """Test creating collector plugin."""
        plugin = loader.create_collector(rss_config)

        assert plugin is not None
        assert isinstance(plugin, DynamicCollectorPlugin)
        assert plugin.metadata.name == 'Test RSS Feed'
        assert plugin.metadata.source_type == SourceType.RSS

    def test_create_collector_invalid_type(self, loader):
        """Test creating collector with invalid source type."""
        config = {
            'name': 'Invalid',
            'source_type': 'invalid_type',
        }

        plugin = loader.create_collector(config)
        assert plugin is None

    @pytest.mark.asyncio
    async def test_collect_rss(self, loader, rss_config):
        """Test RSS collection with mocked response."""
        with patch.object(loader, '_get_http_client') as mock_get_client:
            # Mock HTTP client
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.text = '''<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <item>
            <title>Test Item</title>
            <link>https://example.com/item1</link>
            <description>Test description</description>
            <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
        </item>
    </channel>
</rss>'''
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            # Create and run collector
            collector_impl = loader._create_rss_collector(rss_config)
            items = await collector_impl(rss_config)

            assert len(items) > 0
            assert all(isinstance(item, RawItem) for item in items)

    def test_create_plugin_metadata(self, loader, rss_config):
        """Test plugin metadata creation."""
        plugin = loader.create_collector(rss_config)

        assert plugin.metadata.name == rss_config['name']
        assert plugin.metadata.source_type.value == rss_config['source_type']
        assert plugin.metadata.schedule == rss_config['schedule']
        assert plugin.metadata.rate_limit == rss_config['rate_limit']


class TestDynamicCollectorPlugin:
    """Test cases for dynamic collector plugin."""

    @pytest.fixture
    def mock_collector(self):
        """Create mock collector implementation."""
        async def collect(config):
            return [
                RawItem(
                    source=SourceType.RSS,
                    source_id='test-1',
                    url='https://example.com/1',
                    title='Test Item',
                    description='Test description',
                    published_at=datetime.utcnow(),
                    metrics=Metrics(),
                )
            ]
        return collect

    @pytest.fixture
    def plugin(self, mock_collector):
        """Create plugin instance."""
        config = {
            'name': 'Test Plugin',
            'source_type': 'rss',
            'description': 'Test plugin',
            'schedule': '0 * * * *',
            'enabled': True,
            'rate_limit': 60,
            'timeout_seconds': 30,
            'retry_count': 3,
        }
        return DynamicCollectorPlugin(config, mock_collector)

    @pytest.mark.asyncio
    async def test_collect(self, plugin):
        """Test plugin collection."""
        items = await plugin.collect()

        assert len(items) == 1
        assert items[0].title == 'Test Item'
        assert items[0].source == SourceType.RSS

    def test_plugin_metadata(self, plugin):
        """Test plugin metadata."""
        assert plugin.metadata.name == 'Test Plugin'
        assert plugin.metadata.source_type == SourceType.RSS
        assert plugin.metadata.enabled is True
