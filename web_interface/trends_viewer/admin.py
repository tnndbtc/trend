from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from .models import CollectionRun, CollectedTopic, TrendCluster, CrawlerSource
from .models_preferences import UserPreference, UserPreferenceHistory, UserNotificationPreference


@admin.register(CollectionRun)
class CollectionRunAdmin(admin.ModelAdmin):
    list_display = ['id', 'timestamp', 'status', 'topics_count', 'clusters_count', 'duration_seconds']
    list_filter = ['status', 'timestamp']
    search_fields = ['id']
    readonly_fields = ['timestamp']


@admin.register(CollectedTopic)
class CollectedTopicAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'source', 'timestamp', 'upvotes', 'comments', 'score', 'collection_run']
    list_filter = ['source', 'timestamp', 'collection_run']
    search_fields = ['title', 'description']
    readonly_fields = ['timestamp']


@admin.register(TrendCluster)
class TrendClusterAdmin(admin.ModelAdmin):
    list_display = ['id', 'rank', 'title', 'score', 'collection_run', 'created_at']
    list_filter = ['collection_run', 'created_at']
    search_fields = ['title', 'summary']
    readonly_fields = ['created_at']
    ordering = ['collection_run', 'rank']


@admin.register(CrawlerSource)
class CrawlerSourceAdmin(admin.ModelAdmin):
    """Admin interface for managing crawler sources."""

    # List view configuration
    list_display = [
        'status_indicator',
        'name',
        'source_type',
        'health_badge',
        'success_rate_display',
        'items_collected_display',
        'last_collection_display',
        'schedule',
        'enabled',
    ]

    list_filter = [
        'enabled',
        'source_type',
        'health_status',
        'created_at',
        'last_collection',
    ]

    search_fields = [
        'name',
        'description',
        'url',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'last_collection',
        'health_status',
        'last_error',
        'consecutive_failures',
        'total_collections',
        'successful_collections',
        'total_items_collected',
        'success_rate_display',
        'decrypted_api_key_display',
    ]

    # Field organization in forms
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'source_type', 'description', 'enabled')
        }),
        ('Source Configuration', {
            'fields': ('url', 'config_json'),
            'description': 'Configure the source URL and additional settings'
        }),
        ('Scheduling', {
            'fields': ('schedule', 'collection_interval_hours'),
            'description': 'Configure collection schedule using cron expression or interval'
        }),
        ('Rate Limiting & Timeouts', {
            'fields': ('rate_limit', 'timeout_seconds', 'retry_count', 'backoff_multiplier'),
            'classes': ('collapse',),
        }),
        ('Authentication', {
            'fields': ('decrypted_api_key_display', 'oauth_config', 'custom_headers'),
            'classes': ('collapse',),
            'description': 'Configure API keys, OAuth, and custom headers for authenticated sources'
        }),
        ('Content Filtering', {
            'fields': ('language', 'category_filters', 'keyword_filters', 'content_filters'),
            'classes': ('collapse',),
            'description': 'Filter collected content by language, categories, keywords, etc.'
        }),
        ('Custom Plugin Code', {
            'fields': ('plugin_code',),
            'classes': ('collapse',),
            'description': 'For custom source type: Python code that inherits from CollectorPlugin'
        }),
        ('Health & Monitoring', {
            'fields': (
                'health_status',
                'last_collection',
                'last_error',
                'consecutive_failures',
                'total_collections',
                'successful_collections',
                'total_items_collected',
                'success_rate_display',
            ),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',),
        }),
    )

    # Enable bulk actions
    actions = [
        'enable_sources',
        'disable_sources',
        'test_connections',
        'trigger_collection',
        'reset_health_status',
    ]

    # Custom methods for list display
    def status_indicator(self, obj):
        """Show visual status indicator."""
        if obj.enabled:
            return format_html('<span style="color: green; font-size: 18px;">●</span>')
        return format_html('<span style="color: gray; font-size: 18px;">○</span>')
    status_indicator.short_description = '●'

    def health_badge(self, obj):
        """Show health status as colored badge."""
        colors = {
            'healthy': 'green',
            'warning': 'orange',
            'unhealthy': 'red',
            'unknown': 'gray',
        }
        color = colors.get(obj.health_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_health_status_display().upper()
        )
    health_badge.short_description = 'Health'

    def success_rate_display(self, obj):
        """Display success rate as percentage with color coding."""
        rate = obj.success_rate
        if rate >= 95:
            color = 'green'
        elif rate >= 80:
            color = 'orange'
        elif rate >= 50:
            color = 'red'
        else:
            color = 'darkred'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            f'{rate:.1f}'
        )
    success_rate_display.short_description = 'Success Rate'

    def items_collected_display(self, obj):
        """Display total items collected."""
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            f'{obj.total_items_collected:,}'
        )
    items_collected_display.short_description = 'Items Collected'

    def last_collection_display(self, obj):
        """Display last collection time."""
        if obj.last_collection:
            return obj.last_collection.strftime('%Y-%m-%d %H:%M')
        return format_html('<span style="color: gray;">Never</span>')
    last_collection_display.short_description = 'Last Collection'

    def decrypted_api_key_display(self, obj):
        """Display API key (masked for security)."""
        api_key = obj.api_key
        if api_key:
            # Show only first and last 4 characters
            if len(api_key) > 8:
                masked = f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"
            else:
                masked = '*' * len(api_key)
            return format_html('<code>{}</code>', masked)
        return format_html('<span style="color: gray;">Not set</span>')
    decrypted_api_key_display.short_description = 'API Key'

    # Custom actions
    def enable_sources(self, request, queryset):
        """Enable selected sources."""
        count = queryset.update(enabled=True)
        self.message_user(
            request,
            f'{count} source(s) enabled successfully.',
            messages.SUCCESS
        )
    enable_sources.short_description = '✓ Enable selected sources'

    def disable_sources(self, request, queryset):
        """Disable selected sources."""
        count = queryset.update(enabled=False)
        self.message_user(
            request,
            f'{count} source(s) disabled successfully.',
            messages.SUCCESS
        )
    disable_sources.short_description = '✗ Disable selected sources'

    def test_connections(self, request, queryset):
        """Test connection for selected sources."""
        results = []
        for source in queryset:
            success, message = source.test_connection()
            status = '✓' if success else '✗'
            results.append(f"{status} {source.name}: {message}")

        self.message_user(
            request,
            'Connection test results:\n' + '\n'.join(results),
            messages.INFO
        )
    test_connections.short_description = '🔍 Test connections'

    def trigger_collection(self, request, queryset):
        """Trigger manual collection for selected sources."""
        count = queryset.filter(enabled=True).count()
        if count > 0:
            self.message_user(
                request,
                f'Collection triggered for {count} source(s). Check logs for status.',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                'No enabled sources selected.',
                messages.WARNING
            )
    trigger_collection.short_description = '▶ Trigger collection'

    def reset_health_status(self, request, queryset):
        """Reset health status to unknown."""
        count = queryset.update(
            health_status='unknown',
            consecutive_failures=0,
            last_error=''
        )
        self.message_user(
            request,
            f'Health status reset for {count} source(s).',
            messages.SUCCESS
        )
    reset_health_status.short_description = '↻ Reset health status'

    def save_model(self, request, obj, form, change):
        """Custom save to set created_by field."""
        if not change:  # New object
            obj.created_by = request.user.username if request.user.is_authenticated else 'admin'
        super().save_model(request, obj, form, change)


# ============================================================================
# User Preference Admin (Phase 2)
# ============================================================================

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    """Admin interface for user preference profiles."""

    list_display = [
        'user',
        'name',
        'is_default',
        'view_mode',
        'source_count',
        'last_used',
        'created_at',
    ]

    list_filter = [
        'is_default',
        'view_mode',
        'created_at',
        'last_used',
    ]

    search_fields = [
        'user__username',
        'name',
        'description',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'last_used',
    ]

    fieldsets = (
        ('Profile Information', {
            'fields': ('user', 'name', 'description', 'is_default')
        }),
        ('Data Sources & Languages', {
            'fields': ('sources', 'languages', 'categories')
        }),
        ('Time Range', {
            'fields': ('time_range', 'custom_start_date', 'custom_end_date')
        }),
        ('Keywords', {
            'fields': ('keywords_include', 'keywords_exclude')
        }),
        ('Engagement Thresholds', {
            'fields': ('min_upvotes', 'min_comments', 'min_score')
        }),
        ('Sorting & Display', {
            'fields': ('sort_by', 'sort_order', 'items_per_page', 'view_mode')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_used'),
            'classes': ('collapse',),
        }),
    )

    def source_count(self, obj):
        """Display number of selected sources."""
        count = len(obj.sources)
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    source_count.short_description = 'Sources'


@admin.register(UserPreferenceHistory)
class UserPreferenceHistoryAdmin(admin.ModelAdmin):
    """Admin interface for preference history tracking."""

    list_display = [
        'user',
        'profile',
        'action',
        'timestamp',
        'ip_address',
    ]

    list_filter = [
        'action',
        'timestamp',
    ]

    search_fields = [
        'user__username',
        'profile__name',
    ]

    readonly_fields = [
        'user',
        'profile',
        'action',
        'preferences_snapshot',
        'timestamp',
        'ip_address',
        'user_agent',
    ]

    def has_add_permission(self, request):
        """History entries are created automatically."""
        return False

    def has_change_permission(self, request, obj=None):
        """History entries cannot be modified."""
        return False


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    """Admin interface for notification preferences."""

    list_display = [
        'user',
        'email_enabled',
        'email_frequency',
        'push_enabled',
        'min_trend_score',
        'updated_at',
    ]

    list_filter = [
        'email_enabled',
        'push_enabled',
        'email_frequency',
    ]

    search_fields = [
        'user__username',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
    ]

    fieldsets = (
        ('Email Notifications', {
            'fields': ('email_enabled', 'email_frequency')
        }),
        ('Push Notifications', {
            'fields': ('push_enabled',),
            'description': 'Browser push notifications (future feature)'
        }),
        ('Notification Filters', {
            'fields': ('min_trend_score', 'min_topic_count')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
