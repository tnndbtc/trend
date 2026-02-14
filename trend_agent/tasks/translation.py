"""
Celery tasks for pre-translation of trends.

This module defines tasks for automatically translating newly collected trends
to popular languages (Chinese, Spanish, French, etc.) to improve user experience.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from celery import Task

from trend_agent.tasks import app

logger = logging.getLogger(__name__)


class TranslationTask(Task):
    """Base class for translation tasks with error handling."""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(
            f"Translation task {task_id} failed: {exc}\n"
            f"Args: {args}\n"
            f"Kwargs: {kwargs}\n"
            f"Info: {einfo}"
        )


@app.task(base=TranslationTask, name="trend_agent.tasks.translation.pre_translate_trends")
def pre_translate_trends(
    trend_ids: Optional[List[int]] = None,
    languages: Optional[List[str]] = None,
    collection_run_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Pre-translate trends to specified languages.

    This task runs automatically after trend collection to pre-populate
    translation caches with popular languages.

    Args:
        trend_ids: Specific trend IDs to translate (optional)
        languages: Languages to translate to (default: ['zh-Hans'])
        collection_run_id: ID of collection run to translate all trends from (optional)

    Returns:
        Dictionary with translation results
    """
    # Default to Chinese only
    if languages is None:
        languages = ['zh-Hans']

    logger.info(
        f"Starting pre-translation task for "
        f"{len(trend_ids) if trend_ids else 'all'} trends to {languages}"
    )

    try:
        result = asyncio.run(_pre_translate_trends_async(trend_ids, languages, collection_run_id))
        logger.info(
            f"Pre-translation complete: "
            f"{result['trends_translated']} trends translated to "
            f"{len(languages)} languages"
        )
        return result

    except Exception as e:
        logger.error(f"Pre-translation failed: {e}")
        raise


async def _pre_translate_trends_async(
    trend_ids: Optional[List[int]],
    languages: List[str],
    collection_run_id: Optional[int]
) -> Dict[str, Any]:
    """
    Async implementation of pre-translation.

    Args:
        trend_ids: Trend IDs to translate
        languages: Target languages
        collection_run_id: Collection run ID

    Returns:
        Dictionary with results
    """
    # Import Django models
    import os
    import sys
    import django

    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
    sys.path.insert(0, '/home/tnnd/data/code/trend')
    django.setup()

    from web_interface.trends_viewer.models import TrendCluster, CollectionRun
    from trend_agent.services import get_service_factory

    # Get translation manager
    factory = get_service_factory()
    manager = factory.get_translation_manager()

    # Get trends to translate
    if trend_ids:
        trends = list(TrendCluster.objects.filter(id__in=trend_ids))
    elif collection_run_id:
        trends = list(TrendCluster.objects.filter(collection_run_id=collection_run_id))
    else:
        # Get trends from latest completed run
        latest_run = CollectionRun.objects.filter(status='completed').first()
        if not latest_run:
            logger.warning("No completed collection runs found")
            return {
                "trends_translated": 0,
                "languages": languages,
                "timestamp": datetime.utcnow().isoformat(),
            }
        trends = list(TrendCluster.objects.filter(collection_run=latest_run))

    if not trends:
        logger.warning("No trends found to translate")
        return {
            "trends_translated": 0,
            "languages": languages,
            "timestamp": datetime.utcnow().isoformat(),
        }

    logger.info(f"Found {len(trends)} trends to pre-translate")

    # Collect all texts to translate for all trends
    total_translations = 0
    failed_translations = 0

    for target_lang in languages:
        # Normalize language code for LibreTranslate
        normalized_lang = _normalize_lang_code(target_lang)

        logger.info(f"Pre-translating {len(trends)} trends to {normalized_lang}")

        # Collect all texts from all trends
        texts_to_translate = []
        for trend in trends:
            texts_to_translate.append(trend.title)
            texts_to_translate.append(trend.summary or '')
            texts_to_translate.append(trend.full_summary or '')

        try:
            # Batch translate all texts at once
            translations = await manager.translate_batch(
                texts=texts_to_translate,
                target_language=normalized_lang,
                source_language='en',
                preferred_provider='deepl'  # Use DeepL for better quality
            )

            total_translations += len(translations)
            logger.info(
                f"Successfully translated {len(translations)} texts to {normalized_lang}"
            )

        except Exception as e:
            logger.error(f"Failed to translate to {normalized_lang}: {e}")
            failed_translations += len(texts_to_translate)

    return {
        "trends_translated": len(trends),
        "languages": languages,
        "total_translations": total_translations,
        "failed_translations": failed_translations,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _normalize_lang_code(lang_code: str) -> str:
    """
    Normalize language codes for translation services.

    Args:
        lang_code: Language code (e.g., 'zh-Hans', 'es')

    Returns:
        Normalized language code
    """
    lang_map = {
        'zh': 'zh-Hans',  # Simplified Chinese
        'zh-CN': 'zh-Hans',
        'zh-TW': 'zh-Hant',
    }
    return lang_map.get(lang_code, lang_code)


@app.task(base=TranslationTask, name="trend_agent.tasks.translation.pre_translate_after_collection")
def pre_translate_after_collection(collection_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automatically pre-translate trends after collection completes.

    This task is designed to be chained after collection tasks.

    Args:
        collection_result: Result from collection task

    Returns:
        Dictionary with translation results
    """
    logger.info("Starting automatic pre-translation after collection")

    # Extract collection run ID if available
    collection_run_id = collection_result.get('collection_run_id')

    # Trigger pre-translation for Chinese
    result = pre_translate_trends.delay(
        collection_run_id=collection_run_id,
        languages=['zh-Hans']  # Chinese only for now
    )

    # Wait for translation to complete (with timeout)
    try:
        translation_result = result.get(timeout=300)  # 5 minute timeout
        logger.info("Automatic pre-translation completed")
        return translation_result
    except Exception as e:
        logger.error(f"Automatic pre-translation failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.task(base=TranslationTask, name="trend_agent.tasks.translation.warm_translation_cache")
def warm_translation_cache(languages: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Warm up translation cache by pre-translating recent trends.

    This task can be run periodically to ensure popular content is always
    available in common languages.

    Args:
        languages: Languages to warm cache for (default: ['zh-Hans'])

    Returns:
        Dictionary with cache warming results
    """
    if languages is None:
        languages = ['zh-Hans']

    logger.info(f"Starting cache warming for languages: {languages}")

    try:
        # Import Django models
        import os
        import sys
        import django

        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
        sys.path.insert(0, '/home/tnnd/data/code/trend')
        django.setup()

        from web_interface.trends_viewer.models import TrendCluster, CollectionRun

        # Get top 50 trends from latest run
        latest_run = CollectionRun.objects.filter(status='completed').first()
        if not latest_run:
            logger.warning("No completed runs found for cache warming")
            return {
                "status": "skipped",
                "reason": "no_completed_runs",
                "timestamp": datetime.utcnow().isoformat(),
            }

        top_trends = list(
            TrendCluster.objects.filter(collection_run=latest_run)
            .order_by('rank')[:50]
        )
        trend_ids = [t.id for t in top_trends]

        # Trigger pre-translation
        result = pre_translate_trends.delay(
            trend_ids=trend_ids,
            languages=languages
        )

        # Wait for completion
        translation_result = result.get(timeout=300)

        logger.info("Cache warming completed")
        return translation_result

    except Exception as e:
        logger.error(f"Cache warming failed: {e}")
        raise


# Utility function to trigger pre-translation from views
def trigger_pre_translation(trend_ids: List[int], languages: List[str] = None) -> str:
    """
    Trigger pre-translation task and return task ID.

    Args:
        trend_ids: Trend IDs to translate
        languages: Languages to translate to

    Returns:
        Celery task ID
    """
    if languages is None:
        languages = ['zh-Hans']

    result = pre_translate_trends.delay(
        trend_ids=trend_ids,
        languages=languages
    )

    logger.info(f"Pre-translation task triggered: {result.id}")
    return result.id
