from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.contrib import messages
from django.db import models as django_models
from .models import CollectionRun, CollectedTopic, TrendCluster, CrawlerSource, TranslatedContent, TrendTranslationStatus, SystemSettings
from .models_preferences import UserPreference, UserPreferenceHistory, UserNotificationPreference
from .forms import TrendClusterAdminForm

# Import translation admin functionality
from .admin_translation import (
    TrendTranslationStatusAdmin,
    add_translation_actions_to_admin,
    get_translation_dashboard_urls
)


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
    """
    Simplified admin interface for manually adding trends.

    Auto-fills technical fields (collection_run, rank, score) so users only
    need to provide the trend title and summary.
    """

    form = TrendClusterAdminForm

    list_display = ['rank', 'title', 'language', 'score', 'collection_run_link', 'created_at']
    list_filter = ['language', 'collection_run', 'created_at']
    search_fields = ['title', 'summary']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Essential Information', {
            'fields': ('title', 'summary'),
            'description': (
                '<strong>Quick Add:</strong> Just enter the title and summary - '
                'everything else will be auto-filled! 🎉'
            )
        }),
        ('Advanced Settings', {
            'fields': ('language', 'title_summary', 'full_summary'),
            'classes': ('collapse',),
            'description': (
                'Optional: Customize language and enhanced summaries. '
                'Leave blank to use defaults.'
            )
        }),
        ('Auto-Generated Fields', {
            'fields': ('collection_run', 'rank', 'score', 'created_at'),
            'classes': ('collapse',),
            'description': (
                'These fields are automatically set when you save. '
                'Advanced users can override if needed.'
            )
        }),
    )

    def collection_run_link(self, obj):
        """Show collection run as a clickable link."""
        if obj.collection_run:
            url = reverse('admin:trends_viewer_collectionrun_change', args=[obj.collection_run.id])
            return format_html(
                '<a href="{}">Run #{} ({})</a>',
                url,
                obj.collection_run.id,
                obj.collection_run.timestamp.strftime('%Y-%m-%d')
            )
        return '-'
    collection_run_link.short_description = 'Collection Run'

    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly after creation."""
        if obj:  # Editing existing object - allow editing everything
            return ['created_at']
        # When creating new object, only created_at is readonly
        return ['created_at']

    def save_model(self, request, obj, form, change):
        """Auto-populate technical fields when creating new trend."""
        if not change:  # New object being created
            # 1. Auto-assign collection_run if not provided
            # Use collection_run_id to avoid RelatedObjectDoesNotExist error
            if obj.collection_run_id is None:
                latest_run = CollectionRun.objects.filter(status='completed').first()

                if not latest_run:
                    # Create a manual collection run if none exists
                    latest_run = CollectionRun.objects.create(
                        status='completed',
                        topics_count=0,
                        clusters_count=0
                    )
                    messages.info(
                        request,
                        f'Created new manual Collection Run #{latest_run.id} for this trend.'
                    )

                obj.collection_run = latest_run

            # 2. Auto-generate next rank if not provided
            if obj.rank is None:
                max_rank = TrendCluster.objects.filter(
                    collection_run=obj.collection_run
                ).aggregate(django_models.Max('rank'))['rank__max']
                obj.rank = (max_rank or 0) + 1

            # 3. Set default score if not provided
            if obj.score is None:
                obj.score = 1.0

            # 4. Auto-fill optional summary fields if blank
            if not obj.title_summary:
                obj.title_summary = obj.title
            if not obj.full_summary:
                obj.full_summary = obj.summary

        super().save_model(request, obj, form, change)

        # Update collection run cluster count
        if not change:
            obj.collection_run.clusters_count = TrendCluster.objects.filter(
                collection_run=obj.collection_run
            ).count()
            obj.collection_run.save()

            messages.success(
                request,
                format_html(
                    '✅ Trend created successfully!<br>'
                    '📊 Auto-assigned rank <strong>#{}</strong> in Collection Run <strong>#{}</strong><br>'
                    '🎯 Score: <strong>{}</strong>',
                    obj.rank,
                    obj.collection_run.id,
                    obj.score
                )
            )

    def get_urls(self):
        """Add custom URLs for translation dashboard."""
        urls = super().get_urls()
        custom_urls = get_translation_dashboard_urls(self.admin_site)
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Add translation dashboard link to changelist."""
        extra_context = extra_context or {}
        extra_context['translation_dashboard_url'] = reverse('admin:translation_dashboard')
        return super().changelist_view(request, extra_context=extra_context)


# Apply translation actions to TrendClusterAdmin
add_translation_actions_to_admin(TrendClusterAdmin)


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


# ============================================================================
# Translation Cache Admin
# ============================================================================

@admin.register(TranslatedContent)
class TranslatedContentAdmin(admin.ModelAdmin):
    """Admin interface for managing cached translations."""

    list_display = [
        'id',
        'source_text_hash_display',
        'language_pair_display',
        'provider_badge',
        'text_preview',
        'created_at',
    ]

    list_filter = [
        'provider',
        'target_language',
        'source_language',
        'created_at',
    ]

    search_fields = [
        'translated_text',
        'source_text_hash',
    ]

    readonly_fields = [
        'source_text_hash',
        'created_at',
        'updated_at',
    ]

    fieldsets = (
        ('Translation Info', {
            'fields': ('source_text_hash', 'source_language', 'target_language')
        }),
        ('Content', {
            'fields': ('translated_text',)
        }),
        ('Provider', {
            'fields': ('provider',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # Custom display methods
    def source_text_hash_display(self, obj):
        """Display shortened hash."""
        return format_html('<code>{}</code>', obj.source_text_hash[:16] + '...')
    source_text_hash_display.short_description = 'Source Hash'

    def language_pair_display(self, obj):
        """Display language pair with flags."""
        return format_html(
            '<span style="font-weight: bold;">{} → {}</span>',
            obj.source_language.upper(),
            obj.target_language.upper()
        )
    language_pair_display.short_description = 'Languages'

    def provider_badge(self, obj):
        """Display provider as colored badge."""
        colors = {
            'libretranslate': '#28a745',  # Green (free)
            'openai': '#007bff',          # Blue (AI)
            'deepl': '#6f42c1',           # Purple (AI)
            'google': '#dc3545',          # Red
            'other': '#6c757d',           # Gray
        }
        color = colors.get(obj.provider, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_provider_display().upper()
        )
    provider_badge.short_description = 'Provider'

    def text_preview(self, obj):
        """Display preview of translated text."""
        preview = obj.translated_text[:80]
        if len(obj.translated_text) > 80:
            preview += '...'
        return format_html('<span style="color: #666;">{}</span>', preview)
    text_preview.short_description = 'Translation Preview'

    # Custom actions
    actions = [
        'delete_old_translations',
        'export_translations',
    ]

    def delete_old_translations(self, request, queryset):
        """Delete translations older than selection."""
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            f'{count} translation(s) deleted successfully.',
            messages.SUCCESS
        )
    delete_old_translations.short_description = '🗑️ Delete selected translations'

    def export_translations(self, request, queryset):
        """Export translations (placeholder for future CSV/JSON export)."""
        count = queryset.count()
        self.message_user(
            request,
            f'Export feature coming soon! ({count} translation(s) selected)',
            messages.INFO
        )
    export_translations.short_description = '📤 Export translations'


# ============================================================================
# System Settings Admin
# ============================================================================

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for system-wide settings.

    This is a singleton model - only one record exists.
    """

    # Prevent adding or deleting (singleton pattern)
    def has_add_permission(self, request):
        """Prevent adding new settings (singleton)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of settings."""
        return False

    def changelist_view(self, request, extra_context=None):
        """
        Redirect directly to the change page for singleton model.
        No need to show a list view when there's only one record.
        """
        from django.shortcuts import redirect

        # Get or create the singleton settings
        obj = SystemSettings.load()

        # Redirect to the change page
        return redirect('admin:trends_viewer_systemsettings_change', object_id=obj.pk)

    # List display
    list_display = [
        'provider_with_status',
        'free_algorithm_display',
        'cost_estimate_display',
        'summaries_generated_display',
        'updated_at',
        'updated_by',
    ]

    # Readonly fields
    readonly_fields = [
        'updated_at',
        'estimated_monthly_api_cost',
        'total_summaries_generated',
        'last_cleanup_at',
        'total_records_cleaned',
        'database_size_display',
        'next_cleanup_display',
    ]

    # Field organization
    fieldsets = (
        ('🤖 Summarization Provider', {
            'fields': (
                'summarization_provider',
            ),
            'description': (
                '<strong>Choose how summaries are generated:</strong><br>'
                '• <strong>Free NLP Tools</strong>: Works offline, zero cost, good quality (default)<br>'
                '• <strong>OpenAI GPT</strong>: Paid API, excellent quality<br>'
                '• <strong>Anthropic Claude</strong>: Paid API, excellent quality<br><br>'
                '<em>Free tools are recommended for most use cases.</em>'
            )
        }),
        ('⚙️ Free NLP Configuration', {
            'fields': (
                'free_summarization_algorithm',
            ),
            'description': (
                '<strong>Algorithm to use when Free NLP is selected:</strong><br>'
                '• <strong>TextRank</strong>: Graph-based ranking (recommended)<br>'
                '• <strong>LexRank</strong>: Graph-based with cosine similarity<br>'
                '• <strong>LSA</strong>: Latent Semantic Analysis<br>'
                '• <strong>Luhn</strong>: Word frequency based (fastest)<br>'
                '• <strong>KL</strong>: Statistical approach'
            )
        }),
        ('📏 Summary Length Settings', {
            'fields': (
                'max_summary_length',
                'title_summary_length',
                'key_points_count',
            ),
            'classes': ('collapse',),
        }),
        ('🔑 OpenAI Configuration', {
            'fields': (
                'openai_model',
                'openai_temperature',
            ),
            'classes': ('collapse',),
            'description': 'Only used when OpenAI provider is selected'
        }),
        ('🔑 Anthropic Configuration', {
            'fields': (
                'anthropic_model',
            ),
            'classes': ('collapse',),
            'description': 'Only used when Anthropic provider is selected'
        }),
        ('⚡ Performance', {
            'fields': (
                'batch_size',
                'celery_worker_concurrency',
                'enable_summarization_cache',
            ),
            'description': (
                '<strong>Performance optimization settings:</strong><br>'
                '• <strong>Worker Concurrency</strong>: Number of parallel translation workers. '
                'Higher = faster translations but more CPU/memory usage. '
                '<span style="color: #ff9800; font-weight: bold;">⚠️ Requires worker restart to apply changes</span><br>'
                '• <strong>Batch Size</strong>: Number of items to process in parallel<br>'
                '• <strong>Summary Caching</strong>: Cache generated summaries to avoid re-processing'
            )
        }),
        ('💰 Cost Tracking', {
            'fields': (
                'estimated_monthly_api_cost',
                'total_summaries_generated',
            ),
            'classes': ('collapse',),
        }),
        ('🗑️ Data Retention', {
            'fields': (
                'data_retention_days',
                'enable_auto_cleanup',
                'database_size_display',
                'last_cleanup_at',
                'total_records_cleaned',
                'next_cleanup_display',
            ),
            'description': (
                '<strong>Automatic cleanup configuration:</strong><br>'
                '• Data older than the retention period will be automatically deleted daily at 3:00 AM<br>'
                '• This helps manage disk space and keeps the database performant<br>'
                '• Recommended: 7 days for most installations<br><br>'
                '<em>You can also manually clean old data using setup.sh option 9</em>'
            )
        }),
        ('📝 Metadata', {
            'fields': (
                'updated_at',
                'updated_by',
                'notes',
            ),
            'classes': ('collapse',),
        }),
    )

    # Custom display methods
    def provider_with_status(self, obj):
        """Show provider with visual status indicator."""
        if obj.summarization_provider == 'free':
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 4px 12px; '
                'border-radius: 4px; font-weight: bold; display: inline-block;">✓ {} (FREE)</span>',
                obj.get_summarization_provider_display().split(' - ')[0]
            )
        else:
            cost = obj.estimated_monthly_api_cost
            return format_html(
                '<span style="background-color: #ffc107; color: #000; padding: 4px 12px; '
                'border-radius: 4px; font-weight: bold; display: inline-block;">💰 {} (${:.2f}/mo)</span>',
                obj.get_summarization_provider_display().split(' - ')[0],
                cost
            )
    provider_with_status.short_description = 'Current Provider'

    def free_algorithm_display(self, obj):
        """Show free algorithm if using free provider."""
        if obj.summarization_provider == 'free':
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{}</span>',
                obj.get_free_summarization_algorithm_display().split(' - ')[0]
            )
        return format_html('<span style="color: #999;">N/A (not using free)</span>')
    free_algorithm_display.short_description = 'Free Algorithm'

    def cost_estimate_display(self, obj):
        """Display estimated monthly cost with color coding."""
        cost = obj.estimated_monthly_api_cost

        if cost == 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold; font-size: 14px;">$0.00 🎉</span>'
            )
        elif cost < 10:
            color = '#ffc107'  # warning/yellow
        elif cost < 50:
            color = '#ff9800'  # orange
        else:
            color = '#f44336'  # red

        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 14px;">${:.2f}</span>',
            color,
            cost
        )
    cost_estimate_display.short_description = 'Est. Monthly Cost'

    def summaries_generated_display(self, obj):
        """Display total summaries with formatting."""
        count = obj.total_summaries_generated
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            f'{count:,}'
        )
    summaries_generated_display.short_description = 'Summaries Generated'

    def database_size_display(self, obj):
        """Display current database size and record counts."""
        from trends_viewer.models import CollectionRun, CollectedTopic, TrendCluster
        import os

        try:
            # Get record counts
            runs_count = CollectionRun.objects.count()
            topics_count = CollectedTopic.objects.count()
            clusters_count = TrendCluster.objects.count()

            # Get database file size
            db_path = '/home/tnnd/data/code/trend/web_interface/db/db.sqlite3'
            if os.path.exists(db_path):
                db_size_bytes = os.path.getsize(db_path)
                db_size_mb = db_size_bytes / (1024 * 1024)

                # Color code based on size
                if db_size_mb < 100:
                    color = '#28a745'  # green
                elif db_size_mb < 500:
                    color = '#ffc107'  # yellow
                else:
                    color = '#f44336'  # red

                return format_html(
                    '<div style="line-height: 1.8;">'
                    '<strong style="color: {}; font-size: 16px;">{:.1f} MB</strong><br>'
                    '<span style="font-size: 12px; color: #666;">'
                    '📊 {} runs<br>'
                    '📰 {} topics<br>'
                    '🔗 {} clusters'
                    '</span>'
                    '</div>',
                    color,
                    db_size_mb,
                    runs_count,
                    topics_count,
                    clusters_count
                )
            else:
                return format_html('<span style="color: #999;">Database file not found</span>')

        except Exception as e:
            return format_html('<span style="color: #f44336;">Error: {}</span>', str(e))

    database_size_display.short_description = 'Database Status'

    def next_cleanup_display(self, obj):
        """Display next scheduled cleanup time."""
        from django.utils import timezone
        from datetime import datetime, time, timedelta

        if not obj.enable_auto_cleanup:
            return format_html(
                '<span style="color: #f44336; font-weight: bold;">⚠️ Disabled</span><br>'
                '<span style="font-size: 12px; color: #666;">Enable auto-cleanup to schedule</span>'
            )

        try:
            # Cleanup runs daily at 3:00 AM
            now = timezone.now()
            today_3am = timezone.make_aware(
                datetime.combine(now.date(), time(hour=3, minute=0))
            )

            # If it's past 3 AM today, next cleanup is tomorrow at 3 AM
            if now > today_3am:
                next_cleanup = today_3am + timedelta(days=1)
            else:
                next_cleanup = today_3am

            # Calculate time until next cleanup
            time_until = next_cleanup - now
            hours_until = int(time_until.total_seconds() // 3600)
            minutes_until = int((time_until.total_seconds() % 3600) // 60)

            return format_html(
                '<div style="line-height: 1.8;">'
                '<strong style="color: #28a745;">⏰ {}</strong><br>'
                '<span style="font-size: 12px; color: #666;">in {}h {}m</span>'
                '</div>',
                next_cleanup.strftime('%Y-%m-%d %H:%M'),
                hours_until,
                minutes_until
            )

        except Exception as e:
            return format_html('<span style="color: #f44336;">Error: {}</span>', str(e))

    next_cleanup_display.short_description = 'Next Scheduled Cleanup'

    # Custom actions
    actions = [
        'test_free_summarization',
        'test_current_provider',
        'reset_counters',
        'estimate_costs',
    ]

    def test_free_summarization(self, request, queryset):
        """Test free summarization with sample text."""
        import asyncio
        from trend_agent.services.free_summarization import FreeSummarizationService

        # Get settings
        settings = queryset.first()

        # Create service
        service = FreeSummarizationService(
            algorithm=settings.free_summarization_algorithm
        )

        # Test text
        test_text = (
            "Artificial intelligence is rapidly transforming technology. "
            "Machine learning models are becoming more powerful every year. "
            "Natural language processing enables computers to understand human language. "
            "Computer vision allows machines to interpret visual information. "
            "AI is being applied across many industries including healthcare, finance, and transportation."
        )

        # Run test
        try:
            summary = asyncio.run(service.summarize(test_text, max_length=100))
            self.message_user(
                request,
                format_html(
                    '<strong>✓ Free Summarization Test Successful</strong><br>'
                    'Algorithm: {}<br>'
                    'Input length: {} chars<br>'
                    'Output length: {} chars<br>'
                    '<em>Summary:</em> {}',
                    settings.free_summarization_algorithm,
                    len(test_text),
                    len(summary),
                    summary
                ),
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(
                request,
                f'❌ Test failed: {str(e)}',
                messages.ERROR
            )
    test_free_summarization.short_description = '🧪 Test Free Summarization'

    def test_current_provider(self, request, queryset):
        """Test currently selected provider."""
        import asyncio
        from trend_agent.services.factory import ServiceFactory

        settings = queryset.first()

        factory = ServiceFactory()
        service = factory.get_llm_service(provider=settings.summarization_provider)

        test_text = "AI is transforming technology. Machine learning is advancing rapidly."

        try:
            summary = asyncio.run(service.summarize(test_text, max_length=50))
            self.message_user(
                request,
                format_html(
                    '<strong>✓ Provider Test Successful</strong><br>'
                    'Provider: {}<br>'
                    'Summary: {}',
                    settings.get_summarization_provider_display(),
                    summary
                ),
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(
                request,
                f'❌ Test failed: {str(e)}',
                messages.ERROR
            )
    test_current_provider.short_description = '🔍 Test Current Provider'

    def reset_counters(self, request, queryset):
        """Reset usage counters."""
        for settings in queryset:
            settings.reset_counters()
        self.message_user(
            request,
            'Usage counters reset successfully.',
            messages.SUCCESS
        )
    reset_counters.short_description = '↻ Reset Counters'

    def estimate_costs(self, request, queryset):
        """Recalculate cost estimates."""
        for settings in queryset:
            settings.update_cost_estimate(summaries_generated=0)
        self.message_user(
            request,
            'Cost estimates updated based on current provider.',
            messages.SUCCESS
        )
    estimate_costs.short_description = '💰 Recalculate Costs'

    def save_model(self, request, obj, form, change):
        """Save model and track who updated it."""
        obj.updated_by = request.user.username if request.user.is_authenticated else 'admin'

        # Update cost estimate when provider changes
        if change and 'summarization_provider' in form.changed_data:
            obj.update_cost_estimate(summaries_generated=0)

        super().save_model(request, obj, form, change)

        # Show confirmation message
        if obj.summarization_provider == 'free':
            self.message_user(
                request,
                '✓ Settings saved. Using FREE summarization (zero cost, works offline).',
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                format_html(
                    '⚠️ Settings saved. Using PAID provider: {} (estimated ${:.2f}/month)',
                    obj.get_summarization_provider_display(),
                    obj.estimated_monthly_api_cost
                ),
                messages.WARNING
            )
