"""
Tests for session-based user preferences (Phase 1).

Tests the PreferenceManager, filtered views, and AJAX endpoints.
"""

from datetime import datetime, timedelta
from django.test import TestCase, RequestFactory, Client
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse

from .preferences import PreferenceManager, get_available_sources, get_available_languages
from .models import CollectedTopic, TrendCluster, CollectionRun


class PreferenceManagerTestCase(TestCase):
    """Test PreferenceManager functionality."""

    def setUp(self):
        """Set up test request with session."""
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

        # Add session to request
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(self.request)
        self.request.session.save()

    def test_get_default_preferences(self):
        """Test getting default preferences."""
        manager = PreferenceManager(self.request)
        prefs = manager.get_preferences()

        self.assertEqual(prefs['time_range'], '7d')
        self.assertEqual(prefs['sources'], [])
        self.assertEqual(prefs['languages'], [])
        self.assertEqual(prefs['min_upvotes'], 0)

    def test_update_preferences(self):
        """Test updating preferences."""
        manager = PreferenceManager(self.request)

        updates = {
            'sources': ['reddit', 'hackernews'],
            'languages': ['en'],
            'min_upvotes': 10,
        }
        manager.update_preferences(updates)

        prefs = manager.get_preferences()
        self.assertEqual(prefs['sources'], ['reddit', 'hackernews'])
        self.assertEqual(prefs['languages'], ['en'])
        self.assertEqual(prefs['min_upvotes'], 10)

    def test_reset_preferences(self):
        """Test resetting preferences to defaults."""
        manager = PreferenceManager(self.request)

        # Update preferences
        manager.update_preferences({'sources': ['reddit'], 'min_upvotes': 50})

        # Reset
        manager.reset_preferences()
        prefs = manager.get_preferences()

        self.assertEqual(prefs['sources'], [])
        self.assertEqual(prefs['min_upvotes'], 0)

    def test_get_filter_params(self):
        """Test converting preferences to ORM filter parameters."""
        manager = PreferenceManager(self.request)

        manager.update_preferences({
            'sources': ['reddit'],
            'languages': ['en'],
            'min_upvotes': 10,
            'time_range': '24h',
        })

        filters = manager.get_filter_params()

        self.assertEqual(filters['source__in'], ['reddit'])
        self.assertEqual(filters['language__in'], ['en'])
        self.assertEqual(filters['upvotes__gte'], 10)
        self.assertIn('timestamp__gte', filters)

    def test_time_range_filtering(self):
        """Test time range filter generation."""
        manager = PreferenceManager(self.request)

        # Test predefined ranges
        for range_val in ['24h', '7d', '30d']:
            manager.update_preferences({'time_range': range_val})
            filters = manager.get_filter_params()
            self.assertIn('timestamp__gte', filters)

        # Test 'all' range
        manager.update_preferences({'time_range': 'all'})
        filters = manager.get_filter_params()
        self.assertNotIn('timestamp__gte', filters)

    def test_custom_date_range(self):
        """Test custom date range filtering."""
        manager = PreferenceManager(self.request)

        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()

        manager.update_preferences({
            'time_range': 'custom',
            'custom_start_date': start_date,
            'custom_end_date': end_date,
        })

        filters = manager.get_filter_params()
        self.assertIn('timestamp__gte', filters)
        self.assertIn('timestamp__lte', filters)

    def test_sort_params(self):
        """Test sorting parameters."""
        manager = PreferenceManager(self.request)

        # Test descending (default)
        manager.update_preferences({'sort_by': 'upvotes', 'sort_order': 'desc'})
        sort_field, _ = manager.get_sort_params()
        self.assertEqual(sort_field, '-upvotes')

        # Test ascending
        manager.update_preferences({'sort_by': 'timestamp', 'sort_order': 'asc'})
        sort_field, _ = manager.get_sort_params()
        self.assertEqual(sort_field, 'timestamp')


class FilteredViewsTestCase(TestCase):
    """Test filtered views with preferences."""

    def setUp(self):
        """Create test data."""
        self.client = Client()

        # Create collection run
        self.run = CollectionRun.objects.create(
            status='completed',
            topics_count=10,
            clusters_count=2,
        )

        # Create test topics
        now = datetime.now()
        self.topics = []

        for i in range(10):
            topic = CollectedTopic.objects.create(
                collection_run=self.run,
                title=f'Test Topic {i}',
                description=f'Description for topic {i}',
                source='reddit' if i % 2 == 0 else 'hackernews',
                url=f'http://example.com/{i}',
                timestamp=now - timedelta(days=i),
                language='en',
                upvotes=i * 10,
                comments=i * 5,
                score=i * 15,
            )
            self.topics.append(topic)

        # Create trend cluster
        self.cluster = TrendCluster.objects.create(
            collection_run=self.run,
            rank=1,
            title='Test Trend',
            summary='Test trend summary',
            score=100.0,
        )

        # Add some topics to cluster
        for topic in self.topics[:5]:
            topic.cluster = self.cluster
            topic.save()

    def test_filtered_topics_view_loads(self):
        """Test filtered topics view loads successfully."""
        response = self.client.get(reverse('trends_viewer:filtered_topics'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your Personalized Topic Feed')

    def test_filtered_trends_view_loads(self):
        """Test filtered trends view loads successfully."""
        response = self.client.get(reverse('trends_viewer:filtered_trends'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your Personalized Trend Feed')

    def test_source_filtering(self):
        """Test filtering by source."""
        response = self.client.get(
            reverse('trends_viewer:filtered_topics'),
            {'apply_filters': '1', 'sources': 'reddit'}
        )
        self.assertEqual(response.status_code, 200)

        # Check that only Reddit topics are shown
        topics = response.context['topics']
        for topic in topics:
            self.assertEqual(topic.source, 'reddit')

    def test_language_filtering(self):
        """Test filtering by language."""
        # Add a Chinese topic
        CollectedTopic.objects.create(
            collection_run=self.run,
            title='中文标题',
            description='中文描述',
            source='reddit',
            url='http://example.com/zh',
            timestamp=datetime.now(),
            language='zh-Hans',
            upvotes=100,
        )

        response = self.client.get(
            reverse('trends_viewer:filtered_topics'),
            {'apply_filters': '1', 'languages': 'zh-Hans'}
        )

        topics = response.context['topics']
        for topic in topics:
            self.assertEqual(topic.language, 'zh-Hans')

    def test_min_upvotes_filtering(self):
        """Test filtering by minimum upvotes."""
        response = self.client.get(
            reverse('trends_viewer:filtered_topics'),
            {'apply_filters': '1', 'min_upvotes': '50'}
        )

        topics = response.context['topics']
        for topic in topics:
            self.assertGreaterEqual(topic.upvotes, 50)

    def test_time_range_filtering(self):
        """Test filtering by time range."""
        response = self.client.get(
            reverse('trends_viewer:filtered_topics'),
            {'apply_filters': '1', 'time_range': '24h'}
        )

        topics = response.context['topics']
        yesterday = datetime.now() - timedelta(hours=24)

        for topic in topics:
            self.assertGreaterEqual(topic.timestamp, yesterday)

    def test_pagination(self):
        """Test pagination works correctly."""
        # Create more topics to trigger pagination
        for i in range(60):
            CollectedTopic.objects.create(
                collection_run=self.run,
                title=f'Pagination Test {i}',
                source='reddit',
                url=f'http://example.com/page/{i}',
                timestamp=datetime.now(),
                language='en',
            )

        response = self.client.get(reverse('trends_viewer:filtered_topics'))
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['topics']), 50)  # Default page size


class AjaxEndpointsTestCase(TestCase):
    """Test AJAX endpoints for preference management."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_reset_preferences_ajax(self):
        """Test AJAX reset endpoint."""
        response = self.client.post(
            reverse('trends_viewer:reset_preferences_ajax'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('preferences', data)

    def test_filter_preview_ajax(self):
        """Test AJAX filter preview endpoint."""
        # Create test topic
        run = CollectionRun.objects.create(status='completed')
        CollectedTopic.objects.create(
            collection_run=run,
            title='Test',
            source='reddit',
            url='http://example.com',
            timestamp=datetime.now(),
            language='en',
        )

        response = self.client.get(
            reverse('trends_viewer:filter_preview'),
            {'sources': 'reddit'}
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('total_count', data)
        self.assertIn('source_breakdown', data)


class UtilityFunctionsTestCase(TestCase):
    """Test utility functions."""

    def setUp(self):
        """Create test data."""
        run = CollectionRun.objects.create(status='completed')
        CollectedTopic.objects.create(
            collection_run=run,
            title='Test',
            source='reddit',
            url='http://example.com',
            timestamp=datetime.now(),
            language='en',
        )

    def test_get_available_sources(self):
        """Test getting available sources from database."""
        sources = get_available_sources()
        self.assertIn('reddit', sources)
        self.assertIsInstance(sources, list)

    def test_get_available_languages(self):
        """Test getting available languages from database."""
        languages = get_available_languages()
        self.assertIsInstance(languages, list)
        self.assertTrue(len(languages) > 0)
        self.assertIn('code', languages[0])
        self.assertIn('name', languages[0])
