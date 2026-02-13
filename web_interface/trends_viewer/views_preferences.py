"""
Enhanced views with session-based preference filtering.

These views allow users to filter articles by their interests (sources, languages,
categories, time ranges, etc.) without requiring authentication. Preferences are
stored in Django session and applied to database queries.
"""

import logging
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from django.http import JsonResponse, HttpRequest
from django.db.models import Q, Count, Max
from typing import Dict, Any

from .models import CollectionRun, CollectedTopic, TrendCluster
from .preferences import (
    PreferenceManager,
    get_available_sources,
    get_available_languages,
    get_time_range_options,
    get_sort_options,
)

logger = logging.getLogger(__name__)


class FilteredTopicListView(ListView):
    """
    View for listing topics with advanced preference-based filtering.

    Users can filter by:
    - Data sources (Reddit, HackerNews, etc.)
    - Languages
    - Time ranges
    - Keywords (include/exclude)
    - Minimum engagement metrics (upvotes, comments, score)
    - Sorting options
    """
    model = CollectedTopic
    template_name = 'trends_viewer/filtered_topic_list.html'
    context_object_name = 'topics'
    paginate_by = 50

    def get_queryset(self):
        """
        Build filtered queryset based on user preferences.

        Returns:
            Filtered queryset of CollectedTopic objects
        """
        # Initialize preference manager
        pref_manager = PreferenceManager(self.request)

        # Handle preference updates from GET/POST parameters
        if self.request.method == 'GET' and 'apply_filters' in self.request.GET:
            self._update_preferences_from_request(pref_manager)

        # Start with all topics
        queryset = CollectedTopic.objects.all()

        # Apply filter parameters from preferences
        filter_params = pref_manager.get_filter_params()
        if filter_params:
            queryset = queryset.filter(**filter_params)

        # Apply keyword filtering
        queryset = pref_manager.filter_by_keywords(
            queryset,
            field_names=['title', 'description', 'content']
        )

        # Apply sorting
        sort_field, _ = pref_manager.get_sort_params()
        queryset = queryset.order_by(sort_field)

        return queryset

    def _update_preferences_from_request(self, pref_manager: PreferenceManager):
        """
        Update preferences from request parameters.

        Args:
            pref_manager: PreferenceManager instance
        """
        updates = {}

        # Multi-select fields (can have multiple values)
        sources = self.request.GET.getlist('sources')
        if sources:
            updates['sources'] = sources

        languages = self.request.GET.getlist('languages')
        if languages:
            updates['languages'] = languages

        # Single-value fields
        if 'time_range' in self.request.GET:
            updates['time_range'] = self.request.GET.get('time_range')

        if 'custom_start_date' in self.request.GET:
            updates['custom_start_date'] = self.request.GET.get('custom_start_date')

        if 'custom_end_date' in self.request.GET:
            updates['custom_end_date'] = self.request.GET.get('custom_end_date')

        # Keyword filtering
        keywords_include = self.request.GET.get('keywords_include', '')
        if keywords_include:
            updates['keywords_include'] = [
                kw.strip() for kw in keywords_include.split(',') if kw.strip()
            ]

        keywords_exclude = self.request.GET.get('keywords_exclude', '')
        if keywords_exclude:
            updates['keywords_exclude'] = [
                kw.strip() for kw in keywords_exclude.split(',') if kw.strip()
            ]

        # Minimum metrics
        for metric in ['min_upvotes', 'min_comments', 'min_score']:
            if metric in self.request.GET:
                try:
                    updates[metric] = int(self.request.GET.get(metric, 0))
                except ValueError:
                    updates[metric] = 0

        # Sorting
        if 'sort_by' in self.request.GET:
            updates['sort_by'] = self.request.GET.get('sort_by')

        if 'sort_order' in self.request.GET:
            updates['sort_order'] = self.request.GET.get('sort_order')

        # Apply updates
        if updates:
            pref_manager.update_preferences(updates)

    def get_context_data(self, **kwargs):
        """
        Add preference-related context data.

        Returns:
            Enhanced context dictionary
        """
        context = super().get_context_data(**kwargs)

        pref_manager = PreferenceManager(self.request)
        preferences = pref_manager.get_preferences()

        # Add filter options
        context['available_sources'] = get_available_sources()
        context['available_languages'] = get_available_languages()
        context['time_range_options'] = get_time_range_options()
        context['sort_options'] = get_sort_options()

        # Add current preferences
        context['preferences'] = preferences

        # Add filter statistics
        context['filter_stats'] = self._get_filter_statistics()

        return context

    def _get_filter_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current filters.

        Returns:
            Dictionary with filter statistics
        """
        pref_manager = PreferenceManager(self.request)
        prefs = pref_manager.get_preferences()

        active_filters = []
        if prefs.get('sources'):
            active_filters.append(f"{len(prefs['sources'])} sources")
        if prefs.get('languages'):
            active_filters.append(f"{len(prefs['languages'])} languages")
        if prefs.get('keywords_include'):
            active_filters.append(f"{len(prefs['keywords_include'])} include keywords")
        if prefs.get('keywords_exclude'):
            active_filters.append(f"{len(prefs['keywords_exclude'])} exclude keywords")

        return {
            'active_count': len(active_filters),
            'active_filters': active_filters,
            'is_filtered': len(active_filters) > 0,
        }


class FilteredTrendListView(ListView):
    """
    View for listing trend clusters with preference-based topic filtering.

    Shows trend clusters but filters the topics within each cluster based on
    user preferences (sources, languages, etc.).
    """
    model = TrendCluster
    template_name = 'trends_viewer/filtered_trend_list.html'
    context_object_name = 'trends'
    paginate_by = 20

    def get_queryset(self):
        """
        Get trend clusters, ordered by rank.

        Returns:
            Queryset of TrendCluster objects
        """
        # Handle preference updates
        if self.request.method == 'GET' and 'apply_filters' in self.request.GET:
            pref_manager = PreferenceManager(self.request)
            self._update_preferences_from_request(pref_manager)

        # Get latest completed run
        run_id = self.request.GET.get('run')
        if run_id:
            queryset = TrendCluster.objects.filter(collection_run_id=run_id)
        else:
            latest_run = CollectionRun.objects.filter(status='completed').first()
            if latest_run:
                queryset = TrendCluster.objects.filter(collection_run=latest_run)
            else:
                queryset = TrendCluster.objects.none()

        return queryset.order_by('rank')

    def _update_preferences_from_request(self, pref_manager: PreferenceManager):
        """Update preferences from request (same as FilteredTopicListView)."""
        updates = {}

        sources = self.request.GET.getlist('sources')
        if sources:
            updates['sources'] = sources

        languages = self.request.GET.getlist('languages')
        if languages:
            updates['languages'] = languages

        if 'time_range' in self.request.GET:
            updates['time_range'] = self.request.GET.get('time_range')

        keywords_include = self.request.GET.get('keywords_include', '')
        if keywords_include:
            updates['keywords_include'] = [kw.strip() for kw in keywords_include.split(',') if kw.strip()]

        keywords_exclude = self.request.GET.get('keywords_exclude', '')
        if keywords_exclude:
            updates['keywords_exclude'] = [kw.strip() for kw in keywords_exclude.split(',') if kw.strip()]

        for metric in ['min_upvotes', 'min_comments', 'min_score']:
            if metric in self.request.GET:
                try:
                    updates[metric] = int(self.request.GET.get(metric, 0))
                except ValueError:
                    updates[metric] = 0

        if updates:
            pref_manager.update_preferences(updates)

    def get_context_data(self, **kwargs):
        """
        Add filtered topics for each trend cluster.

        Returns:
            Enhanced context with filtered topics
        """
        context = super().get_context_data(**kwargs)

        pref_manager = PreferenceManager(self.request)
        preferences = pref_manager.get_preferences()
        filter_params = pref_manager.get_filter_params()

        # For each trend, get filtered topics
        for trend in context['trends']:
            # Start with all topics in this cluster
            topics_queryset = trend.topics.all()

            # Apply preference filters
            if filter_params:
                topics_queryset = topics_queryset.filter(**filter_params)

            # Apply keyword filtering
            topics_queryset = pref_manager.filter_by_keywords(
                topics_queryset,
                field_names=['title', 'description']
            )

            # Attach filtered topics to trend object
            trend.filtered_topics = topics_queryset
            trend.filtered_topic_count = topics_queryset.count()

        # Add filter options and preferences
        context['available_sources'] = get_available_sources()
        context['available_languages'] = get_available_languages()
        context['time_range_options'] = get_time_range_options()
        context['preferences'] = preferences

        # Get current run
        run_id = self.request.GET.get('run')
        if run_id:
            context['current_run'] = get_object_or_404(CollectionRun, id=run_id)
        else:
            context['current_run'] = CollectionRun.objects.filter(status='completed').first()

        context['all_runs'] = CollectionRun.objects.all()[:10]

        return context


def update_preferences_ajax(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint for updating preferences without page reload.

    Args:
        request: Django HttpRequest

    Returns:
        JSON response with updated preferences
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    pref_manager = PreferenceManager(request)

    # Get updates from POST data
    updates = {}
    for key in ['sources', 'languages', 'time_range', 'sort_by', 'sort_order']:
        if key in request.POST:
            value = request.POST.getlist(key) if key in ['sources', 'languages'] else request.POST.get(key)
            updates[key] = value

    # Update preferences
    new_prefs = pref_manager.update_preferences(updates)

    return JsonResponse({
        'success': True,
        'preferences': new_prefs,
    })


def reset_preferences_ajax(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint for resetting preferences to defaults.

    Args:
        request: Django HttpRequest

    Returns:
        JSON response with default preferences
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    pref_manager = PreferenceManager(request)
    default_prefs = pref_manager.reset_preferences()

    return JsonResponse({
        'success': True,
        'preferences': default_prefs,
        'message': 'Preferences reset to defaults'
    })


def get_filter_preview(request: HttpRequest) -> JsonResponse:
    """
    AJAX endpoint to preview filter results without applying.

    Args:
        request: Django HttpRequest

    Returns:
        JSON with count of matching topics
    """
    # Create temporary preference manager
    pref_manager = PreferenceManager(request)

    # Build filter params from GET parameters (don't save to session)
    temp_filters = {}

    sources = request.GET.getlist('sources')
    if sources:
        temp_filters['source__in'] = sources

    languages = request.GET.getlist('languages')
    if languages:
        temp_filters['language__in'] = languages

    # Count matching topics
    queryset = CollectedTopic.objects.filter(**temp_filters)
    count = queryset.count()

    # Get breakdown by source
    source_breakdown = list(
        queryset.values('source')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    return JsonResponse({
        'success': True,
        'total_count': count,
        'source_breakdown': source_breakdown,
    })
