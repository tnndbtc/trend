"""
User preference models for persistent storage (Phase 2).

These models store user preferences in the database, allowing:
- Multiple saved preference profiles per user
- Cross-device preference sync
- Preference history tracking
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class UserPreference(models.Model):
    """
    Stores a user's preference profile.

    Users can have multiple profiles (e.g., "Work", "Personal", "Research")
    and switch between them.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='preferences',
        help_text="User who owns this preference profile"
    )

    # Profile Information
    name = models.CharField(
        max_length=100,
        help_text="Profile name (e.g., 'Work', 'Personal', 'AI Research')"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of this preference profile"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the user's default profile"
    )

    # Filter Preferences (stored as JSON for flexibility)
    sources = models.JSONField(
        default=list,
        help_text="List of preferred data sources"
    )
    languages = models.JSONField(
        default=list,
        help_text="List of preferred languages"
    )
    categories = models.JSONField(
        default=list,
        blank=True,
        help_text="List of preferred categories (future use)"
    )

    # Time Range Settings
    time_range = models.CharField(
        max_length=20,
        default='7d',
        choices=[
            ('24h', 'Last 24 hours'),
            ('7d', 'Last 7 days'),
            ('30d', 'Last 30 days'),
            ('all', 'All time'),
            ('custom', 'Custom range'),
        ],
        help_text="Default time range for articles"
    )
    custom_start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Custom start date (if time_range='custom')"
    )
    custom_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Custom end date (if time_range='custom')"
    )

    # Keyword Filtering
    keywords_include = models.JSONField(
        default=list,
        help_text="Keywords to include (OR logic)"
    )
    keywords_exclude = models.JSONField(
        default=list,
        help_text="Keywords to exclude (AND logic)"
    )

    # Engagement Thresholds
    min_upvotes = models.IntegerField(
        default=0,
        help_text="Minimum upvotes for articles"
    )
    min_comments = models.IntegerField(
        default=0,
        help_text="Minimum comments for articles"
    )
    min_score = models.IntegerField(
        default=0,
        help_text="Minimum score for articles"
    )

    # Sorting Preferences
    sort_by = models.CharField(
        max_length=20,
        default='timestamp',
        choices=[
            ('timestamp', 'Time'),
            ('upvotes', 'Upvotes'),
            ('comments', 'Comments'),
            ('score', 'Score'),
        ],
        help_text="Default sort field"
    )
    sort_order = models.CharField(
        max_length=4,
        default='desc',
        choices=[
            ('asc', 'Ascending'),
            ('desc', 'Descending'),
        ],
        help_text="Default sort order"
    )

    # Display Preferences
    items_per_page = models.IntegerField(
        default=50,
        help_text="Number of items per page"
    )
    view_mode = models.CharField(
        max_length=20,
        default='trends',
        choices=[
            ('trends', 'Trend Clusters'),
            ('topics', 'Individual Topics'),
        ],
        help_text="Default view mode"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(
        default=timezone.now,
        help_text="When this profile was last activated"
    )

    class Meta:
        ordering = ['-is_default', '-last_used']
        unique_together = ['user', 'name']
        verbose_name = "User Preference Profile"
        verbose_name_plural = "User Preference Profiles"

    def __str__(self):
        default_marker = " (default)" if self.is_default else ""
        return f"{self.user.username} - {self.name}{default_marker}"

    def save(self, *args, **kwargs):
        """Ensure only one default profile per user."""
        if self.is_default:
            # Set all other profiles for this user to non-default
            UserPreference.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)

        super().save(*args, **kwargs)

    def to_dict(self):
        """
        Convert preference to dictionary format compatible with PreferenceManager.

        Returns:
            Dictionary of preferences
        """
        return {
            'sources': self.sources,
            'languages': self.languages,
            'categories': self.categories,
            'time_range': self.time_range,
            'custom_start_date': self.custom_start_date.isoformat() if self.custom_start_date else None,
            'custom_end_date': self.custom_end_date.isoformat() if self.custom_end_date else None,
            'keywords_include': self.keywords_include,
            'keywords_exclude': self.keywords_exclude,
            'min_upvotes': self.min_upvotes,
            'min_comments': self.min_comments,
            'min_score': self.min_score,
            'sort_by': self.sort_by,
            'sort_order': self.sort_order,
        }

    @classmethod
    def from_dict(cls, user, name, prefs_dict, description='', is_default=False):
        """
        Create UserPreference from dictionary.

        Args:
            user: User instance
            name: Profile name
            prefs_dict: Dictionary of preferences
            description: Optional description
            is_default: Whether this is default profile

        Returns:
            UserPreference instance
        """
        # Handle custom dates
        custom_start = None
        custom_end = None
        if prefs_dict.get('custom_start_date'):
            try:
                from datetime import datetime
                custom_start = datetime.fromisoformat(prefs_dict['custom_start_date'])
            except (ValueError, TypeError):
                pass

        if prefs_dict.get('custom_end_date'):
            try:
                from datetime import datetime
                custom_end = datetime.fromisoformat(prefs_dict['custom_end_date'])
            except (ValueError, TypeError):
                pass

        return cls.objects.create(
            user=user,
            name=name,
            description=description,
            is_default=is_default,
            sources=prefs_dict.get('sources', []),
            languages=prefs_dict.get('languages', []),
            categories=prefs_dict.get('categories', []),
            time_range=prefs_dict.get('time_range', '7d'),
            custom_start_date=custom_start,
            custom_end_date=custom_end,
            keywords_include=prefs_dict.get('keywords_include', []),
            keywords_exclude=prefs_dict.get('keywords_exclude', []),
            min_upvotes=prefs_dict.get('min_upvotes', 0),
            min_comments=prefs_dict.get('min_comments', 0),
            min_score=prefs_dict.get('min_score', 0),
            sort_by=prefs_dict.get('sort_by', 'timestamp'),
            sort_order=prefs_dict.get('sort_order', 'desc'),
        )

    def mark_as_used(self):
        """Update last_used timestamp."""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])


class UserPreferenceHistory(models.Model):
    """
    Tracks changes to user preferences over time.

    Useful for:
    - Understanding user behavior
    - Reverting to previous settings
    - Analytics on preference trends
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='preference_history'
    )
    profile = models.ForeignKey(
        UserPreference,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='history'
    )

    action = models.CharField(
        max_length=20,
        choices=[
            ('created', 'Created'),
            ('updated', 'Updated'),
            ('deleted', 'Deleted'),
            ('activated', 'Activated'),
        ]
    )

    # Snapshot of preferences at this point in time
    preferences_snapshot = models.JSONField(
        help_text="Snapshot of preference values"
    )

    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Preference History Entry"
        verbose_name_plural = "Preference History"

    def __str__(self):
        profile_name = self.profile.name if self.profile else "Unknown"
        return f"{self.user.username} - {self.action} '{profile_name}' at {self.timestamp}"


class UserNotificationPreference(models.Model):
    """
    User preferences for notifications about new trends.

    Future feature: Send email/push notifications when new trends
    match user's interests.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    # Email Notifications
    email_enabled = models.BooleanField(
        default=False,
        help_text="Enable email notifications"
    )
    email_frequency = models.CharField(
        max_length=20,
        default='daily',
        choices=[
            ('realtime', 'Real-time (immediate)'),
            ('hourly', 'Hourly digest'),
            ('daily', 'Daily digest'),
            ('weekly', 'Weekly digest'),
        ]
    )

    # Push Notifications (future)
    push_enabled = models.BooleanField(
        default=False,
        help_text="Enable browser push notifications"
    )

    # Notification Filters
    min_trend_score = models.FloatField(
        default=0.0,
        help_text="Only notify for trends above this score"
    )
    min_topic_count = models.IntegerField(
        default=5,
        help_text="Only notify for trends with at least this many topics"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"

    def __str__(self):
        return f"{self.user.username} - Notifications: {'Enabled' if self.email_enabled else 'Disabled'}"
