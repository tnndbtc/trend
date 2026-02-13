"""
System-wide settings model for Django admin configuration.

Provides database-backed configuration that can be changed at runtime
without rebuilding containers or restarting services.
"""

from django.db import models
from django.core.cache import cache
from django.core.validators import MinValueValidator, MaxValueValidator
import logging

logger = logging.getLogger(__name__)


class SystemSettings(models.Model):
    """
    Singleton model for system-wide settings.

    This model uses a singleton pattern (only one record with pk=1)
    to store global configuration that affects all users.

    Settings are cached to avoid repeated database queries.
    """

    # ============================================================================
    # Summarization Provider
    # ============================================================================

    SUMMARIZATION_PROVIDERS = [
        ('free', 'Free NLP Tools (Default) - Works offline, zero cost'),
        ('openai', 'OpenAI GPT - Paid API, high quality'),
        ('anthropic', 'Anthropic Claude - Paid API, high quality'),
    ]

    summarization_provider = models.CharField(
        max_length=20,
        choices=SUMMARIZATION_PROVIDERS,
        default='free',
        help_text='Summarization service to use. Free tools work offline with no API costs.',
        verbose_name='Summarization Provider'
    )

    # ============================================================================
    # Free NLP Configuration
    # ============================================================================

    FREE_ALGORITHMS = [
        ('textrank', 'TextRank - Graph-based ranking (recommended)'),
        ('lexrank', 'LexRank - Graph-based with cosine similarity'),
        ('lsa', 'LSA - Latent Semantic Analysis'),
        ('luhn', 'Luhn - Word frequency based (fastest)'),
        ('kl', 'KL - Kullback-Leibler divergence'),
    ]

    free_summarization_algorithm = models.CharField(
        max_length=20,
        choices=FREE_ALGORITHMS,
        default='textrank',
        help_text='Algorithm to use when free summarization is selected',
        verbose_name='Free NLP Algorithm'
    )

    # ============================================================================
    # Summary Length Configuration
    # ============================================================================

    max_summary_length = models.IntegerField(
        default=200,
        validators=[MinValueValidator(50), MaxValueValidator(1000)],
        help_text='Maximum characters in full_summary field',
        verbose_name='Maximum Summary Length'
    )

    title_summary_length = models.IntegerField(
        default=80,
        validators=[MinValueValidator(20), MaxValueValidator(200)],
        help_text='Maximum characters in title_summary field',
        verbose_name='Title Summary Length'
    )

    key_points_count = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text='Number of key points to extract per topic',
        verbose_name='Key Points Count'
    )

    # ============================================================================
    # OpenAI Configuration (when using OpenAI provider)
    # ============================================================================

    openai_model = models.CharField(
        max_length=50,
        default='gpt-4-turbo',
        blank=True,
        help_text='OpenAI model to use (e.g., gpt-4-turbo, gpt-3.5-turbo)',
        verbose_name='OpenAI Model'
    )

    openai_temperature = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
        help_text='Temperature for OpenAI generation (0=deterministic, 2=creative)',
        verbose_name='OpenAI Temperature'
    )

    # ============================================================================
    # Anthropic Configuration (when using Anthropic provider)
    # ============================================================================

    anthropic_model = models.CharField(
        max_length=50,
        default='claude-3-sonnet-20240229',
        blank=True,
        help_text='Anthropic model to use (e.g., claude-3-sonnet, claude-3-opus)',
        verbose_name='Anthropic Model'
    )

    # ============================================================================
    # Performance Settings
    # ============================================================================

    batch_size = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text='Number of items to process in parallel',
        verbose_name='Batch Processing Size'
    )

    celery_worker_concurrency = models.IntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(32)],
        help_text=(
            'Number of concurrent Celery workers for translation tasks. '
            'Higher = faster translations but more CPU/memory usage. '
            'Recommended: 2x CPU cores for I/O-bound tasks. '
            'Requires worker restart to apply changes.'
        ),
        verbose_name='Translation Worker Concurrency'
    )

    enable_summarization_cache = models.BooleanField(
        default=True,
        help_text='Cache generated summaries to avoid re-processing',
        verbose_name='Enable Summary Caching'
    )

    # ============================================================================
    # Cost Tracking
    # ============================================================================

    estimated_monthly_api_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        editable=False,
        help_text='Estimated monthly cost based on current provider (auto-calculated)',
        verbose_name='Estimated Monthly Cost (USD)'
    )

    total_summaries_generated = models.IntegerField(
        default=0,
        editable=False,
        help_text='Total summaries generated since last reset',
        verbose_name='Total Summaries Generated'
    )

    # ============================================================================
    # Data Retention Settings
    # ============================================================================

    data_retention_days = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text='Automatically delete collection runs older than N days (default: 7)',
        verbose_name='Data Retention Period (Days)'
    )

    enable_auto_cleanup = models.BooleanField(
        default=True,
        help_text='Automatically clean up old data daily at 3:00 AM',
        verbose_name='Enable Automatic Cleanup'
    )

    last_cleanup_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text='Timestamp of last successful cleanup operation',
        verbose_name='Last Cleanup Time'
    )

    total_records_cleaned = models.IntegerField(
        default=0,
        editable=False,
        help_text='Total collection runs deleted since installation',
        verbose_name='Total Records Cleaned'
    )

    # ============================================================================
    # Metadata
    # ============================================================================

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Last Updated'
    )

    updated_by = models.CharField(
        max_length=100,
        blank=True,
        help_text='Username of last person to update settings',
        verbose_name='Updated By'
    )

    notes = models.TextField(
        blank=True,
        help_text='Internal notes about current configuration',
        verbose_name='Configuration Notes'
    )

    # ============================================================================
    # Model Meta
    # ============================================================================

    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
        db_table = 'system_settings'

    # ============================================================================
    # Singleton Pattern
    # ============================================================================

    def save(self, *args, **kwargs):
        """
        Ensure singleton pattern - only one settings record (pk=1).
        Clear cache when settings change.
        """
        self.pk = 1
        super().save(*args, **kwargs)

        # Clear cache to force reload
        cache.delete('system_settings')

        logger.info(f"System settings updated by {self.updated_by or 'unknown'}")

    def delete(self, *args, **kwargs):
        """Prevent deletion of settings record."""
        logger.warning("Attempted to delete SystemSettings - operation blocked")
        pass

    @classmethod
    def load(cls):
        """
        Load system settings with caching.

        Returns:
            SystemSettings instance (creates if doesn't exist)
        """
        # Try cache first
        settings = cache.get('system_settings')

        if settings is None:
            # Load from database
            settings, created = cls.objects.get_or_create(pk=1)

            if created:
                logger.info("Created new SystemSettings with defaults")

            # Cache for 1 hour
            cache.set('system_settings', settings, timeout=3600)

        return settings

    # Deprecated alias for backward compatibility
    @classmethod
    def get_settings(cls):
        """Deprecated: Use load() instead."""
        return cls.load()

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def is_free_provider(self) -> bool:
        """Check if using free summarization."""
        return self.summarization_provider == 'free'

    def is_paid_provider(self) -> bool:
        """Check if using paid API."""
        return self.summarization_provider in ['openai', 'anthropic']

    def get_provider_display_with_cost(self) -> str:
        """Get provider display name with cost indicator."""
        display = self.get_summarization_provider_display()

        if self.is_free_provider():
            return f"{display} (FREE)"
        else:
            return f"{display} (${self.estimated_monthly_api_cost:.2f}/month)"

    def estimate_cost_per_summary(self) -> float:
        """
        Estimate cost per summary based on provider.

        Returns:
            Cost in USD per summary
        """
        if self.summarization_provider == 'free':
            return 0.0
        elif self.summarization_provider == 'openai':
            # GPT-4-turbo: ~$0.01 input + $0.03 output per 1K tokens
            # Average summary: 500 input tokens, 100 output tokens
            # Cost: (500 * 0.01 + 100 * 0.03) / 1000 = $0.008
            return 0.008
        elif self.summarization_provider == 'anthropic':
            # Claude-3-Sonnet: ~$0.003 input + $0.015 output per 1K tokens
            # Cost: (500 * 0.003 + 100 * 0.015) / 1000 = $0.003
            return 0.003
        else:
            return 0.0

    def update_cost_estimate(self, summaries_generated: int = 0):
        """
        Update cost estimate based on usage.

        Args:
            summaries_generated: Number of new summaries generated
        """
        if summaries_generated > 0:
            self.total_summaries_generated += summaries_generated

        # Estimate monthly cost (assume 1000 summaries/day)
        cost_per_summary = self.estimate_cost_per_summary()
        daily_summaries = 1000
        self.estimated_monthly_api_cost = cost_per_summary * daily_summaries * 30

        self.save()

    def reset_counters(self):
        """Reset usage counters."""
        self.total_summaries_generated = 0
        self.estimated_monthly_api_cost = 0.0
        self.save()

    # ============================================================================
    # String Representation
    # ============================================================================

    def __str__(self):
        return f"System Settings (Provider: {self.get_summarization_provider_display()})"

    def __repr__(self):
        return f"<SystemSettings pk=1 provider={self.summarization_provider}>"
