"""
Celery tasks for background processing.

This module contains Celery tasks for asynchronous operations like:
- Pre-translation of trends after crawls
- Bulk translation operations
- Translation cache warming
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction

from .models import TrendCluster, TrendTranslationStatus
from .views import translate_trends_batch, translate_topics_batch, normalize_lang_code

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def pre_translate_trends(self, trend_ids, target_lang='zh-Hans'):
    """
    Background task to pre-translate trends to a target language.

    This task is called automatically after crawls or manually by admins.
    It translates both the trend and all its topics.

    Args:
        trend_ids: List of TrendCluster IDs to translate
        target_lang: Target language code (default: 'zh-Hans' for Chinese)

    Returns:
        dict: Summary of translation results
    """
    # Normalize language code to ensure consistency (e.g., 'zh' -> 'zh-Hans')
    normalized_lang = normalize_lang_code(target_lang)
    logger.info(f"[PRE-TRANSLATE] Starting translation of {len(trend_ids)} trends to {normalized_lang} (from {target_lang})")

    translated_count = 0
    failed_count = 0
    total_topics = 0

    for trend_id in trend_ids:
        try:
            # Fetch trend with prefetched topics
            trend = TrendCluster.objects.prefetch_related('topics').get(id=trend_id)

            # Check if already translated
            status, created = TrendTranslationStatus.objects.get_or_create(
                trend=trend,
                language=normalized_lang,
                defaults={'translated': False}
            )

            if status.translated:
                logger.info(f"[PRE-TRANSLATE] Trend {trend_id} already translated to {normalized_lang}, skipping")
                continue

            # Translate trend fields
            logger.info(f"[PRE-TRANSLATE] Translating trend {trend_id} to {normalized_lang}")
            translate_trends_batch([trend], normalized_lang, session=None)

            # Translate all topics
            topics = list(trend.topics.all())
            if topics:
                logger.info(f"[PRE-TRANSLATE] Translating {len(topics)} topics for trend {trend_id}")
                translate_topics_batch(topics, normalized_lang, session=None)
                total_topics += len(topics)

            # Update translation status
            with transaction.atomic():
                status.translated = True
                status.translated_at = timezone.now()
                status.topics_count = len(topics)
                status.save()

            translated_count += 1
            logger.info(f"[PRE-TRANSLATE] ✓ Trend {trend_id} translated successfully")

        except TrendCluster.DoesNotExist:
            logger.error(f"[PRE-TRANSLATE] Trend {trend_id} not found")
            failed_count += 1

        except Exception as e:
            logger.error(f"[PRE-TRANSLATE] Error translating trend {trend_id}: {e}")
            failed_count += 1

            # Retry with exponential backoff
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    result = {
        'status': 'completed',
        'translated_count': translated_count,
        'failed_count': failed_count,
        'total_topics': total_topics,
        'target_lang': normalized_lang
    }

    logger.info(f"[PRE-TRANSLATE] Completed: {translated_count} trends, {total_topics} topics to {normalized_lang}")
    return result


@shared_task
def bulk_translate_all_trends(target_lang='zh-Hans', days_back=None):
    """
    Bulk translate all trends (or recent trends) to a target language.

    Called from admin dashboard for manual bulk translation.

    Args:
        target_lang: Target language code
        days_back: If provided, only translate trends from last N days

    Returns:
        dict: Summary of translation job
    """
    # Normalize language code to ensure consistency
    normalized_lang = normalize_lang_code(target_lang)
    logger.info(f"[BULK-TRANSLATE] Starting bulk translation to {normalized_lang} (from {target_lang})")

    # Build queryset
    queryset = TrendCluster.objects.all()

    if days_back:
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=days_back)
        queryset = queryset.filter(created_at__gte=cutoff)

    # Get trends that haven't been translated yet
    translated_ids = TrendTranslationStatus.objects.filter(
        language=normalized_lang,
        translated=True
    ).values_list('trend_id', flat=True)

    trends_to_translate = queryset.exclude(id__in=translated_ids)
    trend_ids = list(trends_to_translate.values_list('id', flat=True))

    logger.info(f"[BULK-TRANSLATE] Found {len(trend_ids)} trends to translate to {normalized_lang}")

    if not trend_ids:
        return {
            'status': 'no_trends',
            'message': f'All trends already translated to {normalized_lang}'
        }

    # Queue the translation task (pass normalized language code)
    result = pre_translate_trends.delay(trend_ids, normalized_lang)

    return {
        'status': 'queued',
        'task_id': result.id,
        'trend_count': len(trend_ids),
        'target_lang': normalized_lang
    }


@shared_task
def translate_single_trend(trend_id, target_lang='zh-Hans'):
    """
    Translate a single trend to a target language.

    Called from admin detail page for individual trend translation.

    Args:
        trend_id: TrendCluster ID
        target_lang: Target language code

    Returns:
        dict: Translation result
    """
    # Normalize language code to ensure consistency
    normalized_lang = normalize_lang_code(target_lang)
    logger.info(f"[SINGLE-TRANSLATE] Translating trend {trend_id} to {normalized_lang} (from {target_lang})")

    result = pre_translate_trends.delay([trend_id], normalized_lang)

    return {
        'status': 'queued',
        'task_id': result.id,
        'trend_id': trend_id,
        'target_lang': normalized_lang
    }
