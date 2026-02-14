"""
Admin interface for translation management.

Provides:
- Translation status tracking
- Bulk translation actions
- Translation dashboard
- Per-trend translation controls
"""

import logging
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings

from .models import TrendTranslationStatus, TrendCluster
from .tasks import pre_translate_trends, bulk_translate_all_trends, translate_single_trend
from .views import normalize_lang_code

logger = logging.getLogger(__name__)


@admin.register(TrendTranslationStatus)
class TrendTranslationStatusAdmin(admin.ModelAdmin):
    """Admin interface for translation status tracking."""

    list_display = [
        'status_indicator',
        'trend_link',
        'language_display',
        'translated',
        'topics_count_display',
        'cost_display',
        'translated_at',
    ]

    list_filter = [
        'language',
        'translated',
        'translated_at',
    ]

    search_fields = [
        'trend__title',
        'trend__id',
    ]

    readonly_fields = [
        'trend',
        'language',
        'translated',
        'translated_at',
        'translation_cost',
        'topics_count',
    ]

    # Custom display methods
    def status_indicator(self, obj):
        """Show visual status indicator."""
        if obj.translated:
            return format_html('<span style="color: green; font-size: 18px;">✓</span>')
        return format_html('<span style="color: red; font-size: 18px;">✗</span>')
    status_indicator.short_description = 'Status'

    def trend_link(self, obj):
        """Show trend as clickable link."""
        url = reverse('admin:trends_viewer_trendcluster_change', args=[obj.trend.id])
        return format_html(
            '<a href="{}">Trend #{}: {}</a>',
            url,
            obj.trend.id,
            obj.trend.title[:50]
        )
    trend_link.short_description = 'Trend'

    def language_display(self, obj):
        """Display language with flag emoji."""
        lang_names = dict(settings.TRANSLATION_PRIORITY_LANGUAGES)
        lang_name = lang_names.get(obj.language, obj.language.upper())
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            lang_name
        )
    language_display.short_description = 'Language'

    def topics_count_display(self, obj):
        """Display topics count."""
        return format_html('<span style="font-weight: bold;">{}</span>', obj.topics_count)
    topics_count_display.short_description = 'Topics'

    def cost_display(self, obj):
        """Display translation cost."""
        if obj.translation_cost > 0:
            return format_html(
                '<span style="color: #ff9800;">${:.4f}</span>',
                obj.translation_cost
            )
        return format_html('<span style="color: #28a745;">$0.00</span>')
    cost_display.short_description = 'Cost'


def get_translation_dashboard_urls(admin_site):
    """
    Generate URLs for translation dashboard.
    This is imported and added to admin URLs in admin.py
    """
    return [
        path(
            'translation-dashboard/',
            admin_site.admin_view(translation_dashboard_view),
            name='translation_dashboard'
        ),
        path(
            'translation-dashboard/stats/',
            admin_site.admin_view(translation_stats_api),
            name='translation_stats_api'
        ),
        path(
            'translation-dashboard/bulk-translate/',
            admin_site.admin_view(bulk_translate_view),
            name='bulk_translate'
        ),
        path(
            'translation-dashboard/translate-trend/<int:trend_id>/',
            admin_site.admin_view(translate_trend_view),
            name='translate_trend'
        ),
    ]


def translation_dashboard_view(request):
    """
    Translation Dashboard - main admin page for translation management.

    Shows:
    - Translation coverage by language
    - Recent translations
    - Bulk translation controls
    - Cost estimates
    """
    from django.utils import timezone
    from datetime import timedelta

    # Get translation statistics
    stats = {}
    for lang_code, lang_name in settings.TRANSLATION_PRIORITY_LANGUAGES:
        # Normalize language code to match database format (e.g., 'zh' -> 'zh-Hans')
        normalized_lang = normalize_lang_code(lang_code)

        total_trends = TrendCluster.objects.count()
        translated_trends = TrendTranslationStatus.objects.filter(
            language=normalized_lang,
            translated=True
        ).count()

        coverage_percent = (translated_trends / total_trends * 100) if total_trends > 0 else 0

        stats[lang_code] = {
            'name': lang_name,
            'translated': translated_trends,
            'total': total_trends,
            'coverage': coverage_percent,
            'untranslated': total_trends - translated_trends,
        }

    # Get recent translations (last 24 hours)
    recent_cutoff = timezone.now() - timedelta(hours=24)
    recent_translations = TrendTranslationStatus.objects.filter(
        translated=True,
        translated_at__gte=recent_cutoff
    ).select_related('trend').order_by('-translated_at')[:20]

    # Calculate daily translation activity
    daily_stats = {}
    for lang_code, lang_name in settings.TRANSLATION_PRIORITY_LANGUAGES:
        # Normalize language code to match database format
        normalized_lang = normalize_lang_code(lang_code)

        count = TrendTranslationStatus.objects.filter(
            language=normalized_lang,
            translated_at__gte=recent_cutoff
        ).count()
        daily_stats[lang_code] = count

    context = {
        'title': 'Translation Dashboard',
        'stats': stats,
        'recent_translations': recent_translations,
        'daily_stats': daily_stats,
        'auto_translate_enabled': settings.AUTO_TRANSLATE_ENABLED,
        'auto_translate_languages': settings.AUTO_TRANSLATE_LANGUAGES,
        'priority_languages': settings.TRANSLATION_PRIORITY_LANGUAGES,
    }

    return render(request, 'admin/translation_dashboard.html', context)


def translation_stats_api(request):
    """
    API endpoint that returns current translation statistics as JSON.
    Used for real-time dashboard updates without page refresh.
    """
    from django.utils import timezone
    from datetime import timedelta

    # Get translation statistics
    stats = {}
    for lang_code, lang_name in settings.TRANSLATION_PRIORITY_LANGUAGES:
        # Normalize language code to match database format
        normalized_lang = normalize_lang_code(lang_code)

        total_trends = TrendCluster.objects.count()
        translated_trends = TrendTranslationStatus.objects.filter(
            language=normalized_lang,
            translated=True
        ).count()

        coverage_percent = (translated_trends / total_trends * 100) if total_trends > 0 else 0

        stats[lang_code] = {
            'name': lang_name,
            'translated': translated_trends,
            'total': total_trends,
            'coverage': round(coverage_percent, 1),
            'untranslated': total_trends - translated_trends,
        }

    # Get recent translations count (last 24 hours)
    recent_cutoff = timezone.now() - timedelta(hours=24)
    recent_count = TrendTranslationStatus.objects.filter(
        translated=True,
        translated_at__gte=recent_cutoff
    ).count()

    return JsonResponse({
        'status': 'success',
        'stats': stats,
        'recent_count': recent_count,
        'timestamp': timezone.now().isoformat()
    })


def bulk_translate_view(request):
    """
    Handle bulk translation requests from dashboard.
    """
    if request.method == 'POST':
        target_lang = request.POST.get('language')
        days_back = request.POST.get('days_back')

        if not target_lang:
            messages.error(request, 'Please select a target language.')
            return redirect('admin:translation_dashboard')

        try:
            days_back = int(days_back) if days_back else None
        except ValueError:
            days_back = None

        # Queue bulk translation task (fire-and-forget)
        result = bulk_translate_all_trends.apply_async((target_lang, days_back), ignore_result=True)

        lang_names = dict(settings.TRANSLATION_PRIORITY_LANGUAGES)
        lang_name = lang_names.get(target_lang, target_lang.upper())

        messages.success(
            request,
            format_html(
                '✓ Bulk translation to <strong>{}</strong> queued successfully!<br>'
                'Task ID: <code>{}</code><br>'
                'Translations will complete in background. Check back in a few minutes.',
                lang_name,
                result.id
            )
        )

        return redirect('admin:translation_dashboard')

    # GET request - show form
    return redirect('admin:translation_dashboard')


def translate_trend_view(request, trend_id):
    """
    Translate a single trend to specified language.
    Called from trend detail page or dashboard.
    """
    if request.method == 'POST':
        target_lang = request.POST.get('language')

        if not target_lang:
            messages.error(request, 'Please select a target language.')
            return redirect('admin:trends_viewer_trendcluster_change', trend_id)

        try:
            trend = TrendCluster.objects.get(id=trend_id)
        except TrendCluster.DoesNotExist:
            messages.error(request, f'Trend #{trend_id} not found.')
            return redirect('admin:trends_viewer_trendcluster_changelist')

        # Queue translation task (fire-and-forget)
        result = translate_single_trend.apply_async((trend_id, target_lang), ignore_result=True)

        lang_names = dict(settings.TRANSLATION_PRIORITY_LANGUAGES)
        lang_name = lang_names.get(target_lang, target_lang.upper())

        messages.success(
            request,
            format_html(
                '✓ Translation of <strong>{}</strong> to <strong>{}</strong> queued!<br>'
                'Task ID: <code>{}</code><br>'
                'Translation will complete in background.',
                trend.title[:50],
                lang_name,
                result.id
            )
        )

        return redirect('admin:trends_viewer_trendcluster_change', trend_id)

    # GET request - show form
    return redirect('admin:trends_viewer_trendcluster_change', trend_id)


def add_translation_actions_to_admin(admin_class):
    """
    Add translation actions to TrendClusterAdmin.
    Call this function in admin.py to extend the admin class.
    """
    # Add custom actions
    original_actions = list(admin_class.actions) if hasattr(admin_class, 'actions') else []

    def translate_selected_trends(modeladmin, request, queryset):
        """Bulk translate selected trends."""
        trend_ids = list(queryset.values_list('id', flat=True))

        # Show language selection form
        if 'apply' in request.POST:
            target_lang = request.POST.get('target_language')

            if not target_lang:
                modeladmin.message_user(
                    request,
                    'Please select a target language.',
                    messages.ERROR
                )
                return

            # Queue translation (fire-and-forget)
            result = pre_translate_trends.apply_async((trend_ids, target_lang), ignore_result=True)

            lang_names = dict(settings.TRANSLATION_PRIORITY_LANGUAGES)
            lang_name = lang_names.get(target_lang, target_lang.upper())

            modeladmin.message_user(
                request,
                format_html(
                    '✓ Translation of {} trend(s) to <strong>{}</strong> queued!<br>'
                    'Task ID: <code>{}</code>',
                    len(trend_ids),
                    lang_name,
                    result.id
                ),
                messages.SUCCESS
            )
            return

        # Show confirmation page with language selector
        context = {
            'title': 'Translate Selected Trends',
            'queryset': queryset,
            'trend_count': len(trend_ids),
            'priority_languages': settings.TRANSLATION_PRIORITY_LANGUAGES,
            'opts': modeladmin.model._meta,
        }

        return render(request, 'admin/translate_trends_confirmation.html', context)

    translate_selected_trends.short_description = '🌐 Translate selected trends'

    # Add the action
    admin_class.actions = original_actions + [translate_selected_trends]

    return admin_class
