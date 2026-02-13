from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from .models import CollectionRun, CollectedTopic, TrendCluster
import asyncio
import logging
import threading
import hashlib

logger = logging.getLogger(__name__)


# Translation helper function
_translation_manager = None
# Thread-local storage for event loops (to avoid creating new loops for each translation)
_thread_local = threading.local()


def get_or_create_event_loop():
    """
    Get or create an event loop for the current thread.

    This reuses event loops within the same thread instead of creating
    a new one for each translation, significantly reducing overhead.

    Returns:
        asyncio event loop instance
    """
    if not hasattr(_thread_local, 'loop') or _thread_local.loop is None or _thread_local.loop.is_closed():
        _thread_local.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_thread_local.loop)
        logger.debug("Created new event loop for thread")
    return _thread_local.loop


def get_translation_manager():
    """Get or create translation manager instance (lazy initialization)."""
    global _translation_manager
    if _translation_manager is None:
        try:
            from trend_agent.services import get_service_factory
            factory = get_service_factory()
            _translation_manager = factory.get_translation_manager()
            logger.info("Translation manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize translation manager: {e}")
            _translation_manager = None
    return _translation_manager


def normalize_lang_code(lang_code):
    """
    Normalize language codes for LibreTranslate compatibility.

    LibreTranslate uses zh-Hans for Simplified Chinese instead of zh.
    """
    lang_map = {
        'zh': 'zh-Hans',  # Simplified Chinese for LibreTranslate
        'zh-CN': 'zh-Hans',
        'zh-TW': 'zh-Hant',
    }
    return lang_map.get(lang_code, lang_code)


def get_preferred_provider(session):
    """
    Get preferred translation provider from session.

    Args:
        session: Django request session

    Returns:
        Preferred provider name or None
    """
    provider_pref = session.get('translation_provider', 'ai')  # Default to AI (DeepL)

    # Map preference to provider name
    if provider_pref == 'ai':
        # Use DeepL for best quality, fallback to OpenAI, then LibreTranslate
        return 'deepl'  # TranslationManager will handle fallback
    else:
        # Use free provider (LibreTranslate)
        return 'libretranslate'


# ============================================================================
# Page-Level Caching Utilities
# ============================================================================

def make_cache_key(prefix, trend_id, lang='en', version=1):
    """
    Generate a cache key for trend pages.

    Args:
        prefix: Cache key prefix (e.g., 'trend_detail')
        trend_id: Trend ID
        lang: Language code
        version: Cache version (increment to invalidate all caches)

    Returns:
        Cache key string
    """
    return f"{prefix}:{trend_id}:{lang}:v{version}"


def get_cached_translation_context(trend_id, lang='en'):
    """
    Get cached translation context for a trend.

    This caches the entire translated trend + topics to avoid
    redundant cache lookups for individual text fragments.

    Args:
        trend_id: Trend ID
        lang: Language code

    Returns:
        Cached context dict or None if not cached
    """
    cache_key = make_cache_key('translated_trend', trend_id, lang)
    return cache.get(cache_key)


def set_cached_translation_context(trend_id, lang, context_data, timeout=3600):
    """
    Cache translation context for a trend.

    Args:
        trend_id: Trend ID
        lang: Language code
        context_data: Context dict containing trend and topics
        timeout: Cache timeout in seconds (default: 1 hour)
    """
    cache_key = make_cache_key('translated_trend', trend_id, lang)
    cache.set(cache_key, context_data, timeout)
    logger.info(f"Cached translation context for trend {trend_id} in {lang}")


def invalidate_trend_cache(trend_id):
    """
    Invalidate all cached versions of a trend across all languages.

    This should be called when a trend is updated.

    Args:
        trend_id: Trend ID to invalidate
    """
    languages = ['en', 'zh', 'es', 'fr', 'de', 'ja', 'ko']  # Common languages
    for lang in languages:
        # Invalidate page cache
        page_cache_key = make_cache_key('trend_detail', trend_id, lang)
        cache.delete(page_cache_key)

        # Invalidate translation context cache
        trans_cache_key = make_cache_key('translated_trend', trend_id, lang)
        cache.delete(trans_cache_key)

    logger.info(f"Invalidated all caches for trend {trend_id}")


def translate_text_sync(text, target_lang='zh', session=None):
    """
    Synchronously translate text to target language.

    Args:
        text: Text to translate
        target_lang: Target language code (default: 'zh' for Chinese)
        session: Django session (optional, for provider preference)

    Returns:
        Translated text, or original text if translation fails
    """
    if not text or target_lang == 'en':
        return text

    try:
        manager = get_translation_manager()
        if not manager:
            logger.warning("Translation manager not available")
            return text

        # Get preferred provider from session
        preferred_provider = get_preferred_provider(session) if session else None

        # Normalize language code for LibreTranslate
        normalized_lang = normalize_lang_code(target_lang)
        logger.info(f"Translating text to {normalized_lang} (original: {target_lang}, provider: {preferred_provider})")

        # Run async translation in sync context using reusable event loop
        loop = get_or_create_event_loop()
        translated = loop.run_until_complete(
            manager.translate(
                text,
                normalized_lang,
                source_language='en',
                preferred_provider=preferred_provider
            )
        )
        logger.info(f"Translation successful: '{text[:50]}...' -> '{translated[:50]}...'")
        return translated
    except Exception as e:
        logger.error(f"Translation error for '{text[:50]}...': {e}")
        return text  # Return original text on error


def translate_texts_batch(texts, target_lang='zh', session=None):
    """
    Batch translate multiple texts to target language.

    This is much more efficient than translating texts one by one,
    as it makes a single API call instead of multiple sequential calls.

    Args:
        texts: List of text strings to translate
        target_lang: Target language code (default: 'zh' for Chinese)
        session: Django session (optional, for provider preference)

    Returns:
        List of translated texts in the same order as input
    """
    if not texts or target_lang == 'en':
        return texts

    # Filter out None/empty texts and track their original positions
    text_map = {}  # position -> original text
    texts_to_translate = []
    for i, text in enumerate(texts):
        if text:
            text_map[i] = text
            texts_to_translate.append(text)

    if not texts_to_translate:
        return texts

    try:
        manager = get_translation_manager()
        if not manager:
            logger.warning("Translation manager not available")
            return texts

        # Get preferred provider from session
        preferred_provider = get_preferred_provider(session) if session else None

        # Normalize language code
        normalized_lang = normalize_lang_code(target_lang)
        logger.info(f"Batch translating {len(texts_to_translate)} texts to {normalized_lang}")

        # Run async batch translation using reusable event loop
        loop = get_or_create_event_loop()
        translations = loop.run_until_complete(
            manager.translate_batch(
                texts=texts_to_translate,
                target_language=normalized_lang,
                source_language='en',
                preferred_provider=preferred_provider
            )
        )

        # Map translations back to original positions
        result = list(texts)  # Copy original list
        translation_idx = 0
        for i in text_map:
            if translation_idx < len(translations):
                result[i] = translations[translation_idx]
                translation_idx += 1

        logger.info(f"Batch translation successful: {len(translations)} texts translated")
        return result

    except Exception as e:
        logger.error(f"Batch translation error: {e}")
        return texts  # Return original texts on error


@require_POST
def set_translation_provider(request):
    """
    AJAX endpoint to set translation provider preference.

    Sets session variable 'translation_provider' to either 'free' or 'ai'.

    Args:
        request: HTTP request with POST data containing 'provider'

    Returns:
        JsonResponse with status
    """
    try:
        provider = request.POST.get('provider', 'free')

        # Validate provider value
        if provider not in ['free', 'ai']:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid provider value'
            }, status=400)

        # Store in session
        request.session['translation_provider'] = provider

        provider_name = 'FREE (LibreTranslate)' if provider == 'free' else 'AI (OpenAI/DeepL)'
        logger.info(f"Translation provider updated to: {provider_name}")

        return JsonResponse({
            'status': 'success',
            'provider': provider,
            'provider_name': provider_name
        })

    except Exception as e:
        logger.error(f"Error setting translation provider: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def translate_trend(trend, target_lang='zh', session=None):
    """
    Translate a TrendCluster object to target language.

    Args:
        trend: TrendCluster instance
        target_lang: Target language code
        session: Django session (optional, for provider preference)

    Returns:
        Modified trend object with translated fields
    """
    if target_lang == 'en' or not trend:
        return trend

    try:
        # Translate title and summary
        trend.title = translate_text_sync(trend.title, target_lang, session)
        if trend.summary:
            trend.summary = translate_text_sync(trend.summary, target_lang, session)
        if trend.full_summary:
            trend.full_summary = translate_text_sync(trend.full_summary, target_lang, session)

        # Mark as translated (for UI display)
        trend.is_translated = True
        trend.translation_lang = target_lang
    except Exception as e:
        logger.error(f"Error translating trend: {e}")
        trend.is_translated = False

    return trend


def translate_topic(topic, target_lang='zh', session=None):
    """
    Translate a CollectedTopic object to target language.

    Args:
        topic: CollectedTopic instance
        target_lang: Target language code
        session: Django session (optional, for provider preference)

    Returns:
        Modified topic object with translated fields
    """
    if target_lang == 'en' or not topic:
        return topic

    try:
        # Translate title and description
        topic.title = translate_text_sync(topic.title, target_lang, session)
        if topic.description:
            topic.description = translate_text_sync(topic.description, target_lang, session)
        if topic.title_summary:
            topic.title_summary = translate_text_sync(topic.title_summary, target_lang, session)

        # Mark as translated
        topic.is_translated = True
        topic.translation_lang = target_lang
    except Exception as e:
        logger.error(f"Error translating topic: {e}")
        topic.is_translated = False

    return topic


def translate_trends_batch(trends, target_lang='zh', session=None):
    """
    Batch translate multiple TrendCluster objects to target language.

    This is significantly faster than translating trends one by one.

    Args:
        trends: List of TrendCluster instances
        target_lang: Target language code
        session: Django session (optional, for provider preference)

    Returns:
        List of modified trend objects with translated fields
    """
    if target_lang == 'en' or not trends:
        return trends

    try:
        # Collect all texts to translate
        texts_to_translate = []
        for trend in trends:
            texts_to_translate.append(trend.title)
            texts_to_translate.append(trend.summary or '')
            texts_to_translate.append(trend.full_summary or '')

        # Batch translate all texts at once
        translations = translate_texts_batch(texts_to_translate, target_lang, session)

        # Map translations back to trends
        idx = 0
        for trend in trends:
            trend.title = translations[idx] or trend.title
            trend.summary = translations[idx + 1] or trend.summary
            trend.full_summary = translations[idx + 2] or trend.full_summary
            idx += 3

            # Mark as translated
            trend.is_translated = True
            trend.translation_lang = target_lang

        logger.info(f"Batch translated {len(trends)} trends successfully")
        return trends

    except Exception as e:
        logger.error(f"Error batch translating trends: {e}")
        # Mark all as not translated on error
        for trend in trends:
            trend.is_translated = False
        return trends


def translate_topics_batch(topics, target_lang='zh', session=None):
    """
    Batch translate multiple CollectedTopic objects to target language.

    This is significantly faster than translating topics one by one.

    Args:
        topics: List of CollectedTopic instances
        target_lang: Target language code
        session: Django session (optional, for provider preference)

    Returns:
        List of modified topic objects with translated fields
    """
    if target_lang == 'en' or not topics:
        return topics

    try:
        # Collect all texts to translate
        texts_to_translate = []
        for topic in topics:
            texts_to_translate.append(topic.title)
            texts_to_translate.append(topic.description or '')
            texts_to_translate.append(topic.title_summary or '')

        # Batch translate all texts at once
        translations = translate_texts_batch(texts_to_translate, target_lang, session)

        # Map translations back to topics
        idx = 0
        for topic in topics:
            topic.title = translations[idx] or topic.title
            topic.description = translations[idx + 1] or topic.description
            topic.title_summary = translations[idx + 2] or topic.title_summary
            idx += 3

            # Mark as translated
            topic.is_translated = True
            topic.translation_lang = target_lang

        logger.info(f"Batch translated {len(topics)} topics successfully")
        return topics

    except Exception as e:
        logger.error(f"Error batch translating topics: {e}")
        # Mark all as not translated on error
        for topic in topics:
            topic.is_translated = False
        return topics


def dashboard(request):
    """Dashboard view showing overview of recent collection runs."""
    recent_runs = CollectionRun.objects.all()[:5]
    latest_run = recent_runs.first() if recent_runs else None

    # Get stats from latest run
    stats = {
        'total_runs': CollectionRun.objects.count(),
        'latest_run': latest_run,
        'recent_runs': recent_runs,
    }

    # Language support (from middleware)
    target_lang = getattr(request, 'LANGUAGE_CODE', 'en')
    stats['current_lang'] = target_lang

    if latest_run:
        latest_trends = list(TrendCluster.objects.filter(
            collection_run=latest_run
        ).order_by('rank')[:10])

        # Translate trends if requested (using batch translation for performance)
        if target_lang != 'en' and latest_trends:
            logger.info(f"Batch translating {len(latest_trends)} dashboard trends to {target_lang}")
            translate_trends_batch(latest_trends, target_lang, request.session)

        stats['latest_trends'] = latest_trends

    return render(request, 'trends_viewer/dashboard.html', stats)


class TrendListView(ListView):
    """View for listing all trends from the latest collection run."""
    model = TrendCluster
    template_name = 'trends_viewer/trend_list.html'
    context_object_name = 'trends'
    paginate_by = 20

    def get_queryset(self):
        run_id = self.request.GET.get('run')
        if run_id:
            return TrendCluster.objects.filter(collection_run_id=run_id).order_by('rank')
        # Get latest run's trends
        latest_run = CollectionRun.objects.filter(status='completed').first()
        if latest_run:
            return TrendCluster.objects.filter(collection_run=latest_run).order_by('rank')
        return TrendCluster.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        run_id = self.request.GET.get('run')
        if run_id:
            context['current_run'] = get_object_or_404(CollectionRun, id=run_id)
        else:
            context['current_run'] = CollectionRun.objects.filter(status='completed').first()
        context['all_runs'] = CollectionRun.objects.all()[:10]

        # Language support (from middleware)
        target_lang = getattr(self.request, 'LANGUAGE_CODE', 'en')
        context['current_lang'] = target_lang

        # Translate trends if requested (using batch translation for performance)
        if target_lang != 'en' and 'object_list' in context:
            trends_list = list(context['object_list'])
            if trends_list:
                logger.info(f"Batch translating {len(trends_list)} trends to {target_lang}")
                translate_trends_batch(trends_list, target_lang, self.request.session)
                # Update context with translated trends
                context['object_list'] = trends_list

        return context


class TrendDetailView(DetailView):
    """View for showing details of a specific trend cluster."""
    model = TrendCluster
    template_name = 'trends_viewer/trend_detail.html'
    context_object_name = 'trend'

    def get_queryset(self):
        """Optimize query with prefetch_related to avoid N+1 queries."""
        return TrendCluster.objects.prefetch_related('topics')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Language support (from middleware)
        target_lang = getattr(self.request, 'LANGUAGE_CODE', 'en')
        context['current_lang'] = target_lang

        # Get topics (already prefetched, so no extra query)
        topics_list = list(self.object.topics.all())
        context['topics'] = topics_list

        # Server-side translation: Translate content before rendering
        # No English flash - content loads directly in requested language
        if target_lang != 'en':
            cached_context = get_cached_translation_context(self.object.id, target_lang)
            if cached_context:
                logger.info(f"✅ Cache HIT: Using cached translation for trend {self.object.id} ({target_lang})")
                context['trend'] = cached_context['trend']
                context['topics'] = cached_context['topics']
                return context

            logger.info(f"⚠️  Cache MISS: Translating trend {self.object.id} to {target_lang}")
            translate_trends_batch([self.object], target_lang, self.request.session)
            if topics_list:
                translate_topics_batch(topics_list, target_lang, self.request.session)

            translation_context = {
                'trend': self.object,
                'topics': topics_list
            }
            set_cached_translation_context(self.object.id, target_lang, translation_context)

        return context


class CollectionRunListView(ListView):
    """View for listing collection run history."""
    model = CollectionRun
    template_name = 'trends_viewer/collection_run_list.html'
    context_object_name = 'runs'
    paginate_by = 20
    ordering = ['-timestamp']
