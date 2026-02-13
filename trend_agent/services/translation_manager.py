"""
Translation Manager with provider selection, fallback, and caching.

Provides intelligent translation routing with multiple providers,
automatic fallback, and Redis-based + database caching to minimize costs.
"""

import hashlib
import logging
from typing import Dict, List, Optional
from asgiref.sync import sync_to_async

from trend_agent.intelligence.interfaces import TranslationError
from trend_agent.observability.metrics import api_request_counter
from trend_agent.storage.interfaces import CacheRepository

logger = logging.getLogger(__name__)


def get_db_translation(source_text_hash: str, source_lang: Optional[str], target_lang: str) -> Optional[str]:
    """
    Get translation from database cache.

    This function is designed to work both inside and outside Django context.
    Returns None if Django is not available or translation not found.

    Args:
        source_text_hash: MD5 hash of source text
        source_lang: Source language code
        target_lang: Target language code

    Returns:
        Cached translation or None
    """
    try:
        # Import Django models (will fail if Django not configured)
        try:
            from web_interface.trends_viewer.models import TranslatedContent
        except ImportError:
            # Try alternate import path (when running inside web container)
            from trends_viewer.models import TranslatedContent

        # Query database
        cached = TranslatedContent.objects.filter(
            source_text_hash=source_text_hash,
            source_language=source_lang or 'auto',
            target_language=target_lang
        ).first()

        if cached:
            logger.info(
                f"[DB CACHE] ✓ HIT - Found translation in database "
                f"(hash: {source_text_hash[:8]}..., {source_lang or 'auto'} -> {target_lang}, provider: {cached.provider})"
            )
            return cached.translated_text

        logger.debug(
            f"[DB CACHE] ✗ MISS - Translation not in database "
            f"(hash: {source_text_hash[:8]}..., {source_lang or 'auto'} -> {target_lang})"
        )
        return None

    except ImportError:
        # Django not available - skip database cache
        logger.debug("Database cache not available (Django not configured)")
        return None
    except Exception as e:
        logger.warning(f"Database cache lookup failed: {e}")
        return None


def save_db_translation(
    source_text: str,
    source_text_hash: str,
    translation: str,
    source_lang: Optional[str],
    target_lang: str,
    provider: str = 'libretranslate'
) -> bool:
    """
    Save translation to database cache.

    This function is designed to work both inside and outside Django context.
    Returns False if Django is not available or save fails.

    Args:
        source_text: Original text (for logging)
        source_text_hash: MD5 hash of source text
        translation: Translated text
        source_lang: Source language code
        target_lang: Target language code
        provider: Provider name

    Returns:
        True if saved successfully
    """
    try:
        # Import Django models (will fail if Django not configured)
        try:
            from web_interface.trends_viewer.models import TranslatedContent
        except ImportError:
            # Try alternate import path (when running inside web container)
            from trends_viewer.models import TranslatedContent

        # Create or update translation record
        obj, created = TranslatedContent.objects.update_or_create(
            source_text_hash=source_text_hash,
            source_language=source_lang or 'auto',
            target_language=target_lang,
            defaults={
                'translated_text': translation,
                'provider': provider,
            }
        )

        action = "CREATED" if created else "UPDATED"
        logger.info(
            f"[DB CACHE] ✓ {action} - Saved translation to database "
            f"(hash: {source_text_hash[:8]}..., {source_lang or 'auto'} -> {target_lang}, provider: {provider})"
        )
        return True

    except ImportError:
        # Django not available - skip database cache
        logger.debug("Database cache not available (Django not configured)")
        return False
    except Exception as e:
        logger.warning(f"Database cache save failed: {e}")
        return False


class TranslationCache:
    """
    Redis-based translation cache.

    Caches translations to avoid redundant API calls and reduce costs.
    Uses a hash of (text + source_lang + target_lang) as cache key.

    Features:
    - Automatic cache key generation
    - Configurable TTL
    - Batch caching support
    - Cache hit/miss tracking

    Example:
        ```python
        cache = TranslationCache(redis_repo, ttl_seconds=604800)  # 7 days

        # Check cache
        cached = await cache.get("Hello", source_lang="en", target_lang="es")
        if cached:
            return cached

        # Translate and cache
        translated = await translate_service.translate("Hello", "es")
        await cache.set("Hello", translated, source_lang="en", target_lang="es")
        ```
    """

    def __init__(
        self,
        cache_repo: CacheRepository,
        ttl_seconds: int = 604800,  # 7 days default
        key_prefix: str = "translation",
    ):
        """
        Initialize translation cache.

        Args:
            cache_repo: Redis cache repository
            ttl_seconds: Cache TTL in seconds (default: 7 days)
            key_prefix: Prefix for cache keys
        """
        self.cache_repo = cache_repo
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix

        # Stats
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info(
            f"Initialized TranslationCache (ttl={ttl_seconds}s, prefix={key_prefix})"
        )

    async def get(
        self,
        text: str,
        source_lang: Optional[str],
        target_lang: str,
    ) -> Optional[str]:
        """
        Get cached translation.

        Lookup order:
        1. Redis cache (fast, in-memory)
        2. Database cache (persistent, slower)
        3. None (will trigger API call)

        Args:
            text: Original text
            source_lang: Source language code (None for auto-detect)
            target_lang: Target language code

        Returns:
            Cached translation if found, None otherwise
        """
        if not text or not text.strip():
            return None

        cache_key = self._generate_cache_key(text, source_lang, target_lang)

        # Step 1: Check Redis cache (fast)
        try:
            cached = await self.cache_repo.get(cache_key)

            if cached:
                self._cache_hits += 1
                logger.debug(f"[REDIS CACHE] HIT: {cache_key[:50]}...")
                return cached

        except Exception as e:
            logger.warning(f"Redis cache get failed: {e}")

        # Step 2: Check Database cache (persistent)
        # Generate MD5 hash for database lookup
        source = source_lang or "auto"
        hash_input = f"{text}|{source}|{target_lang}".encode("utf-8")
        text_hash = hashlib.md5(hash_input).hexdigest()

        db_cached = get_db_translation(text_hash, source_lang, target_lang)
        if db_cached:
            self._cache_hits += 1
            # Populate Redis cache for faster future lookups
            try:
                await self.cache_repo.set(cache_key, db_cached, ttl_seconds=self.ttl_seconds)
                logger.debug(f"[REDIS CACHE] Populated from database: {cache_key[:50]}...")
            except Exception as e:
                logger.warning(f"Failed to populate Redis from database: {e}")
            return db_cached

        # Step 3: Not found in either cache
        self._cache_misses += 1
        logger.debug(f"Cache MISS (Redis + DB): {cache_key[:50]}...")
        return None

    async def set(
        self,
        text: str,
        translation: str,
        source_lang: Optional[str],
        target_lang: str,
        provider: str = 'libretranslate',
    ) -> bool:
        """
        Cache a translation.

        Saves to both Redis (fast, temporary) and Database (persistent).

        Args:
            text: Original text
            translation: Translated text
            source_lang: Source language code
            target_lang: Target language code
            provider: Translation provider used

        Returns:
            True if cached successfully to at least one cache
        """
        if not text or not translation:
            return False

        cache_key = self._generate_cache_key(text, source_lang, target_lang)
        success = False

        # Save to Redis cache (fast, temporary)
        try:
            await self.cache_repo.set(cache_key, translation, ttl_seconds=self.ttl_seconds)
            logger.debug(f"[REDIS CACHE] Saved: {cache_key[:50]}...")
            success = True
        except Exception as e:
            logger.warning(f"Redis cache set failed: {e}")

        # Save to Database cache (persistent)
        source = source_lang or "auto"
        hash_input = f"{text}|{source}|{target_lang}".encode("utf-8")
        text_hash = hashlib.md5(hash_input).hexdigest()

        # Wrap sync function in async context
        db_success = await sync_to_async(save_db_translation)(
            source_text=text,
            source_text_hash=text_hash,
            translation=translation,
            source_lang=source_lang,
            target_lang=target_lang,
            provider=provider
        )

        if db_success:
            success = True

        return success

    async def get_batch(
        self,
        texts: List[str],
        source_lang: Optional[str],
        target_lang: str,
    ) -> Dict[str, str]:
        """
        Get cached translations for multiple texts.

        Args:
            texts: List of texts to look up
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Dictionary mapping text to cached translation
        """
        cached_translations = {}

        for text in texts:
            cached = await self.get(text, source_lang, target_lang)
            if cached:
                cached_translations[text] = cached

        return cached_translations

    async def set_batch(
        self,
        translations: Dict[str, str],
        source_lang: Optional[str],
        target_lang: str,
        provider: str = 'libretranslate',
    ) -> int:
        """
        Cache multiple translations.

        Args:
            translations: Dictionary mapping original text to translation
            source_lang: Source language code
            target_lang: Target language code
            provider: Translation provider used

        Returns:
            Number of translations successfully cached
        """
        cached_count = 0

        for text, translation in translations.items():
            if await self.set(text, translation, source_lang, target_lang, provider):
                cached_count += 1

        return cached_count

    def _generate_cache_key(
        self,
        text: str,
        source_lang: Optional[str],
        target_lang: str,
    ) -> str:
        """
        Generate cache key for translation.

        Uses MD5 hash of (text + source_lang + target_lang) to create
        a compact, deterministic cache key.

        Args:
            text: Text to translate
            source_lang: Source language (or "auto")
            target_lang: Target language

        Returns:
            Cache key string
        """
        source = source_lang or "auto"
        # Create hash of text + languages
        hash_input = f"{text}|{source}|{target_lang}".encode("utf-8")
        text_hash = hashlib.md5(hash_input).hexdigest()

        return f"{self.key_prefix}:{source}:{target_lang}:{text_hash}"

    def get_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit/miss counts and hit rate
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }

    async def clear(self) -> bool:
        """Clear all cached translations."""
        try:
            # Note: This clears the entire cache, not just translation keys
            await self.cache_repo.flush()
            logger.info("Translation cache cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False


class TranslationManager:
    """
    Translation manager with provider selection and fallback.

    Manages multiple translation providers with intelligent routing,
    automatic fallback, and caching to minimize costs and maximize reliability.

    Features:
    - Multiple provider support (OpenAI, LibreTranslate, DeepL)
    - Automatic fallback on failure
    - Redis-based caching
    - Provider selection by priority or rules
    - Cost tracking across providers
    - Prometheus metrics

    Provider Selection Strategy:
    1. Check cache first
    2. Try primary provider
    3. On failure, try fallback providers in order
    4. Cache successful translations

    Example:
        ```python
        manager = TranslationManager(
            providers={
                "libretranslate": libretranslate_service,
                "openai": openai_service,
                "deepl": deepl_service,
            },
            cache=translation_cache,
            provider_priority=["libretranslate", "openai", "deepl"]
        )

        # Translate with automatic fallback
        translated = await manager.translate("Hello", target_language="es")

        # Get stats
        stats = manager.get_stats()
        print(f"Cache hit rate: {stats['cache_hit_rate']}%")
        print(f"Provider usage: {stats['provider_usage']}")
        ```
    """

    def __init__(
        self,
        providers: Dict[str, any],  # Dict[str, TranslationService]
        cache: Optional[TranslationCache] = None,
        provider_priority: Optional[List[str]] = None,
        enable_fallback: bool = True,
    ):
        """
        Initialize translation manager.

        Args:
            providers: Dictionary of provider_name -> TranslationService
            cache: Optional TranslationCache instance
            provider_priority: List of provider names in priority order
            enable_fallback: Enable automatic fallback to next provider
        """
        if not providers:
            raise ValueError("At least one translation provider required")

        self.providers = providers
        self.cache = cache
        self.enable_fallback = enable_fallback

        # Set provider priority
        if provider_priority:
            # Validate all providers in priority list exist
            invalid = set(provider_priority) - set(providers.keys())
            if invalid:
                raise ValueError(f"Unknown providers in priority: {invalid}")
            self.provider_priority = provider_priority
        else:
            # Default priority: libretranslate (free) -> openai -> deepl
            self.provider_priority = list(providers.keys())

        # Stats
        self._provider_usage = {name: 0 for name in providers.keys()}
        self._provider_failures = {name: 0 for name in providers.keys()}
        self._total_translations = 0
        self._cache_hits = 0

        logger.info(
            f"Initialized TranslationManager with {len(providers)} providers "
            f"(priority={self.provider_priority}, fallback={enable_fallback})"
        )

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None,
    ) -> str:
        """
        Translate text with automatic provider selection and fallback.

        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (auto-detect if None)
            preferred_provider: Preferred provider name (uses priority if None)

        Returns:
            Translated text

        Raises:
            TranslationError: If all providers fail
        """
        if not text or not text.strip():
            return text

        # Check cache first
        if self.cache:
            cached = await self.cache.get(text, source_language, target_language)
            if cached:
                self._cache_hits += 1
                self._total_translations += 1

                # Record cache hit metric
                api_request_counter.labels(
                    method="GET", endpoint="translation_cache", status_code=200
                ).inc()

                logger.info(
                    f"[TRANSLATION] ⚡ CACHE HIT - No API call needed "
                    f"(text: '{text[:50]}{'...' if len(text) > 50 else ''}', {source_language or 'auto'} -> {target_language})"
                )
                return cached

        # Determine provider order
        if preferred_provider and preferred_provider in self.providers:
            provider_order = [preferred_provider]
            if self.enable_fallback:
                # Add other providers as fallback
                provider_order.extend(
                    [p for p in self.provider_priority if p != preferred_provider]
                )
        else:
            provider_order = self.provider_priority.copy()

        # Try each provider in order
        last_error = None
        for provider_name in provider_order:
            provider = self.providers[provider_name]

            try:
                logger.info(
                    f"[TRANSLATION] Attempting with provider: {provider_name.upper()} "
                    f"(text: '{text[:50]}{'...' if len(text) > 50 else ''}', {source_language or 'auto'} -> {target_language})"
                )

                translation = await provider.translate(
                    text, target_language, source_language
                )

                # Update stats
                self._provider_usage[provider_name] += 1
                self._total_translations += 1

                # Cache the result (with provider info for database)
                if self.cache:
                    await self.cache.set(text, translation, source_language, target_language, provider_name)

                logger.info(
                    f"[TRANSLATION] ✓ SUCCESS with {provider_name.upper()} "
                    f"(length: {len(text)} chars -> {len(translation)} chars)"
                )

                return translation

            except TranslationError as e:
                last_error = e
                self._provider_failures[provider_name] += 1

                logger.warning(
                    f"Translation failed with {provider_name}: {e}"
                )

                # If fallback disabled, raise immediately
                if not self.enable_fallback:
                    raise

                # Continue to next provider
                continue

            except Exception as e:
                last_error = e
                self._provider_failures[provider_name] += 1

                logger.error(
                    f"Unexpected error with {provider_name}: {e}"
                )

                # Continue to next provider
                continue

        # All providers failed
        error_msg = f"All translation providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise TranslationError(error_msg)

    async def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None,
    ) -> List[str]:
        """
        Translate multiple texts with caching and batching.

        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language code
            preferred_provider: Preferred provider

        Returns:
            List of translated texts in the same order

        Raises:
            TranslationError: If translation fails
        """
        if not texts:
            return []

        # Filter empty texts
        valid_indices = [i for i, t in enumerate(texts) if t and t.strip()]
        valid_texts = [texts[i] for i in valid_indices]

        if not valid_texts:
            return texts

        # Check cache for all texts
        translations_map = {}
        texts_to_translate = []

        if self.cache:
            cached_translations = await self.cache.get_batch(
                valid_texts, source_language, target_language
            )

            for text in valid_texts:
                if text in cached_translations:
                    translations_map[text] = cached_translations[text]
                    self._cache_hits += 1
                else:
                    texts_to_translate.append(text)
        else:
            texts_to_translate = valid_texts

        # Translate uncached texts
        if texts_to_translate:
            # Use primary provider for batch translation
            provider_name = (
                preferred_provider
                if preferred_provider in self.providers
                else self.provider_priority[0]
            )
            provider = self.providers[provider_name]

            logger.info(
                f"[TRANSLATION] Batch translating {len(texts_to_translate)} texts "
                f"with {provider_name.upper()} "
                f"({len(valid_texts) - len(texts_to_translate)} from cache, {source_language or 'auto'} -> {target_language})"
            )

            try:
                batch_translations = await provider.translate_batch(
                    texts_to_translate, target_language, source_language
                )

                # Map translations
                for text, translation in zip(texts_to_translate, batch_translations):
                    translations_map[text] = translation

                # Update stats
                self._provider_usage[provider_name] += len(texts_to_translate)
                self._total_translations += len(texts_to_translate)

                # Cache new translations (with provider info for database)
                if self.cache:
                    new_translations = dict(zip(texts_to_translate, batch_translations))
                    await self.cache.set_batch(
                        new_translations, source_language, target_language, provider_name
                    )

            except Exception as e:
                logger.error(f"Batch translation failed: {e}")
                raise TranslationError(f"Batch translation failed: {e}") from e

        # Reconstruct result in original order
        result = []
        for i, text in enumerate(texts):
            if i in valid_indices:
                result.append(translations_map.get(text, text))
            else:
                result.append(text)  # Empty text stays empty

        return result

    async def detect_language(self, text: str) -> str:
        """
        Detect language using available providers.

        Tries providers in priority order until successful detection.

        Args:
            text: Text to analyze

        Returns:
            ISO 639-1 language code or "unknown"
        """
        if not text or not text.strip():
            return "unknown"

        for provider_name in self.provider_priority:
            provider = self.providers[provider_name]

            try:
                lang = await provider.detect_language(text)
                if lang and lang != "unknown":
                    logger.debug(f"Detected language '{lang}' with {provider_name}")
                    return lang

            except Exception as e:
                logger.warning(f"Language detection failed with {provider_name}: {e}")
                continue

        logger.warning(f"Could not detect language for: {text[:50]}...")
        return "unknown"

    def get_supported_languages(self) -> List[str]:
        """
        Get union of supported languages across all providers.

        Returns:
            List of ISO 639-1 language codes
        """
        all_languages = set()

        for provider in self.providers.values():
            langs = provider.get_supported_languages()
            all_languages.update(langs)

        return sorted(all_languages)

    def get_stats(self) -> Dict:
        """
        Get comprehensive usage statistics.

        Returns:
            Dictionary with usage stats for all providers and cache
        """
        total_attempts = sum(self._provider_usage.values())
        total_failures = sum(self._provider_failures.values())

        cache_stats = self.cache.get_stats() if self.cache else {}

        return {
            "total_translations": self._total_translations,
            "cache_hits": self._cache_hits,
            "cache_enabled": self.cache is not None,
            "cache_stats": cache_stats,
            "provider_usage": self._provider_usage.copy(),
            "provider_failures": self._provider_failures.copy(),
            "total_api_calls": total_attempts,
            "total_failures": total_failures,
            "success_rate": (
                (total_attempts - total_failures) / total_attempts * 100
                if total_attempts > 0
                else 0
            ),
            "fallback_enabled": self.enable_fallback,
        }

    async def close(self):
        """Close all providers."""
        for name, provider in self.providers.items():
            try:
                if hasattr(provider, "close"):
                    await provider.close()
                logger.debug(f"Closed translation provider: {name}")
            except Exception as e:
                logger.warning(f"Error closing provider {name}: {e}")

        logger.info(
            f"Closed TranslationManager "
            f"(total_translations={self._total_translations})"
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
