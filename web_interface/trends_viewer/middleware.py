"""
Language Preference Middleware

Manages language persistence across sessions using:
- URL parameters (?lang=xx)
- Session storage
- Cookie storage (1 year expiration)

Priority order: URL param > Session > Cookie > Default (en)
"""

import logging

logger = logging.getLogger(__name__)


# Supported language codes
SUPPORTED_LANGUAGES = {
    'en', 'zh', 'es', 'fr', 'de', 'ja', 'ko', 'ru'
}

# Language code normalization map
LANGUAGE_NORMALIZATION = {
    'zh-cn': 'zh',
    'zh-hans': 'zh',
    'zh-hant': 'zh',
    'zh-tw': 'zh',
    'en-us': 'en',
    'en-gb': 'en',
    'es-es': 'es',
    'es-mx': 'es',
    'fr-fr': 'fr',
    'de-de': 'de',
    'ja-jp': 'ja',
    'ko-kr': 'ko',
    'ru-ru': 'ru',
}


def normalize_lang_code(lang_code):
    """
    Normalize language code to standard 2-letter format.

    Args:
        lang_code: Raw language code from URL/session/cookie

    Returns:
        Normalized 2-letter language code or 'en' if invalid
    """
    if not lang_code:
        return 'en'

    # Convert to lowercase
    lang_code = str(lang_code).lower().strip()

    # Check if it's in normalization map
    if lang_code in LANGUAGE_NORMALIZATION:
        return LANGUAGE_NORMALIZATION[lang_code]

    # Check if it's already a valid 2-letter code
    if lang_code in SUPPORTED_LANGUAGES:
        return lang_code

    # Try extracting first 2 letters
    if len(lang_code) >= 2:
        short_code = lang_code[:2]
        if short_code in SUPPORTED_LANGUAGES:
            return short_code

    # Default to English
    logger.warning(f"Unsupported language code: {lang_code}, defaulting to 'en'")
    return 'en'


class LanguagePreferenceMiddleware:
    """
    Middleware to handle language preference persistence.

    Features:
    - Reads language from URL parameter (?lang=xx)
    - Falls back to session, then cookie, then default (en)
    - Saves preference to both session and cookie
    - Sets request.LANGUAGE_CODE for easy access in views
    - Cookie expires after 1 year

    Example:
        User visits: /?lang=zh
        -> Middleware saves 'zh' to session and cookie
        -> Sets request.LANGUAGE_CODE = 'zh'

        User visits: / (no lang param)
        -> Middleware reads from session or cookie
        -> Sets request.LANGUAGE_CODE accordingly
    """

    def __init__(self, get_response):
        """
        Initialize middleware.

        Args:
            get_response: Django get_response callable
        """
        self.get_response = get_response
        logger.info("LanguagePreferenceMiddleware initialized")

    def __call__(self, request):
        """
        Process request and set language preference.

        Priority order:
        1. URL parameter (?lang=xx)
        2. Session variable
        3. Cookie
        4. Default ('en')

        Args:
            request: Django HttpRequest

        Returns:
            Django HttpResponse
        """
        # Step 1: Check URL parameter (highest priority)
        lang_from_url = request.GET.get('lang')

        # Step 2: Check session
        lang_from_session = request.session.get('language')

        # Step 3: Check cookie
        lang_from_cookie = request.COOKIES.get('language')

        # Step 4: Determine language (priority order)
        if lang_from_url:
            raw_lang = lang_from_url
            source = 'URL'
        elif lang_from_session:
            raw_lang = lang_from_session
            source = 'session'
        elif lang_from_cookie:
            raw_lang = lang_from_cookie
            source = 'cookie'
        else:
            raw_lang = 'en'
            source = 'default'

        # Normalize language code
        normalized_lang = normalize_lang_code(raw_lang)

        # Save to session
        request.session['language'] = normalized_lang

        # Set request attribute for easy access in views
        request.LANGUAGE_CODE = normalized_lang

        logger.debug(
            f"Language preference: {normalized_lang} "
            f"(source: {source}, raw: {raw_lang})"
        )

        # Process request
        response = self.get_response(request)

        # Set cookie for long-term persistence (1 year)
        if normalized_lang != response.cookies.get('language'):
            response.set_cookie(
                'language',
                normalized_lang,
                max_age=31536000,  # 1 year in seconds
                httponly=False,  # Allow JavaScript access if needed
                samesite='Lax'  # CSRF protection
            )

        return response
