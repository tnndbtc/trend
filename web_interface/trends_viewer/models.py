from django.db import models
from django.utils import timezone
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import json
from cryptography.fernet import Fernet
from django.conf import settings


class CollectionRun(models.Model):
    """Represents a single execution of the trend collection pipeline."""
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=[
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='running')
    topics_count = models.IntegerField(default=0)
    clusters_count = models.IntegerField(default=0)
    duration_seconds = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Collection Run {self.id} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class CollectedTopic(models.Model):
    """Represents a single topic collected from a data source."""
    collection_run = models.ForeignKey(CollectionRun, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    source = models.CharField(max_length=50)  # No choices constraint - sources discovered dynamically
    url = models.URLField(max_length=1000)
    timestamp = models.DateTimeField()

    # Metrics stored as JSON-like fields
    upvotes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    score = models.IntegerField(default=0)

    # Content and language fields
    language = models.CharField(max_length=10, default='en')
    content = models.TextField(blank=True)

    # AI-generated summaries
    title_summary = models.CharField(max_length=500, blank=True)
    full_summary = models.TextField(blank=True)

    cluster = models.ForeignKey('TrendCluster', on_delete=models.SET_NULL, null=True, blank=True, related_name='topics')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.source}: {self.title[:50]}"


class TrendCluster(models.Model):
    """Represents a cluster of related topics identified as a trend."""
    collection_run = models.ForeignKey(CollectionRun, on_delete=models.CASCADE, related_name='clusters')
    rank = models.IntegerField()
    title = models.CharField(max_length=500)
    summary = models.TextField()
    score = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)

    # Language and structured summaries
    language = models.CharField(max_length=10, default='en')
    title_summary = models.CharField(max_length=500, blank=True)
    full_summary = models.TextField(blank=True)

    class Meta:
        ordering = ['rank']
        unique_together = ['collection_run', 'rank']

    def __str__(self):
        return f"Trend #{self.rank}: {self.title}"

    def get_sources(self):
        """Get unique sources for topics in this cluster."""
        return self.topics.values_list('source', flat=True).distinct()

    def get_topic_count(self):
        """Get count of topics in this cluster."""
        return self.topics.count()


class CrawlerSource(models.Model):
    """Represents a configurable data source for the crawler."""

    # Source type choices (matches SourceType enum from trend_agent/schemas.py)
    SOURCE_TYPE_CHOICES = [
        ('reddit', 'Reddit'),
        ('hackernews', 'Hacker News'),
        ('twitter', 'Twitter/X'),
        ('youtube', 'YouTube'),
        ('google_news', 'Google News'),
        ('bbc', 'BBC News'),
        ('reuters', 'Reuters'),
        ('ap_news', 'AP News'),
        ('al_jazeera', 'Al Jazeera'),
        ('guardian', 'The Guardian'),
        ('rss', 'RSS Feed'),
        ('custom', 'Custom Plugin'),
        ('demo', 'Demo/Test'),
    ]

    # Health status choices
    HEALTH_STATUS_CHOICES = [
        ('unknown', 'Unknown'),
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('unhealthy', 'Unhealthy'),
    ]

    # Basic Information
    name = models.CharField(max_length=100, unique=True, help_text="Unique name for this source")
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPE_CHOICES, help_text="Type of data source")
    description = models.TextField(blank=True, help_text="Description of what this source collects")
    url = models.URLField(max_length=1000, blank=True, help_text="Source URL (for RSS, API endpoints, etc.)")
    enabled = models.BooleanField(default=True, help_text="Enable/disable collection from this source")

    # Scheduling Configuration
    schedule = models.CharField(
        max_length=50,
        default="0 */4 * * *",
        help_text="Cron expression for collection schedule (e.g., '0 */4 * * *' for every 4 hours)"
    )
    collection_interval_hours = models.IntegerField(
        default=4,
        help_text="Alternative: Collection interval in hours (if not using cron)"
    )

    # Rate Limiting & Timeouts
    rate_limit = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum requests per hour (null = unlimited)"
    )
    timeout_seconds = models.IntegerField(
        default=30,
        help_text="Timeout for requests in seconds"
    )
    retry_count = models.IntegerField(
        default=3,
        help_text="Number of retries on failure"
    )
    backoff_multiplier = models.FloatField(
        default=2.0,
        help_text="Exponential backoff multiplier for retries"
    )

    # Authentication (Encrypted)
    api_key_encrypted = models.BinaryField(
        blank=True,
        null=True,
        help_text="Encrypted API key for authenticated sources"
    )
    oauth_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="OAuth configuration (client_id, client_secret, tokens, etc.)"
    )
    custom_headers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom HTTP headers for requests"
    )

    # Content Filtering
    category_filters = models.JSONField(
        default=list,
        blank=True,
        help_text="List of allowed categories (empty = all categories)"
    )
    keyword_filters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Keyword filters: {'include': ['keyword1'], 'exclude': ['keyword2']}"
    )
    language = models.CharField(
        max_length=10,
        default='en',
        help_text="Target language code (ISO 639-1, e.g., 'en', 'es', 'ja')"
    )
    content_filters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Advanced content filters (min_length, max_length, etc.)"
    )

    # Custom Plugin Code (for CUSTOM source type)
    plugin_code = models.TextField(
        blank=True,
        help_text="Python code for custom collector plugin (must inherit from CollectorPlugin)"
    )

    # Additional Configuration
    config_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional source-specific configuration"
    )

    # Health & Monitoring
    health_status = models.CharField(
        max_length=20,
        choices=HEALTH_STATUS_CHOICES,
        default='unknown',
        help_text="Current health status of this source"
    )
    last_collection = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last successful collection"
    )
    last_error = models.TextField(
        blank=True,
        help_text="Last error message (if any)"
    )
    consecutive_failures = models.IntegerField(
        default=0,
        help_text="Number of consecutive collection failures"
    )
    total_collections = models.IntegerField(
        default=0,
        help_text="Total number of collection runs"
    )
    successful_collections = models.IntegerField(
        default=0,
        help_text="Number of successful collection runs"
    )
    total_items_collected = models.IntegerField(
        default=0,
        help_text="Total number of items collected from this source"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, blank=True, help_text="User who created this source")

    class Meta:
        ordering = ['name']
        verbose_name = "Crawler Source"
        verbose_name_plural = "Crawler Sources"

    def __str__(self):
        status = "✓" if self.enabled else "✗"
        return f"{status} {self.name} ({self.get_source_type_display()})"

    def clean(self):
        """Validate model fields."""
        super().clean()

        # Validate URL for RSS and API-based sources
        if self.source_type in ['rss', 'google_news', 'bbc', 'reuters', 'ap_news', 'al_jazeera', 'guardian']:
            if not self.url:
                raise ValidationError({'url': 'URL is required for this source type.'})

        # Validate custom plugin code
        if self.source_type == 'custom' and not self.plugin_code:
            raise ValidationError({'plugin_code': 'Plugin code is required for custom source type.'})

        # Validate cron expression (basic validation)
        if self.schedule:
            parts = self.schedule.split()
            if len(parts) not in [5, 6]:  # Standard cron or with seconds
                raise ValidationError({'schedule': 'Invalid cron expression. Expected 5 or 6 parts.'})

    def save(self, *args, **kwargs):
        """Custom save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def api_key(self):
        """Decrypt and return the API key."""
        if not self.api_key_encrypted:
            return None
        try:
            # Get encryption key from settings
            key = getattr(settings, 'CRAWLER_SOURCE_ENCRYPTION_KEY', None)
            if not key:
                return None
            fernet = Fernet(key.encode() if isinstance(key, str) else key)
            return fernet.decrypt(self.api_key_encrypted).decode()
        except Exception:
            return None

    @api_key.setter
    def api_key(self, value):
        """Encrypt and store the API key."""
        if not value:
            self.api_key_encrypted = None
            return
        try:
            # Get or generate encryption key
            key = getattr(settings, 'CRAWLER_SOURCE_ENCRYPTION_KEY', None)
            if not key:
                # Generate a key if not configured (for development)
                key = Fernet.generate_key()
            fernet = Fernet(key.encode() if isinstance(key, str) else key)
            self.api_key_encrypted = fernet.encrypt(value.encode())
        except Exception as e:
            raise ValueError(f"Failed to encrypt API key: {e}")

    @property
    def success_rate(self):
        """Calculate success rate as a percentage."""
        if self.total_collections == 0:
            return 0.0
        return (self.successful_collections / self.total_collections) * 100

    def record_collection_attempt(self, success=True, items_collected=0, error_message=""):
        """Record a collection attempt and update health metrics."""
        self.total_collections += 1

        if success:
            self.successful_collections += 1
            self.total_items_collected += items_collected
            self.last_collection = timezone.now()
            self.consecutive_failures = 0
            self.last_error = ""

            # Update health status
            if self.success_rate >= 95:
                self.health_status = 'healthy'
            elif self.success_rate >= 80:
                self.health_status = 'warning'
            else:
                self.health_status = 'unhealthy'
        else:
            self.consecutive_failures += 1
            self.last_error = error_message[:1000]  # Limit error message length

            # Update health status based on consecutive failures
            if self.consecutive_failures >= 5:
                self.health_status = 'unhealthy'
            elif self.consecutive_failures >= 3:
                self.health_status = 'warning'

        self.save()

    def test_connection(self):
        """Test connection to the source (to be implemented by collector)."""
        # This will be implemented in the dynamic loader
        # For now, return basic validation
        if self.source_type == 'rss' and self.url:
            return True, "URL configured"
        elif self.source_type == 'custom' and self.plugin_code:
            return True, "Plugin code provided"
        return False, "Incomplete configuration"

    def to_plugin_metadata(self):
        """Convert to PluginMetadata schema for compatibility."""
        return {
            'name': self.name,
            'version': '1.0',
            'author': self.created_by or 'system',
            'description': self.description,
            'source_type': self.source_type,
            'schedule': self.schedule,
            'enabled': self.enabled,
            'rate_limit': self.rate_limit,
            'timeout_seconds': self.timeout_seconds,
            'retry_count': self.retry_count,
        }


class TranslatedContent(models.Model):
    """
    Persistent storage for translations to reduce API costs.

    Stores translations from various providers with MD5 hash-based lookup
    for efficient duplicate detection and caching.

    Features:
    - Content-based deduplication using MD5 hash
    - Multi-provider support (LibreTranslate, OpenAI, DeepL)
    - Automatic timestamps for cache management
    - Indexed for fast lookups

    Usage:
        # Check if translation exists
        cached = TranslatedContent.objects.filter(
            source_text_hash=hash_value,
            source_language='en',
            target_language='zh'
        ).first()

        # Create new translation record
        TranslatedContent.objects.create(
            source_text_hash=hash_value,
            source_language='en',
            target_language='zh',
            translated_text='翻译后的文本',
            provider='libretranslate'
        )
    """

    # MD5 hash of source text for efficient lookups
    source_text_hash = models.CharField(
        max_length=32,
        help_text="MD5 hash of source text for deduplication"
    )

    # Language codes (ISO 639-1)
    source_language = models.CharField(
        max_length=10,
        help_text="Source language code (e.g., 'en', 'zh', 'auto')"
    )

    target_language = models.CharField(
        max_length=10,
        help_text="Target language code (e.g., 'en', 'zh', 'es')"
    )

    # Translation content
    translated_text = models.TextField(
        help_text="The translated text"
    )

    # Provider tracking
    provider = models.CharField(
        max_length=20,
        choices=[
            ('libretranslate', 'LibreTranslate'),
            ('openai', 'OpenAI'),
            ('deepl', 'DeepL'),
            ('google', 'Google Translate'),
            ('other', 'Other'),
        ],
        default='libretranslate',
        help_text="Translation provider used"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this translation was first cached"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this translation was last updated"
    )

    class Meta:
        # Ensure unique translation per source hash + language pair
        unique_together = [
            ['source_text_hash', 'source_language', 'target_language']
        ]

        # Indexes for fast lookups
        indexes = [
            models.Index(fields=['source_text_hash', 'target_language']),
            models.Index(fields=['target_language', 'created_at']),
            models.Index(fields=['provider', 'created_at']),
        ]

        ordering = ['-created_at']
        verbose_name = "Translated Content"
        verbose_name_plural = "Translated Contents"

    def __str__(self):
        return f"{self.source_language} → {self.target_language} ({self.provider}) - {self.source_text_hash[:8]}..."


# Import SystemSettings from separate module
from .models_system import SystemSettings

__all__ = [
    'CollectionRun',
    'CollectedTopic',
    'TrendCluster',
    'CrawlerSource',
    'TranslatedContent',
    'SystemSettings',
]
