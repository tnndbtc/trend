"""
Django signals for cache invalidation.

This module handles automatic cache invalidation when trends are updated or deleted.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import TrendCluster
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TrendCluster)
def invalidate_trend_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate cached translations when a trend is saved.

    This ensures users always see the latest content after updates.

    Args:
        sender: The model class (TrendCluster)
        instance: The actual trend instance being saved
        created: Boolean indicating if this is a new record
        **kwargs: Additional signal arguments
    """
    # Import here to avoid circular imports
    from .views import invalidate_trend_cache

    if not created:  # Only invalidate on update, not on creation
        logger.info(f"Trend {instance.id} updated - invalidating caches")
        invalidate_trend_cache(instance.id)


@receiver(post_delete, sender=TrendCluster)
def invalidate_trend_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate cached translations when a trend is deleted.

    Args:
        sender: The model class (TrendCluster)
        instance: The trend instance being deleted
        **kwargs: Additional signal arguments
    """
    # Import here to avoid circular imports
    from .views import invalidate_trend_cache

    logger.info(f"Trend {instance.id} deleted - invalidating caches")
    invalidate_trend_cache(instance.id)
