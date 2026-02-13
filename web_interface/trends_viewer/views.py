from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import CollectionRun, CollectedTopic, TrendCluster
import asyncio
import logging

logger = logging.getLogger(__name__)


# Translation helper function
_translation_manager = None

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
    provider_pref = session.get('translation_provider', 'free')

    # Map preference to provider name
    if provider_pref == 'ai':
        # Try OpenAI first, then DeepL, then LibreTranslate as fallback
        return 'openai'  # TranslationManager will handle fallback
    else:
        # Use free provider (LibreTranslate)
        return 'libretranslate'


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

        # Run async translation in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
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
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Translation error for '{text[:50]}...': {e}")
        return text  # Return original text on error


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
        latest_trends = TrendCluster.objects.filter(
            collection_run=latest_run
        ).order_by('rank')[:10]

        # Translate trends if requested
        if target_lang != 'en':
            logger.info(f"Translating {len(latest_trends)} dashboard trends to {target_lang}")
            for trend in latest_trends:
                translate_trend(trend, target_lang, request.session)

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

        # Translate trends if requested
        if target_lang != 'en' and 'object_list' in context:
            logger.info(f"Translating {len(context['object_list'])} trends to {target_lang}")
            for trend in context['object_list']:
                translate_trend(trend, target_lang, self.request.session)

        return context


class TrendDetailView(DetailView):
    """View for showing details of a specific trend cluster."""
    model = TrendCluster
    template_name = 'trends_viewer/trend_detail.html'
    context_object_name = 'trend'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['topics'] = self.object.topics.all()

        # Language support (from middleware)
        target_lang = getattr(self.request, 'LANGUAGE_CODE', 'en')
        context['current_lang'] = target_lang

        # Translate trend and topics if requested
        if target_lang != 'en':
            logger.info(f"Translating trend detail to {target_lang}")
            translate_trend(self.object, target_lang, self.request.session)

            # Translate all topics in this trend
            for topic in context['topics']:
                translate_topic(topic, target_lang, self.request.session)

        return context


class TopicListView(ListView):
    """View for listing all collected topics grouped by cluster."""
    model = TrendCluster
    template_name = 'trends_viewer/topic_list.html'
    context_object_name = 'clusters'
    paginate_by = 20

    def get_queryset(self):
        # Get latest run or filter by run_id if specified
        run_id = self.request.GET.get('run')
        if run_id:
            queryset = TrendCluster.objects.filter(collection_run_id=run_id)
        else:
            latest_run = CollectionRun.objects.filter(status='completed').first()
            if latest_run:
                queryset = TrendCluster.objects.filter(collection_run=latest_run)
            else:
                queryset = TrendCluster.objects.none()

        # Filter by source if specified (filter topics within clusters)
        source = self.request.GET.get('source')
        if source:
            # This will be handled in the template to filter topics by source
            pass

        return queryset.order_by('rank')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get sources dynamically from collector registry
        from collectors import list_collector_names
        context['sources'] = sorted(list_collector_names())
        context['current_source'] = self.request.GET.get('source', '')
        context['all_runs'] = CollectionRun.objects.all()[:10]

        # Get current run
        run_id = self.request.GET.get('run')
        if run_id:
            context['current_run'] = get_object_or_404(CollectionRun, id=run_id)
        else:
            context['current_run'] = CollectionRun.objects.filter(status='completed').first()

        return context


class CollectionRunListView(ListView):
    """View for listing collection run history."""
    model = CollectionRun
    template_name = 'trends_viewer/collection_run_list.html'
    context_object_name = 'runs'
    paginate_by = 20
    ordering = ['-timestamp']
