"""
Unit tests for content filtering system.
"""

import pytest
from datetime import datetime, timedelta

from trend_agent.ingestion.filters import (
    ContentFilter,
    FilterPipeline,
    FilterResult,
    apply_filters,
)
from trend_agent.schemas import RawItem, SourceType, Metrics


class TestContentFilter:
    """Test cases for content filter."""

    @pytest.fixture
    def sample_item(self):
        """Create sample RawItem for testing."""
        return RawItem(
            source=SourceType.RSS,
            source_id='test-1',
            url='https://example.com/test',
            title='Technology News About AI',
            description='This is a test article about artificial intelligence',
            content='Full content here',
            published_at=datetime.utcnow(),
            metrics=Metrics(),
            language='en',
        )

    def test_keyword_include_filter(self, sample_item):
        """Test keyword inclusion filter."""
        config = {
            'keyword_filters': {
                'include': ['ai', 'technology'],
                'exclude': [],
            }
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is True

    def test_keyword_exclude_filter(self, sample_item):
        """Test keyword exclusion filter."""
        config = {
            'keyword_filters': {
                'include': [],
                'exclude': ['sports', 'entertainment'],
            }
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is True

    def test_keyword_exclude_match(self, sample_item):
        """Test item rejected by exclude keyword."""
        config = {
            'keyword_filters': {
                'include': [],
                'exclude': ['technology'],
            }
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is False
        assert len(result.reasons) > 0

    def test_keyword_include_no_match(self, sample_item):
        """Test item rejected when include keywords don't match."""
        config = {
            'keyword_filters': {
                'include': ['sports', 'entertainment'],
                'exclude': [],
            }
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is False

    def test_language_filter(self, sample_item):
        """Test language filter."""
        config = {
            'language': 'en',
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is True

    def test_language_filter_mismatch(self, sample_item):
        """Test language filter rejection."""
        sample_item.language = 'es'

        config = {
            'language': 'en',
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is False

    def test_length_filter(self, sample_item):
        """Test content length filter."""
        config = {
            'content_filters': {
                'min_length': 10,
                'max_length': 1000,
            }
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is True

    def test_length_filter_too_short(self, sample_item):
        """Test rejection for too short content."""
        sample_item.title = 'Hi'
        sample_item.description = ''
        sample_item.content = ''

        config = {
            'content_filters': {
                'min_length': 100,
            }
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is False

    def test_date_filter_max_age(self, sample_item):
        """Test max age filter."""
        # Item published 1 hour ago
        sample_item.published_at = datetime.utcnow() - timedelta(hours=1)

        config = {
            'content_filters': {
                'max_age_hours': 24,
            }
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is True

    def test_date_filter_too_old(self, sample_item):
        """Test rejection for old content."""
        # Item published 48 hours ago
        sample_item.published_at = datetime.utcnow() - timedelta(hours=48)

        config = {
            'content_filters': {
                'max_age_hours': 24,
            }
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is False

    def test_category_filter(self, sample_item):
        """Test category filter."""
        sample_item.metadata = {'category': 'Technology'}

        config = {
            'category_filters': ['Technology', 'Science'],
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is True

    def test_category_filter_reject(self, sample_item):
        """Test category filter rejection."""
        sample_item.metadata = {'category': 'Sports'}

        config = {
            'category_filters': ['Technology', 'Science'],
        }

        content_filter = ContentFilter(config)
        result = content_filter.filter_item(sample_item)

        assert result.passed is False


class TestFilterPipeline:
    """Test cases for filter pipeline."""

    @pytest.fixture
    def sample_items(self):
        """Create sample items for testing."""
        return [
            RawItem(
                source=SourceType.RSS,
                source_id=f'test-{i}',
                url=f'https://example.com/{i}',
                title=f'Technology Article {i}',
                description='About AI and technology',
                published_at=datetime.utcnow(),
                metrics=Metrics(),
                language='en',
            )
            for i in range(5)
        ]

    def test_filter_pipeline(self, sample_items):
        """Test filtering multiple items."""
        config = {
            'keyword_filters': {
                'include': ['technology'],
                'exclude': [],
            }
        }

        pipeline = FilterPipeline.create_from_config(config)
        filtered_items, stats = pipeline.filter_items(sample_items)

        assert len(filtered_items) == 5
        assert stats['total_items'] == 5
        assert stats['passed'] == 5
        assert stats['rejected'] == 0
        assert stats['pass_rate'] == 1.0

    def test_filter_pipeline_with_rejections(self, sample_items):
        """Test pipeline with some rejected items."""
        # Make some items not match
        sample_items[0].title = 'Sports News'
        sample_items[2].title = 'Entertainment Update'

        config = {
            'keyword_filters': {
                'include': ['technology'],
                'exclude': [],
            }
        }

        pipeline = FilterPipeline.create_from_config(config)
        filtered_items, stats = pipeline.filter_items(sample_items)

        assert len(filtered_items) == 3
        assert stats['total_items'] == 5
        assert stats['passed'] == 3
        assert stats['rejected'] == 2
        assert stats['pass_rate'] == 0.6

    def test_apply_filters_convenience(self, sample_items):
        """Test convenience function."""
        config = {
            'keyword_filters': {
                'include': ['technology'],
                'exclude': [],
            }
        }

        filtered = apply_filters(sample_items, config)

        assert len(filtered) == 5

    def test_apply_filters_empty_config(self, sample_items):
        """Test with empty config (no filtering)."""
        filtered = apply_filters(sample_items, {})

        assert len(filtered) == 5  # All passed


class TestFilterResult:
    """Test cases for FilterResult."""

    def test_filter_result_passed(self):
        """Test passed result."""
        result = FilterResult(True)

        assert result.passed is True
        assert bool(result) is True
        assert len(result.reasons) == 0

    def test_filter_result_failed(self):
        """Test failed result."""
        result = FilterResult(False, ['Reason 1', 'Reason 2'])

        assert result.passed is False
        assert bool(result) is False
        assert len(result.reasons) == 2
