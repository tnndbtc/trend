"""
Context Processors for Templates

Provides global template variables for all views, including:
- Menu translations based on current language
- Current language code
- Translation provider preference
- Category translation function
"""

from .translations import MENU_TRANSLATIONS, translate_category


def menu_translations(request):
    """
    Context processor to add menu translations to all templates.

    Makes menu translations available in templates via the 'menu' variable.

    Args:
        request: Django HttpRequest

    Returns:
        Dictionary with menu translations and current language

    Example:
        In template:
        {{ menu.dashboard }}  -> "Dashboard" (en) or "仪表板" (zh)
        {{ current_lang }}    -> "en" or "zh"
    """
    # Get current language from request
    # The middleware sets request.LANGUAGE_CODE
    current_lang = getattr(request, 'LANGUAGE_CODE', 'en')

    # Fallback to session if attribute not set
    if not current_lang:
        current_lang = request.session.get('language', 'en')

    # Get translations for current language
    translations = MENU_TRANSLATIONS.get(current_lang, MENU_TRANSLATIONS['en'])

    return {
        'menu': translations,
        'current_lang': current_lang,
        'translate_category': translate_category,
    }


def translation_settings(request):
    """
    Context processor to add translation settings to all templates.

    Provides translation provider preference from session.

    Args:
        request: Django HttpRequest

    Returns:
        Dictionary with translation settings

    Example:
        In template:
        {{ translation_provider }}  -> "free" or "ai"
        {{ is_ai_translation }}     -> True/False
    """
    provider = request.session.get('translation_provider', 'free')

    return {
        'translation_provider': provider,
        'is_ai_translation': provider == 'ai',
        'is_free_translation': provider == 'free',
    }
