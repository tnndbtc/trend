"""
Session-based user preference management.

This module handles storing and retrieving user preferences from Django sessions,
allowing users to filter articles by their interests without requiring authentication.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.http import HttpRequest


class PreferenceManager:
    """
    Manages user preferences stored in Django session.

    Preferences include:
    - Sources (reddit, hackernews, etc.)
    - Languages (en, zh, ja, etc.)
    - Categories (technology, science, etc.)
    - Time ranges (last 24h, 7d, 30d, custom)
    - Keywords (include/exclude)
    - Minimum engagement metrics (upvotes, comments, score)
    """

    SESSION_KEY = 'user_preferences'

    DEFAULT_PREFERENCES = {
        'sources': [],  # Empty list means all sources
        'languages': [],  # Empty list means all languages
        'categories': [],  # Empty list means all categories
        'time_range': '7d',  # Options: '24h', '7d', '30d', 'all', 'custom'
        'custom_start_date': None,
        'custom_end_date': None,
        'keywords_include': [],
        'keywords_exclude': [],
        'min_upvotes': 0,
        'min_comments': 0,
        'min_score': 0,
        'sort_by': 'timestamp',  # Options: 'timestamp', 'upvotes', 'comments', 'score'
        'sort_order': 'desc',  # Options: 'asc', 'desc'
    }

    def __init__(self, request: HttpRequest):
        """
        Initialize preference manager with Django request.

        Args:
            request: Django HttpRequest object
        """
        self.request = request
        self.session = request.session

    def get_preferences(self) -> Dict[str, Any]:
        """
        Get current user preferences from session.

        Returns:
            Dictionary of preferences
        """
        if self.SESSION_KEY not in self.session:
            self.session[self.SESSION_KEY] = self.DEFAULT_PREFERENCES.copy()
            self.session.modified = True

        return self.session[self.SESSION_KEY]

    def update_preferences(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user preferences in session.

        Args:
            updates: Dictionary of preference updates

        Returns:
            Updated preferences dictionary
        """
        current = self.get_preferences()
        current.update(updates)
        self.session[self.SESSION_KEY] = current
        self.session.modified = True
        return current

    def reset_preferences(self) -> Dict[str, Any]:
        """
        Reset preferences to defaults.

        Returns:
            Default preferences dictionary
        """
        self.session[self.SESSION_KEY] = self.DEFAULT_PREFERENCES.copy()
        self.session.modified = True
        return self.session[self.SESSION_KEY]

    def get_filter_params(self) -> Dict[str, Any]:
        """
        Convert preferences to database filter parameters.

        Returns:
            Dictionary suitable for Django ORM filtering
        """
        prefs = self.get_preferences()
        filters = {}

        # Source filtering
        if prefs.get('sources'):
            filters['source__in'] = prefs['sources']

        # Language filtering
        if prefs.get('languages'):
            filters['language__in'] = prefs['languages']

        # Category filtering (if categories are set)
        # Note: CollectedTopic doesn't have category field yet, will be added

        # Time range filtering
        time_filter = self._get_time_filter(prefs)
        if time_filter:
            filters.update(time_filter)

        # Minimum metrics
        if prefs.get('min_upvotes', 0) > 0:
            filters['upvotes__gte'] = prefs['min_upvotes']
        if prefs.get('min_comments', 0) > 0:
            filters['comments__gte'] = prefs['min_comments']
        if prefs.get('min_score', 0) > 0:
            filters['score__gte'] = prefs['min_score']

        return filters

    def _get_time_filter(self, prefs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate time-based filter from preferences.

        Args:
            prefs: User preferences

        Returns:
            Time filter dictionary or None
        """
        time_range = prefs.get('time_range', '7d')

        if time_range == 'all':
            return None

        if time_range == 'custom':
            filters = {}
            if prefs.get('custom_start_date'):
                try:
                    start_date = datetime.fromisoformat(prefs['custom_start_date'])
                    filters['timestamp__gte'] = start_date
                except (ValueError, TypeError):
                    pass
            if prefs.get('custom_end_date'):
                try:
                    end_date = datetime.fromisoformat(prefs['custom_end_date'])
                    filters['timestamp__lte'] = end_date
                except (ValueError, TypeError):
                    pass
            return filters if filters else None

        # Predefined time ranges
        now = datetime.now()
        time_deltas = {
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30),
        }

        if time_range in time_deltas:
            start_time = now - time_deltas[time_range]
            return {'timestamp__gte': start_time}

        return None

    def filter_by_keywords(self, queryset, field_names: List[str] = None):
        """
        Apply keyword filtering to a queryset.

        Args:
            queryset: Django queryset to filter
            field_names: List of field names to search (default: ['title', 'description'])

        Returns:
            Filtered queryset
        """
        from django.db.models import Q

        if field_names is None:
            field_names = ['title', 'description']

        prefs = self.get_preferences()

        # Include keywords (OR logic)
        include_keywords = prefs.get('keywords_include', [])
        if include_keywords:
            q_include = Q()
            for keyword in include_keywords:
                for field in field_names:
                    q_include |= Q(**{f'{field}__icontains': keyword})
            queryset = queryset.filter(q_include)

        # Exclude keywords (AND logic)
        exclude_keywords = prefs.get('keywords_exclude', [])
        if exclude_keywords:
            for keyword in exclude_keywords:
                for field in field_names:
                    queryset = queryset.exclude(**{f'{field}__icontains': keyword})

        return queryset

    def get_sort_params(self) -> tuple[str, str]:
        """
        Get sorting parameters.

        Returns:
            Tuple of (sort_field, sort_order)
        """
        prefs = self.get_preferences()
        sort_by = prefs.get('sort_by', 'timestamp')
        sort_order = prefs.get('sort_order', 'desc')

        # Add minus prefix for descending order
        order_prefix = '-' if sort_order == 'desc' else ''
        return f'{order_prefix}{sort_by}', sort_order


def get_available_sources() -> List[str]:
    """
    Get list of available data sources from database.

    Returns:
        List of unique source names
    """
    from .models import CollectedTopic

    sources = CollectedTopic.objects.values_list('source', flat=True).distinct()
    return sorted(list(sources))


def get_available_languages() -> List[Dict[str, str]]:
    """
    Get list of available languages from database.

    Returns:
        List of dicts with 'code' and 'name' keys
    """
    from .models import CollectedTopic

    # Language code to name mapping
    LANGUAGE_NAMES = {
        'en': 'English',
        'zh': 'Chinese (简体中文)',
        'zh-Hans': 'Chinese Simplified',
        'zh-Hant': 'Chinese Traditional',
        'ja': 'Japanese (日本語)',
        'ko': 'Korean (한국어)',
        'es': 'Spanish (Español)',
        'fr': 'French (Français)',
        'de': 'German (Deutsch)',
        'ar': 'Arabic (العربية)',
        'ru': 'Russian (Русский)',
        'pt': 'Portuguese (Português)',
        'it': 'Italian (Italiano)',
    }

    lang_codes = CollectedTopic.objects.values_list('language', flat=True).distinct()
    languages = [
        {'code': code, 'name': LANGUAGE_NAMES.get(code, code.upper())}
        for code in lang_codes if code
    ]

    return sorted(languages, key=lambda x: x['name'])


def get_time_range_options() -> List[Dict[str, str]]:
    """
    Get available time range options.

    Returns:
        List of dicts with 'value' and 'label' keys
    """
    return [
        {'value': '24h', 'label': 'Last 24 hours'},
        {'value': '7d', 'label': 'Last 7 days'},
        {'value': '30d', 'label': 'Last 30 days'},
        {'value': 'all', 'label': 'All time'},
        {'value': 'custom', 'label': 'Custom range'},
    ]


def get_sort_options() -> List[Dict[str, str]]:
    """
    Get available sorting options.

    Returns:
        List of dicts with 'value' and 'label' keys
    """
    return [
        {'value': 'timestamp', 'label': 'Time (newest/oldest)'},
        {'value': 'upvotes', 'label': 'Upvotes'},
        {'value': 'comments', 'label': 'Comments'},
        {'value': 'score', 'label': 'Score'},
    ]
